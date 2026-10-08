# ADR 0001: A provider-agnostic LLM with a fallback cascade

## Status

Accepted.

## Context

The analysis depends on a large language model. Binding the code directly to one
vendor's SDK would be a mistake: vendors change pricing and availability,
different models suit different budgets, and a single provider is a single point
of failure. We also want to be able to prefer a cheap or local model first and
only escalate to a stronger one when needed.

## Decision

Depend on one small interface — `LLMClient.complete(system, prompt)` — and wrap
every provider as an adapter behind it. A `CascadeLLM` holds an ordered list of
clients and tries them in turn; if one fails (no key, rate limit, network error,
unparseable response) it moves to the next. The cascade is built from a config
string like `anthropic,openai,gemini,deepseek,ollama`.

The adapters talk plain HTTP with `httpx` rather than each vendor's SDK, so they
are uniform and share one dependency. API keys come only from the environment.

## Consequences

- **Freedom.** Switching or reordering providers is a config change, not a code
  change. A local Ollama model and a hosted model sit behind the same interface.
- **Resilience.** One provider being down, or lacking a key, does not stop the
  analysis; the cascade falls through to the next.
- **Testability.** A `FakeLLM` and a `FailingLLM` implement the same interface,
  so the cascade and the analyser are tested with no network at all.
- **Trade-off.** Plain HTTP adapters mean we maintain a little request/response
  mapping per provider instead of using their SDKs. That cost is small and buys
  uniformity and a single dependency.
