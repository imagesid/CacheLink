# CacheLink

**CacheLink** is an efficient multi-device secondary caching framework for RocksDB.

CacheLink extends RocksDB's experimental `SecondaryCache` interface with a CacheLib-based backend. It allows blocks evicted from RocksDB's DRAM block cache to be stored on local secondary devices such as HDDs, SATA SSDs, and NVMe SSDs.

CacheLink is designed for RocksDB deployments where the main database is placed on remote or disaggregated storage, such as NFS. In this environment, a miss in the DRAM block cache can trigger an expensive backend read. CacheLink reduces this cost by inserting a local secondary-cache layer between RocksDB's DRAM block cache and the remote storage path.

The framework supports configurable cache size, cache path, admission control, and eviction policies, including LRU, LRU2Q, and TinyLFU. These options make CacheLink useful not only as a device-backed secondary cache implementation, but also as an experimental framework for studying how secondary-cache design choices affect RocksDB throughput, latency, and tail-latency behavior.

Experimental results using `db_bench` and YCSB show that CacheLink substantially improves throughput and reduces average latency compared with baseline RocksDB without secondary caching. In the paper's secondary-cache size experiment, the best-performing configuration uses a 2 GB NVMe secondary cache with TinyLFU eviction and full admission, improving throughput by 2.5× and reducing average latency by 60.7% relative to the baseline.

---

## Key Features

- RocksDB secondary-cache integration through the `SecondaryCache` interface
- CacheLib-based local secondary-cache backend
- Support for heterogeneous local storage devices:
  - HDD
  - SATA SSD
  - NVMe SSD
- Runtime-configurable cache size and cache file path
- Configurable admission control
- Multiple eviction policies:
  - LRU
  - LRU2Q
  - TinyLFU
- Support for `db_bench` and YCSB experiments
- Designed for remote-storage scenarios where RocksDB data resides on NFS or other slower backing storage

---

## 1. Experimental Model

CacheLink is intended for a two-storage-path setup:

```text
Client / Benchmark Server
├── Runs RocksDB + CacheLink
├── Uses local device for secondary cache
│   └── Example: local HDD, SATA SSD, or NVMe SSD
└── Accesses RocksDB database through NFS

NFS Target Server
└── Stores the RocksDB database files
```

The database should be created first on the NFS target storage. After that, the benchmark server mounts the NFS path and runs read experiments using `--use_existing_db=1`.

---

## 2. Docker Environment

CacheLink can be built and evaluated inside an Ubuntu 22.04 Docker container.

### 2.1 Start the Docker Container

```bash
docker run -dit \
  --name cachelink_env \
  --privileged \
  -v <HOST_WORKDIR>:/workspace \
  -v <LOCAL_HDD_PATH>:/mnt/hdd \
  -v <LOCAL_SSD_PATH>:/mnt/ssd \
  -v <LOCAL_NVME_PATH>:/mnt/nvme \
  ubuntu:22.04
```

Example placeholder meaning:

| Placeholder | Meaning |
|---|---|
| `<HOST_WORKDIR>` | Host directory that contains CacheLink, CacheLib, scripts, and experiment files |
| `<LOCAL_HDD_PATH>` | Host HDD mount path used for secondary-cache experiments |
| `<LOCAL_SSD_PATH>` | Host SATA SSD mount path used for secondary-cache experiments |
| `<LOCAL_NVME_PATH>` | Host NVMe mount path used for secondary-cache experiments |

Do not use important production directories as experiment paths.

### 2.2 Docker Option Explanation

| Option | Description |
|---|---|
| `docker run` | Creates and starts a new Docker container |
| `-d` | Runs the container in detached mode |
| `-i` | Keeps standard input open |
| `-t` | Allocates a pseudo-terminal |
| `--name cachelink_env` | Assigns the container name `cachelink_env` |
| `--privileged` | Gives the container extended system privileges, useful for storage experiments |
| `-v <HOST_WORKDIR>:/workspace` | Mounts the host working directory into the container |
| `-v <LOCAL_HDD_PATH>:/mnt/hdd` | Mounts a local HDD path into the container |
| `-v <LOCAL_SSD_PATH>:/mnt/ssd` | Mounts a local SATA SSD path into the container |
| `-v <LOCAL_NVME_PATH>:/mnt/nvme` | Mounts a local NVMe path into the container |
| `ubuntu:22.04` | Uses the official Ubuntu 22.04 Docker image |

