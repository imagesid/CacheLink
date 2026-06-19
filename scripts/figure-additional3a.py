# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Data
# -----------------------------
labels = ["No-sec", "256MB", "512MB", "1GB", "2GB"]

block_miss = np.array([119602, 98497, 97176, 95728, 94035], dtype=float)
block_hit = np.array([15015, 211273, 226029, 240960, 242653], dtype=float)
secondary_hit = np.array([0, 176552, 189763, 203246, 204939], dtype=float)

# -----------------------------
# Rates
# -----------------------------
total_cache_interface_access = block_hit + block_miss

block_cache_hit_rate = (
    (block_hit - secondary_hit) / total_cache_interface_access * 100.0
)
secondary_cache_hit_rate = (
    secondary_hit / total_cache_interface_access * 100.0
)
total_hit_rate = block_cache_hit_rate + secondary_cache_hit_rate

# -----------------------------
# Plot
# -----------------------------
x = np.arange(len(labels))
width = 0.56

fig, ax = plt.subplots(figsize=(5.2, 2.25))

bars1 = ax.bar(
    x,
    block_cache_hit_rate,
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
    bottom=block_cache_hit_rate,
    label="Secondary cache hit rate",
    color="0.72",
    edgecolor="black",
    linewidth=0.6,
    hatch="//",
)

# -----------------------------
# Axis / style
# -----------------------------
ax.set_ylabel("Rate (%)", fontsize=9)
ax.set_xlabel("Secondary cache size", fontsize=9)
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
    block_val = block_cache_hit_rate[i]
    sec_val = secondary_cache_hit_rate[i]
    total_val = total_hit_rate[i]

    # Block-cache segment label
    if block_val >= 4:
        ax.text(
            x[i],
            block_val / 2,
            f"{block_val:.1f}",
            ha="center",
            va="center",
            fontsize=7.2,
            color="white",
            fontweight="bold",
        )
    else:
        ax.text(
            x[i],
            block_val + 1.0,
            f"{block_val:.1f}",
            ha="center",
            va="bottom",
            fontsize=7.2,
            color="black",
        )

    # Secondary-cache segment label
    # Secondary-cache segment label
    if sec_val > 0:
        if sec_val >= 4:
            ax.text(
                x[i],
                block_val + sec_val / 2,
                f"{sec_val:.1f}",
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
                f"{sec_val:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.2,
                color="black",
            )

    # Total hit rate label above bar
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
output_pdf = "cachelink_primary_secondary_hit_rate_stacked.pdf"
output_png = "cachelink_primary_secondary_hit_rate_stacked.png"

plt.savefig(output_pdf, bbox_inches="tight")
plt.savefig(output_png, dpi=300, bbox_inches="tight")

print(output_pdf)
print(output_png)

# Optional: print values for checking
for i, label in enumerate(labels):
    print(
        f"{label}: block={block_cache_hit_rate[i]:.2f}%, "
        f"secondary={secondary_cache_hit_rate[i]:.2f}%, "
        f"total_hit={total_hit_rate[i]:.2f}%"
    )