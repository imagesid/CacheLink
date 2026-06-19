#!/usr/bin/env python3

import os
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


LOG_DIR = "scripts/cpu_overhead_logs"
OUT_DIR = "scripts/cpu_mem_compare"

BASELINE_CPU = os.path.join(LOG_DIR, "baseline_pidstat_cpu.txt")
BASELINE_MEM = os.path.join(LOG_DIR, "baseline_pidstat_mem.txt")

CACHELINK_CPU = os.path.join(LOG_DIR, "cachelink_nvme_TinyLFU_1.0_pidstat_cpu.txt")
CACHELINK_MEM = os.path.join(LOG_DIR, "cachelink_nvme_TinyLFU_1.0_pidstat_mem.txt")


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

            # Expected:
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

            # Expected:
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
    }


def check_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for path in [BASELINE_CPU, BASELINE_MEM, CACHELINK_CPU, CACHELINK_MEM]:
        check_file(path)

    baseline_cpu = parse_cpu(BASELINE_CPU, "Baseline")
    cachelink_cpu = parse_cpu(CACHELINK_CPU, "CacheLink")

    baseline_mem = parse_mem(BASELINE_MEM, "Baseline")
    cachelink_mem = parse_mem(CACHELINK_MEM, "CacheLink")

    if baseline_cpu.empty:
        raise RuntimeError(f"No CPU samples parsed from {BASELINE_CPU}")
    if cachelink_cpu.empty:
        raise RuntimeError(f"No CPU samples parsed from {CACHELINK_CPU}")
    if baseline_mem.empty:
        raise RuntimeError(f"No MEM samples parsed from {BASELINE_MEM}")
    if cachelink_mem.empty:
        raise RuntimeError(f"No MEM samples parsed from {CACHELINK_MEM}")

    cpu_summary = pd.DataFrame([
        {"mode": "Baseline", **summarize_cpu(baseline_cpu)},
        {"mode": "CacheLink", **summarize_cpu(cachelink_cpu)},
    ])

    mem_summary = pd.DataFrame([
        {"mode": "Baseline", **summarize_mem(baseline_mem)},
        {"mode": "CacheLink", **summarize_mem(cachelink_mem)},
    ])

    generated = []

    cpu_csv = os.path.join(OUT_DIR, "cpu_comparison_summary.csv")
    mem_csv = os.path.join(OUT_DIR, "memory_comparison_summary.csv")

    cpu_summary.to_csv(cpu_csv, index=False)
    mem_summary.to_csv(mem_csv, index=False)

    generated.append(cpu_csv)
    generated.append(mem_csv)

    # -----------------------------
    # CPU average comparison
    # -----------------------------
    plt.figure(figsize=(5.5, 4))
    plt.bar(cpu_summary["mode"], cpu_summary["cpu_avg"])
    plt.ylabel("Average CPU utilization (%)")
    plt.title("CPU Overhead: Baseline vs CacheLink")
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "cpu_avg_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    # -----------------------------
    # User/System CPU comparison
    # -----------------------------
    x = range(len(cpu_summary))
    width = 0.35

    plt.figure(figsize=(6, 4))
    plt.bar([i - width / 2 for i in x], cpu_summary["usr_avg"], width, label="User CPU")
    plt.bar([i + width / 2 for i in x], cpu_summary["system_avg"], width, label="System CPU")
    plt.xticks(list(x), cpu_summary["mode"])
    plt.ylabel("Average CPU utilization (%)")
    plt.title("User/System CPU: Baseline vs CacheLink")
    plt.legend()
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "cpu_user_system_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    # -----------------------------
    # CPU time series comparison
    # -----------------------------
    plt.figure(figsize=(8, 4))
    plt.plot(baseline_cpu["sec"], baseline_cpu["cpu"], label="Baseline")
    plt.plot(cachelink_cpu["sec"], cachelink_cpu["cpu"], label="CacheLink")
    plt.xlabel("Time (s)")
    plt.ylabel("CPU utilization (%)")
    plt.title("CPU Utilization Over Time")
    plt.legend()
    plt.grid(True, linewidth=0.3)
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "cpu_timeseries_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    # -----------------------------
    # Memory average RSS comparison
    # -----------------------------
    plt.figure(figsize=(5.5, 4))
    plt.bar(mem_summary["mode"], mem_summary["rss_avg_mb"])
    plt.ylabel("Average RSS memory (MB)")
    plt.title("Memory Overhead: Baseline vs CacheLink")
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "memory_avg_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    # -----------------------------
    # Memory peak RSS comparison
    # -----------------------------
    plt.figure(figsize=(5.5, 4))
    plt.bar(mem_summary["mode"], mem_summary["rss_max_mb"])
    plt.ylabel("Peak RSS memory (MB)")
    plt.title("Peak Memory: Baseline vs CacheLink")
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "memory_peak_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    # -----------------------------
    # Memory time series comparison
    # -----------------------------
    plt.figure(figsize=(8, 4))
    plt.plot(baseline_mem["sec"], baseline_mem["rss_mb"], label="Baseline")
    plt.plot(cachelink_mem["sec"], cachelink_mem["rss_mb"], label="CacheLink")
    plt.xlabel("Time (s)")
    plt.ylabel("RSS memory (MB)")
    plt.title("Memory Usage Over Time")
    plt.legend()
    plt.grid(True, linewidth=0.3)
    plt.tight_layout()

    out = os.path.join(OUT_DIR, "memory_timeseries_comparison.png")
    plt.savefig(out, dpi=300)
    plt.close()
    generated.append(out)

    print("======================================")
    print("CPU Summary")
    print(cpu_summary.to_string(index=False))
    print("======================================")
    print("Memory Summary")
    print(mem_summary.to_string(index=False))
    print("======================================")
    print("Generated files:")
    for path in generated:
        print(path)
    print("======================================")


if __name__ == "__main__":
    main()