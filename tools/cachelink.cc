#include "cachelink.h"
#include "rocksdb/utilities/options_type.h"

#include "folly/init/Init.h"
#include "folly/synchronization/Rcu.h"
#include "rocksdb/version.h"

#include <sstream>



namespace facebook::rocks_secondary_cache {

#define FB_CACHE_MAX_ITEM_SIZE 4 << 20

// ---------------------------------------------------------------------------
// InsertSaved guard macro — only exists in RocksDB >= 8.7
// ---------------------------------------------------------------------------
#if ROCKSDB_MAJOR > 8 || (ROCKSDB_MAJOR == 8 && ROCKSDB_MINOR >= 7)
#define DEFINE_INSERT_SAVED                                                    \
  rocksdb::Status InsertSaved(const rocksdb::Slice&, const rocksdb::Slice&,   \
                              rocksdb::CompressionType,                        \
                              rocksdb::CacheTier) override {                   \
    return rocksdb::Status::NotSupported();                                    \
  }
#define CALL_CREATE_CB(helper, slice, ctx, val, charge)                        \
  (helper)->create_cb((slice),                                                 \
                      rocksdb::CompressionType::kNoCompression,                \
                      rocksdb::CacheTier::kVolatileTier,                       \
                      (ctx), nullptr, (val), (charge))
#else
#define DEFINE_INSERT_SAVED
#define CALL_CREATE_CB(helper, slice, ctx, val, charge)                        \
  (helper)->create_cb((slice), (ctx), nullptr, (val), (charge))
#endif

// ============================================================================
// Anonymous namespace — RCU domain, result handles, shared NVM config helper
// ============================================================================
namespace {

folly::rcu_domain& GetRcuDomain() {
  static folly::rcu_domain domain;
  return domain;
}

// ---------------------------------------------------------------------------
// Async result handle — used by the LRU path.
// FbCacheReadHandle resolves via a SemiFuture so lookups can be async.
// ---------------------------------------------------------------------------
class RocksCachelibWrapperHandle : public rocksdb::SecondaryCacheResultHandle {
 public:
  RocksCachelibWrapperHandle(folly::SemiFuture<FbCacheReadHandle>&& future,
                             const rocksdb::Cache::CacheItemHelper* helper,
                             rocksdb::Cache::CreateContext* create_context,
                             std::unique_lock<folly::rcu_domain>&& guard)
      : future_(std::move(future)),
        helper_(helper),
        create_context_(create_context),
        val_(nullptr),
        charge_(0),
        is_value_ready_(false),
        guard_(std::move(guard)) {}

  ~RocksCachelibWrapperHandle() override = default;
  RocksCachelibWrapperHandle(const RocksCachelibWrapperHandle&) = delete;
  RocksCachelibWrapperHandle& operator=(
      const RocksCachelibWrapperHandle&) = delete;

  bool IsReady() override {
    if (!is_value_ready_) {
      if (future_.isReady()) {
        handle_ = std::move(future_).value();
        CalcValue();
      }
    }
    return is_value_ready_;
  }

  void Wait() override {
    if (!is_value_ready_) {
      future_.wait();
      handle_ = std::move(future_).value();
      CalcValue();
    }
  }

  static void WaitAll(
      std::vector<rocksdb::SecondaryCacheResultHandle*> handles) {
    std::vector<folly::SemiFuture<FbCacheReadHandle>> h_semi;
    for (auto* h_ptr : handles) {
      auto* hdl = static_cast<RocksCachelibWrapperHandle*>(h_ptr);
      if (!hdl->is_value_ready_) {
        h_semi.emplace_back(std::move(hdl->future_));
      }
    }
    auto new_handles = folly::collectAll(std::move(h_semi)).get();
    int idx = 0;
    for (auto* h_ptr : handles) {
      auto* hdl = static_cast<RocksCachelibWrapperHandle*>(h_ptr);
      if (!hdl->is_value_ready_) {
        hdl->handle_ = std::move(new_handles[idx++]).value();
        hdl->CalcValue();
      }
    }
  }

