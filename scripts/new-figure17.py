# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =========================
# LOAD CSV
# =========================
df = pd.read_csv("scripts/figure10-big.csv")

df = df[df["threads"].notna()]
df = df[df["throughput_ops"].notna()]
df = df[df["avg_lat_us"].notna()]

threads = sorted(df["threads"].unique())
policies = ["none", "LRU", "LRU2Q", "TinyLFU"]
labels = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

# =========================
# MDPI formatter
# 10000 -> 10,000
# 4000  -> 4000
# =========================
def mdpi_label(x):
    x = int(round(float(x)))
    return f"{x:,}" if abs(x) >= 10000 else f"{x}"

def force_mdpi_y_ticks(ax):
    ticks = ax.get_yticks()
    ax.set_yticks(ticks)
    ax.set_yticklabels([mdpi_label(t) for t in ticks])

# =========================
# ORGANIZE DATA
# =========================
qps_data = {}
lat_data = {}

for p in policies:
    sub = df[df["policy"] == p].sort_values("threads")
    qps_data[p] = sub["throughput_ops"].values
    lat_data[p] = sub["avg_lat_us"].values

policy_list = ["LRU", "LRU2Q", "TinyLFU"]

# =========================
# AUTO LIMIT FUNCTION
# =========================
def get_padded_limits(values, pad_ratio=0.12):
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax != vmin else max(abs(vmax), 1)
    pad = vrange * pad_ratio
    return vmin - pad, vmax + pad

all_qps = sum([list(qps_data[p]) for p in policies], [])
all_lat = sum([list(lat_data[p]) for p in policies], [])

qps_low, qps_high = get_padded_limits(all_qps)
lat_low, lat_high = get_padded_limits(all_lat)
lat_low = 0
# =========================
# STYLE
# =========================
styles = {
    "none":    dict(marker='o', linestyle='-',  linewidth=1.5),
    "LRU":     dict(marker='s', linestyle='--', linewidth=1.5),
    "LRU2Q":   dict(marker='^', linestyle='-.', linewidth=1.5),
    "TinyLFU": dict(marker='D', linestyle=':',  linewidth=1.5),
}

colors = ["#bbbbbb", "#888888", "#444444"]

plt.rcParams.update({
    "font.size": 7,
    "figure.dpi": 300,
})

# =========================
# FIGURE (2x2)
# =========================
fig, axes = plt.subplots(2, 2, figsize=(5.5, 3.8))
x = list(range(len(threads)))
thread_labels = [mdpi_label(t) for t in threads]

# =========================
# ROW 1 — LINE PLOTS
# =========================
# Throughput
ax = axes[0, 0]
line_handles = []

for p, label in zip(policies, labels):
    line, = ax.plot(x, qps_data[p], color="black", label=label, **styles[p])
    line_handles.append(line)

ax.set_title("Throughput (Full)")
ax.set_xticks(x)
ax.set_xticklabels(thread_labels)
ax.set_xlim(-0.3, len(x) - 1 + 0.3)
ax.set_ylabel("Ops/sec")
ax.set_ylim(qps_low, qps_high)
ax.grid(axis="y", linestyle="--", alpha=0.3)

# Latency
ax = axes[0, 1]

for p in policies:
    ax.plot(x, lat_data[p], color="black", **styles[p])

ax.set_title("Latency (Full)")
ax.set_xticks(x)
ax.set_xticklabels(thread_labels)
ax.set_xlim(-0.3, len(x) - 1 + 0.3)
ax.set_ylabel("Latency (µs)")
ax.set_ylim(lat_low, lat_high)
ax.grid(axis="y", linestyle="--", alpha=0.3)

# =========================
# ROW 2 — BAR CHARTS
# =========================
bar_width = 0.22
offsets = [-bar_width, 0, bar_width]

# -------- Throughput (Policy) --------
ax = axes[1, 0]
bar_handles = []

for i, p in enumerate(policy_list):
    vals = qps_data[p]
    bars = ax.bar(
        np.array(x) + offsets[i],
        vals,
        width=bar_width,
        color=colors[i],
        edgecolor="black",
        label=p
    )

    bar_handles.append(bars[0])

    for xi, yi in zip(np.array(x) + offsets[i], vals):
        ax.text(
            xi,
            yi * 0.5,
            mdpi_label(yi),
            ha="center",
            va="center",
            rotation=90,
            fontsize=6
        )

ax.set_title("Throughput (Policy)")
ax.set_xticks(x)
ax.set_xticklabels(thread_labels)
ax.set_xlim(-0.3, len(x) - 1 + 0.3)
ax.set_xlabel("Threads")
ax.set_ylabel("Ops/sec")
ax.grid(axis="y", linestyle="--", alpha=0.3)

# -------- Latency (Policy) --------
ax = axes[1, 1]

for i, p in enumerate(policy_list):
    vals = lat_data[p]
    ax.bar(
        np.array(x) + offsets[i],
        vals,
        width=bar_width,
        color=colors[i],
        edgecolor="black"
    )

    for xi, yi in zip(np.array(x) + offsets[i], vals):
        ax.text(
            xi,
            yi * 0.5,
            mdpi_label(yi),
            ha="center",
            va="center",
            rotation=90,
            fontsize=6
        )

ax.set_title("Latency (Policy)")
ax.set_xticks(x)
ax.set_xticklabels(thread_labels)
ax.set_xlim(-0.3, len(x) - 1 + 0.3)
ax.set_xlabel("Threads")
ax.set_ylabel("Latency (µs)")
ax.grid(axis="y", linestyle="--", alpha=0.3)

# =========================
# LEGENDS
# =========================
fig.legend(
    line_handles,
    labels,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.05),
    ncol=4,
    frameon=True
)

axes[1, 0].legend(
    bar_handles,
    ["LRU", "LRU2Q", "TinyLFU"],
    loc="upper left",
    fontsize=6,
    frameon=True
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.22)

# =========================
# FORCE THOUSAND SEPARATORS AFTER LAYOUT
# =========================
for ax in axes.ravel():
    force_mdpi_y_ticks(ax)

# =========================
# SAVE
# Use a new filename to avoid Overleaf/image cache issue
# =========================
filename = "figure_threads_2x2_bar_final_commas.png"
plt.savefig(filename, bbox_inches="tight", dpi=300)

print("Saved:", filename)
