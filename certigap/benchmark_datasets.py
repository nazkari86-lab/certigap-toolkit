"""Download and turn public access traces into ordered lookup workloads.

Raw source files are cached locally but never committed.  Every derived run
records source URL, retrieval time, SHA-256, aggregation, and key order.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import ssl
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .core import normalize_weights


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "external"
MANIFEST_PATH = CACHE_DIR / "manifest.json"
SOURCES = {
    "movielens_100k": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-100k/u.data",
        "filename": "movielens_100k_u.data",
        "description": "MovieLens 100K ratings aggregated by numeric movie identifier.",
        "order": "ascending numeric movie id",
    },
    "uci_online_retail": {
        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx",
        "filename": "uci_online_retail.xlsx",
        "description": "UCI Online Retail completed purchase rows aggregated by lexical StockCode.",
        "order": "ascending lexical StockCode",
    },
    "wikimedia_pageviews": {
        "url": "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2025/07/01",
        "filename": "wikimedia_top_en_2025-07-01.json",
        "description": "English Wikipedia all-access top pages for a pinned day, aggregated by API article count.",
        "order": "API top-pages rank (descending observed views)",
    },
    "movielens_32m": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-32m.zip",
        "filename": "movielens_32m.zip",
        "description": "MovieLens 32M ratings aggregated by numeric movie identifier.",
        "order": "ascending numeric movie id",
        "license": "GroupLens dataset terms in ml-32m-README.html",
        "expected_bytes": 238_950_008,
        "expected_md5": "d472be332d4daa821edc399621853b57",
    },
    "uci_online_retail_ii": {
        "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx",
        "filename": "uci_online_retail_ii.xlsx",
        "description": "UCI Online Retail II completed purchase rows from both years aggregated by lexical StockCode.",
        "order": "ascending lexical StockCode",
        "license": "CC BY 4.0; DOI 10.24432/C5CG6D",
    },
    "hetrec_lastfm_2k": {
        "url": "https://files.grouplens.org/datasets/hetrec2011/hetrec2011-lastfm-2k.zip",
        "filename": "hetrec2011_lastfm_2k.zip",
        "description": "HetRec Last.fm artist listening weights aggregated by numeric artist identifier.",
        "order": "ascending numeric artist id",
        "license": "HetRec 2011 terms in the archive readme",
    },
    "hetrec_delicious_2k": {
        "url": "https://files.grouplens.org/datasets/hetrec2011/hetrec2011-delicious-2k.zip",
        "filename": "hetrec2011_delicious_2k.zip",
        "description": "HetRec Delicious distinct user-bookmark events aggregated by numeric bookmark identifier.",
        "order": "ascending numeric bookmark id",
        "license": "HetRec 2011 terms in the archive readme",
    },
}

for language in ("en", "de", "es", "ru", "kk"):
    for day in ("2025-02-01", "2025-04-01", "2025-07-01", "2025-10-01"):
        if language != "en" and day != "2025-07-01":
            continue
        if language == "en" and day == "2025-07-01":
            continue
        name = f"wikimedia_{language}_{day}"
        SOURCES[name] = {
            "url": (
                "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
                f"{language}.wikipedia/all-access/{day.replace('-', '/')}"
            ),
            "filename": f"wikimedia_top_{language}_{day}.json",
            "description": f"{language} Wikipedia all-access top pages for {day}.",
            "order": "API top-pages rank (descending observed views)",
            "license": "Wikimedia REST API terms; aggregate pageview statistics",
        }


SOSD_SOURCES = {
    "sosd_books_200m": {
        "url": "https://dataverse.harvard.edu/api/access/datafile/3811099",
        "filename": "sosd_books_200M_uint32.zst",
        "bytes": 580452341,
        "md5": "2f5e8b7931f5240ebe5447edea96d431",
        "value_type": "uint32",
    },
    "sosd_fb_200m": {
        "url": "https://dataverse.harvard.edu/api/access/datafile/3811100",
        "filename": "sosd_fb_200M_uint64.zst",
        "bytes": 313994338,
        "md5": "fec241e8b021b198b0849fbd5564c05f",
        "value_type": "uint64",
    },
    "sosd_osm_200m": {
        "url": "https://dataverse.harvard.edu/api/access/datafile/3821004",
        "filename": "sosd_osm_cellids_200M_uint64.zst",
        "bytes": 1205063374,
        "md5": "42575cb58f24bb7ea0a623d422d4c9a6",
        "value_type": "uint64",
    },
    "sosd_wiki_200m": {
        "url": "https://dataverse.harvard.edu/api/access/datafile/3860043",
        "filename": "sosd_wiki_ts_200M_uint64.zst",
        "bytes": 116483593,
        "md5": "6a2b17020959084ce2640177ee4afd5e",
        "value_type": "uint64",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _download(name: str) -> tuple[Path, dict]:
    if name not in SOURCES:
        raise ValueError(f"unknown dataset: {name}")
    source = SOURCES[name]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / source["filename"]
    manifest = _load_manifest()
    zip_container = target.suffix in {".zip", ".xlsx"}
    invalid_cache = target.exists() and (
        (zip_container and not zipfile.is_zipfile(target))
        or (
            source.get("expected_bytes") is not None
            and target.stat().st_size != source["expected_bytes"]
        )
        or (
            source.get("expected_md5") is not None
            and _md5(target) != source["expected_md5"]
        )
    )
    if not target.exists() or invalid_cache:
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.unlink(missing_ok=True)
        request = urllib.request.Request(source["url"], headers={"User-Agent": "CertiGap-research-benchmark/0.3"})
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=90, context=context) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if zip_container and not zipfile.is_zipfile(temporary):
                raise ValueError(f"{name} response is not a valid ZIP container")
            if (
                source.get("expected_bytes") is not None
                and temporary.stat().st_size != source["expected_bytes"]
            ):
                raise ValueError(f"{name} byte-size mismatch")
            if (
                source.get("expected_md5") is not None
                and _md5(temporary) != source["expected_md5"]
            ):
                raise ValueError(f"{name} source MD5 mismatch")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    record = {
        "url": source["url"],
        "filename": target.name,
        "sha256": _sha256(target),
        "bytes": target.stat().st_size,
        "retrieved_utc": manifest.get(name, {}).get("retrieved_utc", datetime.now(timezone.utc).isoformat()),
        "description": source["description"],
        "key_order": source["order"],
        "license": source.get("license", "See the source dataset terms"),
    }
    if source.get("expected_md5") is not None:
        record["source_md5"] = source["expected_md5"]
    manifest[name] = record
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target, record


def _movielens(path: Path) -> list[float]:
    counts: Counter[int] = Counter()
    for line in path.read_text(encoding="latin-1").splitlines():
        _, movie, *_ = line.split("\t")
        counts[int(movie)] += 1
    return normalize_weights([counts[key] for key in range(1, max(counts) + 1)])


def load_movielens_100k_temporal_trace() -> tuple[list[tuple[int, int]], dict]:
    """Return the original rating-event order as `(timestamp, movie_id)` rows.

    Equal timestamps retain their original file order, so the function never
    fabricates a request sequence from aggregate popularity counts.
    """
    path, record = _download("movielens_100k")
    trace = _movielens_100k_temporal_trace(path)
    return trace, {
        **record,
        "dataset_class": "timestamped_access_event_trace",
        "event_count": len(trace),
        "event_order": "ascending original Unix timestamp, then source-file order",
        "key_definition": "MovieLens numeric movie identifier",
    }


def _movielens_100k_temporal_trace(path: Path) -> list[tuple[int, int]]:
    """Parse the source chronology, resolving equal timestamps by file order."""
    events: list[tuple[int, int, int]] = []
    for ordinal, line in enumerate(
        path.read_text(encoding="latin-1").splitlines()
    ):
        _, movie, _, timestamp = line.split("\t")
        events.append((int(timestamp), ordinal, int(movie)))
    events.sort()
    return [(timestamp, movie) for timestamp, _, movie in events]


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    return ["".join(node.itertext()) for node in root.findall(f"{namespace}si")]


def _uci_online_retail(path: Path) -> list[float]:
    return _retail_xlsx(path, ("xl/worksheets/sheet1.xml",))


def _retail_xlsx(path: Path, sheets: tuple[str, ...]) -> list[float]:
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        for sheet_name in sheets:
            with archive.open(sheet_name) as sheet:
                for _, row in ET.iterparse(sheet, events=("end",)):
                    if row.tag != f"{namespace}row":
                        continue
                    cells: dict[str, str] = {}
                    for cell in row.findall(f"{namespace}c"):
                        reference = cell.attrib.get("r", "")
                        column = re.match(r"[A-Z]+", reference)
                        value = cell.find(f"{namespace}v")
                        if column is None or value is None:
                            continue
                        text = value.text or ""
                        cells[column.group(0)] = (
                            shared[int(text)] if cell.attrib.get("t") == "s" else text
                        )
                    invoice = cells.get("A", "")
                    stock = cells.get("B", "")
                    quantity = cells.get("D", "0")
                    try:
                        positive_quantity = float(quantity) > 0
                    except ValueError:
                        positive_quantity = False
                    if stock and not invoice.lower().startswith("c") and positive_quantity:
                        counts[stock] += 1
                    row.clear()
    if not counts:
        raise ValueError("UCI Online Retail parser found no completed purchase rows")
    return normalize_weights([counts[key] for key in sorted(counts)])


def _wikimedia_pageviews(path: Path) -> list[float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    articles = payload["items"][0]["articles"]
    # Exclude the synthetic Main_Page entry; it is not a regular key lookup.
    counts = [int(article["views"]) for article in articles if article.get("article") != "Main_Page"]
    return normalize_weights(counts)


def _movielens_32m(path: Path) -> list[float]:
    counts: Counter[int] = Counter()
    with zipfile.ZipFile(path) as archive:
        with archive.open("ml-32m/ratings.csv") as raw:
            rows = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            next(rows)
            for line in rows:
                _, movie, *_ = line.split(",")
                counts[int(movie)] += 1
    return normalize_weights([counts[key] for key in sorted(counts)])


def _hetrec_lastfm(path: Path) -> list[float]:
    counts: Counter[int] = Counter()
    with zipfile.ZipFile(path) as archive:
        with archive.open("user_artists.dat") as raw:
            rows = io.TextIOWrapper(raw, encoding="utf-8")
            next(rows)
            for line in rows:
                _, artist, weight = line.rstrip("\n").split("\t")
                counts[int(artist)] += int(weight)
    return normalize_weights([counts[key] for key in sorted(counts)])


def _hetrec_delicious(path: Path) -> list[float]:
    events: set[tuple[int, int]] = set()
    with zipfile.ZipFile(path) as archive:
        with archive.open("user_taggedbookmarks.dat") as raw:
            rows = io.TextIOWrapper(raw, encoding="utf-8")
            next(rows)
            for line in rows:
                user, bookmark, *_ = line.rstrip("\n").split("\t")
                events.add((int(user), int(bookmark)))
    counts = Counter(bookmark for _, bookmark in events)
    return normalize_weights([counts[key] for key in sorted(counts)])


def load_real_workload(name: str) -> tuple[list[float], dict]:
    """Return a normalized observed-popularity vector and full provenance."""
    path, record = _download(name)
    loaders = {
        "movielens_100k": _movielens,
        "uci_online_retail": _uci_online_retail,
        "wikimedia_pageviews": _wikimedia_pageviews,
        "movielens_32m": _movielens_32m,
        "uci_online_retail_ii": lambda path: _retail_xlsx(
            path,
            ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"),
        ),
        "hetrec_lastfm_2k": _hetrec_lastfm,
        "hetrec_delicious_2k": _hetrec_delicious,
    }
    if name in loaders:
        loader = loaders[name]
    elif name.startswith("wikimedia_"):
        loader = _wikimedia_pageviews
    else:
        raise ValueError(f"no workload parser registered for {name}")
    weights = loader(path)
    return weights, {**record, "keys": len(weights), "aggregation": "frequency count normalized to probability mass"}


def download_sosd_dataset(name: str) -> tuple[Path, dict]:
    """Download and validate one official compressed SOSD key distribution."""
    if name not in SOSD_SOURCES:
        raise ValueError(f"unknown SOSD dataset: {name}")
    source = SOSD_SOURCES[name]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / source["filename"]
    temporary = target.with_suffix(target.suffix + ".part")
    valid = (
        target.exists()
        and target.stat().st_size == source["bytes"]
        and _md5(target) == source["md5"]
    )
    if not valid:
        if shutil.which("aria2c"):
            command = [
                "aria2c",
                "-c",
                "-x",
                "8",
                "-s",
                "8",
                "--min-split-size=4M",
                "--file-allocation=none",
                "-d",
                str(temporary.parent),
                "-o",
                temporary.name,
                source["url"],
            ]
        else:
            command = [
                "curl",
                "-L",
                "--fail",
                "--retry",
                "8",
                "--retry-all-errors",
                "-C",
                "-",
                source["url"],
                "-o",
                str(temporary),
            ]
        subprocess.run(command, check=True)
        if temporary.stat().st_size != source["bytes"]:
            raise ValueError(f"{name} byte-size mismatch")
        if _md5(temporary) != source["md5"]:
            raise ValueError(f"{name} compressed MD5 mismatch")
        temporary.replace(target)
    manifest = _load_manifest()
    record = {
        "url": source["url"],
        "filename": target.name,
        "sha256": _sha256(target),
        "md5": source["md5"],
        "bytes": target.stat().st_size,
        "retrieved_utc": manifest.get(name, {}).get(
            "retrieved_utc", datetime.now(timezone.utc).isoformat()
        ),
        "description": "Official SOSD sorted real-world key distribution.",
        "dataset_class": "sorted_key_distribution",
        "elements": 200_000_000,
        "value_type": source["value_type"],
        "compression": "zstd",
        "license": "SOSD/Harvard Dataverse source terms; DOI 10.7910/DVN/JGVF9A",
    }
    manifest[name] = record
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target, record
