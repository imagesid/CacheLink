import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

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
                buffer += line

        if buffer:
            rows.append(buffer)

    columns = [
        "mode","workload","policy",
        "runtime_ms","throughput_ops","read_ops",
        "avg_lat_us","min_lat_us","max_lat_us",
        "p50_us","p95_us","p99_us"
    ]

    data = []
    for r in rows:
        parts = r.split(",")
        if len(parts) >= 12:
            data.append(parts[:12])

    df = pd.DataFrame(data, columns=columns)

    # Convert numeric
    for col in columns[3:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


file_path = "scripts/figure6-big.csv"
df = load_clean_csv(file_path)

# ============================================
# Step 2: Normalize labels
# ============================================
# df["workload"] = df["workload"].str.replace("workloads/", "")
df["workload"] = (
    df["workload"]
    .str.replace("workloads/", "")
    .str.replace("workload", "")
    .str.upper()
)

df["policy"] = df.apply(
    lambda r: "Baseline" if r["mode"] == "baseline" else r["policy"],
    axis=1
)

policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
workloads = sorted(df["workload"].unique())

# ============================================
# Step 3: Prepare data
# ============================================
runtime = {p: [] for p in policies}
throughput = {p: [] for p in policies}

for w in workloads:
    sub = df[df["workload"] == w]
    for p in policies:
        row = sub[sub["policy"] == p]
        if not row.empty:
            runtime[p].append(row["runtime_ms"].values[0])
            throughput[p].append(row["throughput_ops"].values[0])
        else:
            runtime[p].append(0)
            throughput[p].append(0)

# ============================================
# Step 4: Plot
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3))

x = np.arange(len(workloads))
width = 0.18

# grayscale colors
colors = {
    "Baseline": "#000000",
    "LRU": "#555555",
    "LRU2Q": "#888888",
    "TinyLFU": "#BBBBBB"
}

# ---------- Runtime ----------
for i, p in enumerate(policies):
    ax1.bar(x + i*width, runtime[p], width, color=colors[p], label=p)

ax1.set_ylabel("Runtime (ms)")
ax1.set_xticks(x + width*1.5)
ax1.set_xticklabels(workloads)
ax1.set_title("(a) Runtime")

# ---------- Throughput ----------
for i, p in enumerate(policies):
    ax2.bar(x + i*width, throughput[p], width, color=colors[p], label=p)

ax2.set_ylabel("Throughput (ops/sec)")
ax2.set_xticks(x + width*1.5)
ax2.set_xticklabels(workloads)
ax2.set_title("(b) Throughput")

# ============================================
# Shared legend
# ============================================
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)

# ============================================
# Add filename (important for experiments)
# ============================================
# fig.text(0.5, -0.05, file_path, ha='center', fontsize=7)

# ============================================
# Clean style
# ============================================
for ax in [ax1, ax2]:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout(rect=[0, 0.05, 1, 0.9])
plt.savefig("figure6_subfig.png", dpi=300, bbox_inches='tight')
plt.show()
print("figure6_subfig.png")