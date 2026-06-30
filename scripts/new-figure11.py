import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import StrMethodFormatter

# ============================================
# Step 1: Fix broken CSV rows
# ============================================
def load_clean_csv(file):
    rows = []
    with open(file, "r") as f:
        buffer = ""

        for line in f:
            line = line.strip()

            if line.startswith("mode,"):
                continue

            if line.startswith("baseline") or line.startswith("cachelink"):
                if buffer:
                    rows.append(buffer)
                buffer = line
            else:
                buffer += "," + line

        if buffer:
            rows.append(buffer)

    columns = [
        "mode", "workload", "policy", "distribution",
        "runtime_ms", "throughput_ops", "read_ops",
        "avg_lat_us", "min_lat_us", "max_lat_us",
        "p50_us", "p95_us", "p99_us"
    ]

    clean_rows = []

    for r in rows:
        parts = r.split(",")

        # fixed fields until max_lat_us
        base = parts[:10]
        tail = parts[10:]

        nums = []
        for t in tail:
            try:
                nums.append(float(t))
            except:
                continue

        # keep only READ p50/p95/p99
        if len(nums) >= 3:
            base.extend(nums[:3])
        else:
            base.extend([0, 0, 0])

        clean_rows.append(base)

    df = pd.DataFrame(clean_rows, columns=columns)

    for col in columns[4:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


file_path = "scripts/new-figure11.csv"
df = load_clean_csv(file_path)

# ============================================
# Step 2: Clean labels
# ============================================
df["workload"] = (
    df["workload"]
    .str.replace("workloads/", "", regex=False)
    .str.replace("workload", "", regex=False)
    .str.upper()
)

df["policy"] = df.apply(
    lambda r: "Baseline" if r["mode"] == "baseline" else r["policy"],
    axis=1
)

policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
workloads = sorted(df["workload"].unique())
distributions = ["uniform", "zipfian"]

# ============================================
# Step 3: Plot
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8
})

fig, axes = plt.subplots(2, 2, figsize=(8, 5))

x = np.arange(len(workloads))
width = 0.18

colors = {
    "Baseline": "#000000",
    "LRU": "#555555",
    "LRU2Q": "#888888",
    "TinyLFU": "#BBBBBB"
}

for col_idx, dist in enumerate(distributions):
    runtime = {p: [] for p in policies}
    throughput = {p: [] for p in policies}

    for w in workloads:
        sub = df[(df["workload"] == w) & (df["distribution"] == dist)]

        for p in policies:
            row = sub[sub["policy"] == p]
            if not row.empty:
                runtime[p].append(row["runtime_ms"].values[0])
                throughput[p].append(row["throughput_ops"].values[0])
            else:
                runtime[p].append(0)
                throughput[p].append(0)

    # Scale runtime to avoid Matplotlib showing "1e6"
    runtime_million = {
        p: [v / 1e6 for v in runtime[p]]
        for p in policies
    }

    # ---------- Top row: runtime ----------
    ax_rt = axes[0, col_idx]
    for i, p in enumerate(policies):
        ax_rt.bar(x + i * width, runtime_million[p], width, color=colors[p])

    ax_rt.set_xticks(x + width * 1.5)
    ax_rt.set_xticklabels(workloads)
    ax_rt.spines["top"].set_visible(False)
    ax_rt.spines["right"].set_visible(False)

    # Scientific notation in axis label, not as "1e6"
    ax_rt.set_ylabel(r"Runtime ($\times 10^6$ ms)")
    # ax_rt.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
    ax_rt.yaxis.get_offset_text().set_visible(False)

    if col_idx == 0:
        ax_rt.set_title("(a) Uniform")
    else:
        ax_rt.set_title("(b) Zipfian")

    # ---------- Bottom row: throughput ----------
    ax_tp = axes[1, col_idx]
    for i, p in enumerate(policies):
        ax_tp.bar(x + i * width, throughput[p], width, color=colors[p])

    ax_tp.set_xticks(x + width * 1.5)
    ax_tp.set_xticklabels(workloads)
    ax_tp.spines["top"].set_visible(False)
    ax_tp.spines["right"].set_visible(False)

    # Thousand comma separator for throughput axis
    ax_tp.set_ylabel("Throughput (ops/sec)")
    # ax_tp.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax_tp.yaxis.get_offset_text().set_visible(False)

    if col_idx == 0:
        ax_tp.set_title("(c) Uniform")
    else:
        ax_tp.set_title("(d) Zipfian")

# ============================================
# Legend
# ============================================
handles = [plt.Rectangle((0, 0), 1, 1, color=colors[p]) for p in policies]
fig.legend(handles, policies, loc="upper center", ncol=4, frameon=False)

# ============================================
# Layout
# ============================================
plt.tight_layout(rect=[0, 0.02, 1, 0.9])

output_file = "new-figure11.png"
plt.savefig(output_file, dpi=300, bbox_inches="tight")
plt.show()

print(output_file)