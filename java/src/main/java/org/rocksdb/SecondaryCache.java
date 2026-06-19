package org.rocksdb;

public abstract class SecondaryCache extends RocksObject {
  protected SecondaryCache(final long nativeHandle) {
    super(nativeHandle);
  }
}