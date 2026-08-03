# SOSD-Derived Streaming Benchmark

`benchmarks/sosd_streaming.py` validates and streams all 200 million values
from each compressed real-world SOSD distribution without writing the full
decompressed arrays to disk. It retains a deterministic evenly spaced rank
sample, then executes native equality lookups over the sampled real key values.

Compared methods are `std::lower_bound`, Eytzinger order, interpolation search
guarded by a 32-probe fallback, CertiGap partial routing, and RadixSpline from the pinned official SOSD checkout
at commit `f52f4cba01dfcd37f1574551fccef00198863b88`.

```bash
python3 benchmarks/sosd_streaming.py \
  --sample-keys 100000 --queries 100000 --repeats 7 --budget 32
```

The key distributions are official SOSD values. The uniform, Zipf, hotspot,
and latest-biased query distributions are additional synthetic workloads. This
is therefore SOSD-derived evidence, not an execution of the official SOSD
harness. The committed CSV includes losses as well as wins and the metadata
binds the source, result, compiler, platform, sample, and pinned competitor.

For the official YCSB RocksDB binding, start Docker and run:

```bash
RECORDS=1000000 OPERATIONS=1000000 \
  bash benchmarks/official_ycsb_rocksdb.sh
```

That protocol is an external storage-engine baseline. It does not claim a
CertiGap RocksDB plugin.

The pinned RocksDB JNI is x86-64, so the runner deliberately uses
`linux/amd64` on Apple Silicon. It fails before building unless the host has
at least `max(5 GiB, 12 KiB * RECORDS)` free, rejects zero-throughput runs,
worker exceptions, error returns, and incomplete operation counts, and removes
each reproducible database after retaining raw metrics. On Docker Desktop,
`RECLAIM_SPACE=1` asks Docker to discard free VM blocks after every workload.

Interrupted experiments can reuse the already built image and rerun selected
workloads; final metadata is emitted only after all A/B/C/D/F logs pass the
same complete verification:

```bash
REBUILD_IMAGE=0 RECLAIM_SPACE=1 WORKLOADS_TO_RUN="d f" \
  RECORDS=1000000 OPERATIONS=1000000 \
  bash benchmarks/official_ycsb_rocksdb.sh
```

No official YCSB result is committed yet. The local full-scale attempt exposed
and fixed the Python-launcher, source-distribution, ARM JNI, silent worker
failure, and disk-preflight issues, but the host lacked the required free disk.
This failed attempt is not performance evidence.