---

## 3. Enter the Docker Container

```bash
docker exec -it cachelink_env /bin/bash
```

Move to the workspace:

```bash
cd /workspace
```

---

## 4. Install Required Packages

Because the container starts from the official `ubuntu:22.04` image, install the required packages first.

```bash
apt update
apt install -y \
  build-essential \
  cmake \
  git \
  wget \
  curl \
  vim \
  pkg-config \
  libgflags-dev \
  libsnappy-dev \
  zlib1g-dev \
  libbz2-dev \
  liblz4-dev \
  libzstd-dev \
  libaio-dev \
  liburing-dev \
  libssl-dev \
  libboost-all-dev \
  python3 \
  python3-pip \
  nfs-common
```

---

## 5. Install CacheLib

CacheLink uses CacheLib as the underlying cache backend.

### 5.1 Clone CacheLib

```bash
cd /workspace
git clone https://github.com/facebook/CacheLib.git
cd CacheLib
```

### 5.2 Checkout the Tested Version

The tested CacheLib version is `v2024.06.21`.

```bash
git checkout c5c0d9b
```

### 5.3 Build CacheLib

```bash
./contrib/build.sh -d -j -v
```

### 5.4 CacheLib Build Option Explanation

| Option | Description |
|---|---|
| `-d` | Builds CacheLib with debug-related configuration |
| `-j` | Enables parallel compilation |
| `-v` | Enables verbose build output |

---

## 6. Build CacheLink

Return to the workspace:

```bash
cd /workspace
```

Clone CacheLink:

```bash
git clone https://github.com/imagesid/CacheLink
cd CacheLink
```

Example:

```bash
git clone https://github.com/imagesid/CacheLink.git
cd CacheLink
```

Clean previous build artifacts:

```bash
make clean
```

Build `db_bench`:

```bash
make db_bench -j$(nproc)
```

After a successful build, check that `db_bench` exists:

```bash
ls -lah db_bench
```

---

## 7. Preparing the NFS Database

For remote-storage experiments, the RocksDB database should be created first on the NFS target server.

This means:

1. Go to the NFS target server.
2. Edit `fill.sh`.
3. Change the target database directory to the exported NFS directory.
4. Run `fill.sh` to create and fill the database.
5. Mount the NFS export from the benchmark server.
6. Run CacheLink experiments with `--use_existing_db=1`.

---

## 8. Fill the Database on the NFS Target Server

On the NFS target server, go to the CacheLink repository:

```bash
cd <CACHELINK_DIR>
```

Open the fill script:

```bash
vim scripts/fill.sh
```

Change the target database directory inside `fill.sh`.

Example:

```bash
DB_DIR="<NFS_EXPORT_DIR>/rocksdb_data"
```

The exact variable name may differ depending on the script. The important point is that the database path should point to the directory exported by the NFS server.

Run the fill script:

```bash
bash scripts/fill.sh
```

After the script finishes, check that the RocksDB files were created:

```bash
ls -lah <NFS_EXPORT_DIR>/rocksdb_data
```

The directory should contain RocksDB database files such as `.sst`, `CURRENT`, `MANIFEST`, `OPTIONS`, and `LOG`.

---

## 9. Mount NFS on the Benchmark Server

After the database has been filled on the NFS target server and the NFS export is ready, mount the exported directory on the benchmark server.

### 9.1 Create a Local Mount Directory

```bash
mkdir -p <LOCAL_NFS_MOUNT_DIR>
```

Example:

```bash
mkdir -p /mnt/rocksdb_nfs
```

### 9.2 Mount the NFS Export

