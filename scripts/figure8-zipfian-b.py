# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Zipfian Workload B)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

read_avg   = [1847.75, 1418.67, 1289.02, 1211.59]
update_avg = [7146.00, 6708.32, 6631.56, 6554.75]

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
output_file = "workload_b_zipfian.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")