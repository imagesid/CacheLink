# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Uniform Workload B)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

read_avg   = [3034.75, 2265.13, 1938.78, 1857.26]
update_avg = [8660.74, 7741.63, 7332.62, 7232.64]

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
# UPDATE
# =========================
axes[1].bar(x, update_avg, color='lightgray', edgecolor='black')
axes[1].set_title("Update Latency (Avg)")
axes[1].set_xticks(x)
axes[1].set_xticklabels(policies)

# =========================
# Save
# =========================
output_file = "workload_b_uniform.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")