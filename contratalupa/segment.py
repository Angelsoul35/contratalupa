"""Split a contract's plain text into individual clauses.

Contracts are written as numbered or titled sections. The segmenter recognises
the common patterns — ``1.`` / ``1.1`` / ``Section 3`` / ``ARTICLE IV`` / an
ALL-CAPS heading — and groups each heading with the text that follows it. If no
headings are found, it falls back to splitting on blank lines, so even an
unstructured document yields clauses to analyse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A line that starts a new clause: "1.", "1.1", "12)", "Section 4", "Article V",
# or a short ALL-CAPS title line.
_HEADING = re.compile(
    r"""^\s*(
        (?:\d+(?:\.\d+)*[.)]?\s)            # 1.  1.1  2)
        | (?:section\s+\d+)                 # Section 3
        | (?:article\s+[ivxlcdm\d]+)        # Article IV
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_CAPS_TITLE = re.compile(r"^\s*[A-Z][A-Z \-/&]{3,60}\s*$")


@dataclass(frozen=True)
class Clause:
    index: int
    heading: str
    text: str

    @property
    def full_text(self) -> str:
        return f"{self.heading} {self.text}".strip() if self.heading else self.text


def _is_heading(line: str) -> bool:
    return bool(_HEADING.match(line)) or bool(_CAPS_TITLE.match(line))


def segment(contract: str) -> list[Clause]:
    lines = [ln.rstrip() for ln in contract.strip().splitlines()]
    blocks: list[list[str]] = []
    current: list[str] = []

    found_heading = any(_is_heading(ln) for ln in lines if ln.strip())

    if found_heading:
        for line in lines:
            if not line.strip():
                continue
            if _is_heading(line) and current:
                blocks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append(current)
    else:
        # No headings: split on blank-line paragraph breaks.
        paragraph: list[str] = []
        for line in lines:
            if line.strip():
                paragraph.append(line)
            elif paragraph:
                blocks.append(paragraph)
                paragraph = []
        if paragraph:
            blocks.append(paragraph)

    clauses: list[Clause] = []
    for i, block in enumerate(blocks):
        first = block[0].strip()
        if found_heading and _is_heading(first):
            # Separate the heading token from any text on the same line.
            rest = block[1:]
            heading = first
            body = " ".join(line.strip() for line in rest)
            if not body and len(first.split()) > 4:
                heading, body = "", first
            clauses.append(Clause(index=i, heading=heading, text=body))
        else:
            clauses.append(Clause(index=i, heading="", text=" ".join(b.strip() for b in block)))
    return clauses
