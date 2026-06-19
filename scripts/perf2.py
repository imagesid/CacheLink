#!/usr/bin/env python3

import os
import re
from collections import defaultdict

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# Input / Output paths
# ============================================================

OUT_DIR = "scripts/perf_cpu_profile"
FIG_DIR = os.path.join(OUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

BASELINE_REPORT = os.path.join(OUT_DIR, "baseline_perf_report.txt")
CACHELINK_REPORT = os.path.join(OUT_DIR, "cachelink_nvme_TinyLFU_1.0_perf_report.txt")

CSV_OUT = os.path.join(OUT_DIR, "perf_path_rocksdb_cachelib_comparison.csv")
FIG_OUT = os.path.join(FIG_DIR, "perf_path_rocksdb_cachelib_comparison.png")
STACKED_OUT = os.path.join(FIG_DIR, "perf_path_rocksdb_cachelib_stacked.png")


# ============================================================
# Category rules
# ============================================================

CATEGORIES = {
    # -------------------------
    # RocksDB-related paths
    # -------------------------
    "RocksDB: read path": [
        "DBImpl::Get",
        "DBImpl::GetImpl",
        "Version::Get",
        "TableCache::Get",
        "BlockBasedTable::Get",
        "BlockIter",
        "DataBlockIter",
        "IndexBlockIter",
        "LookupKey",
        "GetContext",
    ],

    "RocksDB: block fetch / NFS read": [
        "BlockFetcher::ReadBlockContents",
        "RandomAccessFileReader::Read",
        "nfs_",
        "NFS",
        "nfs4_",
        "vfs_read",
        "ksys_pread64",
        "__x64_sys_pread64",
        "new_sync_read",
    ],

    "RocksDB: primary block-cache mgmt.": [
        "LRUCacheShard",
        "ShardedCache",
        "PutDataBlockToCache",
    ],

    "RocksDB: statistics / instrumentation": [
        "StatisticsImpl",
        "recordTick",
        "recordInHistogram",
        "StopWatch",
        "Histogram",
        "iostats_context",
        "perf_context",
    ],

    # -------------------------
    # CacheLink / CacheLib paths
    # -------------------------
    "CacheLink: secondary adapter": [
        "CacheWithSecondaryAdapter",
        "RocksCachelibWrapper",
        "rocks_secondary_cache",
    ],

    "CacheLib: allocation / policy metadata": [
        "MemoryAllocator",
        "MemoryPool",
        "AllocationClass",
        "CacheAllocator",
        "MMTinyLFU",
        "TinyLFU",
        "ChainedHashTable",
        "CompressedPtr",
        "DList",
        "Slab",
        "SlabAllocator",
    ],

    "CacheLib: Navy writer / checksum": [
        "navy_writer",
        "navy::",
        "Navy",
        "BlockCache::writeEntry",
        "BlockCache::insert",
        "RegionManager",
        "checksum",
        "crc32",
        "crc_update",
        "EnginePair::insert",
        "EnginePair::scheduleInsert",
        "JobQueue",
        "ThreadPoolExecutor",
    ],

    # -------------------------
    # Other system-level paths
    # -------------------------
    "Kernel / memory mgmt.": [
        "[kernel.kallsyms]",
        "__handle_mm_fault",
        "do_user_addr_fault",
        "page_fault",
        "prep_new_page",
        "release_pages",
        "get_mem_cgroup_from_mm",
        "kmem_cache",
        "alloc_pages",
        "clear_page",
        "free_pages",
        "try_grab_compound_head",
    ],
}


CATEGORY_ORDER = [
    "RocksDB: read path",
    "RocksDB: block fetch / NFS read",
    "RocksDB: primary block-cache mgmt.",
    "RocksDB: statistics / instrumentation",
    "CacheLink: secondary adapter",
    "CacheLib: allocation / policy metadata",
    "CacheLib: Navy writer / checksum",
    "Kernel / memory mgmt.",
    "Other / unresolved",
]


# ============================================================
# Parser
# ============================================================

PERCENT_RE = re.compile(r"^\s*([0-9]+\.[0-9]+)%\s+")


def check_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")


def parse_perf_report(path):
    rows = []

    with open(path, "r", errors="ignore") as f:
        current_pct = None
        current_block = []

        for line in f:
            m = PERCENT_RE.match(line)

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


def classify_block(block):
    matched = []

    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in block:
                matched.append(category)
                break

    if not matched:
        matched.append("Other / unresolved")

    return matched


def aggregate_report(path):
    rows = parse_perf_report(path)
    category_sum = defaultdict(float)

    for pct, block in rows:
        cats = classify_block(block)

        # Split across categories if one call path matches multiple groups.
        share = pct / len(cats)

        for cat in cats:
            category_sum[cat] += share

    return category_sum


# ============================================================
# Plot helpers
# ============================================================

def setup_paper_style():
    plt.rcParams.update({
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.titlesize": 9,
    })


def add_labels_horizontal(ax, bars, fontsize=7):
    for bar in bars:
        width = bar.get_width()
        if width <= 0:
            continue

        ax.annotate(
            f"{width:.1f}",
            xy=(width, bar.get_y() + bar.get_height() / 2),
            xytext=(3, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=fontsize,
            clip_on=False,
        )


def add_group_background(ax, y_positions, labels):
    """
    Lightly separate RocksDB, CacheLib, Kernel/Other groups.
    """
    for idx, label in enumerate(labels):
        if label.startswith("CacheLib"):
            ax.axhspan(idx - 0.48, idx + 0.48, color="0.95", zorder=0)
        elif label.startswith("Kernel") or label.startswith("Other"):
            ax.axhspan(idx - 0.48, idx + 0.48, color="0.90", zorder=0)


def plot_grouped_bar(df):
    plot_df = df.set_index("category").reindex(CATEGORY_ORDER).fillna(0.0).reset_index()

    # Reverse order so first category appears at the top
    plot_df = plot_df.iloc[::-1].copy()

    categories = plot_df["category"].tolist()
    y = list(range(len(categories)))
    height = 0.34

    fig, ax = plt.subplots(figsize=(7.6, 4.8))

    add_group_background(ax, y, categories)

    # Baseline first: shown slightly above each category center
    baseline_bars = ax.barh(
        [i + height / 2 for i in y],
        plot_df["Baseline"],
        height=height,
        color="white",
        edgecolor="black",
        hatch="///",
        linewidth=0.8,
        label="Baseline",
        zorder=3,
    )

    # CacheLink second: shown slightly below each category center
    cachelink_bars = ax.barh(
        [i - height / 2 for i in y],
        plot_df["CacheLink"],
        height=height,
        color="0.70",
        edgecolor="black",
        hatch="\\\\\\",
        linewidth=0.8,
        label="CacheLink",
        zorder=3,
    )

    ax.set_yticks(y)
    ax.set_yticklabels(categories)
    ax.set_xlabel("Sampled CPU cycles (%)")
    # ax.set_title("Perf Path Attribution: RocksDB vs CacheLib")
    ax.grid(axis="x", linestyle="--", linewidth=0.4, alpha=0.6, zorder=1)
    ax.set_axisbelow(True)

    max_val = max(plot_df["Baseline"].max(), plot_df["CacheLink"].max())
    ax.set_xlim(0, max_val * 1.22)

    add_labels_horizontal(ax, baseline_bars)
    add_labels_horizontal(ax, cachelink_bars)

    ax.legend(frameon=False, loc="lower right")

    plt.tight_layout()
    fig.savefig(FIG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_stacked_bar(df):
    plot_df = df.set_index("category").reindex(CATEGORY_ORDER).fillna(0.0)

    modes = ["Baseline", "CacheLink"]

    fig, ax = plt.subplots(figsize=(6.4, 3.7))

    bottoms = [0.0, 0.0]

    hatches = [
        "///", "///", "///", "///",
        "\\\\\\", "\\\\\\", "\\\\\\",
        "...", "",
    ]

    grays = [
        "1.0", "0.90", "0.80", "0.70",
        "0.60", "0.50", "0.40",
        "0.30", "0.95",
    ]

    for idx, category in enumerate(CATEGORY_ORDER):
        values = [
            plot_df.loc[category, "Baseline"],
            plot_df.loc[category, "CacheLink"],
        ]

        ax.bar(
            modes,
            values,
            bottom=bottoms,
            color=grays[idx],
            edgecolor="black",
            hatch=hatches[idx],
            linewidth=0.6,
            label=category,
        )

        bottoms = [bottoms[i] + values[i] for i in range(2)]

    ax.set_ylabel("Sampled CPU cycles (%)")
    ax.set_title("CPU Path Composition")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    ax.legend(
        frameon=False,
        bbox_to_anchor=(1.02, 1.0),
        loc="upper left",
        borderaxespad=0,
    )

    plt.tight_layout()
    fig.savefig(STACKED_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# Main
# ============================================================

def main():
    check_file(BASELINE_REPORT)
    check_file(CACHELINK_REPORT)

    setup_paper_style()

    baseline = aggregate_report(BASELINE_REPORT)
    cachelink = aggregate_report(CACHELINK_REPORT)

    rows = []
    for cat in CATEGORY_ORDER:
        rows.append({
            "category": cat,
            "Baseline": baseline.get(cat, 0.0),
            "CacheLink": cachelink.get(cat, 0.0),
        })

    df = pd.DataFrame(rows)

    df.to_csv(CSV_OUT, index=False)

    plot_grouped_bar(df)
    plot_stacked_bar(df)

    print("======================================")
    print("Perf Path Percentage Summary")
    print(df.to_string(index=False))
    print("======================================")
    print("Generated files:")
    print(CSV_OUT)
    print(FIG_OUT)
    print(STACKED_OUT)
    print("======================================")


if __name__ == "__main__":
    main()