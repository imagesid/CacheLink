# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (UPDATED Workload F)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

# Avg latency (us) - UPDATED
read_avg   = [2319.66, 1641.30, 1695.89, 1517.44]
rmw_avg    = [7564.97, 6938.61, 7240.62, 6908.73]
update_avg = [5239.80, 5294.70, 5546.46, 5379.27]

# =========================
# Style (same as yours)
# =========================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 5
})

# 3 plots instead of 2
fig, axes = plt.subplots(1, 3, figsize=(4.8, 1.2))

# =========================
# READ
# =========================
axes[0].bar(x, read_avg, color='lightgray', edgecolor='black')
axes[0].set_title("Read Latency (Avg)")
axes[0].set_xticks(x)
axes[0].set_xticklabels(policies)
axes[0].set_ylabel("Latency (µs)")

# =========================
# RMW
# =========================
axes[1].bar(x, rmw_avg, color='lightgray', edgecolor='black')
axes[1].set_title("RMW Latency (Avg)")
axes[1].set_xticks(x)
axes[1].set_xticklabels(policies)

# =========================
# UPDATE
# =========================
axes[2].bar(x, update_avg, color='lightgray', edgecolor='black')
axes[2].set_title("Update Latency (Avg)")
axes[2].set_xticks(x)
axes[2].set_xticklabels(policies)

# =========================
# Save
# =========================
output_file = "workload_f_3box.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")