package org.rocksdb;

public class CompressedSecondaryCacheOptions extends RocksObject {
  public CompressedSecondaryCacheOptions() {
    super(newCompressedSecondaryCacheOptions());
  }

  public CompressedSecondaryCacheOptions setCapacity(final long capacity) {
    setCapacity(nativeHandle_, capacity);
    return this;
  }

  @Override
  protected void disposeInternal(final long handle) {
    disposeInternalJni(handle);
  }

  private static native long newCompressedSecondaryCacheOptions();
  private static native void setCapacity(long handle, long capacity);
  private static native void disposeInternalJni(long handle);
}