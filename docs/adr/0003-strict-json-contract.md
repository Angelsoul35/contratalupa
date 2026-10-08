# ADR 0003: A strict JSON contract with the model

## Status

Accepted.

## Context

To use the LLM's output in a program, we have to parse it. Free-form prose is
hard to parse reliably and invites ambiguity ("medium-to-high risk", hedged
language, extra commentary). We need a predictable, machine-readable answer we
can validate.

## Decision

Ask the model for **only** a JSON object with three fields — `type`, `risk`,
`rationale` — and give it the exact allowed values for `type` and `risk` in the
prompt. On the way back:

- extract the first `{...}` block from the response (models sometimes wrap JSON
  in prose), and `json.loads` it;
- validate `type` against the `ClauseType` vocabulary and `risk` against the
  `Risk` levels; coerce anything invalid to the heuristic value;
- if there is no JSON at all, treat it as a provider failure and fall back.

## Consequences

- **Predictable parsing.** The program works with structured fields, not prose.
- **Validated, not trusted.** Every field is checked against a known set; the
  model cannot inject an out-of-vocabulary type.
- **Robust to messy output.** Extracting the first JSON block tolerates a model
  that adds a sentence before or after the object.
- **Short and cheap.** A tiny JSON object keeps the token budget per clause low
  (`CL_LLM_MAX_TOKENS` defaults to 400), which matters when a contract has many
  clauses.
- **Trade-off.** A rigid schema gives up some of the model's nuance (it cannot
  explain at length). The one-line `rationale` keeps a human-readable reason while
  staying parseable, which is the right balance for a first-pass tool.
