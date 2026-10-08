# ADR 0004: Flag missing clauses from a checklist

## Status

Accepted.

## Context

Much of a contract's risk is in what is **not** there. A services agreement with
no limitation-of-liability clause, no data-protection clause, or no dispute-
resolution mechanism can be far riskier than one with a slightly aggressive
clause. A clause-by-clause reading alone does not surface an absence — you only
notice what is on the page.

## Decision

Keep a checklist of the clauses a sound commercial contract is normally expected
to contain (`STANDARD_CLAUSES`), and after classifying every clause, report which
standard types were **not** detected anywhere in the document. The report lists
them as `missing_clauses`.

## Consequences

- **Absence becomes visible.** A reviewer sees "data protection: missing" rather
  than having to remember to look for it.
- **Simple and explainable.** It is a set difference between the expected types
  and the detected types — easy to reason about and to test.
- **Configurable.** The checklist is plain data, so it can be tailored per
  contract type (an NDA expects a different set than a master services agreement)
  and per jurisdiction.
- **Trade-off.** "Missing" means "no clause was classified as this type", which
  depends on classification quality; a mislabelled clause could make a present
  clause look absent. We treat the list as a prompt for a human to confirm, not a
  final judgement — which is the right posture for a decision-support tool. A
  present-but-weak clause is caught separately by the per-clause risk rating.
