# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Uniform Workload D)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

read_avg   = [3336.14, 2149.22, 1518.39, 1638.96]
insert_avg = [5374.12, 5182.17, 5226.11, 5309.93]

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
output_file = "workload_d_uniform.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")