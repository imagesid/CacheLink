/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once
#include <sstream>
#include <string>
#include "cachelib/allocator/CacheAllocator.h"
#include "rocksdb/secondary_cache.h"
#include "rocksdb/types.h"
#include "rocksdb/version.h"
#include "rocksdb/utilities/customizable_util.h"
#include "rocksdb/utilities/object_registry.h"


namespace facebook {
namespace rocks_secondary_cache {

// ---------------------------------------------------------------------------
// Eviction policy (DRAM L1 allocator type)
// ---------------------------------------------------------------------------
enum class EvictionPolicy {
  kLru,      // cachelib::LruAllocator     (default)
  kLru2Q,    // cachelib::Lru2QAllocator
  kTinyLFU,  // cachelib::TinyLFUAllocator
};

inline rocksdb::Status EvictionPolicyFromString(const std::string& s,
                                                EvictionPolicy* out) {
  if (s == "lru"     || s == "LRU")     { *out = EvictionPolicy::kLru;     return rocksdb::Status::OK(); }
  if (s == "lru2q"   || s == "LRU2Q")   { *out = EvictionPolicy::kLru2Q;   return rocksdb::Status::OK(); }
  if (s == "tinylfu" || s == "TinyLFU") { *out = EvictionPolicy::kTinyLFU; return rocksdb::Status::OK(); }
  return rocksdb::Status::InvalidArgument(
      "Unknown eviction policy '" + s + "'. Valid: lru, lru2q, tinylfu");
}

inline std::string EvictionPolicyToString(EvictionPolicy p) {
  switch (p) {
    case EvictionPolicy::kLru:     return "lru";
    case EvictionPolicy::kLru2Q:   return "lru2q";
    case EvictionPolicy::kTinyLFU: return "tinylfu";
  }
  return "unknown";
}

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------
struct RocksCachelibOptions {
  // A name for the use case
  std::string cacheName;

  // Path to the NVM cache file
  std::string fileName;

  // Maximum size of the NVM cache file (REQUIRED, must be > 0)
  size_t size = 0;

  // Minimum IO granularity. Typically the device block size
  size_t blockSize = 4096;

  // Size of a cache region. A region is the granularity for garbage collection
  size_t regionSize = 16 * 1024 * 1024;

  // Eviction policy for the DRAM (L1) portion of the cache
  EvictionPolicy evictionPolicy = EvictionPolicy::kLru;

  // Admission control policy for NVM writes - "random" or "dynamic_random".
  // "dynamic_random" rate-limits writes to prolong flash life.
  std::string admPolicy = "random";

  // For "random" admission policy: probability of admitting [0.0, 1.0]
  double admProbability = 1.0;

  // For "dynamic_random": maximum write rate in bytes/s
  uint64_t maxWriteRate = 128 << 20;

  // For "dynamic_random": target daily write rate in bytes/s
  uint64_t admissionWriteRate = 128 << 20;

  // Size of the volatile (DRAM) portion of the cache
  size_t volatileSize = 256 * 1024 * 1024;

  // Base-2 exponent for number of hash table buckets
  uint32_t bktPower = 12;

  // Base-2 exponent for number of locks
  uint32_t lockPower = 12;

  // If true, enable Cachelib FB303 stats
  bool fb303Stats = false;

