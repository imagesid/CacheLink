import os
import matplotlib.pyplot as plt
import numpy as np

# ============================================
# Config
# ============================================
base_dir = "scripts/logs"

workloads = ["b", "c", "d"]
policies = ["Baseline", "LRU", "LRU2Q", "TinyLFU"]
distributions = ["uniform", "zipfian"]

# ============================================
# Mapping filenames (NEW FORMAT)
# ============================================
def get_file(workload, policy, dist):
    if policy == "Baseline":
        return f"{base_dir}/baseline_workload{workload}_{dist}-big.txt"
    else:
        return f"{base_dir}/cachelink_workload{workload}_{policy}_{dist}-big.txt"


# ============================================
# Parse log (READ only)
# ============================================
def parse_log(file):
    p50 = p95 = p99 = None

    with open(file, "r") as f:
        for line in f:
            if "[READ], 50thPercentileLatency" in line:
                p50 = float(line.split(",")[-1])
            elif "[READ], 95thPercentileLatency" in line:
                p95 = float(line.split(",")[-1])
            elif "[READ], 99thPercentileLatency" in line:
                p99 = float(line.split(",")[-1])

    return p50, p95, p99


# ============================================
# Plot setup
# ============================================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8
})

fig, axes = plt.subplots(2, 3, figsize=(10, 5))  # 2 rows × 3 cols

x = np.arange(len(workloads))
width = 0.18

colors = {
    "Baseline": "#000000",
    "LRU": "#555555",
    "LRU2Q": "#888888",
    "TinyLFU": "#BBBBBB"
}

# ============================================
# Loop distributions
# ============================================
for row_idx, dist in enumerate(distributions):

    # prepare containers
    p50_data = {p: [] for p in policies}
    p95_data = {p: [] for p in policies}
    p99_data = {p: [] for p in policies}

    # collect data
    for w in workloads:
        for p in policies:
            file = get_file(w, p, dist)

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

    print("p50", p50_data)
    print("p95", p95_data)
    print("p99", p99_data)
    
    # ============================================
    # Plot each column
    # ============================================

    # ---- P50 ----
    ax = axes[row_idx, 0]
    for i, p in enumerate(policies):
        ax.bar(x + i*width, p50_data[p], width, color=colors[p])

    ax.set_xticks(x + width*1.5)
    ax.set_xticklabels([w.upper() for w in workloads])
    if row_idx == 0:
        ax.set_title("(a) P50")
    else:
        ax.set_title("(d) P50")

    if row_idx == 0:
        ax.set_ylabel("Uniform\nLatency (us)")
    else:
        ax.set_ylabel("Zipfian\nLatency (us)")

    # ---- P95 ----
    ax = axes[row_idx, 1]
    for i, p in enumerate(policies):
        ax.bar(x + i*width, p95_data[p], width, color=colors[p])

    ax.set_xticks(x + width*1.5)
    ax.set_xticklabels([w.upper() for w in workloads])
    if row_idx == 0:
        ax.set_title("(b) P95")
    else:
        ax.set_title("(e) P95")

    # ---- P99 ----
    ax = axes[row_idx, 2]
    for i, p in enumerate(policies):
        ax.bar(x + i*width, p99_data[p], width, color=colors[p])

    ax.set_xticks(x + width*1.5)
    ax.set_xticklabels([w.upper() for w in workloads])
    ax.set_yscale("log")  # IMPORTANT

    if row_idx == 0:
        ax.set_title("(c) P99")
    else:
        ax.set_title("(f) P99")

# ============================================
# Legend
# ============================================
handles = [plt.Rectangle((0,0),1,1,color=colors[p]) for p in policies]
fig.legend(handles, policies, loc="upper center", ncol=4, frameon=False)

# ============================================
# Clean style
# ============================================
for ax in axes.flatten():
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.tight_layout(rect=[0, 0.05, 1, 0.9])

output_file = "figure9_latency_2rows.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.show()

print(output_file)