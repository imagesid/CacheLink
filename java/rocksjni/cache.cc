#include <jni.h>

#include "include/org_rocksdb_Cache.h"
#include "rocksdb/advanced_cache.h"
#include "rocksdb/secondary_cache.h"
#include "tools/cachelink.h"

#include <iostream>
#include <string>

// ==============================
// GLOBAL CONFIG FROM JAVA
// ==============================
std::string g_secondary_cache_id = "";
std::string g_cachelink_config = "";

// ==============================
// BUILD FINAL URI
// ==============================
std::string GetFullCacheURI() {
  if (g_secondary_cache_id.empty()) return "";

  if (g_cachelink_config.empty()) {
    return g_secondary_cache_id;
  }

  return g_secondary_cache_id + "," + g_cachelink_config;
}

// ==============================
// REGISTER FACTORY
// ==============================
void RegisterMyCache() {
  rocksdb::ObjectLibrary::Default()->AddFactory<rocksdb::SecondaryCache>(
      "CacheLink",
      [](const std::string& uri,
         std::unique_ptr<rocksdb::SecondaryCache>* guard,
         std::string* errmsg) -> rocksdb::SecondaryCache* {

        // Use JNI-configured URI if available
        std::string full_uri = GetFullCacheURI();
        if (full_uri.empty()) {
          full_uri = uri;  // fallback
        }

        fprintf(stderr, "[Factory] USING URI: %s\n", full_uri.c_str());

        facebook::rocks_secondary_cache::RocksCachelibOptions opts;
        auto s = facebook::rocks_secondary_cache::RocksCachelibWrapper
                     ::OptionsFromString(full_uri, &opts);

        if (!s.ok()) {
          *errmsg = s.ToString();
          return nullptr;
        }

        std::unique_ptr<rocksdb::SecondaryCache> cache;

        switch (opts.evictionPolicy) {
          case facebook::rocks_secondary_cache::EvictionPolicy::kLru:
            cache = facebook::rocks_secondary_cache::NewRocksCachelibWrapperLru(opts);
            break;
          case facebook::rocks_secondary_cache::EvictionPolicy::kLru2Q:
            cache = facebook::rocks_secondary_cache::NewRocksCachelibWrapperLru2Q(opts);
            break;
          case facebook::rocks_secondary_cache::EvictionPolicy::kTinyLFU:
            cache = facebook::rocks_secondary_cache::NewRocksCachelibWrapperTinyLFU(opts);
            break;
        }

        if (!cache) {
          *errmsg = "CacheLink returned nullptr";
          return nullptr;
        }

        auto* raw = cache.get();
        guard->reset(cache.release());
        return raw;
      });

  fprintf(stderr, "[REGISTER] CacheLink registered\n");
}

// ==============================
// JNI LIFECYCLE
// ==============================
extern "C"
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {
  (void)vm;
  (void)reserved;

  std::cerr << "[JNI] JNI_OnLoad called" << std::endl;

  RegisterMyCache();

  return JNI_VERSION_1_8;
}

// ==============================
// JNI CONFIG SETTERS
// ==============================
extern "C"
JNIEXPORT void JNICALL
Java_site_ycsb_db_rocksdb_CacheLink_setSecondaryUri(
    JNIEnv* env, jclass, jstring juri) {

  const char* uri = env->GetStringUTFChars(juri, nullptr);
  g_secondary_cache_id = uri;
  env->ReleaseStringUTFChars(juri, uri);

  std::cerr << "[JNI] secondary_cache_uri = "
            << g_secondary_cache_id << std::endl;
}

extern "C"
JNIEXPORT void JNICALL
Java_site_ycsb_db_rocksdb_CacheLink_setCacheLinkConfig(
    JNIEnv* env, jclass, jstring jcfg) {

  const char* cfg = env->GetStringUTFChars(jcfg, nullptr);
  g_cachelink_config = cfg;
  env->ReleaseStringUTFChars(jcfg, cfg);

  std::cerr << "[JNI] cachelink = "
            << g_cachelink_config << std::endl;
}

// ==============================
// OPTIONAL: CACHE STATS
// ==============================
jlong Java_org_rocksdb_Cache_getUsage(JNIEnv*, jclass, jlong jhandle) {
  auto* sptr_cache =
      reinterpret_cast<std::shared_ptr<ROCKSDB_NAMESPACE::Cache>*>(jhandle);
  return static_cast<jlong>(sptr_cache->get()->GetUsage());
}

jlong Java_org_rocksdb_Cache_getPinnedUsage(JNIEnv*, jclass, jlong jhandle) {
  auto* sptr_cache =
      reinterpret_cast<std::shared_ptr<ROCKSDB_NAMESPACE::Cache>*>(jhandle);
  return static_cast<jlong>(sptr_cache->get()->GetPinnedUsage());
}