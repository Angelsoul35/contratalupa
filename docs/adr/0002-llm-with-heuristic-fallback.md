# ADR 0002: An LLM primary with a deterministic fallback

## Status

Accepted.

## Context

An LLM is excellent at reading a clause and judging its type and risk in natural
language. But it has two failure modes we cannot ignore:

- **It may be unreachable.** No API key, a rate limit, a provider outage, or an
  air-gapped deployment all leave the model unavailable.
- **It may answer badly.** It can return prose instead of JSON, or a clause type
  that is not in our vocabulary.

A tool that returns nothing when the model is down, or that blindly trusts a
malformed answer, is not dependable enough for contract review.

## Decision

Keep a **deterministic fallback** alongside the LLM, built from plain data:

- the clause vocabulary, a standard-clause checklist, and weighted risk phrases
  live in `clauses.py`;
- the analyser asks the LLM for a strict JSON verdict and **validates** it against
  the vocabulary — an unknown clause type is coerced to the heuristic type;
- if the LLM is unreachable or its answer cannot be parsed, the analyser falls
  back entirely to the keyword heuristics.

Every finding records its `source` (`llm` or `heuristic`).

## Consequences

- **Always available.** The service returns a result with or without a model, so
  it runs offline and in CI with no secrets.
- **Never blindly trusting.** The LLM's answer is checked against a known
  vocabulary, and obviously wrong fields are repaired from the heuristics.
- **Transparent.** The `source` field tells a reader how each verdict was reached,
  which matters when a human is deciding whether to rely on it.
- **Trade-off.** The heuristics are coarser than the model — they key off
  phrases, not meaning. They are a safety net and a cross-check, not a
  replacement; when the model is available, its richer judgement is used.