  void* Value() override { return val_; }
  size_t Size() override { return charge_; }

 private:
  FbCacheReadHandle handle_;
  folly::SemiFuture<FbCacheReadHandle> future_;
  const rocksdb::Cache::CacheItemHelper* const helper_;
  rocksdb::Cache::CreateContext* const create_context_;
  void* val_;
  size_t charge_;
  bool is_value_ready_;
  std::unique_lock<folly::rcu_domain> guard_;

  void CalcValue() {
    is_value_ready_ = true;
    if (handle_) {
      uint32_t size = handle_->getSize();
      const char* item = static_cast<const char*>(handle_->getMemory());
      auto s = CALL_CREATE_CB(helper_,
                              rocksdb::Slice(item, size),
                              create_context_,
                              &val_,
                              &charge_);
      if (!s.ok()) val_ = nullptr;
      handle_.reset();
    }
  }
};

// ---------------------------------------------------------------------------
// Synchronous result handle — used by Lru2Q and TinyLFU paths.
// Those allocators' ReadHandle types differ from FbCacheReadHandle so we
// resolve the lookup synchronously and return an already-complete handle.
// ---------------------------------------------------------------------------
class SyncSecondaryCacheHandle : public rocksdb::SecondaryCacheResultHandle {
 public:
  SyncSecondaryCacheHandle(void* val, size_t charge)
      : val_(val), charge_(charge) {}
  bool IsReady() override { return true; }
  void Wait() override {}
  void* Value() override { return val_; }
  size_t Size() override { return charge_; }
 private:
  void* val_;
  size_t charge_;
};

// ---------------------------------------------------------------------------
// ApplyNvmOptions — shared NVM config builder used by all three allocators
// ---------------------------------------------------------------------------
template <typename NvmConfig>
void ApplyNvmOptions(const RocksCachelibOptions& opts, NvmConfig& nvmConfig) {
  nvmConfig.navyConfig.setBlockSize(opts.blockSize);
  nvmConfig.navyConfig.setSimpleFile(opts.fileName, opts.size,
                                     /*truncateFile=*/true);
  nvmConfig.navyConfig.blockCache().setRegionSize(opts.regionSize);
  if (opts.admPolicy == "random") {
    nvmConfig.navyConfig.enableRandomAdmPolicy()
        .setAdmProbability(opts.admProbability);
  } else {
    // dynamic_random
    nvmConfig.navyConfig.enableDynamicRandomAdmPolicy()
        .setMaxWriteRate(opts.maxWriteRate)
        .setAdmWriteRate(opts.admissionWriteRate);
  }
}

} // namespace

// ============================================================================
// RocksCachelibWrapper (LRU) — original methods, unchanged from your .cc
// ============================================================================

RocksCachelibWrapper::~RocksCachelibWrapper() { Close(); }

void RocksCachelibWrapper::Close() {
  FbCache* cache = cache_.load();
  if (cache) {
    cache_.store(nullptr);
    GetRcuDomain().synchronize();
    delete cache;
  }
}

rocksdb::Status RocksCachelibWrapper::Insert(
    const rocksdb::Slice& key,
    void* value,
    const rocksdb::Cache::CacheItemHelper* helper,
    bool /*force_erase*/) {
  FbCacheKey k(key.data(), key.size());
  rocksdb::Status s;
  std::scoped_lock guard(GetRcuDomain());
  FbCache* cache = cache_.load();
  if (cache) {
    size_t size = (*helper->size_cb)(value);
    if (FbCacheItem::getRequiredSize(k, size) <= FB_CACHE_MAX_ITEM_SIZE) {
      auto handle = cache->allocate(pool_, k, size);
      if (handle) {
        char* buf = static_cast<char*>(handle->getMemory());
        s = (*helper->saveto_cb)(value, /*offset=*/0, size, buf);
        try {
          cache->insertOrReplace(handle);
        } catch (const std::exception& ex) {
          s = rocksdb::Status::Aborted(folly::sformat(
              "Cachelib insertOrReplace exception, error:{}", ex.what()));
        }
      }
    } else {
      s = rocksdb::Status::InvalidArgument();
    }
  }
  return s;
}

std::unique_ptr<rocksdb::SecondaryCacheResultHandle>
RocksCachelibWrapper::Lookup(const rocksdb::Slice& key,
                             const rocksdb::Cache::CacheItemHelper* helper,
                             rocksdb::Cache::CreateContext* create_context,
                             bool wait,
                             bool /*advise_erase*/,
                             rocksdb::Statistics* /*stats*/,
                             bool& is_in_sec_cache) {
  std::unique_lock guard(GetRcuDomain());
  FbCache* cache = cache_.load();
  std::unique_ptr<rocksdb::SecondaryCacheResultHandle> hdl;
  if (cache) {
    auto handle = cache->find(FbCacheKey(key.data(), key.size()));
    hdl = std::make_unique<RocksCachelibWrapperHandle>(
        std::move(handle).toSemiFuture(),
        helper,
        create_context,
        std::move(guard));
    if (hdl->IsReady() || wait) {
      if (!hdl->IsReady()) hdl->Wait();
      if (hdl->Value() == nullptr) hdl.reset();
    }
  }
  is_in_sec_cache = hdl != nullptr;
  return hdl;
}

void RocksCachelibWrapper::Erase(const rocksdb::Slice& key) {
  std::scoped_lock guard(GetRcuDomain());
  FbCache* cache = cache_.load();
  if (cache) {
    cache->remove(FbCacheKey(key.data(), key.size()));
  }
}

void RocksCachelibWrapper::WaitAll(
    std::vector<rocksdb::SecondaryCacheResultHandle*> handles) {
  RocksCachelibWrapperHandle::WaitAll(handles);
}

std::string RocksCachelibWrapper::GetPrintableOptions() const {
  std::ostringstream ss;
  ss << "eviction=" << EvictionPolicyToString(eviction_)
     << ";pool="    << static_cast<int>(pool_);
  return ss.str();
}

// ============================================================================
// OptionsFromString
// ============================================================================
static void PrintOptions(const RocksCachelibOptions& o) {
  printf("\n===== RocksCachelibWrapper Options =====\n");

  printf("cacheName           = %s\n", o.cacheName.c_str());
  printf("fileName            = %s\n", o.fileName.c_str());
  printf("size                = %zu\n", o.size);
  printf("blockSize           = %zu\n", o.blockSize);
  printf("regionSize          = %zu\n", o.regionSize);

  printf("evictionPolicy      = %s\n",
         EvictionPolicyToString(o.evictionPolicy).c_str());

  printf("admPolicy           = %s\n", o.admPolicy.c_str());
  printf("admProbability      = %.4f\n", o.admProbability);

  printf("maxWriteRate        = %lu\n", o.maxWriteRate);
  printf("admissionWriteRate  = %lu\n", o.admissionWriteRate);

  printf("volatileSize        = %zu\n", o.volatileSize);
  printf("bktPower            = %u\n", o.bktPower);
  printf("lockPower           = %u\n", o.lockPower);

  printf("fb303Stats          = %s\n", o.fb303Stats ? "true" : "false");
  printf("oncallName          = %s\n", o.oncallName.c_str());

  printf("========================================\n\n");
}

rocksdb::Status RocksCachelibWrapper::OptionsFromString(
    const std::string& uri, RocksCachelibOptions* opts) {

  fprintf(stderr, "\n========== OptionsFromString DEBUG ==========\n");
  fprintf(stderr, "RAW URI: [%s]\n", uri.c_str());

  std::istringstream ss(uri);
  std::string token;

  // 🔥 FIRST TOKEN = NAME → MUST SKIP
  if (std::getline(ss, token, ',')) {
    fprintf(stderr, "[DEBUG] Skip cache name: [%s]\n", token.c_str());
  }

  int token_id = 0;

  // Now parse ONLY key=value pairs
  while (std::getline(ss, token, ',')) {
    fprintf(stderr, "\n[TOKEN %d] RAW: [%s]\n", token_id++, token.c_str());

    auto eq = token.find('=');
    if (eq == std::string::npos) {
      fprintf(stderr, "  -> SKIP (no '=')\n");
      continue;
    }

    std::string k = token.substr(0, eq);
    std::string v = token.substr(eq + 1);

    auto trim = [](std::string& s) {
      s.erase(0, s.find_first_not_of(" \t"));
      s.erase(s.find_last_not_of(" \t") + 1);
    };

    trim(k);
    trim(v);

    fprintf(stderr, "  -> PARSED key=[%s], value=[%s]\n",
            k.c_str(), v.c_str());

    try {

      if (k == "id") {
        fprintf(stderr, "  -> id detected: %s (handled by registry)\n", v.c_str());
      }

      else if (k == "size") {
        opts->size = std::stoull(v);
        fprintf(stderr, "  -> size set to %zu\n", opts->size);
      }

      else if (k == "eviction") {
        auto s = EvictionPolicyFromString(v, &opts->evictionPolicy);
        if (!s.ok()) {
          fprintf(stderr, "  -> ERROR: invalid eviction policy\n");
          return s;
        }
        fprintf(stderr, "  -> eviction set to %s\n",
                EvictionPolicyToString(opts->evictionPolicy).c_str());
      }

      else if (k == "adm_policy") {
        if (v != "random" && v != "dynamic_random") {
          fprintf(stderr, "  -> ERROR: invalid adm_policy: %s\n", v.c_str());
          return rocksdb::Status::InvalidArgument(
              "adm_policy must be 'random' or 'dynamic_random', got: " + v);
        }
        opts->admPolicy = v;
        fprintf(stderr, "  -> admPolicy set to %s\n", opts->admPolicy.c_str());
      }

      else if (k == "adm_prob") {
        opts->admProbability = std::stod(v);
        fprintf(stderr, "  -> admProbability set to %.4f\n", opts->admProbability);
      }

      else if (k == "max_write_rate") {
        opts->maxWriteRate = std::stoull(v);
        fprintf(stderr, "  -> maxWriteRate set to %lu\n", opts->maxWriteRate);
      }

      else if (k == "adm_write_rate") {
        opts->admissionWriteRate = std::stoull(v);
        fprintf(stderr, "  -> admissionWriteRate set to %lu\n",
                opts->admissionWriteRate);
      }

      else if (k == "volatile_size") {
        opts->volatileSize = std::stoull(v);
        fprintf(stderr, "  -> volatileSize set to %zu\n", opts->volatileSize);
      }

      else if (k == "block_size") {
        opts->blockSize = std::stoull(v);
        fprintf(stderr, "  -> blockSize set to %zu\n", opts->blockSize);
      }

      else if (k == "region_size") {
        opts->regionSize = std::stoull(v);
        fprintf(stderr, "  -> regionSize set to %zu\n", opts->regionSize);
      }

      else if (k == "file") {
        opts->fileName = v;
        fprintf(stderr, "  -> fileName set to %s\n", opts->fileName.c_str());
      }

      else if (k == "name") {
        opts->cacheName = v;
        fprintf(stderr, "  -> cacheName set to %s\n", opts->cacheName.c_str());
      }

      else {
        fprintf(stderr,
                "  -> UNKNOWN PARAM IGNORED: %s=%s\n",
                k.c_str(), v.c_str());
      }

    } catch (const std::exception& e) {
      fprintf(stderr,
              "  -> EXCEPTION while parsing key=%s value=%s\n",
              k.c_str(), v.c_str());
      fprintf(stderr, "  -> what(): %s\n", e.what());
      return rocksdb::Status::InvalidArgument(
          "Failed parsing option: " + k + "=" + v);
    }
  }

  // ==========================
  // FINAL STATE
  // ==========================
  fprintf(stderr, "\n===== FINAL PARSED OPTIONS =====\n");
  fprintf(stderr, "size                = %zu\n", opts->size);
  fprintf(stderr, "evictionPolicy      = %s\n",
          EvictionPolicyToString(opts->evictionPolicy).c_str());
  fprintf(stderr, "admPolicy           = %s\n", opts->admPolicy.c_str());
  fprintf(stderr, "admProbability      = %.4f\n", opts->admProbability);
  fprintf(stderr, "maxWriteRate        = %lu\n", opts->maxWriteRate);
  fprintf(stderr, "admissionWriteRate  = %lu\n", opts->admissionWriteRate);
  fprintf(stderr, "volatileSize        = %zu\n", opts->volatileSize);
  fprintf(stderr, "blockSize           = %zu\n", opts->blockSize);
  fprintf(stderr, "regionSize          = %zu\n", opts->regionSize);
  fprintf(stderr, "fileName            = %s\n", opts->fileName.c_str());
  fprintf(stderr, "cacheName           = %s\n", opts->cacheName.c_str());
  fprintf(stderr, "================================\n");

  // ==========================
  // VALIDATION
  // ==========================
  if (opts->size == 0) {
    fprintf(stderr, "ERROR: size is 0\n");
    return rocksdb::Status::InvalidArgument(
        "size= is required and must be > 0");
  }

  fprintf(stderr, "OptionsFromString SUCCESS\n");
  fprintf(stderr, "===========================================\n\n");

  return rocksdb::Status::OK();
}

// ============================================================================
// CreateFromString
// ============================================================================

rocksdb::Status RocksCachelibWrapper::CreateFromString(
    const rocksdb::ConfigOptions& /*config_options*/,
    const std::string& uri,
    std::shared_ptr<rocksdb::SecondaryCache>* result) {
      printf(">>> CreateFromString CALLED\n");
  RocksCachelibOptions opts;
  auto s = OptionsFromString(uri, &opts);
  if (!s.ok()) return s;

  PrintOptions(opts);

  std::unique_ptr<rocksdb::SecondaryCache> cache;
  switch (opts.evictionPolicy) {
    case EvictionPolicy::kLru:
      cache = NewRocksCachelibWrapperLru(opts);     break;
    case EvictionPolicy::kLru2Q:
      cache = NewRocksCachelibWrapperLru2Q(opts);   break;
    case EvictionPolicy::kTinyLFU:
      cache = NewRocksCachelibWrapperTinyLFU(opts); break;
  }
  if (!cache)
    return rocksdb::Status::IOError(
        "Failed to allocate CacheLink");
  *result = std::move(cache);
  return rocksdb::Status::OK();
}

// ============================================================================
// Typed subclasses for Lru2Q and TinyLFU — defined entirely in .cc
//
// Each subclass holds std::atomic<AllocatorType*> so the type matches exactly.
// Insert/Lookup/Erase/WaitAll/Close logic is identical across all three
// policies so we use a macro to stamp it out without copy-paste.
// The LRU path uses the original RocksCachelibWrapper class directly.
// ============================================================================

#define DEFINE_TYPED_WRAPPER(ClassName, AllocatorType, PolicyStr)              \
                                                                               \
class ClassName : public rocksdb::SecondaryCache {                             \
 public:                                                                       \
  ClassName(std::unique_ptr<AllocatorType>&& cache, cachelib::PoolId pool)    \
      : cache_(std::move(cache).release()), pool_(pool) {}                     \
                                                                               \
  ~ClassName() override { Close(); }                                           \
                                                                               \
  const char* Name() const override {                                          \
    return RocksCachelibWrapper::kClassName();                                 \
  }                                                                            \
                                                                               \
  bool SupportForceErase() const override { return false; }                   \
                                                                               \
  std::string GetPrintableOptions() const override {                           \
    return "eviction=" PolicyStr;                                              \
  }                                                                            \
                                                                               \
  DEFINE_INSERT_SAVED                                                          \
                                                                               \
  void Close() {                                                               \
    AllocatorType* cache = cache_.load();                                      \
    if (cache) {                                                               \
      cache_.store(nullptr);                                                   \
      GetRcuDomain().synchronize();                                            \
      delete cache;                                                            \
    }                                                                          \
  }                                                                            \
                                                                               \
  rocksdb::Status Insert(const rocksdb::Slice& key,                           \
                         void* value,                                          \
                         const rocksdb::Cache::CacheItemHelper* helper,        \
                         bool /*force_erase*/) override {                      \
    using Key  = typename AllocatorType::Key;                                  \
    using Item = typename AllocatorType::Item;                                 \
    Key k(key.data(), key.size());                                             \
    rocksdb::Status s;                                                         \
    std::scoped_lock guard(GetRcuDomain());                                    \
    AllocatorType* cache = cache_.load();                                      \
    if (cache) {                                                               \
      size_t size = (*helper->size_cb)(value);                                 \
      if (Item::getRequiredSize(k, size) <= FB_CACHE_MAX_ITEM_SIZE) {          \
        auto handle = cache->allocate(pool_, k, size);                         \
        if (handle) {                                                          \
          char* buf = static_cast<char*>(handle->getMemory());                 \
          s = (*helper->saveto_cb)(value, /*offset=*/0, size, buf);            \
          try {                                                                 \
            cache->insertOrReplace(handle);                                    \
          } catch (const std::exception& ex) {                                 \
            s = rocksdb::Status::Aborted(folly::sformat(                       \
                "Cachelib insertOrReplace exception, error:{}", ex.what()));   \
          }                                                                    \
        }                                                                      \
      } else {                                                                 \
        s = rocksdb::Status::InvalidArgument();                                \
      }                                                                        \
    }                                                                          \
    return s;                                                                  \
  }                                                                            \
                                                                               \
  std::unique_ptr<rocksdb::SecondaryCacheResultHandle> Lookup(                 \
      const rocksdb::Slice& key,                                               \
      const rocksdb::Cache::CacheItemHelper* helper,                           \
      rocksdb::Cache::CreateContext* create_context,                           \
      bool /*wait*/,                                                           \
      bool /*advise_erase*/,                                                   \
      rocksdb::Statistics* /*stats*/,                                          \
      bool& is_in_sec_cache) override {                                        \
    using Key = typename AllocatorType::Key;                                   \
    std::scoped_lock guard(GetRcuDomain());                                    \
    AllocatorType* cache = cache_.load();                                      \
    std::unique_ptr<rocksdb::SecondaryCacheResultHandle> hdl;                  \
    if (cache) {                                                               \
      auto handle = cache->find(Key(key.data(), key.size()));                  \
      if (handle) {                                                            \
        uint32_t sz = handle->getSize();                                       \
        const char* item = static_cast<const char*>(handle->getMemory());     \
        void* val = nullptr;                                                   \
        size_t charge = 0;                                                     \
        auto s = CALL_CREATE_CB(helper,                                        \
                                rocksdb::Slice(item, sz),                      \
                                create_context,                                \
                                &val,                                          \
                                &charge);                                      \
        if (s.ok() && val != nullptr) {                                        \
          hdl = std::make_unique<SyncSecondaryCacheHandle>(val, charge);       \
        }                                                                      \
      }                                                                        \
    }                                                                          \
    is_in_sec_cache = hdl != nullptr;                                          \
    return hdl;                                                                \
  }                                                                            \
                                                                               \
  void Erase(const rocksdb::Slice& key) override {                            \
    using Key = typename AllocatorType::Key;                                   \
    std::scoped_lock guard(GetRcuDomain());                                    \
    AllocatorType* cache = cache_.load();                                      \
    if (cache) { cache->remove(Key(key.data(), key.size())); }                \
  }                                                                            \
                                                                               \
  void WaitAll(                                                                \
      std::vector<rocksdb::SecondaryCacheResultHandle*> handles) override {    \
    for (auto* h : handles) { if (h && !h->IsReady()) h->Wait(); }           \
  }                                                                            \
                                                                               \
 private:                                                                      \
  std::atomic<AllocatorType*> cache_;                                          \
  cachelib::PoolId pool_;                                                      \
};

// Stamp out Lru2Q and TinyLFU subclasses
DEFINE_TYPED_WRAPPER(RocksCachelibWrapperLru2QImpl,
                     cachelib::Lru2QAllocator,
                     "lru2q")

DEFINE_TYPED_WRAPPER(RocksCachelibWrapperTinyLFUImpl,
                     cachelib::TinyLFUAllocator,
                     "tinylfu")

// ============================================================================
// Factory functions
// ============================================================================

// Internal helper — builds allocator config and returns typed wrapper.
// Used by Lru2Q and TinyLFU factories. LRU uses its own path below to
// keep the original RocksCachelibWrapper constructor call intact.
template <typename Allocator, typename WrapperImpl>
static std::unique_ptr<rocksdb::SecondaryCache>
NewTypedWrapper(const RocksCachelibOptions& opts) {
  typename Allocator::NvmCacheConfig nvmConfig;
  ApplyNvmOptions(opts, nvmConfig);

  typename Allocator::Config config;
  config.setCacheSize(opts.volatileSize)
        .setCacheName(opts.cacheName)
        .setAccessConfig({opts.bktPower, opts.lockPower})
        .enableNvmCache(nvmConfig)
        .validate(); // throws on bad config

  auto cache = std::make_unique<Allocator>(config);
  auto pool  = cache->addPool("default",
                              cache->getCacheMemoryStats().ramCacheSize);
  return std::make_unique<WrapperImpl>(std::move(cache), pool);
}

// LRU — uses original RocksCachelibWrapper (constructor takes FbCache/LRU)
std::unique_ptr<rocksdb::SecondaryCache>
NewRocksCachelibWrapperLru(const RocksCachelibOptions& opts) {
  NvmCacheConfig nvmConfig;
  ApplyNvmOptions(opts, nvmConfig);

  FbCacheConfig config;
  config.setCacheSize(opts.volatileSize)
        .setCacheName(opts.cacheName)
        .setAccessConfig({opts.bktPower, opts.lockPower})
        .enableNvmCache(nvmConfig)
        .validate();

  auto cache = std::make_unique<FbCache>(config);
  auto pool  = cache->addPool("default",
                              cache->getCacheMemoryStats().ramCacheSize);
  return std::unique_ptr<rocksdb::SecondaryCache>(
      new RocksCachelibWrapper(std::move(cache), pool, EvictionPolicy::kLru));
}

// Backward-compatible default — delegates to LRU
std::unique_ptr<rocksdb::SecondaryCache>
NewRocksCachelibWrapper(const RocksCachelibOptions& opts) {
  return NewRocksCachelibWrapperLru(opts);
}

// Lru2Q
std::unique_ptr<rocksdb::SecondaryCache>
NewRocksCachelibWrapperLru2Q(const RocksCachelibOptions& opts) {
  return NewTypedWrapper<cachelib::Lru2QAllocator,
                         RocksCachelibWrapperLru2QImpl>(opts);
}

// TinyLFU
std::unique_ptr<rocksdb::SecondaryCache>
NewRocksCachelibWrapperTinyLFU(const RocksCachelibOptions& opts) {
  return NewTypedWrapper<cachelib::TinyLFUAllocator,
                         RocksCachelibWrapperTinyLFUImpl>(opts);
}

} // namespace facebook::rocks_secondary_cache 

