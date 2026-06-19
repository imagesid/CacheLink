# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Data
# -----------------------------
labels = ["baseline", "256MB", "512MB", "1GB", "2GB"]

block_miss = np.array([119602, 98497, 97176, 95728, 94035], dtype=float)
block_hit = np.array([15015, 211273, 226029, 240960, 242653], dtype=float)
secondary_hit = np.array([0, 176552, 189763, 203246, 204939], dtype=float)

# -----------------------------
# Rates
# -----------------------------
total_cache_interface_access = block_hit + block_miss

primary_only_hit_rate = (block_hit - secondary_hit) / total_cache_interface_access * 100.0
secondary_hit_rate = secondary_hit / total_cache_interface_access * 100.0
remaining_miss_rate = block_miss / total_cache_interface_access * 100.0

# -----------------------------
# Plot
# -----------------------------
x = np.arange(len(labels))
width = 0.34

fig, ax = plt.subplots(figsize=(5.2, 2))

bars1 = ax.bar(
    x - width / 2,
    primary_only_hit_rate,
    width,
    label="Block cache hit rate",
    color="0.25",
    edgecolor="black",
    linewidth=0.6,
)

bars2 = ax.bar(
    x + width / 2,
    secondary_hit_rate,
    width,
    label="Secondary cache hit rate",
    color="0.70",
    edgecolor="black",
    linewidth=0.6,
    hatch="//",
)

ax.set_ylabel("Rate (%)", fontsize=9)
ax.set_xlabel("Secondary cache size", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.tick_params(axis="y", labelsize=8)
ax.set_ylim(0, 65)

ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.45)
ax.set_axisbelow(True)

ax.legend(
    fontsize=7.5,
    frameon=False,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.20),
    ncol=2,
)

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 1.0,
            f"{h:.1f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_linewidth(0.8)
ax.spines["bottom"].set_linewidth(0.8)

plt.tight_layout(pad=0.4)

output_pdf = "cachelink_primary_secondary_hit_rate.pdf"
output_png = "cachelink_primary_secondary_hit_rate.png"

plt.savefig(output_pdf, bbox_inches="tight")
plt.savefig(output_png, dpi=300, bbox_inches="tight")

print(output_pdf)
print(output_png)

# Optional: print values for checking
for i, label in enumerate(labels):
    print(
        f"{label}: primary={primary_only_hit_rate[i]:.2f}%, "
        f"secondary={secondary_hit_rate[i]:.2f}%, "
        f"miss={remaining_miss_rate[i]:.2f}%"
    )