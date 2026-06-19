# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Workload C - REAL)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

read_avg = [1395.11, 1034.13, 995.73, 981.28]

x = np.arange(len(policies))

# =========================
# Style (paper)
# =========================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 5
})

fig, ax = plt.subplots(1, 1, figsize=(1.7, 1.2))

# =========================
# READ ONLY
# =========================
ax.bar(x, read_avg, color='lightgray', edgecolor='black')

ax.set_title("Read Latency (Avg)")
ax.set_xticks(x)
ax.set_xticklabels(policies)
ax.set_ylabel("Latency (µs)")

# =========================
# Save
# =========================
output_file = "workload_c_read_avg_bar.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")