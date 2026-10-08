"""Tie the pieces together: build the LLM cascade and analyse a contract."""

from __future__ import annotations

from dataclasses import asdict

from .analyzer import ClauseAnalyzer, ContractReport
from .config import Settings, get_settings
from .llm.base import LLMClient
from .llm.factory import build_llm


class ContractService:
    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        analyzer: ClauseAnalyzer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm if llm is not None else build_llm(self.settings.llm_spec)
        self.analyzer = analyzer or ClauseAnalyzer(
            llm=self.llm, max_tokens=self.settings.llm_max_tokens
        )

    def analyze(self, contract_text: str) -> ContractReport:
        return self.analyzer.analyze(contract_text)

    def analyze_as_dict(self, contract_text: str) -> dict:
        report = self.analyze(contract_text)
        result = asdict(report)
        result["clauses"] = [
            {
                "index": f.index,
                "heading": f.heading,
                "excerpt": f.excerpt,
                "clause_type": f.clause_type.value,
                "risk": f.risk.value,
                "rationale": f.rationale,
                "source": f.source,
            }
            for f in report.clauses
        ]
        result["overall_risk"] = report.overall_risk.value
        return result
