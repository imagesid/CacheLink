# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import io
import re
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# INPUT DATA
# =========================
data = """mode,latency_us,qps,seconds,operations,mbps
baseline_nvme_33554432,160142.999,6,320.126,1999,0.0
cachelink_nvme_TinyLFU_1.0.33554432.268435456,87091.353,11,348.278,3999,0.0
cachelink_nvme_TinyLFU_1.0.33554432.536870912,9475.000,105,303.191,31999,0.4
cachelink_nvme_TinyLFU_1.0.33554432.1073741824,4249.197,235,301.689,70999,0.9
cachelink_nvme_TinyLFU_1.0.33554432.2147483648,4083.683,244,310.356,75999,1.0
"""

data = """mode,latency_us,qps,seconds,operations,mbps
baseline_nvme_33554432.268435456,10199.700,98,305.981,29999,0.4
cachelink_nvmeb_TinyLFU_1.0.33554432.268435456,4385.813,228,302.617,68999,0.9
cachelink_nvmeb_TinyLFU_1.0.33554432.536870912,4166.937,239,300.015,71999,0.9
cachelink_nvmeb_TinyLFU_1.0.33554432.1073741824,4018.306,248,301.369,74999,1.0
cachelink_nvmeb_TinyLFU_1.0.33554432.2147483648,4006.560,249,300.488,74999,1.0
"""

df = pd.read_csv(io.StringIO(data))

# =========================
# PARSE
# =========================
rows = []
for _, row in df.iterrows():
    mode = row["mode"]
    nums = re.findall(r'\d+', mode)

    if "baseline" in mode:
        size = 0
        t = "Baseline"
    else:
        size = int(nums[-1])
        t = "CacheLink"

    rows.append({
        "type": t,
        "size": size,
        "latency": row["latency_us"],
        "qps": row["qps"]
    })

df2 = pd.DataFrame(rows)

# =========================
# ORDER
# =========================
sizes = [268435456, 536870912, 1073741824, 2147483648]
labels = ["baseline", "256MB", "512MB", "1GB", "2GB"]

baseline = df2[df2["type"] == "Baseline"].iloc[0]

qps_vals = [baseline["qps"]]
lat_vals = [baseline["latency"]]

for s in sizes:
    row = df2[df2["size"] == s].iloc[0]
    qps_vals.append(row["qps"])
    lat_vals.append(row["latency"])

# =========================
# AUTO LIMIT FUNCTION
# =========================
def get_padded_limits(values, pad_ratio=0.12):
    vmin = min(values)
    vmax = max(values)
    vrange = vmax - vmin

    if vrange == 0:
        vrange = abs(vmax) if vmax != 0 else 1

    pad = vrange * pad_ratio
    return vmin - pad, vmax + pad

qps_low, qps_high = get_padded_limits(qps_vals)
lat_low, lat_high = get_padded_limits(lat_vals)

# =========================
# SMART ANNOTATION
# =========================
def annotate_inside(ax, x, y_vals, fmt="{:.0f}", fontsize=7):
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min

    for xi, yi in zip(x, y_vals):
        if yi > (y_min + y_range * 0.7):
            offset = -0.05 * y_range
            va = 'top'
        else:
            offset = 0.05 * y_range
            va = 'bottom'

        y_text = yi + offset
        y_text = max(y_min + 0.02 * y_range,
                     min(y_text, y_max - 0.02 * y_range))

        ax.text(xi, y_text, fmt.format(yi),
                ha='center', va=va, fontsize=fontsize)

# =========================
# PLOT
# =========================
plt.rcParams.update({
    "font.size": 8,
    "figure.dpi": 300,
})

fig, ax1 = plt.subplots(figsize=(4.2, 2.2))
ax2 = ax1.twinx()

x = list(range(len(labels)))

# QPS
line1, = ax1.plot(
    x, qps_vals,
    marker='o', linestyle='-',
    color='black', linewidth=1.8,
    label="QPS"
)

# Latency
line2, = ax2.plot(
    x, lat_vals,
    marker='s', linestyle='--',
    color='black', linewidth=1.8,
    label="Latency"
)

# =========================
# AXES
# =========================
ax1.set_xticks(x)
ax1.set_xticklabels(labels)

# ✔ horizontal padding (NEW)
ax1.set_xlim(-0.3, len(labels) - 1 + 0.3)

ax1.set_ylabel("QPS")
ax2.set_ylabel("Latency (us)")

ax1.set_ylim(qps_low, qps_high)
ax2.set_ylim(lat_low, lat_high)

ax1.grid(axis="y", linestyle="--", alpha=0.3)

# =========================
# ANNOTATIONS
# =========================
annotate_inside(ax1, x, qps_vals, fmt="{:.0f}", fontsize=7)
annotate_inside(ax2, x, lat_vals, fmt="{:.0f}", fontsize=6)

# =========================
# LEGEND
# =========================
fig.legend(
    [line1, line2],
    ["QPS", "Latency"],
    loc="lower center",
    ncol=2,
    frameon=True
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.25)

# =========================
# SAVE
# =========================
filename = "figure_secondary_cache_scaling.png"
plt.savefig(filename, bbox_inches="tight")

print("Saved:", filename)