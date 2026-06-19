#!/usr/bin/env python3

import os
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =========================================================
# Paths
# =========================================================
LOG_DIR = "scripts/cpu_overhead_logs"
OUT_DIR = "scripts/cpu_mem_compare"

BASELINE_CPU = os.path.join(LOG_DIR, "baseline_pidstat_cpu.txt")
BASELINE_MEM = os.path.join(LOG_DIR, "baseline_pidstat_mem.txt")

CACHELINK_CPU = os.path.join(LOG_DIR, "cachelink_nvme_TinyLFU_1.0_pidstat_cpu.txt")
CACHELINK_MEM = os.path.join(LOG_DIR, "cachelink_nvme_TinyLFU_1.0_pidstat_mem.txt")


# =========================================================
# Helpers
# =========================================================
def check_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")


def parse_cpu(path, mode):
    rows = []

    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("Linux"):
                continue
            if "UID" in line or line.startswith("Average:"):
                continue

            parts = line.split()

            # Expected pidstat CPU format:
            # time UID PID %usr %system %guest %wait %CPU CPU Command
            if len(parts) < 10:
                continue

            if parts[-1] != "db_bench":
                continue

            try:
                rows.append({
                    "mode": mode,
                    "time": parts[0],
                    "pid": int(parts[2]),
                    "usr": float(parts[3]),
                    "system": float(parts[4]),
                    "guest": float(parts[5]),
                    "wait": float(parts[6]),
                    "cpu": float(parts[7]),
                })
            except ValueError:
                continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df["sec"] = range(len(df))

    return df


def parse_mem(path, mode):
    rows = []

    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("Linux"):
                continue
            if "UID" in line or line.startswith("Average:"):
                continue

            parts = line.split()

            # Expected pidstat MEM format:
            # time UID PID minflt/s majflt/s VSZ RSS %MEM Command
            if len(parts) < 9:
                continue

            if parts[-1] != "db_bench":
                continue

            try:
                rows.append({
                    "mode": mode,
                    "time": parts[0],
                    "pid": int(parts[2]),
                    "minflt_s": float(parts[3]),
                    "majflt_s": float(parts[4]),
                    "vsz_kb": float(parts[5]),
                    "rss_kb": float(parts[6]),
                    "mem_pct": float(parts[7]),
                })
            except ValueError:
                continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df["sec"] = range(len(df))
        df["rss_mb"] = df["rss_kb"] / 1024.0
        df["vsz_mb"] = df["vsz_kb"] / 1024.0

    return df


def summarize_cpu(df):
    return {
        "cpu_avg": df["cpu"].mean(),
        "cpu_max": df["cpu"].max(),
        "usr_avg": df["usr"].mean(),
        "system_avg": df["system"].mean(),
        "wait_avg": df["wait"].mean(),
    }


def summarize_mem(df):
    return {
        "rss_avg_mb": df["rss_mb"].mean(),
        "rss_max_mb": df["rss_mb"].max(),
        "mem_pct_avg": df["mem_pct"].mean(),
        "mem_pct_max": df["mem_pct"].max(),
        "vsz_avg_mb": df["vsz_mb"].mean(),
    }


def add_y_headroom(ax, values, ratio=0.18):
    values = [v for v in values if pd.notna(v)]

    if not values:
        return

    ymax = max(values)

    if ymax <= 0:
        ymax = 1.0

    ax.set_ylim(0, ymax * (1.0 + ratio))


def add_bar_labels(ax, bars, fmt="{:.1f}", fontsize=7):
    for bar in bars:
        height = bar.get_height()

        ax.annotate(
            fmt.format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
            clip_on=False,
        )


