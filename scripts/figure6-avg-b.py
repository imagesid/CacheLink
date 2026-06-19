# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (REAL - Workload B)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

# Average latency (us)
read_avg = [2260.68, 1245.96, 1148.11, 1118.53]
update_avg = [7383.22, 6427.20, 6320.78, 6329.13]

x = np.arange(len(policies))

# =========================
# Style (paper)
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
# UPDATE
# =========================
axes[1].bar(x, update_avg, color='lightgray', edgecolor='black')

axes[1].set_title("Update Latency (Avg)")
axes[1].set_xticks(x)
axes[1].set_xticklabels(policies)

# =========================
# Save
# =========================
output_file = "workload_b_latency_avg_bar.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")