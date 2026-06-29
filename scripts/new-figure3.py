# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')

import io
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.ticker import StrMethodFormatter

from matplotlib.ticker import FuncFormatter


data = """mode,latency_us,qps,seconds,operations,mbps
baseline_figure3,10187.979,98,305.629,29999,0.4
cachelink_nvme_LRU_0.2,5663.573,176,300.164,52999,0.7
cachelink_nvme_LRU2Q_0.2,5823.688,171,302.826,51999,0.7
cachelink_nvme_TinyLFU_0.2,4632.972,215,301.139,64999,0.8
cachelink_nvme_LRU_0.5,5108.858,195,301.418,58999,0.8
cachelink_nvme_LRU2Q_0.5,5178.294,193,300.336,57999,0.8
cachelink_nvme_TinyLFU_0.5,4352.685,229,300.331,68999,0.9
cachelink_nvme_LRU_0.8,4737.454,211,303.192,63999,0.8
cachelink_nvme_LRU2Q_0.8,4798.846,208,302.323,62999,0.8
cachelink_nvme_TinyLFU_0.8,4123.604,242,301.019,72999,1.0
cachelink_nvme_LRU_1.0,4659.786,214,302.881,64999,0.8
cachelink_nvme_LRU2Q_1.0,4680.814,213,304.248,64999,0.8
cachelink_nvme_TinyLFU_1.0,4016.635,248,301.244,74999,1.0
"""

df = pd.read_csv(io.StringIO(data))



def mdpi_number(x, pos=None):
    x = int(round(float(x)))
    return f"{x:,}" if abs(x) >= 10000 else f"{x}"

# =========================
# PARSE
# =========================
rows = []
for _, row in df.iterrows():
    mode = row["mode"]
    if mode == "baseline_figure3":
        rows.append({
            "policy": "Baseline",
            "ratio": "baseline",
            "latency": row["latency_us"],
            "qps": row["qps"]
        })
    else:
        parts = mode.split("_")
        rows.append({
            "policy": parts[2],
            "ratio": parts[3],
            "latency": row["latency_us"],
            "qps": row["qps"]
        })

df2 = pd.DataFrame(rows)

ratios_order = ["baseline", "0.2", "0.5", "0.8", "1.0"]
policies = ["LRU", "LRU2Q", "TinyLFU"]

# =========================
# GLOBAL MIN/MAX (IMPORTANT FIX)
# =========================
global_qps_min = df2["qps"].min()
global_qps_max = df2["qps"].max()

global_lat_min = df2["latency"].min()
global_lat_max = df2["latency"].max()

plt.rcParams.update({
    "font.size": 8,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
})

fig, axes = plt.subplots(1, 3, figsize=(9.0, 2.8))

qps_handle = None
lat_handle = None

for i, policy in enumerate(policies):
    ax1 = axes[i]
    ax2 = ax1.twinx()
    
    
    # MDPI number style: comma only for five or more digits
    ax1.yaxis.set_major_formatter(FuncFormatter(mdpi_number))
    ax2.yaxis.set_major_formatter(FuncFormatter(mdpi_number))

    sub = df2[df2["policy"].isin([policy, "Baseline"])]

    qps_vals = []
    lat_vals = []

    for r in ratios_order:
        if r == "baseline":
            row = sub[sub["policy"] == "Baseline"].iloc[0]
        else:
            row = sub[(sub["policy"] == policy) & (sub["ratio"] == r)].iloc[0]

        qps_vals.append(row["qps"])
        lat_vals.append(row["latency"])

    x = list(range(len(ratios_order)))

    line1, = ax1.plot(
        x, qps_vals,
        color="black",
        linestyle="-",
        marker="o",
        linewidth=1.6,
        markersize=5,
        label="QPS"
    )

    line2, = ax2.plot(
        x, lat_vals,
        color="black",
        linestyle="--",
        marker="s",
        linewidth=1.6,
        markersize=5,
        label="Latency"
    )

    if qps_handle is None:
        qps_handle = line1
    if lat_handle is None:
        lat_handle = line2

    ax1.set_title(policy)
    ax1.set_xticks(x)
    ax1.set_xticklabels(ratios_order)

    # =========================
    # UPDATED LIMITS (KEY CHANGE)
    # =========================
    ax1.set_ylim(global_qps_min * 0.95, global_qps_max * 1.05)
    ax2.set_ylim(global_lat_min * 0.95, global_lat_max * 1.05)

    ax1.grid(axis="y", linestyle="--", linewidth=0.8, alpha=0.35)

    if i == 0:
        ax1.set_ylabel("QPS")
    else:
        ax1.set_ylabel("")

    if i == len(policies) - 1:
        ax2.set_ylabel("Latency (µs)")
    else:
        ax2.set_ylabel("")

# =========================
# LEGEND
# =========================
fig.legend(
    [qps_handle, lat_handle],
    ["QPS", "Latency"],
    loc="lower center",
    ncol=2,
    frameon=True,
    bbox_to_anchor=(0.5, -0.02)
)

plt.tight_layout(rect=[0, 0.10, 1, 1])

filename = "new-figure3.png"
plt.savefig(filename, bbox_inches="tight")

print("Saved:", filename)