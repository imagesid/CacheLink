#include <jni.h>
#include <memory>
#include "include/rocksdb/cache.h"

using rocksdb::LRUCacheOptions;
using rocksdb::SecondaryCache;

extern "C" {

jlong Java_org_rocksdb_LRUCacheOptions_newLRUCacheOptions(
    JNIEnv*, jclass, jlong capacity) {
  auto* opts = new LRUCacheOptions(static_cast<size_t>(capacity));
  return reinterpret_cast<jlong>(opts);
}

void Java_org_rocksdb_LRUCacheOptions_setSecondaryCache(
    JNIEnv*, jclass, jlong jlru_opts_handle, jlong jsecondary_handle) {
  auto* lru_opts = reinterpret_cast<LRUCacheOptions*>(jlru_opts_handle);
  auto* secondary =
      reinterpret_cast<std::shared_ptr<SecondaryCache>*>(jsecondary_handle);
  lru_opts->secondary_cache = *secondary;
}

void Java_org_rocksdb_LRUCacheOptions_disposeInternalJni(
    JNIEnv*, jclass, jlong jhandle) {
  delete reinterpret_cast<LRUCacheOptions*>(jhandle);
}

}