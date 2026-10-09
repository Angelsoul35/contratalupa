# Contratalupa

A reading glass for contracts. It segments a contract into clauses, classifies
each one, flags risky language, and reports the standard clauses that are
missing — using a provider-agnostic LLM cascade, with an offline heuristic
fallback so it always returns an answer.

The name is a play on *contrato* (contract) and *lupa* (magnifying glass): it
reads a contract the way a careful reviewer would, and explains what it finds.

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Why it matters

A contract's risk lives in its clauses: an unlimited-liability clause, an
automatic renewal, a broad indemnification, or a standard protection that is
simply absent. Reading every clause of every contract by hand is slow and
uneven. Contratalupa gives a first pass in seconds — a structured, explainable
view a lawyer can then focus and trust.

Two properties make it suitable for this job:

- **Explainable.** Every clause gets a type, a risk level, and a one-line reason.
  Nothing is a black box.
- **Resilient.** It uses an LLM when one is reachable, and falls back to
  deterministic keyword heuristics when none is — so a missing API key or a
  provider outage never leaves you without a result.

## How it works

```mermaid
flowchart LR
    A[Contract text<br/>plain text] --> B[Segment<br/>clauses by numbered/<br/>titled sections]
    B --> C[Classify + risk<br/>LLM cascade JSON,<br/>offline heuristic fallback]
    C --> D[Report<br/>per-clause risk + missing<br/>standard clauses + overall]
```

1. **Segment (`segment.py`).** Splits the text into clauses by recognising
   numbered or titled sections (`1.`, `1.1`, `Section 3`, `ARTICLE IV`), falling
   back to paragraph breaks for unstructured text.
2. **Analyse (`analyzer.py`).** For each clause, it asks the LLM for a strict
   JSON verdict (type, risk, rationale). If the LLM is unreachable or its answer
   cannot be parsed, it falls back to keyword heuristics. It then compares the
   detected clause types against a standard-clause checklist to report what is
   missing.
3. **Orchestrate (`llm/`).** A cascade tries each provider in order
   (Anthropic → OpenAI → Gemini → DeepSeek → Ollama); the first to answer wins,
   and a provider with no key or a transient failure is skipped.

## How the risk score and the JSON contract work

**Risk heuristic.** `clauses.py` holds a weighted list of risk phrases — e.g.
`unlimited liability` (+3), `sole discretion` (+2), `automatically renew` (+2),
`without limitation` (+1). A clause's weight is the sum of the phrases it
contains; `weight ≥ 3 → high`, `≥ 1 → medium`, `0 → low`, and the matched phrases
become the rationale. This runs as the offline fallback *and* as a sanity signal
regardless of the LLM.

**Strict JSON, validated not trusted.** The LLM is asked for exactly
`{"type", "risk", "rationale"}` with the allowed values enumerated in the prompt.
On the way back the analyser extracts the first `{...}` block (models sometimes
wrap JSON in prose), parses it, and **validates** each field against the
`ClauseType` and `Risk` enums — an out-of-vocabulary `type` is coerced to the
heuristic type, a bad `risk` to the heuristic risk, and a response with no JSON
is treated as a provider failure that triggers the fallback. The model proposes;
the vocabulary disposes. Every finding records its `source` (`llm` or
`heuristic`) so a reader knows how it was produced.

**Missing clauses** are a set difference: `STANDARD_CLAUSES − detected_types`.
It surfaces absence (no limitation-of-liability, no data-protection clause), which
is often where the real risk hides, and is treated as a prompt for human review,
not a verdict.

This is decision-support, not legal advice: it gives a fast, explainable first
read for a lawyer to focus and trust, never an automated judgement.

## Validated on real contract clauses (LEDGAR)

Alongside the LLM and the keyword heuristics, Contratalupa ships a third,
data-driven classification path: a trainable offline clause classifier
(`contratalupa/ml.py`, `ClauseClassifier`). It turns each clause into TF-IDF
unigram/bigram features and learns one weight vector per clause type with
multinomial logistic regression. It needs no API key and reports calibrated
per-class probabilities.

To show it generalises to clauses written by other people, it is benchmarked on
**LEDGAR** (part of the LexGLUE legal-NLP benchmark): a balanced slice of the 20
most frequent clause types, 150 clauses each — 3,000 real clauses from U.S. SEC
contract filings, vendored under `datasets/`.

