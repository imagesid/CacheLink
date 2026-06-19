# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Data from 1M random-read experiment
# -----------------------------
labels = ["No-sec", "SAS-Cache", "CacheLink-NVMe"]

block_miss = np.array([3990465, 1114361, 1054034], dtype=float)
block_hit = np.array([502540, 3378644, 3438971], dtype=float)
secondary_hit = np.array([0, 2876528, 2936431], dtype=float)

# -----------------------------
# Rates
# -----------------------------
total_cache_interface_access = block_hit + block_miss

# Separate reported block.cache.hit into:
# primary-only hit + secondary-cache hit returned through adapter
primary_only_hit_rate = (
    (block_hit - secondary_hit) / total_cache_interface_access * 100.0
)

secondary_cache_hit_rate = (
    secondary_hit / total_cache_interface_access * 100.0
)

total_hit_rate = primary_only_hit_rate + secondary_cache_hit_rate

# -----------------------------
# Plot
# -----------------------------
x = np.arange(len(labels))
width = 0.50

fig, ax = plt.subplots(figsize=(4.6, 2.25))

bars1 = ax.bar(
    x,
    primary_only_hit_rate,
    width,
    label="Block cache hit rate",
    color="0.22",
    edgecolor="black",
    linewidth=0.6,
)

bars2 = ax.bar(
    x,
    secondary_cache_hit_rate,
    width,
    bottom=primary_only_hit_rate,
    label="Secondary cache hit rate",
    color="0.72",
    edgecolor="black",
    linewidth=0.6,
    hatch="//",
)

# -----------------------------
# Axis / style
# -----------------------------
ax.set_ylabel("Hit Rate (%)", fontsize=9)
# ax.set_xlabel("Configuration", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.tick_params(axis="y", labelsize=8)
ax.set_ylim(0, 80)

ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.45)
ax.set_axisbelow(True)

ax.legend(
    fontsize=7.5,
    frameon=False,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.20),
    ncol=2,
)

# -----------------------------
# Segment labels inside bars
# -----------------------------
for i in range(len(labels)):
    primary_val = primary_only_hit_rate[i]
    secondary_val = secondary_cache_hit_rate[i]
    total_val = total_hit_rate[i]

    # Primary block-cache segment label
    if primary_val >= 4:
        ax.text(
            x[i],
            primary_val / 2,
            f"{primary_val:.1f}",
            ha="center",
            va="center",
            fontsize=7.2,
            color="white",
            fontweight="bold",
        )
    else:
        ax.text(
            x[i],
            primary_val + 1.0,
            f"{primary_val:.1f}",
            ha="center",
            va="bottom",
            fontsize=7.2,
            color="black",
        )

    # Secondary-cache segment label
    if secondary_val > 0:
        if secondary_val >= 4:
            ax.text(
                x[i],
                primary_val + secondary_val / 2,
                f"{secondary_val:.1f}",
                ha="center",
                va="center",
                fontsize=7.2,
                color="black",
                fontweight="bold",
            )
        else:
            ax.text(
                x[i],
                total_val + 1.0,
                f"{secondary_val:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.2,
                color="black",
            )

    # Total hit rate above each bar
    ax.text(
        x[i],
        total_val + 1.5,
        f"{total_val:.1f}",
        ha="center",
        va="bottom",
        fontsize=7.4,
        color="black",
        fontweight="bold",
    )

# -----------------------------
# Clean frame
# -----------------------------
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_linewidth(0.8)
ax.spines["bottom"].set_linewidth(0.8)

plt.tight_layout(pad=0.45)

# -----------------------------
# Save
# -----------------------------
output_pdf = "cachelink_sascache_hit_rate_comparison.pdf"
output_png = "cachelink_sascache_hit_rate_comparison.png"

plt.savefig(output_pdf, bbox_inches="tight")
plt.savefig(output_png, dpi=300, bbox_inches="tight")

print(output_pdf)
print(output_png)

# Optional: print values for checking
for i, label in enumerate(labels):
    print(
        f"{label}: primary={primary_only_hit_rate[i]:.2f}%, "
        f"secondary={secondary_cache_hit_rate[i]:.2f}%, "
        f"total_hit={total_hit_rate[i]:.2f}%"
    )