```bash
mount -t nfs -o nfsvers=4.1,tcp,sync \
  <NFS_SERVER>:/<NFS_EXPORT_PATH> \
  <LOCAL_NFS_MOUNT_DIR>
```

Example:

```bash
mount -t nfs -o nfsvers=4.1,tcp,sync \
  <NFS_SERVER>:/export/rocksdb_data \
  /mnt/rocksdb_nfs
```

Replace the placeholders with your own environment values.

| Placeholder | Meaning |
|---|---|
| `<NFS_SERVER>` | NFS server hostname or IP address |
| `<NFS_EXPORT_PATH>` | Exported directory path on the NFS server |
| `<LOCAL_NFS_MOUNT_DIR>` | Local mount point on the benchmark server |

### 9.3 Check the NFS Mount

```bash
df -h | grep <LOCAL_NFS_MOUNT_DIR>
```

or:

```bash
mount | grep nfs
```

---

## 10. Safe Experiment Rules

Before running any benchmark, follow these safety rules.

1. Do not use an important existing RocksDB database as the test path.
2. Use a separate database directory for each experiment.
3. Use a separate secondary-cache file or directory for each run.
4. Save benchmark logs separately from database and cache files.
5. Use `--use_existing_db=0` only when creating a new benchmark database.
6. Use `--use_existing_db=1` only when intentionally reusing a previously created database.
7. Be careful with `rm -rf`. Only remove files inside temporary experiment directories.
8. For NFS experiments, fill the database first on the NFS target server before running read benchmarks from the benchmark server.

Recommended local experiment layout:

```text
/tmp/cachelink_exp/
├── cache/
└── logs/
```

Create directories:

```bash
mkdir -p /tmp/cachelink_exp/cache
mkdir -p /tmp/cachelink_exp/logs
```

Clean only temporary cache and log files:

```bash
rm -rf /tmp/cachelink_exp/cache/*
rm -rf /tmp/cachelink_exp/logs/*
```

---

## 11. Basic Local `db_bench` Sanity Test

Before running NFS experiments, verify that `db_bench` works locally.

Create a safe temporary database directory:

```bash
mkdir -p /tmp/cachelink_local_db
```

Clean old test data if needed:

```bash
rm -rf /tmp/cachelink_local_db/*
```

Run a simple local test:

```bash
./db_bench \
  --benchmarks=fillrandom,readrandom \
  --use_existing_db=0 \
  --db=/tmp/cachelink_local_db \
  --cache_size=33554432 \
  --secondary_cache_uri="id=CacheLink" \
  --cachelink="size=1073741824,eviction=tinylfu,adm_policy=dynamic_random,adm_prob=0.8,file=/tmp/cachelink_exp/cache/cachelink_local.data" \
  --statistics
```

This test checks whether the CacheLink-enabled `db_bench` binary runs correctly.

---

## 12. Run CacheLink with NFS-Backed RocksDB Data

After the database has been filled on the NFS target server and mounted on the benchmark server, run the benchmark with `--use_existing_db=1`.

Example:

```bash
./db_bench \
  --benchmarks=readrandom \
  --use_existing_db=1 \
  --db=<LOCAL_NFS_MOUNT_DIR>/rocksdb_data \
  --cache_size=33554432 \
  --secondary_cache_uri="id=CacheLink" \
  --cachelink="size=1073741824,eviction=tinylfu,adm_policy=dynamic_random,adm_prob=0.8,file=/mnt/nvme/cachelink.data" \
  --statistics \
  2>&1 | tee /tmp/cachelink_exp/logs/db_bench_nfs_nvme.log
```

In this setup:

| Path | Meaning |
|---|---|
| `<LOCAL_NFS_MOUNT_DIR>/rocksdb_data` | RocksDB database path mounted from NFS |
| `/mnt/nvme/cachelink.data` | Local NVMe secondary-cache file |
| `/tmp/cachelink_exp/logs/db_bench_nfs_nvme.log` | Benchmark log file |

---

## 13. `db_bench` Parameter Explanation

