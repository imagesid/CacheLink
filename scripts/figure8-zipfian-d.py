# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Zipfian Workload D)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

read_avg   = [2669.98, 1418.20, 1020.58, 1092.39]
insert_avg = [5345.06, 5309.72, 5348.80, 5255.65]

# =========================
# Style
# =========================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 5
})

fig, axes = plt.subplots(1, 2, figsize=(3.2, 1.2))

# =========================
# READ
# =========================
axes[0].bar(x, read_avg, color='lightgray', edgecolor='black')
axes[0].set_title("Read Latency (Avg)")
axes[0].set_xticks(x)
axes[0].set_xticklabels(policies)
axes[0].set_ylabel("Latency (µs)")

# =========================
# INSERT
# =========================
axes[1].bar(x, insert_avg, color='lightgray', edgecolor='black')
axes[1].set_title("Insert Latency (Avg)")
axes[1].set_xticks(x)
axes[1].set_xticklabels(policies)

# =========================
# Save
# =========================
output_file = "workload_d_zipfian.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")