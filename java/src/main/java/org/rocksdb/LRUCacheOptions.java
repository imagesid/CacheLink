package org.rocksdb;

public class LRUCacheOptions extends RocksObject {
  public LRUCacheOptions(final long capacity) {
    super(newLRUCacheOptions(capacity));
  }

  public LRUCacheOptions setSecondaryCache(
      final SecondaryCache secondaryCache) {
    setSecondaryCache(nativeHandle_, secondaryCache.nativeHandle_);
    return this;
  }

  @Override
  protected void disposeInternal(final long handle) {
    disposeInternalJni(handle);
  }

  private static native long newLRUCacheOptions(long capacity);
  private static native void setSecondaryCache(
      long lruCacheOptionsHandle, long secondaryCacheHandle);
  private static native void disposeInternalJni(long handle);
}