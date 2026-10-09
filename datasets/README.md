# Vendored benchmark data — LEDGAR

This folder holds a small, balanced sample of the **LEDGAR** contract-clause
classification dataset, vendored so the real-data benchmark
(`python -m contratalupa.real_benchmark`) runs offline and reproducibly.

## What is here

- **`ledgar.jsonl.gz`** — gzip-compressed JSONL, one clause per line:
  `{"text": "<contract clause>", "label": "<clause type>"}`.
  It contains the **20 most frequent clause types**, with **150 clauses each**
  (**3,000 clauses total**), taken in dataset order so the slice is
  deterministic. The classes are balanced, so the random/majority accuracy
  baseline is `1/20 = 0.05`.

## Source

- **Dataset:** [`MAdAiLab/lex_glue_ledgar`](https://huggingface.co/datasets/MAdAiLab/lex_glue_ledgar)
  on the Hugging Face Hub (60,000 training rows, 100 clause types).
- **Origin:** LEDGAR is part of **LexGLUE** (Chalkidis et al., *LexGLUE: A
  Benchmark Dataset for Legal Language Understanding in English*, ACL 2022),
  built from LEDGAR (Tuggener et al., LREC 2020). The clauses are extracted from
  public U.S. SEC EDGAR contract filings.
- **Schema (upstream):** `text` (string) and `label` (a `ClassLabel` integer
  whose `names` list maps each integer to one of 100 clause-type strings).

## License / use

LEDGAR is published as part of LexGLUE for research and benchmarking. The
clauses originate from public SEC EDGAR filings. This repository vendors only a
small educational sample for an offline, reproducible benchmark; consult the
Hugging Face dataset card and the LexGLUE and LEDGAR sources for the
authoritative terms before any other use. Contratalupa's own code is MIT; this
sample is redistributed under the upstream dataset's terms, not MIT.

## How to regenerate

The fetch uses the Hugging Face **datasets-server** `rows` API (no
authentication, paginated at 100 rows per request) with retries:

```
https://datasets-server.huggingface.co/rows?dataset=MAdAiLab%2Flex_glue_ledgar&config=default&split=train&offset=N&length=100
```

From the project root:

```bash
python -m contratalupa.real_data        # refresh ledgar.jsonl.gz in place
```

Programmatically (see `contratalupa/real_data.py`):

```python
from contratalupa.real_data import fetch_ledgar, save_ledgar

texts, labels, names = fetch_ledgar(n_classes=20, per_class=150)
save_ledgar(texts, labels)
```

`fetch_ledgar` walks the train split, buckets clauses by label name, keeps the
most frequent `n_classes` types, and takes `per_class` clauses from each to
build the balanced slice.
