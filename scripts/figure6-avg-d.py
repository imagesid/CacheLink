# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Workload D - REAL)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

read_avg = [971.42, 674.89, 652.97, 698.10]
insert_avg = [5156.95, 5184.77, 5190.69, 5134.73]

x = np.arange(len(policies))

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
output_file = "workload_d_read_insert_avg_bar.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")