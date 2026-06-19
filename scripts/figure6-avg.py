# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (REAL)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

# Average latency (us)
read_avg = [2167.48, 1634.50, 1699.79, 1541.50]
update_avg = [7265.36, 6881.39, 7083.31, 6835.53]

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
output_file = "latency_avg_bar.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")