| Parameter | Description |
|---|---|
| `./db_bench` | Runs the RocksDB benchmark tool |
| `--benchmarks=fillrandom,readrandom` | Runs both database creation and random-read phases |
| `--benchmarks=readrandom` | Runs only random reads, usually used with an existing database |
| `--use_existing_db=0` | Creates a new database for the benchmark |
| `--use_existing_db=1` | Reuses an existing database |
| `--db=<PATH>` | Sets the RocksDB database directory |
| `--cache_size=33554432` | Sets the primary RocksDB block cache to 32 MiB |
| `--secondary_cache_uri="id=CacheLink"` | Enables CacheLink through RocksDB's secondary-cache interface |
| `--cachelink="..."` | Passes CacheLink-specific configuration options |
| `size=1073741824` | Sets the CacheLink secondary-cache size to 1 GiB |
| `eviction=tinylfu` | Uses TinyLFU as the secondary-cache eviction policy |
| `adm_policy=dynamic_random` | Uses the dynamic-random admission policy |
| `adm_prob=0.8` | Sets the admission probability to 0.8 |
| `file=<PATH>` | Specifies the local secondary-cache file |
| `--statistics` | Enables RocksDB statistics output |
| `2>&1 | tee <LOG_FILE>` | Prints output to the terminal and saves it to a log file |

---

## 14. Common CacheLink Configurations

### 14.1 NVMe Secondary Cache with TinyLFU

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=tinylfu,adm_policy=dynamic_random,adm_prob=0.8,file=/mnt/nvme/cachelink.data"
```

### 14.2 SSD Secondary Cache with LRU

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=lru,adm_policy=dynamic_random,adm_prob=0.8,file=/mnt/ssd/cachelink.data"
```

