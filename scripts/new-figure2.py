# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import io
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.ticker import StrMethodFormatter
from matplotlib.ticker import FuncFormatter


data = """mode,latency_us,qps,seconds,operations,mbps
baseline_figure2,10118.188,98,303.536,29999,0.4
rocksdb-sec,4002.519,249,300.185,74999,1.0
sas_cache_nvme,8768.141,114,306.876,34999,0.4
cachelink_hdd_LRU_1.0.device,7506.200,133,300.241,39999,0.5
cachelink_workspace_ssd_LRU_1.0.device,4955.297,201,302.268,60999,0.8
cachelink_ssd_LRU_1.0.device,4733.032,211,302.909,63999,0.8
cachelink_nvme_LRU_1.0.device,4667.745,214,303.399,64999,0.8
"""



df = pd.read_csv(io.StringIO(data))

# ============================================
# MDPI formatter
# 10000 -> 10,000
# 4000  -> 4000
# ============================================
def mdpi_number(x, pos=None):
    x = int(round(float(x)))
    return f"{x:,}" if abs(x) >= 10000 else f"{x}"

# ============================================
# LABELS
# ============================================
label_map = {
    "baseline_figure2": "baseline",
    "rocksdb-sec": "RAM-sec",
    "sas_cache_nvme": "SAS-Cache",
    "cachelink_hdd_LRU_1.0.device": "HDD",
    "cachelink_workspace_ssd_LRU_1.0.device": "SATA1",
    "cachelink_ssd_LRU_1.0.device": "SATA2",
    "cachelink_nvme_LRU_1.0.device": "NVMe",
}

df["label"] = df["mode"].map(label_map)

# Safety check for missing labels
if df["label"].isna().any():
    print("Missing label mapping for:")
    print(df[df["label"].isna()]["mode"].tolist())
    df = df.dropna(subset=["label"])

order = ["baseline", "RAM-sec", "SAS-Cache", "HDD", "SATA1", "SATA2", "NVMe"]
df["label"] = pd.Categorical(df["label"], categories=order, ordered=True)
df = df.sort_values("label")

# ============================================
# STYLE
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "figure.dpi": 300,
    "axes.linewidth": 0.8,
})

# Increased height for vertical x-labels
fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.85))

colors = [
    "#222222",
    "#dddddd",
    "#555555",
    "#777777",
    "#999999",
    "#bbbbbb",
    "#eeeeee",
]

hatches = [
    "",
    "//",
    "\\\\",
    "xx",
    "..",
    "--",
    "++",
]

# ============================================
# Helper function
# ============================================
def draw_bar(ax, metric, ylabel, title, value_format):
    bars = ax.bar(
        df["label"].astype(str),
        df[metric],
        color=colors[:len(df)],
        edgecolor="black",
        linewidth=0.5,
        width=0.72,
    )

    for bar, hatch in zip(bars, hatches[:len(df)]):
        bar.set_hatch(hatch)

    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(FuncFormatter(mdpi_number))
    ax.set_title(title, fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Vertical x-axis labels
    ax.tick_params(axis="x", labelsize=7, rotation=90)
    ax.tick_params(axis="y", labelsize=7)

    for label in ax.get_xticklabels():
        label.set_ha("center")
        label.set_va("top")

    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)

    ymax = df[metric].max()
    ax.set_ylim(0, ymax * 1.18)

    # Value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + ymax * 0.025,
            mdpi_number(height),
            ha="center",
            va="bottom",
            fontsize=6.5,
        )


# # ============================================
# # Latency
# # ============================================
# draw_bar(
#     axes[0],
#     metric="latency_us",
#     ylabel="Latency (μs)",
#     title="Latency",
#     value_format="{:.0f}",
# )

# # ============================================
# # Throughput
# # ============================================
# draw_bar(
#     axes[1],
#     metric="qps",
#     ylabel="Throughput (QPS)",
#     title="Throughput",
#     value_format="{:.0f}",
# )

# ============================================
# Latency
# ============================================
draw_bar(
    axes[0],
    metric="latency_us",
    ylabel="Latency (μs)",
    title="Latency",
    value_format="{:,.0f}",
)

# ============================================
# Throughput
# ============================================
draw_bar(
    axes[1],
    metric="qps",
    ylabel="Throughput (QPS)",
    title="Throughput",
    value_format="{:,.0f}",
)

plt.tight_layout(w_pad=1.4)

filename = "new-figure2.png"
plt.savefig(filename, bbox_inches="tight", dpi=300)
# plt.savefig("cachelink_baseline_comparison.pdf", bbox_inches="tight")

print("Saved:", filename)