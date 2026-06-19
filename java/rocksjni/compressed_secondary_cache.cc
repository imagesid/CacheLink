#include <jni.h>
#include <memory>
#include "include/rocksdb/cache.h"

using rocksdb::CompressedSecondaryCacheOptions;
using rocksdb::SecondaryCache;
using rocksdb::NewCompressedSecondaryCache;

extern "C" {

jlong Java_org_rocksdb_CompressedSecondaryCache_newCompressedSecondaryCache(
    JNIEnv*, jclass, jlong joptions_handle) {
  auto* opts =
      reinterpret_cast<CompressedSecondaryCacheOptions*>(joptions_handle);

  auto* ptr = new std::shared_ptr<SecondaryCache>(
      NewCompressedSecondaryCache(*opts));
  return reinterpret_cast<jlong>(ptr);
}

void Java_org_rocksdb_CompressedSecondaryCache_disposeInternalJni(
    JNIEnv*, jclass, jlong jhandle) {
  delete reinterpret_cast<std::shared_ptr<SecondaryCache>*>(jhandle);
}

}