#include <jni.h>
#include "include/rocksdb/cache.h"

using rocksdb::CompressedSecondaryCacheOptions;

extern "C" {

jlong Java_org_rocksdb_CompressedSecondaryCacheOptions_newCompressedSecondaryCacheOptions(
    JNIEnv*, jclass) {
  auto* opts = new CompressedSecondaryCacheOptions();
  return reinterpret_cast<jlong>(opts);
}

void Java_org_rocksdb_CompressedSecondaryCacheOptions_setCapacity(
    JNIEnv*, jclass, jlong jhandle, jlong capacity) {
  auto* opts =
      reinterpret_cast<CompressedSecondaryCacheOptions*>(jhandle);
  opts->capacity = static_cast<size_t>(capacity);
}

void Java_org_rocksdb_CompressedSecondaryCacheOptions_disposeInternalJni(
    JNIEnv*, jclass, jlong jhandle) {
  delete reinterpret_cast<CompressedSecondaryCacheOptions*>(jhandle);
}

}