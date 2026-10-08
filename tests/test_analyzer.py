from __future__ import annotations

from contratalupa.analyzer import ClauseAnalyzer
from contratalupa.clauses import ClauseType, Risk
from contratalupa.llm.fake import FailingLLM, FakeLLM
from contratalupa.samples import SAMPLE_CONTRACT
from contratalupa.segment import Clause


def _clause(text: str) -> Clause:
    return Clause(index=0, heading="", text=text)


def test_heuristic_classifies_known_clause_types():
    a = ClauseAnalyzer(llm=None)
    assert a._heuristic_type("The Client shall pay all fees within 15 days.") is ClauseType.PAYMENT
    assert (
        a._heuristic_type("This Agreement is governed by the laws of Delaware.")
        is ClauseType.GOVERNING_LAW
    )


def test_heuristic_risk_flags_dangerous_language():
    a = ClauseAnalyzer(llm=None)
    risk, rationale = a._heuristic_risk("The Provider shall bear unlimited liability.")
    assert risk is Risk.HIGH
    assert "unlimited liability" in rationale

    risk, _ = a._heuristic_risk("Each party shall act in good faith.")
    assert risk is Risk.LOW


def test_llm_path_parses_json():
    llm = FakeLLM('{"type": "liability", "risk": "high", "rationale": "unlimited exposure"}')
    finding = ClauseAnalyzer(llm=llm).analyze_clause(_clause("Provider bears all damages."))
    assert finding.clause_type is ClauseType.LIABILITY
    assert finding.risk is Risk.HIGH
    assert finding.source == "llm"
    assert finding.rationale == "unlimited exposure"


def test_llm_failure_falls_back_to_heuristics():
    finding = ClauseAnalyzer(llm=FailingLLM()).analyze_clause(
        _clause("The Provider shall bear unlimited liability.")
    )
    assert finding.source == "heuristic"
    assert finding.clause_type is ClauseType.LIABILITY
    assert finding.risk is Risk.HIGH


def test_malformed_llm_json_falls_back():
    finding = ClauseAnalyzer(llm=FakeLLM("sorry, I cannot help")).analyze_clause(
        _clause("The Client shall pay all fees.")
    )
    assert finding.source == "heuristic"
    assert finding.clause_type is ClauseType.PAYMENT


def test_invalid_type_in_json_is_coerced():
    llm = FakeLLM('{"type": "banana", "risk": "high", "rationale": "x"}')
    finding = ClauseAnalyzer(llm=llm).analyze_clause(
        _clause("The Provider shall bear unlimited liability.")
    )
    # Unknown type -> heuristic type; still an LLM-sourced finding.
    assert finding.source == "llm"
    assert finding.clause_type is ClauseType.LIABILITY


def test_full_report_finds_missing_standard_clauses():
    report = ClauseAnalyzer(llm=None).analyze(SAMPLE_CONTRACT)
    assert report.overall_risk is Risk.HIGH
    assert "data_protection" in report.missing_clauses
    assert "dispute_resolution" in report.missing_clauses
    assert report.risk_counts["high"] >= 1
    assert report.llm_model == "heuristic-only"
