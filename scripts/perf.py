#!/usr/bin/env python3

import re
import sys
from collections import defaultdict

FILES = {
    "Baseline": "scripts/perf_cpu_profile/baseline_perf_report.txt",
    "CacheLink": "scripts/perf_cpu_profile/cachelink_nvme_TinyLFU_1.0_perf_report.txt",
}

CATEGORIES = {
    "RocksDB read path": [
        "DBImpl::Get",
        "Version::Get",
        "TableCache::Get",
        "BlockBasedTable::Get",
        "BlockIter",
        "DataBlockIter",
    ],
    "Block fetch / storage read": [
        "BlockFetcher::ReadBlockContents",
        "RandomAccessFileReader::Read",
        "nfs_",
        "NFS",
        "ksys_pread64",
        "vfs_read",
    ],
    "Primary block-cache management": [
        "LRUCacheShard",
        "PutDataBlockToCache",
        "ShardedCache",
    ],
    "Statistics / instrumentation": [
        "StatisticsImpl",
        "recordTick",
        "recordInHistogram",
        "StopWatch",
    ],
    "CacheLink secondary adapter": [
        "CacheWithSecondaryAdapter",
        "RocksCachelibWrapper",
    ],
    "CacheLib allocation / TinyLFU metadata": [
        "MemoryAllocator",
        "MemoryPool",
        "AllocationClass",
        "MMTinyLFU",
        "TinyLFU",
        "ChainedHashTable",
        "CompressedPtr",
    ],
    "Navy writer / checksum": [
        "navy",
        "Navy",
        "navy_writer",
        "BlockCache::writeEntry",
        "BlockCache::insert",
        "checksum",
        "crc32",
    ],
}

percent_re = re.compile(r"^\s*([0-9]+\.[0-9]+)%\s+")


def parse_report(path):
    rows = []

    with open(path, "r", errors="ignore") as f:
        current_pct = None
        current_block = []

        for line in f:
            m = percent_re.match(line)

            if m:
                if current_pct is not None:
                    rows.append((current_pct, "\n".join(current_block)))

                current_pct = float(m.group(1))
                current_block = [line.rstrip()]
            else:
                if current_pct is not None:
                    current_block.append(line.rstrip())

        if current_pct is not None:
            rows.append((current_pct, "\n".join(current_block)))

    return rows


def classify(block):
    matched = []

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in block:
                matched.append(category)
                break

    if not matched:
        matched.append("Other / unresolved")

    return matched


def main():
    results = {}

    for mode, path in FILES.items():
        category_sum = defaultdict(float)
        rows = parse_report(path)

        for pct, block in rows:
            cats = classify(block)

            # If multiple categories match one call path, split the sample equally
            share = pct / len(cats)
            for cat in cats:
                category_sum[cat] += share

        results[mode] = category_sum

    categories = list(CATEGORIES.keys()) + ["Other / unresolved"]

    print("category,baseline_pct,cachelink_pct")
    for cat in categories:
        b = results.get("Baseline", {}).get(cat, 0.0)
        c = results.get("CacheLink", {}).get(cat, 0.0)
        print(f"{cat},{b:.2f},{c:.2f}")


if __name__ == "__main__":
    main()