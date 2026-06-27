import re
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.ticker import FuncFormatter

# ============================================
# MDPI formatter
# 10000 -> 10,000
# 4000  -> 4000
# ============================================
def mdpi_number(x, pos=None):
    x = int(round(float(x)))
    return f"{x:,}" if abs(x) >= 10000 else f"{x}"

# ============================================
# Global style (compact + clean)
# ============================================
plt.rcParams.update({
    # "font.family": "serif",
    "font.size": 5,
    "axes.labelsize": 5,
    "legend.fontsize": 5,
    "xtick.labelsize": 5,
    "ytick.labelsize": 5,
    "lines.linewidth": 0.7,
})

# ============================================
# Parse
# ============================================
def parse_file(filename):
    times, qps, latency = [], [], []

    pattern = re.compile(
        r"\(([\d.]+),([\d.]+)\) ops/second.*\(([\d.]+),([\d.]+)\) seconds"
    )

    with open(filename, "r") as f:
        for line in f:
            if "ops/second" not in line:
                continue

            m = pattern.search(line)
            if m:
                qps_val = float(m.group(2))
                time_val = float(m.group(4))
                lat_val = 1e6 / qps_val if qps_val > 0 else 0

                times.append(time_val)
                qps.append(qps_val)
                latency.append(lat_val)

    return times, qps, latency


# ============================================
# Helper: exactly 5 markers
# ============================================
def get_markevery(x, n_markers=5):
    if len(x) <= n_markers:
        return list(range(len(x)))
    return np.linspace(0, len(x) - 1, n_markers, dtype=int)


# ============================================
# Load
# ============================================
t_base, q_base, lat_base = parse_file("scripts/baseline_nvme_tsb.txt")
t_hdd, q_hdd, lat_hdd = parse_file("scripts/cachelink_hdd_TinyLFU_1.0_tsb.txt")
t_ssd1, q_ssd1, lat_ssd1 = parse_file("scripts/cachelink_ssd1_TinyLFU_1.0_tsb.txt")
t_ssd2, q_ssd2, lat_ssd2 = parse_file("scripts/cachelink_ssd2_TinyLFU_1.0_tsb.txt")
t_nvme, q_nvme, lat_nvme = parse_file("scripts/cachelink_nvme_TinyLFU_1.0_tsb.txt")


# ============================================
# Styles (clean + spaced)
# ============================================
styles = {
    "baseline": dict(color="0.4", linestyle="-",  marker="o"),
    "hdd":      dict(color="0.4", linestyle=(0, (5, 3)), marker="s"),
    "ssd1":     dict(color="0.55", linestyle="-.", marker="^"),
    "ssd2":     dict(color="0.7", linestyle=":", marker="D"),
    "nvme":     dict(color="0.0", linestyle=(0, (3, 2)), marker="x"),
}

marker_size = 2


# ============================================
# Plot
# ============================================
fig, (ax1, ax2) = plt.subplots(
    2, 1,
    figsize=(3.5, 1.0),
    sharex=True,
    gridspec_kw={"hspace": 0.12}
)

# ---------- QPS ----------
ax1.plot(t_base, q_base, label="baseline",
         markevery=get_markevery(t_base), markersize=marker_size,
         **styles["baseline"])
ax1.plot(t_hdd, q_hdd, label="HDD",
         markevery=get_markevery(t_hdd), markersize=marker_size,
         **styles["hdd"])
ax1.plot(t_ssd1, q_ssd1, label="SATA1",
         markevery=get_markevery(t_ssd1), markersize=marker_size,
         **styles["ssd1"])
ax1.plot(t_ssd2, q_ssd2, label="SATA2",
         markevery=get_markevery(t_ssd2), markersize=marker_size,
         **styles["ssd2"])
ax1.plot(t_nvme, q_nvme, label="NVMe",
         markevery=get_markevery(t_nvme), markersize=marker_size,
         **styles["nvme"])

ax1.set_ylabel("QPS")
ax1.yaxis.set_major_formatter(FuncFormatter(mdpi_number))
ax1.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)


# ---------- Latency ----------
ax2.plot(t_base, lat_base, label="baseline",
         markevery=get_markevery(t_base), markersize=marker_size,
         **styles["baseline"])
ax2.plot(t_hdd, lat_hdd, label="HDD",
         markevery=get_markevery(t_hdd), markersize=marker_size,
         **styles["hdd"])
ax2.plot(t_ssd1, lat_ssd1, label="SATA1",
         markevery=get_markevery(t_ssd1), markersize=marker_size,
         **styles["ssd1"])
ax2.plot(t_ssd2, lat_ssd2, label="SATA2",
         markevery=get_markevery(t_ssd2), markersize=marker_size,
         **styles["ssd2"])
ax2.plot(t_nvme, lat_nvme, label="NVMe",
         markevery=get_markevery(t_nvme), markersize=marker_size,
         **styles["nvme"])

ax2.set_xlabel("Time (s)")
ax2.xaxis.set_major_formatter(FuncFormatter(mdpi_number))

ax2.set_ylabel("Latency (µs)")
ax2.yaxis.set_major_formatter(FuncFormatter(mdpi_number))
ax2.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)


# ============================================
# Legend
# ============================================
handles, labels = ax2.get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc="lower center",
    ncol=5,
    frameon=False,
    columnspacing=0.8,
    handlelength=1.5,
    bbox_to_anchor=(0.5, -0.4)
)

plt.tight_layout(rect=[0, 0.10, 1, 1])


# ============================================
# Save
# ============================================
plt.savefig("timeseries_final_clean.png", dpi=300, bbox_inches="tight")

print("Generated: timeseries_final_clean.png")
