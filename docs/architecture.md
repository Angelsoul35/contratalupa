# Architecture

Contratalupa reads a contract, splits it into clauses, classifies and risk-rates
each one, and reports missing standard clauses. This document describes the
pieces, the data flow, and the boundaries between them.

## The pieces

| Layer          | Module                      | Responsibility                                            |
| -------------- | --------------------------- | --------------------------------------------------------- |
| Vocabulary     | `contratalupa/clauses.py`   | Clause types, the standard-clause checklist, risk cues    |
| Segmentation   | `contratalupa/segment.py`   | Split contract text into clauses                          |
| Analysis       | `contratalupa/analyzer.py`  | Classify + risk-rate each clause; find missing clauses    |
| LLM interface  | `contratalupa/llm/base.py`  | The provider-agnostic `LLMClient` protocol                |
| Providers      | `contratalupa/llm/providers.py` | HTTP adapters for Anthropic/OpenAI/Gemini/DeepSeek/Ollama |
| Cascade        | `contratalupa/llm/cascade.py` | Try providers in order, fall back on failure            |
| Orchestration  | `contratalupa/service.py`   | Build the cascade and analyse a contract                  |
| HTTP API       | `contratalupa/main.py`      | Expose analysis over REST                                 |
| CLI            | `contratalupa/cli.py`       | Analyse the sample or a text file                         |

## Data flow

```
┌──────────────┐  segment()  ┌──────────────┐  per clause  ┌──────────────────┐
│ contract text│ ──────────▶ │ list[Clause] │ ───────────▶ │ LLM JSON verdict  │
└──────────────┘             └──────────────┘               │  or heuristic     │
                                                             └─────────┬─────────┘
                                                                       ▼
                                                        ┌──────────────────────────┐
                                                        │ ContractReport            │
                                                        │ findings, missing, risk   │
                                                        └──────────────────────────┘
```

## Two design ideas carry the project

### 1. Provider-agnostic LLM with a cascade

The code depends on one small interface — `LLMClient.complete(system, prompt)` —
not on any vendor. Each provider (Anthropic, OpenAI, Gemini, DeepSeek, a local
Ollama model) is an adapter behind that interface. A `CascadeLLM` tries them in
order and falls back on any failure.

This gives two things at once: **freedom** (switch or reorder providers with a
config string, prefer a cheap or local model first) and **resilience** (one
provider down, or without a key, does not stop the analysis). The adapters talk
plain HTTP with `httpx`, so they are uniform and share one dependency; API keys
come only from the environment.

### 2. LLM plus an offline fallback, with the rules as a safety net

An LLM is the primary classifier, but the system must never be helpless without
it, and must never trust it blindly. So the clause vocabulary, the
standard-clause checklist, and keyword risk cues live as plain data in
`clauses.py`. When the LLM is reachable, the analyser asks it for a strict JSON
verdict and validates the answer against that vocabulary (an unknown type is
coerced to a heuristic one). When the LLM is unreachable or returns unparseable
text, the analyser falls back entirely to the keyword heuristics.

Every finding records its `source` (`llm` or `heuristic`), so a reader always
knows how a verdict was reached.

## Segmentation

Contracts are written as numbered or titled sections. The segmenter recognises
the common patterns (`1.`, `1.1`, `Section 3`, `ARTICLE IV`, ALL-CAPS titles) and
groups each heading with the text beneath it. With no headings, it splits on
blank-line paragraph breaks, so an unstructured document still yields clauses.
Segmentation is deliberately simple and deterministic; it is the input to the
analysis, not the place for judgement.

## The report

`ContractReport` carries:

- `clauses` — one `ClauseFinding` each (index, heading, excerpt, type, risk,
  rationale, source);
- `missing_clauses` — standard clauses not detected anywhere;
- `risk_counts` — how many clauses at each risk level;
- `overall_risk` — high if any clause is high, else medium if any is medium, else
  low;
- `llm_model` — the model (or `heuristic-only`) that produced the findings.

## Extension points

- **Checklist.** `STANDARD_CLAUSES` can vary by contract type and jurisdiction;
  it is plain data, easy to parameterise.
- **Risk cues.** `RISK_PHRASES` is a weighted list; new phrases drop straight in.
- **Providers.** A new LLM provider is one adapter implementing `LLMClient` plus
  one line in the provider registry.
- **Prompt.** The clause-classification prompt lives in one place in
  `analyzer.py` and can be tuned without touching the rest.