# =========================================================
# Main
# =========================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for path in [BASELINE_CPU, BASELINE_MEM, CACHELINK_CPU, CACHELINK_MEM]:
        check_file(path)

    baseline_cpu = parse_cpu(BASELINE_CPU, "Baseline")
    cachelink_cpu = parse_cpu(CACHELINK_CPU, "CacheLink")

    baseline_mem = parse_mem(BASELINE_MEM, "Baseline")
    cachelink_mem = parse_mem(CACHELINK_MEM, "CacheLink")

    if baseline_cpu.empty:
        raise RuntimeError(f"No CPU data parsed from {BASELINE_CPU}")

    if cachelink_cpu.empty:
        raise RuntimeError(f"No CPU data parsed from {CACHELINK_CPU}")

    if baseline_mem.empty:
        raise RuntimeError(f"No MEM data parsed from {BASELINE_MEM}")

    if cachelink_mem.empty:
        raise RuntimeError(f"No MEM data parsed from {CACHELINK_MEM}")

    cpu_summary = pd.DataFrame([
        {"mode": "Baseline", **summarize_cpu(baseline_cpu)},
        {"mode": "CacheLink", **summarize_cpu(cachelink_cpu)},
    ])

    mem_summary = pd.DataFrame([
        {"mode": "Baseline", **summarize_mem(baseline_mem)},
        {"mode": "CacheLink", **summarize_mem(cachelink_mem)},
    ])

    # Save summaries
    cpu_csv = os.path.join(OUT_DIR, "cpu_comparison_summary.csv")
    mem_csv = os.path.join(OUT_DIR, "memory_comparison_summary.csv")

    cpu_summary.to_csv(cpu_csv, index=False)
    mem_summary.to_csv(mem_csv, index=False)

    # =========================================================
    # Paper-style compact figure settings
    # =========================================================
    plt.rcParams.update({
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
        "figure.titlesize": 9,
    })

    modes = ["Baseline", "CacheLink"]

    # Grayscale + hatch pattern
    facecolors = ["white", "0.70"]
    hatches = ["///", "\\\\\\"]
    edgecolor = "black"

    fig, axes = plt.subplots(2, 2, figsize=(4, 3))
    axes = axes.flatten()

    # =========================================================
    # (a) Average CPU utilization
    # =========================================================
    ax = axes[0]

    values = cpu_summary["cpu_avg"].tolist()
    bars = []

    for i, v in enumerate(values):
        b = ax.bar(
            modes[i],
            v,
            color=facecolors[i],
            edgecolor=edgecolor,
            hatch=hatches[i],
            linewidth=0.8,
            width=0.65,
        )
        bars.extend(b)

    ax.set_title("(a) Average CPU")
    ax.set_ylabel("CPU (%)")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    add_y_headroom(ax, values, ratio=0.22)
    add_bar_labels(ax, bars, fmt="{:.2f}", fontsize=7)

    # =========================================================
    # (b) User/System CPU
    # =========================================================
    ax = axes[1]

    x = [0, 1]
    width = 0.28

    bars1 = ax.bar(
        [i - width / 2 for i in x],
        cpu_summary["usr_avg"],
        width=width,
        color="white",
        edgecolor="black",
        hatch="///",
        linewidth=0.8,
        label="User",
    )

    bars2 = ax.bar(
        [i + width / 2 for i in x],
        cpu_summary["system_avg"],
        width=width,
        color="0.70",
        edgecolor="black",
        hatch="\\\\\\",
        linewidth=0.8,
        label="System",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(modes)
    ax.set_title("(b) User/System CPU")
    ax.set_ylabel("CPU (%)")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")

    values = list(cpu_summary["usr_avg"]) + list(cpu_summary["system_avg"])
    add_y_headroom(ax, values, ratio=0.24)
    add_bar_labels(ax, bars1, fmt="{:.2f}", fontsize=7)
    add_bar_labels(ax, bars2, fmt="{:.2f}", fontsize=7)

    # =========================================================
    # (c) Average RSS memory
    # =========================================================
    ax = axes[2]

    values = mem_summary["rss_avg_mb"].tolist()
    bars = []

    for i, v in enumerate(values):
        b = ax.bar(
            modes[i],
            v,
            color=facecolors[i],
            edgecolor=edgecolor,
            hatch=hatches[i],
            linewidth=0.8,
            width=0.65,
        )
        bars.extend(b)

    ax.set_title("(c) Average RSS")
    ax.set_ylabel("RSS (MB)")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    add_y_headroom(ax, values, ratio=0.22)
    add_bar_labels(ax, bars, fmt="{:.1f}", fontsize=7)

    # =========================================================
    # (d) Peak RSS memory
    # =========================================================
    ax = axes[3]

    values = mem_summary["rss_max_mb"].tolist()
    bars = []

    for i, v in enumerate(values):
        b = ax.bar(
            modes[i],
            v,
            color=facecolors[i],
            edgecolor=edgecolor,
            hatch=hatches[i],
            linewidth=0.8,
            width=0.65,
        )
        bars.extend(b)

    ax.set_title("(d) Peak RSS")
    ax.set_ylabel("RSS (MB)")
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    add_y_headroom(ax, values, ratio=0.22)
    add_bar_labels(ax, bars, fmt="{:.1f}", fontsize=7)

    # Compact layout
    plt.tight_layout(pad=0.8, w_pad=0.9, h_pad=1.0)

    summary_fig = os.path.join(OUT_DIR, "cpu_mem_summary_subfigures_paper.png")

    plt.savefig(summary_fig, dpi=300, bbox_inches="tight")
    plt.close(fig)

    # =========================================================
    # Print output
    # =========================================================
    print("======================================")
    print("CPU Summary")
    print(cpu_summary.to_string(index=False))
    print("======================================")
    print("Memory Summary")
    print(mem_summary.to_string(index=False))
    print("======================================")
    print("Generated files:")
    print(cpu_csv)
    print(mem_csv)
    print(summary_fig)
    print("======================================")


if __name__ == "__main__":
    main()