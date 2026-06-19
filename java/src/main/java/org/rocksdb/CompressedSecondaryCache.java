package org.rocksdb;

public class CompressedSecondaryCache extends SecondaryCache {
  public CompressedSecondaryCache(
      final CompressedSecondaryCacheOptions options) {
    super(newCompressedSecondaryCache(options.nativeHandle_));
  }

  @Override
  protected void disposeInternal(final long handle) {
    disposeInternalJni(handle);
  }

  private static native long newCompressedSecondaryCache(long optionsHandle);
  private static native void disposeInternalJni(long handle);
}