### 14.3 HDD Secondary Cache with LRU2Q

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=lru2q,adm_policy=dynamic_random,adm_prob=0.8,file=/mnt/hdd/cachelink.data"
```

Adjust paths according to your mounted devices.

---

## 15. Reproducing Artifact Results

The repository includes scripts for reproducing artifact results and figures.

The scripts cover both:

- `db_bench` experiments
- YCSB experiments

Before running any artifact script, inspect it first to verify database paths, cache paths, device paths, and output directories.

```bash
cat scripts/figure0.sh
```

or:

```bash
vim scripts/figure0.sh
```

---

## 16. Main Artifact Figures

To run a main figure script:

```bash
bash scripts/figure{n}.sh
```

Replace `{n}` with the target figure number.

Examples:

```bash
bash scripts/figure0.sh
bash scripts/figure1.sh
bash scripts/figure2.sh
```

Expected main figure scripts:

```bash
bash scripts/figure0.sh
bash scripts/figure1.sh
bash scripts/figure2.sh
bash scripts/figure3.sh
bash scripts/figure4.sh
bash scripts/figure5.sh
bash scripts/figure6.sh
bash scripts/figure7.sh
bash scripts/figure8.sh
bash scripts/figure9.sh
bash scripts/figure10.sh
```

---

## 17. Additional Artifact Figures

To run an additional figure script:

```bash
bash scripts/figure-additional{n}.sh
```

Examples:

```bash
bash scripts/figure-additional0.sh
bash scripts/figure-additional1.sh
bash scripts/figure-additional2.sh
```

---

## 18. YCSB Experiments

Some artifact scripts may run YCSB workloads. The paper evaluates YCSB workloads A, B, C, D, and F.

| Workload | Description |
|---|---|
| Workload A | Balanced read/update workload |
| Workload B | Read-heavy workload |
| Workload C | Read-only workload |
| Workload D | Read-latest workload |
| Workload F | Read-modify-write workload |

Workload E is not the main target because it uses short-range scans, which exercise a different RocksDB path from the point lookups targeted by CacheLink.

Before running YCSB scripts, check:

1. RocksDB build path
2. YCSB path
3. Database directory
4. Secondary-cache directory
5. Workload file
6. Number of records
7. Number of operations
8. Output log directory

---

## 19. Expected Output

Depending on the script, the output may include:

- Raw benchmark logs
- Processed result files
- Throughput results
- Average latency results
- Tail-latency results
- Generated figures
- Intermediate experiment data

Store outputs in a separate directory:

```bash
mkdir -p /tmp/cachelink_results
```

---

## 20. Troubleshooting

### 20.1 Docker Container Already Exists

Check existing containers:

```bash
docker ps -a
```

If the old container is no longer needed, remove it:

```bash
docker rm -f cachelink_env
```

Then rerun the `docker run` command.

---

### 20.2 Cannot Enter the Container

Check whether the container is running:

```bash
docker ps
```

If it is stopped, start it:

```bash
docker start cachelink_env
```

Then enter it:

```bash
docker exec -it cachelink_env /bin/bash
```

---

### 20.3 Permission Problem in Mounted Directories

Check permissions:

```bash
ls -lah /mnt/hdd
ls -lah /mnt/ssd
ls -lah /mnt/nvme
```

Also check the NFS-mounted database path:

```bash
ls -lah <LOCAL_NFS_MOUNT_DIR>
```

If needed, adjust ownership or permissions carefully on the host machine.

---

### 20.4 NFS Mount Failed

Check whether the mount directory exists:

```bash
ls -lah <LOCAL_NFS_MOUNT_DIR>
```

Check NFS mount status:

```bash
mount | grep nfs
```

Check disk visibility:

```bash
df -h
```

If the NFS server is unreachable, check network connectivity and server export configuration.

---

### 20.5 `db_bench` Not Found

Make sure you are inside the CacheLink directory:

```bash
pwd
ls -lah
```

Check whether `db_bench` exists:

```bash
ls -lah db_bench
```

If it does not exist, rebuild:

```bash
make clean
make db_bench -j$(nproc)
```

---

### 20.6 CacheLib Build Failed

Check the CacheLib directory:

```bash
cd /workspace/CacheLib
git status
git rev-parse HEAD
```

The expected commit is:

```text
c5c0d9b
```

Rebuild CacheLib:

```bash
./contrib/build.sh -d -j -v
```

---

### 20.7 Git Clone Failed

If cloning with HTTPS fails:

```bash
git clone https://github.com/imagesid/CacheLink.git
```

check network access and repository permissions.

If cloning with SSH fails:

```bash
git clone git@github.com:imagesid/CacheLink.git
```

check your SSH connection:

```bash
ssh -T git@github.com
```

---

### 20.8 Benchmark Accidentally Uses Old Data

Check the database directory:

```bash
ls -lah <DATABASE_DIR>
```

For a fresh local run, clean only the intended temporary directory:

```bash
rm -rf /tmp/cachelink_local_db/*
```

Then rerun with:

```bash
--use_existing_db=0
```

For a read-only run on an existing NFS database, use:

```bash
--use_existing_db=1
```

---

## 21. Notes for Reproducibility

For each experiment, record the following information:

- Git commit hash
- CacheLib commit hash
- Docker image name
- CPU model
- Memory size
- Operating system
- Storage device used for RocksDB database
- Storage device used for secondary cache
- `db_bench` command
- YCSB workload configuration
- Cache size
- Admission policy
- Admission probability
- Eviction policy
- Number of records
- Number of operations
- Log file path

Useful commands:

```bash
git rev-parse HEAD
```

```bash
uname -a
```

```bash
lscpu
```

```bash
free -h
```

```bash
df -h
```

---

## 22. Citation

If you use CacheLink in your research, please cite the associated paper:

```bibtex
@article{cachelink2026,
  title   = {CacheLink: Efficient Multi-Device Secondary Caching for RocksDB},
  journal = {Electronics},
  year    = {2026}
}
```

---

## 23. License and Upstream Notice

CacheLink is built on top of RocksDB and uses CacheLib.

Please refer to the original RocksDB and CacheLib repositories for their respective licenses and upstream documentation:

- RocksDB: https://github.com/facebook/rocksdb
- CacheLib: https://github.com/facebook/CacheLib

RocksDB is dual-licensed under GPLv2 and Apache License 2.0. CacheLink follows the licensing requirements of the upstream components used in this repository.
