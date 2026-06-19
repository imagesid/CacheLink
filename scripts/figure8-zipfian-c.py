# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

# =========================
# Data (Zipfian Workload C)
# =========================
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
x = np.arange(len(policies))

read_avg = [1247.50, 906.26, 862.46, 853.64]

# =========================
# Style (paper)
# =========================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 5
})

fig, ax = plt.subplots(figsize=(1.7, 1.2))

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
output_file = "workload_c_zipfian.png"

plt.tight_layout()
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close()

print(f"Figure saved as: {output_file}")