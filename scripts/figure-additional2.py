# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

# Data from fixed-request experiment: 1M read requests
modes = ["No-sec", "CacheLink-NVMe"]

block_hit = np.array([502540, 3438971])
block_miss = np.array([3990465, 1054034])
secondary_hits = np.array([0, 2936431])
operations = np.array([1000000, 1000000])

block_hit_rate = block_hit / (block_hit + block_miss) * 100
misses_per_op = block_miss / operations
secondary_hits_per_op = secondary_hits / operations

x = np.arange(len(modes))
width = 0.22

fig, ax1 = plt.subplots(figsize=(7.2, 3.6))

b1 = ax1.bar(x - width, block_hit_rate, width, label="Block-cache hit rate (%)")
ax1.set_ylabel("Block-cache hit rate (%)")
ax1.set_ylim(0, 100)

ax2 = ax1.twinx()
b2 = ax2.bar(x, misses_per_op, width, label="Block misses / request")
b3 = ax2.bar(x + width, secondary_hits_per_op, width, label="Secondary hits / request")
ax2.set_ylabel("Events per request")
ax2.set_ylim(0, 4.5)

ax1.set_xticks(x)
ax1.set_xticklabels(modes)
ax1.set_xlabel("Configuration")

# Value labels
for bar in b1:
    h = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, h + 2, f"{h:.1f}%",
             ha="center", va="bottom", fontsize=9)

for bars in [b2, b3]:
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.08, f"{h:.2f}",
                 ha="center", va="bottom", fontsize=9)

# Combined legend
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(handles1 + handles2, labels1 + labels2,
           loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=3, frameon=False)

ax1.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
# plt.savefig("cachelink_mechanism.pdf", bbox_inches="tight")
plt.savefig("cachelink_mechanism.png", dpi=300, bbox_inches="tight")
print("cachelink_mechanism.png")