```
$ python -m contratalupa.real_benchmark
dataset        : 3000 clauses, 20 clause types (balanced)
model          : TF-IDF (1-2 grams) + logistic regression, C=2.0
random baseline: 0.050 accuracy (20 classes)

Cross-validation (stratified 5-fold, on the training split)
  macro-F1     : 0.906 +/- 0.007
  accuracy     : 0.906
  per fold F1  : 0.902, 0.903, 0.900, 0.903, 0.920

Held-out test split (never seen while fitting)
  accuracy     : 0.910
  macro-F1     : 0.908

Training split (for the generalisation gap)
  accuracy     : 0.989
  macro-F1     : 0.989

Generalisation
  train -> test accuracy gap : +0.079
  train -> CV macro-F1 gap   : +0.083
  CV vs test macro-F1 agree  : 0.003 apart

Shuffled-label control (labels permuted; signal must vanish)
  CV macro-F1  : 0.053  (vs real 0.906, baseline 0.005)

VERDICT        : WELL-FIT
```

How to read it:

- **Strong signal.** macro-F1 of 0.906 (cross-validation) and 0.908 (held-out
  test) against a most-frequent-class macro-F1 of 0.005 and a 0.05 random-accuracy
  floor on 20 classes.
- **Leakage-free and stable.** The vectoriser is fit only on training folds.
  Stratified 5-fold cross-validation and an untouched held-out test agree to
  within 0.003 macro-F1, with a ±0.007 per-fold spread.
- **Well-fit, not memorised.** The train → cross-validation macro-F1 gap is a
  small +0.083, so the model generalises rather than overfits. The verdict is
  computed from that gap and the CV/test agreement — it reports which conclusion
  the numbers support, it is not asserted.
- **The signal is grounded.** Permuting the labels collapses cross-validated
  macro-F1 from 0.906 to 0.053 (the random floor), which shows the model learns
  real clause structure rather than memorising noise.

Regenerate the data with `python -m contratalupa.real_data`; see
`datasets/README.md` for provenance and license.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Analyse a built-in sample contract (works offline, no API key needed):
python -m contratalupa.cli demo

# Analyse your own contract text file:
python -m contratalupa.cli analyze path/to/contract.txt

# Run the HTTP API:
uvicorn contratalupa.main:app --reload
```

Example API call:

```bash
curl -s -X POST localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"text": "1. Liability. The Provider shall bear unlimited liability..."}'
```

## Using real LLM providers

The analyser is provider-agnostic. Set the API keys for the providers you want
to use; the cascade skips any provider without a key:

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
# GEMINI_API_KEY, DEEPSEEK_API_KEY, or a local OLLAMA_HOST are also supported
```

The order and set of providers is configurable with `CL_LLM_SPEC` (see
`.env.example`). With no keys set, everything still runs on the offline
heuristics.

## Configuration

Settings load from environment variables with the `CL_` prefix:

| Variable            | Default                                      | Meaning                          |
| ------------------- | -------------------------------------------- | -------------------------------- |
| `CL_LLM_SPEC`       | `anthropic,openai,gemini,deepseek,ollama`    | Provider cascade, tried in order |
| `CL_LLM_MAX_TOKENS` | `400`                                        | Max tokens per clause call       |

Provider API keys are read from their own environment variables
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`) and
are never hard-coded.

## Testing

```bash
ruff check contratalupa tests
pytest --cov=contratalupa --cov-report=term-missing --cov-fail-under=80
```

The suite covers segmentation, the clause vocabulary, the analyser (both the LLM
JSON path with a fake client and the heuristic fallback), the LLM cascade and its
fallback behaviour, the HTTP API, the CLI, and the real-data benchmark — the
loader and its exact counts, the trainable classifier, the well-fit verdict, and
the shuffled-label control, with the LEDGAR fetch exercised behind a
monkeypatched `urlopen`. Nothing in the tests touches a real network.

## A note on scope

Contratalupa is a decision-support tool, not legal advice. It gives a fast,
explainable first read; a qualified lawyer makes the call. A production
deployment would add clause-level citations, a configurable checklist per
contract type and jurisdiction, and human-in-the-loop review of every flagged
clause.

## Documentation

- `docs/architecture.md` — the full picture and the data flow.
- `docs/adr/` — the main design decisions and why they were made.
- `docs/estudio/` — a study guide in Spanish, for learning the project in depth,
  including a chapter on the real-data (LEDGAR) evaluation.
- `datasets/README.md` — provenance, license, and how to regenerate the LEDGAR
  benchmark sample.

## License

[MIT](LICENSE) © Angelo David Padilla Romero
