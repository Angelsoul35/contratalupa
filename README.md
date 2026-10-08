# Contratalupa

A reading glass for contracts. It segments a contract into clauses, classifies
each one, flags risky language, and reports the standard clauses that are
missing — using a provider-agnostic LLM cascade, with an offline heuristic
fallback so it always returns an answer.

The name is a play on *contrato* (contract) and *lupa* (magnifying glass): it
reads a contract the way a careful reviewer would, and explains what it finds.

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

```
 contract text        segment              classify + risk          report
 ─────────────    ───────────────    ──────────────────────    ────────────────
 plain text   ─▶  clauses (by     ─▶  LLM cascade (JSON) with ─▶ per-clause risk +
                  numbered/titled      offline heuristic          missing standard
                  sections)            fallback                   clauses + overall
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
fallback behaviour, the HTTP API, and the CLI. Nothing in the tests touches a
real network.

## A note on scope

Contratalupa is a decision-support tool, not legal advice. It gives a fast,
explainable first read; a qualified lawyer makes the call. A production
deployment would add clause-level citations, a configurable checklist per
contract type and jurisdiction, and human-in-the-loop review of every flagged
clause.

## Documentation

- `docs/architecture.md` — the full picture and the data flow.
- `docs/adr/` — the main design decisions and why they were made.
- `docs/estudio/` — a study guide in Spanish, for learning the project in depth.

## License

MIT. See [LICENSE](LICENSE).
