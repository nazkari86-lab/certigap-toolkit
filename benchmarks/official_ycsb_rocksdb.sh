#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="certigap-ycsb-rocksdb:d9faaac"
YCSB_COMMIT="d9faaac85a95acd4c650a3436ac41eeaeb49c365"
RECORDS="${RECORDS:-1000000}"
OPERATIONS="${OPERATIONS:-1000000}"
THREADS="${THREADS:-1}"
RESULTS="${ROOT}/results/ycsb_rocksdb"

if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is required for the official YCSB/RocksDB run." >&2
    exit 2
fi

mkdir -p "${RESULTS}"
docker build \
    --build-arg "YCSB_COMMIT=${YCSB_COMMIT}" \
    -t "${IMAGE}" \
    -f "${ROOT}/benchmarks/ycsb/Dockerfile" \
    "${ROOT}"

for workload in a b c d f; do
    database="ycsb_${workload}"
    rm -rf "${RESULTS:?}/${database}"
    mkdir -p "${RESULTS}/${database}"
    common=(
        rocksdb
        -P "workloads/workload${workload}"
        -p "recordcount=${RECORDS}"
        -p "operationcount=${OPERATIONS}"
        -p "threadcount=${THREADS}"
        -p "rocksdb.dir=/results/${database}/db"
        -s
    )
    docker run --rm -v "${RESULTS}:/results" "${IMAGE}" \
        load "${common[@]}" | tee "${RESULTS}/${database}/load.txt"
    docker run --rm -v "${RESULTS}:/results" "${IMAGE}" \
        run "${common[@]}" | tee "${RESULTS}/${database}/run.txt"
done

python3 - "${RESULTS}" "${YCSB_COMMIT}" "${RECORDS}" "${OPERATIONS}" "${THREADS}" <<'PY'
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

root, commit, records, operations, threads = (
    Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
)
required = re.compile(r"^\[(OVERALL|READ|UPDATE|INSERT|READ-MODIFY-WRITE)\],", re.MULTILINE)
hashes = {}
for workload in "abcdf":
    for phase in ("load", "run"):
        path = root / f"ycsb_{workload}" / f"{phase}.txt"
        payload = path.read_bytes()
        if not required.search(payload.decode("utf-8")):
            raise SystemExit(f"missing YCSB metrics in {path}")
        hashes[str(path.relative_to(root))] = hashlib.sha256(payload).hexdigest()
metadata = {
    "schema": "certigap-official-ycsb-rocksdb-v1",
    "ycsb_commit": commit,
    "record_count": records,
    "operation_count": operations,
    "threads": threads,
    "workloads": ["A", "B", "C", "D", "F"],
    "binding": "official site.ycsb:rocksdb-binding",
    "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    "host_platform": platform.platform(),
    "artifact_sha256": hashes,
    "claim_boundary": "External baseline only; no CertiGap/RocksDB plugin is claimed.",
}
(root / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
PY

echo "Official YCSB/RocksDB artifacts written to ${RESULTS}"
