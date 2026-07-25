"""Download and turn public access traces into ordered lookup workloads.

Raw source files are cached locally but never committed.  Every derived run
records source URL, retrieval time, SHA-256, aggregation, and key order.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
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
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
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
    invalid_cache = name == "uci_online_retail" and target.exists() and not zipfile.is_zipfile(target)
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
            if name == "uci_online_retail" and not zipfile.is_zipfile(temporary):
                raise ValueError("UCI response is not a valid XLSX/ZIP container")
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
    }
    manifest[name] = record
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target, record


def _movielens(path: Path) -> list[float]:
    counts: Counter[int] = Counter()
    for line in path.read_text(encoding="latin-1").splitlines():
        _, movie, *_ = line.split("\t")
        counts[int(movie)] += 1
    return normalize_weights([counts[key] for key in range(1, max(counts) + 1)])


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    return ["".join(node.itertext()) for node in root.findall(f"{namespace}si")]


def _uci_online_retail(path: Path) -> list[float]:
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        shared = _xlsx_shared_strings(archive)
        with archive.open("xl/worksheets/sheet1.xml") as sheet:
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
                    cells[column.group(0)] = shared[int(text)] if cell.attrib.get("t") == "s" else text
                # A=InvoiceNo, B=StockCode, D=Quantity.  Exclude cancellations and returns.
                invoice, stock, quantity = cells.get("A", ""), cells.get("B", ""), cells.get("D", "0")
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


def load_real_workload(name: str) -> tuple[list[float], dict]:
    """Return a normalized observed-popularity vector and full provenance."""
    path, record = _download(name)
    loaders = {
        "movielens_100k": _movielens,
        "uci_online_retail": _uci_online_retail,
        "wikimedia_pageviews": _wikimedia_pageviews,
    }
    weights = loaders[name](path)
    return weights, {**record, "keys": len(weights), "aggregation": "frequency count normalized to probability mass"}
