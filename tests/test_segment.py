from __future__ import annotations

from contratalupa.samples import SAMPLE_CONTRACT
from contratalupa.segment import segment


def test_numbered_contract_splits_into_clauses():
    clauses = segment(SAMPLE_CONTRACT)
    # The title plus eight numbered sections.
    assert len(clauses) >= 8
    headings = [c.heading for c in clauses if c.heading]
    assert any(h.startswith("1.") for h in headings)
    assert any(h.startswith("8.") for h in headings)


def test_clause_full_text_combines_heading_and_body():
    clauses = segment("1. Payment. The Client shall pay all fees.")
    assert clauses[0].full_text.startswith("1.")
    assert "pay all fees" in clauses[0].full_text


def test_fallback_splits_on_blank_lines_without_headings():
    text = "This is the first paragraph with no heading.\n\nAnd here is a second one."
    clauses = segment(text)
    assert len(clauses) == 2
    assert all(c.heading == "" for c in clauses)


def test_section_and_article_headings_are_detected():
    text = (
        "Section 1 Confidentiality. Keep it secret.\n\n"
        "Article II Governing Law. Laws of Delaware apply."
    )
    clauses = segment(text)
    assert len(clauses) == 2
