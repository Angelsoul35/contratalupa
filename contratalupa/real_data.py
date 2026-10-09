"""Load and refresh the LEDGAR contract-clause benchmark.

LEDGAR (part of the LexGLUE benchmark) is a public dataset of contract clauses
drawn from US SEC filings: each row is one clause, labelled with one of 100
clause types (``Governing Laws``, ``Notices``, ``Indemnifications``, ...). This
module vendors a balanced subset of the most frequent clause types under
``datasets/`` so the real-data benchmark runs offline and reproducibly, and can
refresh that subset from the Hugging Face datasets-server with ``fetch_ledgar``.

The datasets-server ``rows`` API needs no authentication and is paginated
(``length`` is capped at 100 rows per request), so ``fetch_ledgar`` walks the
train split, buckets clauses by their label name, and keeps the most frequent
clause types in a balanced, deterministic slice.
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.error
from pathlib import Path
from urllib.request import urlopen

#: Hugging Face dataset id and the datasets-server rows endpoint (no auth).
DATASET_ID = "MAdAiLab/lex_glue_ledgar"
_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=MAdAiLab%2Flex_glue_ledgar&config=default&split=train"
)

#: Where the vendored subset lives, relative to the installed package.
DATA_DIR = Path(__file__).resolve().parent.parent / "datasets"
DATA_FILE = DATA_DIR / "ledgar.jsonl.gz"

#: Shape of the vendored subset: the 20 most frequent clause types, balanced.
DEFAULT_N_CLASSES = 20
DEFAULT_PER_CLASS = 150
_PAGE = 100  # datasets-server caps `length` at 100 rows per request.


def _normalize(text: str) -> str:
    """Collapse runs of whitespace, matching how the analyser reads clauses."""
    return " ".join(text.split())


def _fetch_page(offset: int, length: int, *, retries: int = 4, backoff: float = 2.0) -> dict:
    """Fetch one page of rows, retrying transient network failures.

    Retries on URL, timeout and decode errors with exponential backoff
    (``backoff`` seconds, doubling each attempt). ``urlopen`` is referenced as a
    module global so tests can monkeypatch it without touching the network.
    """
    url = f"{_ROWS_URL}&offset={offset}&length={length}"
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(url, timeout=60) as response:  # nosec B310 (fixed HTTPS host)
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
    raise RuntimeError(f"failed to fetch LEDGAR rows at offset {offset}: {last_error}")


def _label_names(page: dict) -> list[str]:
    """Extract the 100 clause-type names that map the integer label field."""
    for feature in page["features"]:
        if feature["name"] == "label":
            return list(feature["type"]["names"])
    raise ValueError("LEDGAR response did not describe the 'label' feature")


def fetch_ledgar(
    n_classes: int = DEFAULT_N_CLASSES,
    per_class: int = DEFAULT_PER_CLASS,
    max_scan_rows: int = 30000,
) -> tuple[list[str], list[str], list[str]]:
    """Fetch a balanced subset of the most frequent LEDGAR clause types.

    Walks the train split one page at a time, buckets clauses by label name, and
    stops once the ``n_classes`` most frequent types each hold at least
    ``per_class`` clauses (or ``max_scan_rows`` is reached). Returns
    ``(texts, labels, label_names)`` where every selected class contributes the
    same number of clauses, taken in dataset order so the slice is reproducible.
    """
    label_names: list[str] | None = None
    buckets: dict[str, list[str]] = {}
    offset = 0
    while offset < max_scan_rows:
        page = _fetch_page(offset, _PAGE)
        if label_names is None:
            label_names = _label_names(page)
        rows = page["rows"]
        if not rows:
            break
        for item in rows:
            row = item["row"]
            name = label_names[row["label"]]
            buckets.setdefault(name, []).append(_normalize(row["text"]))
        offset += len(rows)
        top = sorted(buckets, key=lambda k: len(buckets[k]), reverse=True)[:n_classes]
        if len(top) == n_classes and all(len(buckets[k]) >= per_class for k in top):
            break

    if len(buckets) < n_classes:
        raise RuntimeError(f"found only {len(buckets)} clause types; need {n_classes}")

    selected = sorted(buckets, key=lambda k: (len(buckets[k]), k), reverse=True)[:n_classes]
    available = min(len(buckets[name]) for name in selected)
    take = min(per_class, available)

    texts: list[str] = []
    labels: list[str] = []
    for name in sorted(selected):
        for clause in buckets[name][:take]:
            texts.append(clause)
            labels.append(name)
    return texts, labels, sorted(selected)


def save_ledgar(texts: list[str], labels: list[str], path: Path = DATA_FILE) -> Path:
    """Write the subset as gzip-compressed JSONL (one ``{text, label}`` per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for text, label in zip(texts, labels, strict=True):
            handle.write(json.dumps({"text": text, "label": label}, ensure_ascii=False) + "\n")
    return path


def load_ledgar(path: Path = DATA_FILE) -> tuple[list[str], list[str], list[str]]:
    """Load the vendored subset, returning ``(texts, labels, label_names)``.

    ``label_names`` is the sorted set of clause types present, so callers get a
    stable class order without a separate metadata file.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"vendored LEDGAR subset not found at {path}; "
            "run `python -m contratalupa.real_data` to regenerate it"
        )
    texts: list[str] = []
    labels: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            texts.append(obj["text"])
            labels.append(obj["label"])
    return texts, labels, sorted(set(labels))


def refresh(
    n_classes: int = DEFAULT_N_CLASSES,
    per_class: int = DEFAULT_PER_CLASS,
    path: Path = DATA_FILE,
) -> Path:
    """Refresh the vendored subset from Hugging Face and save it to ``path``."""
    texts, labels, names = fetch_ledgar(n_classes, per_class)
    save_ledgar(texts, labels, path)
    print(f"vendored {len(texts)} clauses across {len(names)} clause types -> {path}")
    return path


if __name__ == "__main__":  # pragma: no cover - manual regeneration entry point
    refresh()
