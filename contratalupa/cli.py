"""Contratalupa command-line demo."""

from __future__ import annotations

import argparse

from .analyzer import ClauseAnalyzer
from .samples import SAMPLE_CONTRACT
from .service import ContractService


def demo() -> None:
    print("1) Building the LLM cascade (falls back to offline heuristics) ...")
    service = ContractService()
    print(f"   analyser model: {service.llm.model}")

    print("2) Analysing the sample Master Services Agreement ...")
    report = service.analyze(SAMPLE_CONTRACT)
    print(f"   {len(report.clauses)} clauses, overall risk: {report.overall_risk.value.upper()}")
    print(f"   risk breakdown: {report.risk_counts}")

    print("3) Clause-by-clause:")
    for f in report.clauses:
        marker = {"low": " ", "medium": "!", "high": "!!"}[f.risk.value]
        print(f"   [{marker:2}] {f.clause_type.value:22} ({f.risk.value}) - {f.rationale}")

    print("4) Standard clauses missing from the contract:")
    if report.missing_clauses:
        for name in report.missing_clauses:
            print(f"   - {name}")
    else:
        print("   none")

    print("5) Note: with API keys set (ANTHROPIC/OPENAI/GEMINI/DEEPSEEK), the same")
    print("   run uses the LLM cascade for classification instead of heuristics.")


def analyze_file(path: str) -> None:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    service = ContractService()
    report = service.analyze(text)
    print(f"overall risk: {report.overall_risk.value.upper()}  ({service.llm.model})")
    for f in report.clauses:
        print(f"  {f.clause_type.value:22} {f.risk.value:6} {f.rationale}")
    if report.missing_clauses:
        print("missing:", ", ".join(report.missing_clauses))


def main() -> None:
    parser = argparse.ArgumentParser(description="Contratalupa CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="analyse a built-in sample contract")
    analyze_cmd = sub.add_parser("analyze", help="analyse a contract text file")
    analyze_cmd.add_argument("path", help="path to a plain-text contract")
    args = parser.parse_args()
    if args.command == "demo":
        demo()
    elif args.command == "analyze":
        analyze_file(args.path)


# Expose for tests that build an analyzer directly.
__all__ = ["ClauseAnalyzer", "ContractService", "demo", "main"]


if __name__ == "__main__":
    main()
