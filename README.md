# CacheLink

**CacheLink** is an efficient multi-device secondary caching framework for RocksDB.

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

## Important Notice

The database should be created first on the NFS target storage. After that, the benchmark server mounts the NFS path and runs read experiments using `--use_existing_db=1`.

---
# Preparing NFS Data

## 1. Preparing the NFS Database

For remote-storage experiments, the RocksDB database should be created first on the NFS target server. We must install RocksDB db_bench on the NFS target server to create a db.

```bash
git clone https://github.com/facebook/rocksdb.git
cd rocksdb
git checkout v8.10.0
make -j$(nproc) db_bench
```

## 2. Fill the Database on the NFS Target Server

Copy fill.py from CacheLink repo to rocksdb folder:

Open the fill script:

```bash
vim fill.sh
```

Change the target database directory inside `fill.sh`.

Example:

```bash
DB_PATH="/export/rocksdb_data"
```

The exact variable name may differ depending on the script. The important point is that the database path should point to the directory exported by the NFS server.

Run the fill script:

```bash
bash fill.sh
```

After the script finishes, check that the RocksDB files were created:

```bash
ls -lah /export/rocksdb_data
```

The directory should contain RocksDB database files such as `.sst`, `CURRENT`, `MANIFEST`, `OPTIONS`, and `LOG`.

---

## 3. Mount NFS on the Benchmark Server

After the database has been filled on the NFS target server and the NFS export is ready, mount the exported directory on the benchmark server.

### 3.1 Create a Local Mount Directory

```bash
mkdir -p <LOCAL_NFS_MOUNT_DIR>
```

Example:

```bash
mkdir -p /home/agung/rocksdb_nfs
```

### 3.2 Mount the NFS Export

```bash
mount -t nfs -o nfsvers=4.1,tcp,sync \
  <NFS_SERVER>:/<NFS_EXPORT_PATH> \
  <LOCAL_NFS_MOUNT_DIR>
```

Example:

```bash
mount -t nfs -o nfsvers=4.1,tcp,sync \
  220.221.110.xxx:/export/rocksdb_data \
  /home/agung/rocksdb_nfs
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

# Installing CacheLink

## 1. Docker Environment

CacheLink can be built and evaluated inside an Ubuntu 22.04 Docker container.

### 1.1 Check Local Storage Devices

Before starting the Docker container, check which local paths correspond to the HDD, SATA SSD, and NVMe SSD.

```bash
lsblk -o NAME,SIZE,MODEL,ROTA,TRAN,MOUNTPOINT
````

Use the following rule:

```text
ROTA=1, TRAN=sata  -> HDD
ROTA=0, TRAN=sata  -> SATA SSD
ROTA=0, TRAN=nvme  -> NVMe SSD
```

Example output:

```text
NAME        SIZE MODEL                    ROTA TRAN MOUNTPOINT
sdb         1.8T Samsung_SSD_870_EVO_2TB     0 sata
└─sdb1      1.8T                                  /mnt/hdd1
sdc         3.7T ST4000NM002A-2HZ101         1 sata
└─sdc1        2T                                  /mnt/hdd2
nvme0n1     1.8T Samsung SSD 980 PRO 2TB     0 nvme
└─nvme0n1p1 1.8T                                  /mnt/nvme
```

In this example:

```text
/mnt/hdd2  -> HDD
/mnt/hdd1  -> SATA SSD
/mnt/nvme  -> NVMe SSD
```

### 1.2 Start the Docker Container

Replace the paths below with your own local paths:

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

For example, on our testbed:

```bash
docker run -dit \
  --name cachelink_env \
  --privileged \
  -v /home/agung:/workspace \
  -v /mnt/hdd2:/mnt/hdd \
  -v /mnt/hdd1:/mnt/ssd \
  -v /mnt/nvme:/mnt/nvme \
  ubuntu:22.04
```

Alternatively, use the one-line version to avoid shell line-break errors:

```bash
docker run -dit --name cachelink_env --privileged -v /home/agung:/workspace -v /mnt/hdd2:/mnt/hdd -v /mnt/hdd1:/mnt/ssd -v /mnt/nvme:/mnt/nvme ubuntu:22.04
```


If a container with the same name already exists, remove it first:

```bash
docker rm -f cachelink_env
```




Example placeholder meaning:

| Placeholder | Meaning |
|---|---|
| `<HOST_WORKDIR>` | Host directory that contains CacheLink, CacheLib, scripts, and experiment files |
| `<LOCAL_HDD_PATH>` | Host HDD mount path used for secondary-cache experiments |
| `<LOCAL_SSD_PATH>` | Host SATA SSD mount path used for secondary-cache experiments |
| `<LOCAL_NVME_PATH>` | Host NVMe mount path used for secondary-cache experiments |

Do not use important production directories as experiment paths.

### Docker Option Explanation

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

## 2. Enter the Docker Container

```bash
docker exec -it cachelink_env /bin/bash
```

Move to the workspace:

```bash
cd /workspace
```

---

## 3. Install Required Packages

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
  nfs-common \
  sudo
