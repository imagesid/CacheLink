# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import io
import re
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.ticker import StrMethodFormatter

from matplotlib.ticker import FuncFormatter


# =========================
# MDPI formatter
# 10000 -> 10,000
# 4000  -> 4000
# =========================
def mdpi_number(x, pos=None):
    x = int(round(float(x)))
    return f"{x:,}" if abs(x) >= 10000 else f"{x}"


data = """mode,latency_us,qps,seconds,operations,mbps
baseline_figure4_33554432,10082.699,99,302.471,29999,0.4
cachelink_nvmec_TinyLFU_1.0.8388608,4022.325,248,301.670,74999,1.0
cachelink_nvmec_TinyLFU_1.0.16777216,4061.649,246,300.558,73999,1.0
cachelink_nvmec_TinyLFU_1.0.33554432,4033.999,247,302.546,74999,1.0
cachelink_nvmec_TinyLFU_1.0.67108864,4001.437,249,300.104,74999,1.0
"""


df = pd.read_csv(io.StringIO(data))

# =========================
# PARSE
# =========================
rows = []
for _, row in df.iterrows():
    mode = row["mode"]
    size = int(re.findall(r'\d+', mode)[-1])
    t = "Baseline" if "baseline" in mode else "CacheLink"

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
sizes = [8388608, 16777216, 33554432, 67108864]
labels = ["baseline", "8MB", "16MB", "32MB", "64MB"]

baseline = df2[df2["type"] == "Baseline"].iloc[0]

qps_vals = [baseline["qps"]]
lat_vals = [baseline["latency"]]

for s in sizes:
    row = df2[(df2["type"] == "CacheLink") & (df2["size"] == s)].iloc[0]
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

        label = mdpi_number(yi) if fmt == "mdpi" else fmt.format(yi)

        ax.text(xi, y_text, label,
                ha='center', va=va, fontsize=fontsize)
# =========================
# PLOT
# =========================
plt.rcParams.update({
    "font.size": 8,
    "figure.dpi": 300,
})

fig, ax1 = plt.subplots(figsize=(4, 2.0))
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

# ✔ horizontal padding
ax1.set_xlim(-0.3, len(labels) - 1 + 0.3)

ax1.set_ylabel("QPS")
ax2.set_ylabel("Latency (µs)")

# Add thousands comma to both left and right y-axes 

ax1.yaxis.set_major_formatter(FuncFormatter(mdpi_number))
ax2.yaxis.set_major_formatter(FuncFormatter(mdpi_number))

# ✔ automatic scaling
ax1.set_ylim(qps_low, qps_high)
ax2.set_ylim(lat_low, lat_high)

ax1.grid(axis="y", linestyle="--", alpha=0.3)

# =========================
# ANNOTATIONS
# =========================
# annotate_inside(ax1, x, qps_vals, fmt="{:.0f}", fontsize=7)
# annotate_inside(ax2, x, lat_vals, fmt="{:.0f}", fontsize=6)
annotate_inside(ax1, x, qps_vals, fmt="mdpi", fontsize=7)
annotate_inside(ax2, x, lat_vals, fmt="mdpi", fontsize=6)
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
filename = "new-figure4.png"
plt.savefig(filename, bbox_inches="tight")

print("Saved:", filename)