"""Classify clauses and assess risk, with an LLM and an offline fallback.

For each clause the analyser asks the LLM to return a strict JSON object with a
clause type, a risk level, and a one-line rationale. If the LLM is unreachable or
its answer cannot be parsed, it falls back to keyword heuristics, so the service
always returns a result. The missing-clause check compares the detected types
against the standard-clause checklist.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .clauses import KEYWORDS, RISK_PHRASES, STANDARD_CLAUSES, ClauseType, Risk
from .llm.base import LLMClient, LLMError
from .segment import Clause, segment

_SYSTEM = (
    "You are a meticulous contract analyst. You classify a single contract clause "
    "and assess its risk to the party receiving the contract. Be conservative and "
    "precise."
)

_ALLOWED_TYPES = ", ".join(t.value for t in ClauseType)

_PROMPT_PREFIX = (
    "Classify the following contract clause.\n"
    "Respond with ONLY a JSON object: "
    '{"type": one of [' + _ALLOWED_TYPES + "], "
    '"risk": one of [low, medium, high], '
    '"rationale": "<one short sentence>"}\n\n'
    "Clause:\n"
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class ClauseFinding:
    index: int
    heading: str
    excerpt: str
    clause_type: ClauseType
    risk: Risk
    rationale: str
    source: str  # "llm" or "heuristic"


@dataclass
class ContractReport:
    clauses: list[ClauseFinding]
    missing_clauses: list[str]
    risk_counts: dict[str, int]
    overall_risk: Risk
    llm_model: str


def _excerpt(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ClauseAnalyzer:
    def __init__(self, llm: LLMClient | None = None, max_tokens: int = 400) -> None:
        self.llm = llm
        self.max_tokens = max_tokens

    # --- offline heuristics -------------------------------------------------
    def _heuristic_type(self, text: str) -> ClauseType:
        low = text.lower()
        best, best_score = ClauseType.OTHER, 0
        for ctype, cues in KEYWORDS.items():
            score = sum(1 for cue in cues if cue in low)
            if score > best_score:
                best, best_score = ctype, score
        return best

    def _heuristic_risk(self, text: str) -> tuple[Risk, str]:
        low = text.lower()
        weight = 0
        reasons: list[str] = []
        for phrase, w, reason in RISK_PHRASES:
            if phrase in low:
                weight += w
                reasons.append(reason)
        if weight >= 3:
            risk = Risk.HIGH
        elif weight >= 1:
            risk = Risk.MEDIUM
        else:
            risk = Risk.LOW
        rationale = "; ".join(reasons) if reasons else "no high-risk language detected"
        return risk, rationale

    # --- LLM path -----------------------------------------------------------
    def _llm_classify(self, text: str) -> tuple[ClauseType, Risk, str]:
        if self.llm is None:
            raise LLMError("no LLM configured")
        result = self.llm.complete(_SYSTEM, _PROMPT_PREFIX + text, max_tokens=self.max_tokens)
        match = _JSON_RE.search(result.text)
        if not match:
            raise LLMError("LLM response had no JSON object")
        data = json.loads(match.group(0))
        try:
            ctype = ClauseType(str(data["type"]).strip().lower())
        except (KeyError, ValueError):
            ctype = self._heuristic_type(text)
        try:
            risk = Risk(str(data["risk"]).strip().lower())
        except (KeyError, ValueError):
            risk, _ = self._heuristic_risk(text)
        rationale = str(data.get("rationale", "")).strip() or "classified by model"
        return ctype, risk, rationale

    # --- public -------------------------------------------------------------
    def analyze_clause(self, clause: Clause) -> ClauseFinding:
        text = clause.full_text
        try:
            ctype, risk, rationale = self._llm_classify(text)
            source = "llm"
        except (LLMError, ValueError, json.JSONDecodeError):
            ctype = self._heuristic_type(text)
            risk, rationale = self._heuristic_risk(text)
            source = "heuristic"
        return ClauseFinding(
            index=clause.index,
            heading=clause.heading,
            excerpt=_excerpt(text),
            clause_type=ctype,
            risk=risk,
            rationale=rationale,
            source=source,
        )

    def analyze(self, contract_text: str) -> ContractReport:
        clauses = segment(contract_text)
        findings = [self.analyze_clause(c) for c in clauses]

        detected = {f.clause_type for f in findings}
        missing = [c.value for c in STANDARD_CLAUSES if c not in detected]

        counts = {level.value: 0 for level in Risk}
        for f in findings:
            counts[f.risk.value] += 1

        if counts[Risk.HIGH.value]:
            overall = Risk.HIGH
        elif counts[Risk.MEDIUM.value]:
            overall = Risk.MEDIUM
        else:
            overall = Risk.LOW

        model = self.llm.model if self.llm is not None else "heuristic-only"
        return ContractReport(
            clauses=findings,
            missing_clauses=missing,
            risk_counts=counts,
            overall_risk=overall,
            llm_model=model,
        )
