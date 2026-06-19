# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import io
import pandas as pd
import matplotlib.pyplot as plt

data = """mode,latency_us,qps,seconds,operations,mbps
baseline_no_secondary_cache,12790.353,78,306.956,23999,0.3
cachelink_hdd_LRU_1.0.device,11287.720,88,304.757,26999,0.3
cachelink_ssd1_LRU_1.0.device,7296.737,137,306.456,41999,0.5
cachelink_ssd2_LRU_1.0.device,7013.872,142,301.590,42999,0.6
cachelink_nvme_LRU_1.0.device,6880.791,145,302.748,43999,0.6"""

data = """mode,latency_us,qps,seconds,operations,mbps
baseline_no_secondary_cache,132379.190,7,397.005,2999,0.0
cachelink_hdd_LRU_1.0.device,81878.883,12,327.434,3999,0.0
cachelink_ssd1_LRU_1.0.device,6023.649,166,301.176,49999,0.7
cachelink_ssd2_LRU_1.0.device,4703.984,212,301.050,63999,0.8
cachelink_nvme_LRU_1.0.device,4651.418,214,302.338,64999,0.8"""

data = """mode,latency_us,qps,seconds,operations,mbps
baseline_no_secondary_cache,10118.188,98,303.536,29999,0.4
cachelink_hdd_LRU_1.0.device,7506.200,133,300.241,39999,0.5
cachelink_ssd1_LRU_1.0.device,4955.297,201,302.268,60999,0.8
cachelink_ssd2_LRU_1.0.device,4733.032,211,302.909,63999,0.8
cachelink_nvme_LRU_1.0.device,4667.745,214,303.399,64999,0.8
"""

df = pd.read_csv(io.StringIO(data))

# ============================================
# LABELS
# ============================================
label_map = {
    "baseline_no_secondary_cache": "Baseline",
    "cachelink_hdd_LRU_1.0.device": "HDD",
    "cachelink_ssd1_LRU_1.0.device": "SATA1",
    "cachelink_ssd2_LRU_1.0.device": "SATA2",
    "cachelink_nvme_LRU_1.0.device": "NVMe",
}
df["label"] = df["mode"].map(label_map)

order = ["Baseline", "HDD", "SATA1", "SATA2", "NVMe"]
df["label"] = pd.Categorical(df["label"], categories=order, ordered=True)
df = df.sort_values("label")

# ============================================
# STYLE (match your main figure)
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "figure.dpi": 300,
})

fig, axes = plt.subplots(1, 2, figsize=(6, 2.5))

# grayscale colors (same style as your latency figure)
colors = ["#000000", "#555555", "#888888", "#AAAAAA", "#CCCCCC"]

# ============================================
# Latency
# ============================================
axes[0].bar(df["label"], df["latency_us"],
            color=colors)

axes[0].set_ylabel("Latency (μs)")
axes[0].set_title("Latency")

# ============================================
# QPS
# ============================================
axes[1].bar(df["label"], df["qps"],
            color=colors)

axes[1].set_ylabel("QPS")
axes[1].set_title("Throughput")

# ============================================
# CLEAN STYLE
# ============================================
for ax in axes:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout()

filename = "paper_latency_qps_clean.png"
plt.savefig(filename, bbox_inches="tight")

print("Saved:", filename)