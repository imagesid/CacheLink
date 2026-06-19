import os
import re
import matplotlib.pyplot as plt
import numpy as np

# ============================================
# Config
# ============================================
base_dir = "scripts/logs"

workloads = ["a", "b", "c", "d", "f"]
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]

# mapping to filenames
def get_file(workload, policy):
    if policy == "Baseline":
        return f"{base_dir}/baseline_workload{workload}-big.txt"
    else:
        return f"{base_dir}/cachelink_workload{workload}_{policy}-big.txt"


# ============================================
# Step 1: Parse ONE log file (READ only)
# ============================================
def parse_log(file):
    p50 = p95 = p99 = None

    with open(file, "r") as f:
        for line in f:
            # ONLY take READ lines
            if "[READ], 50thPercentileLatency" in line:
                p50 = float(line.split(",")[-1])
            elif "[READ], 95thPercentileLatency" in line:
                p95 = float(line.split(",")[-1])
            elif "[READ], 99thPercentileLatency" in line:
                p99 = float(line.split(",")[-1])

    return p50, p95, p99


# ============================================
# Step 2: Collect data
# ============================================
p50_data = {p: [] for p in policies}
p95_data = {p: [] for p in policies}
p99_data = {p: [] for p in policies}

for w in workloads:
    for p in policies:
        file = get_file(w, p)

        if not os.path.exists(file):
            print(f"Missing: {file}")
            p50_data[p].append(0)
            p95_data[p].append(0)
            p99_data[p].append(0)
            continue

        p50, p95, p99 = parse_log(file)

        p50_data[p].append(p50 if p50 else 0)
        p95_data[p].append(p95 if p95 else 0)
        p99_data[p].append(p99 if p99 else 0)


# ============================================
# Step 3: Plot
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8
})

fig, axes = plt.subplots(1, 3, figsize=(10, 3))

x = np.arange(len(workloads))
width = 0.18

colors = {
    "Baseline": "#000000",
    "LRU": "#555555",
    "LRU2Q": "#888888",
    "TinyLFU": "#BBBBBB"
}

# ---------- P50 ----------
for i, p in enumerate(policies):
    axes[0].bar(x + i*width, p50_data[p], width, color=colors[p])

axes[0].set_title("(a) P50")
axes[0].set_ylabel("Latency (us)")
axes[0].set_xticks(x + width*1.5)
axes[0].set_xticklabels([w.upper() for w in workloads])

# ---------- P95 ----------
for i, p in enumerate(policies):
    axes[1].bar(x + i*width, p95_data[p], width, color=colors[p])

axes[1].set_title("(b) P95")
axes[1].set_xticks(x + width*1.5)
axes[1].set_xticklabels([w.upper() for w in workloads])

# ---------- P99 ----------
for i, p in enumerate(policies):
    axes[2].bar(x + i*width, p99_data[p], width, color=colors[p])

axes[2].set_title("(c) P99")
axes[2].set_xticks(x + width*1.5)
axes[2].set_xticklabels([w.upper() for w in workloads])

# OPTIONAL (stronger visualization)
axes[2].set_yscale("log")  # <-- highly recommended

# ============================================
# Legend
# ============================================
handles = [plt.Rectangle((0,0),1,1,color=colors[p]) for p in policies]
fig.legend(handles, policies, loc="upper center", ncol=4, frameon=False)

# ============================================
# Label
# ============================================
fig.text(0.5, -0.05, base_dir, ha='center', fontsize=7)

# ============================================
# Clean style
# ============================================
for ax in axes:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout(rect=[0, 0.05, 1, 0.88])

output_file = "figure7_latency_from_logs.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.show()

print(f"Saved figure as: {output_file}")