  // An oncall name for FB303 stats
  std::string oncallName;
};

// ---------------------------------------------------------------------------
// Legacy type aliases (backward compatibility — LRU is the default allocator)
// ---------------------------------------------------------------------------
using FbCache           = cachelib::LruAllocator;
using FbCacheConfig     = typename FbCache::Config;
using NvmCacheConfig    = typename FbCache::NvmCacheConfig;
using FbCacheKey        = typename FbCache::Key;
using FbCacheReadHandle = typename FbCache::ReadHandle;
using FbCacheItem       = typename FbCache::Item;

// ---------------------------------------------------------------------------
// RocksCachelibWrapper — LRU-backed implementation of rocksdb::SecondaryCache
//
// For Lru2Q and TinyLFU, CreateFromString() returns typed subclasses defined
// in the .cc. All three share the same Name()/kClassName() so RocksDB's
// ObjectRegistry treats them identically.
//
// URI format for --secondary_cache_uri in db_bench:
//   id=CacheLink,size=<bytes>,eviction=<lru|lru2q|tinylfu>,
//   adm_policy=<random|dynamic_random>[,adm_prob=0.5]
//   [,volatile_size=<bytes>][,max_write_rate=<bytes/s>]
//   [,adm_write_rate=<bytes/s>][,block_size=<bytes>]
//   [,region_size=<bytes>][,file=<path>][,name=<tag>]
// ---------------------------------------------------------------------------
class RocksCachelibWrapper : public rocksdb::SecondaryCache {
 public:
  RocksCachelibWrapper(std::unique_ptr<FbCache>&& cache,
                       cachelib::PoolId pool,
                       EvictionPolicy eviction = EvictionPolicy::kLru)
      : cache_(std::move(cache).release()),
        pool_(pool),
        eviction_(eviction) {}

  ~RocksCachelibWrapper() override;

  static const char* kClassName() { return "RocksCachelibWrapper"; }
  const char* Name() const override { return kClassName(); }

  // Called by RocksDB ObjectRegistry when --secondary_cache_uri is set.
  // Parses URI params and returns the correct allocator-typed instance.
  static rocksdb::Status CreateFromString(
      const rocksdb::ConfigOptions& config_options,
      const std::string& config_string,
      std::shared_ptr<rocksdb::SecondaryCache>* result);

  // Parse URI param string into options.
  // Also used by db_bench registration and tests.
  static rocksdb::Status OptionsFromString(const std::string& uri,
                                           RocksCachelibOptions* opts);

  rocksdb::Status Insert(const rocksdb::Slice& key,
                         void* value,
                         const rocksdb::Cache::CacheItemHelper* helper,
                         bool force_erase) override;

#if ROCKSDB_MAJOR > 8 || (ROCKSDB_MAJOR == 8 && ROCKSDB_MINOR >= 7)
  rocksdb::Status InsertSaved(const rocksdb::Slice& /*key*/,
                              const rocksdb::Slice& /*saved*/,
                              rocksdb::CompressionType /*type*/,
                              rocksdb::CacheTier /*source*/) override {
    return rocksdb::Status::NotSupported();
  }
#endif

  std::unique_ptr<rocksdb::SecondaryCacheResultHandle> Lookup(
      const rocksdb::Slice& key,
      const rocksdb::Cache::CacheItemHelper* helper,
      rocksdb::Cache::CreateContext* create_context,
      bool wait,
      bool advise_erase,
      rocksdb::Statistics* stats,
      bool& is_in_sec_cache) override;

  bool SupportForceErase() const override { return false; }

  void Erase(const rocksdb::Slice& key) override;

  void WaitAll(
      std::vector<rocksdb::SecondaryCacheResultHandle*> handles) override;

  std::string GetPrintableOptions() const override;

  // Persists state to file and frees the cache object. Not thread safe.
  void Close();

 private:
  std::atomic<FbCache*> cache_;
  cachelib::PoolId      pool_;
  EvictionPolicy        eviction_;
};

// ---------------------------------------------------------------------------
// Public factory functions
// ---------------------------------------------------------------------------

// Default — LRU backed (backward compatible)
extern std::unique_ptr<rocksdb::SecondaryCache> NewRocksCachelibWrapper(
    const RocksCachelibOptions& opts);

// Explicit policy factories — used by CreateFromString and db_bench
extern std::unique_ptr<rocksdb::SecondaryCache> NewRocksCachelibWrapperLru(
    const RocksCachelibOptions& opts);
extern std::unique_ptr<rocksdb::SecondaryCache> NewRocksCachelibWrapperLru2Q(
    const RocksCachelibOptions& opts);
extern std::unique_ptr<rocksdb::SecondaryCache> NewRocksCachelibWrapperTinyLFU(
    const RocksCachelibOptions& opts);

} // namespace rocks_secondary_cache
} // namespace facebook