```

---

## 4. Install CacheLib

CacheLink uses CacheLib as the underlying cache backend.

### Preparation
Install manually the liburing.

```bash
cd /tmp
git clone https://github.com/axboe/liburing.git
cd liburing
./configure --prefix=/usr/local
make -j$(nproc)
make install
ldconfig
```

### 4.1 Clone CacheLib

```bash
cd /workspace
git clone https://github.com/facebook/CacheLib.git
cd CacheLib
```

### 4.2 Checkout the Tested Version

The tested CacheLib version is `v2024.06.21`.

```bash
git checkout c5c0d9b
```

### 4.3 Build CacheLib

```bash
./contrib/build.sh -d -j -v
```

### 4.4 CacheLib Build Option Explanation

| Option | Description |
|---|---|
| `-d` | Builds CacheLib with debug-related configuration |
| `-j` | Enables parallel compilation |
| `-v` | Enables verbose build output |

---

## 5. Build CacheLink

Return to the workspace:

```bash
cd /workspace
```

Clone CacheLink:

```bash
git clone https://github.com/imagesid/CacheLink
cd CacheLink
```

If you install Cachelib or CacheLink in different folder, edit the Makefile file.

```bash
CACHELIB_PATH = /workspace/CacheLib/opt/cachelib
WRAPPER_PATH = /workspace/CacheLink
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

## 7. Basic Local `db_bench` Sanity Test

Before running NFS experiments, verify that `db_bench` works locally.

Create a safe temporary database directory:

```bash
mkdir -p /tmp/cachelink_local_db
mkdir -p /tmp/temp_cache
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
  --cachelink="size=1073741824,eviction=tinylfu,adm_policy=random,adm_prob=1.0,file=/tmp/temp_cache/cachelink_local.data" \
  --statistics
```

This test checks whether the CacheLink-enabled `db_bench` binary runs correctly.

---

## 8. Run CacheLink with NFS-Backed RocksDB Data

After the database has been filled on the NFS target server and mounted on the benchmark server, run the benchmark with `--use_existing_db=1`.

Example:

```bash
./db_bench \
  --benchmarks=readrandom \
  --use_existing_db=1 \
  --db=/workspace/rocksdb_nfs \
  --cache_size=33554432 \
  --secondary_cache_uri="id=CacheLink" \
  --cachelink="size=1073741824,eviction=tinylfu,adm_policy=random,adm_prob=1.0,file=/mnt/nvme/cachelink.data" \
  --statistics
```


---

##  `db_bench` Parameter Explanation

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

## 9. Common CacheLink Configurations

### 9.1 NVMe Secondary Cache with TinyLFU

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=tinylfu,adm_policy=random,adm_prob=1.0,file=/mnt/nvme/cachelink.data"
```

### 9.2 SSD Secondary Cache with LRU

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=lru,adm_policy=random,adm_prob=1.0,file=/mnt/ssd/cachelink.data"
```

### 9.3 HDD Secondary Cache with LRU2Q

```bash
--secondary_cache_uri="id=CacheLink" \
--cachelink="size=1073741824,eviction=lru2q,adm_policy=random,adm_prob=1.0,file=/mnt/hdd/cachelink.data"
```

Adjust paths according to your mounted devices.

---

## 10. Installing YCSB

### Build YCSB with Custom CacheLink RocksDB

Install Java and Maven:

```bash
apt update
apt install -y openjdk-11-jdk maven
```

Set Java environment variables:

```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

Build the custom RocksDB JNI library:

```bash
cd /workspace/CacheLink

DEBUG_LEVEL=0 \
EXTRA_CXXFLAGS=-fPIC \
EXTRA_CFLAGS=-fPIC \
USE_RTTI=1 \
make -j$(nproc) rocksdbjavastatic
```

Install the custom RocksDB JNI jar into the local Maven repository:

```bash
VERSION=8.10.0

mvn install:install-file \
  -Dfile=java/target/rocksdbjni-${VERSION}-linux64.jar \
  -DgroupId=org.rocksdb \
  -DartifactId=rocksdbjni \
  -Dversion=${VERSION} \
  -Dpackaging=jar
```

Set the CacheLib library path:

```bash
export LD_LIBRARY_PATH=/workspace/CacheLib/opt/cachelib/lib:$LD_LIBRARY_PATH
```

Build the YCSB RocksDB binding:

```bash
cd /workspace
git clone https://github.com/imagesid/CacheLink-YCSB YCSB
cd /workspace/YCSB

mvn -o -pl site.ycsb:rocksdb-binding -am clean package
```

If Maven dependencies have not been downloaded yet, run this command once before the offline build:

```bash
mvn -pl site.ycsb:rocksdb-binding -am clean package
```

Run a simple YCSB load test with CacheLink:

```bash
./bin/ycsb load rocksdb -s \
  -P workloads/workloada \
  -p rocksdb.dir=/tmp/ycsb-rocksdb-data \
  -p secondary_cache_uri="id=CacheLink" \
  -p cachelink="size=1073741824,eviction=tinylfu,adm_policy=random,adm_prob=0.2,file=/workspace/cache_file"
```

If the output shows the `CacheLink` parameters, then YCSB is correctly connected to the custom RocksDB with CacheLink support. You can then proceed with the full evaluation.

## 11. Reproducing Artifact Results

The repository includes scripts for reproducing artifact results and figures.

The scripts cover both:

- `db_bench` experiments
- YCSB experiments

Before running any artifact script, inspect it first to verify database paths, cache paths, device paths, and output directories.

```bash
cat scripts/new-figure2.sh
```

or:

```bash
vim scripts/new-figure2.sh
```

---

## 11. Main Artifact Figures

To run a main figure script:

```bash
bash scripts/new-figure{n}.sh
```

Replace `{n}` with the target figure number from 2 to 17.

Examples:

```bash
bash scripts/new-figure2.sh
python scripts/new-figure3.py
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
