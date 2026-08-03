#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="certigap-ycsb-rocksdb:d9faaac"
YCSB_COMMIT="d9faaac85a95acd4c650a3436ac41eeaeb49c365"
RECORDS="${RECORDS:-1000000}"
OPERATIONS="${OPERATIONS:-1000000}"
THREADS="${THREADS:-1}"
PLATFORM="${PLATFORM:-linux/amd64}"
REBUILD_IMAGE="${REBUILD_IMAGE:-1}"
RECLAIM_SPACE="${RECLAIM_SPACE:-0}"
RESULTS="${ROOT}/results/ycsb_rocksdb"
read -r -a WORKLOAD_LIST <<< "${WORKLOADS_TO_RUN:-a b c d f}"

if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is required for the official YCSB/RocksDB run." >&2
    exit 2
fi

if [[ ! "${RECORDS}" =~ ^[1-9][0-9]*$ || ! "${OPERATIONS}" =~ ^[1-9][0-9]*$ ]]; then
    echo "RECORDS and OPERATIONS must be positive integers." >&2
    exit 2
fi
# Docker Desktop may retain deleted VM blocks until TRIM. Require enough host
# space for one database plus container copy-on-write and compaction overhead.
available_kib="$(df -Pk "${ROOT}" | awk 'NR == 2 {print $4}')"
required_kib=$((RECORDS * 12))
minimum_kib=$((5 * 1024 * 1024))
if (( required_kib < minimum_kib )); then
    required_kib="${minimum_kib}"
fi
if (( available_kib < required_kib )); then
    printf 'YCSB/RocksDB needs at least %.1f GiB free; only %.1f GiB is available.\n' \
        "$(awk -v value="${required_kib}" 'BEGIN {print value / 1048576}')" \
        "$(awk -v value="${available_kib}" 'BEGIN {print value / 1048576}')" >&2
    exit 2
fi

mkdir -p "${RESULTS}"
if [[ "${REBUILD_IMAGE}" == "1" ]]; then
    docker build \
        --platform "${PLATFORM}" \
        --build-arg "YCSB_COMMIT=${YCSB_COMMIT}" \
        -t "${IMAGE}" \
        -f "${ROOT}/benchmarks/ycsb/Dockerfile" \
        "${ROOT}"
elif [[ "${REBUILD_IMAGE}" != "0" ]]; then
    echo "REBUILD_IMAGE must be 0 or 1." >&2
    exit 2
fi
docker image inspect "${IMAGE}" >/dev/null

for workload in "${WORKLOAD_LIST[@]}"; do
    case "${workload}" in
        a|b|c|d|f) ;;
        *) echo "Unsupported workload: ${workload}" >&2; exit 2 ;;
    esac
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
    docker run --rm --platform "${PLATFORM}" \
        -v "${RESULTS}:/results" "${IMAGE}" \
        load "${common[@]}" 2>&1 | tee "${RESULTS}/${database}/load.txt"
    docker run --rm --platform "${PLATFORM}" \
        -v "${RESULTS}:/results" "${IMAGE}" \
        run "${common[@]}" 2>&1 | tee "${RESULTS}/${database}/run.txt"
    # Each workload is self-contained; retain metrics, not the reproducible DB.
    find "${RESULTS}/${database}" -type d -name db -prune -exec rm -rf {} +
    if [[ "${RECLAIM_SPACE}" == "1" ]]; then
        docker run --rm --privileged --pid=host docker/desktop-reclaim-space
    elif [[ "${RECLAIM_SPACE}" != "0" ]]; then
        echo "RECLAIM_SPACE must be 0 or 1." >&2
        exit 2
    fi
done

python3 - "${RESULTS}" "${YCSB_COMMIT}" "${RECORDS}" "${OPERATIONS}" "${THREADS}" "${PLATFORM}" <<'PY'
import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root, commit, records, operations, threads, container_platform = (
    Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
)
required = re.compile(r"^\[(OVERALL|READ|UPDATE|INSERT|READ-MODIFY-WRITE)\],", re.MULTILINE)
hashes = {}
metrics = []
for workload in "abcdf":
    for phase in ("load", "run"):
        path = root / f"ycsb_{workload}" / f"{phase}.txt"
        payload = path.read_bytes()
        text = payload.decode("utf-8")
        if not required.search(text) or "Exception" in text or "ERROR" in text:
            raise SystemExit(f"invalid or failed YCSB output in {path}")
        hashes[str(path.relative_to(root))] = hashlib.sha256(payload).hexdigest()
        for line in text.splitlines():
            match = re.fullmatch(r"\[([^]]+)\], ([^,]+), (.+)", line.strip())
            if match:
                group, metric, value = match.groups()
                metrics.append(
                    {
                        "workload": workload.upper(),
                        "phase": phase,
                        "group": group,
                        "metric": metric,
                        "value": value,
                    }
                )
        phase_metrics = {
            (row["group"], row["metric"]): row["value"]
            for row in metrics
            if row["workload"] == workload.upper() and row["phase"] == phase
        }
        throughput = float(phase_metrics.get(("OVERALL", "Throughput(ops/sec)"), "0"))
        operation_total = sum(
            int(value)
            for (group, metric), value in phase_metrics.items()
            if metric == "Operations" and group not in {"CLEANUP"}
        )
        expected = records if phase == "load" else operations
        errors = sum(
            int(value)
            for (group, metric), value in phase_metrics.items()
            if metric == "Return=ERROR"
        )
        if throughput <= 0 or operation_total != expected or errors:
            raise SystemExit(
                f"invalid YCSB execution in {path}: throughput={throughput}, "
                f"operations={operation_total}/{expected}, errors={errors}"
            )
if len(metrics) < 50:
    raise SystemExit(f"too few parsed YCSB metrics: {len(metrics)}")
with (root / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle, fieldnames=["workload", "phase", "group", "metric", "value"]
    )
    writer.writeheader()
    writer.writerows(metrics)
hashes["metrics.csv"] = hashlib.sha256((root / "metrics.csv").read_bytes()).hexdigest()

repo = root.parent.parent
image_id = subprocess.check_output(
    ["docker", "image", "inspect", "--format={{.Id}}", "certigap-ycsb-rocksdb:d9faaac"],
    text=True,
).strip()
metadata = {
    "schema": "certigap-official-ycsb-rocksdb-v1",
    "ycsb_commit": commit,
    "record_count": records,
    "operation_count": operations,
    "threads": threads,
    "container_platform": container_platform,
    "workloads": ["A", "B", "C", "D", "F"],
    "binding": "official site.ycsb:rocksdb-binding",
    "docker_image_id": image_id,
    "dockerfile_sha256": hashlib.sha256(
        (repo / "benchmarks" / "ycsb" / "Dockerfile").read_bytes()
    ).hexdigest(),
    "runner_sha256": hashlib.sha256(
        (repo / "benchmarks" / "official_ycsb_rocksdb.sh").read_bytes()
    ).hexdigest(),
    "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    "host_platform": platform.platform(),
    "artifact_sha256": hashes,
    "claim_boundary": "External baseline only; no CertiGap/RocksDB plugin is claimed.",
}
(root / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
PY

echo "Official YCSB/RocksDB artifacts written to ${RESULTS}"
