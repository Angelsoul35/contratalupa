"""The clause vocabulary, the standard-clause checklist, and risk heuristics.

Classification is done by an LLM when one is reachable, but the system must still
work offline and must never trust a model blindly. So the vocabulary, the list of
clauses a sound commercial contract is expected to have, and a set of
keyword-based risk heuristics all live here as plain data. They power the
offline fallback and double-check the model's output.
"""

from __future__ import annotations

from enum import StrEnum


class ClauseType(StrEnum):
    PAYMENT = "payment"
    TERM = "term"
    TERMINATION = "termination"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    WARRANTY = "warranty"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    DATA_PROTECTION = "data_protection"
    NON_COMPETE = "non_compete"
    ASSIGNMENT = "assignment"
    OTHER = "other"


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Clauses a sound B2B services contract is normally expected to contain. Their
# absence is reported so a reviewer can decide whether it is deliberate.
STANDARD_CLAUSES: tuple[ClauseType, ...] = (
    ClauseType.PAYMENT,
    ClauseType.TERM,
    ClauseType.TERMINATION,
    ClauseType.LIABILITY,
    ClauseType.CONFIDENTIALITY,
    ClauseType.INTELLECTUAL_PROPERTY,
    ClauseType.GOVERNING_LAW,
    ClauseType.DISPUTE_RESOLUTION,
    ClauseType.DATA_PROTECTION,
)

# Keyword cues per clause type, used by the offline fallback classifier.
KEYWORDS: dict[ClauseType, tuple[str, ...]] = {
    ClauseType.PAYMENT: ("payment", "invoice", "fee", "fees", "price", "shall pay"),
    ClauseType.TERM: ("term of this agreement", "effective date", "commence", "renew"),
    ClauseType.TERMINATION: ("terminate", "termination", "notice of termination"),
    ClauseType.LIABILITY: ("liability", "liable", "damages", "limitation of liability"),
    ClauseType.INDEMNIFICATION: ("indemnify", "indemnification", "hold harmless"),
    ClauseType.CONFIDENTIALITY: ("confidential", "confidentiality", "non-disclosure"),
    ClauseType.INTELLECTUAL_PROPERTY: (
        "intellectual property",
        "copyright",
        "ownership of",
        "work product",
    ),
    ClauseType.WARRANTY: ("warrant", "warranty", "warranties", "as is"),
    ClauseType.GOVERNING_LAW: ("governing law", "governed by the laws", "jurisdiction"),
    ClauseType.DISPUTE_RESOLUTION: ("arbitration", "dispute", "mediation", "courts of"),
    ClauseType.FORCE_MAJEURE: ("force majeure", "acts of god", "beyond the reasonable control"),
    ClauseType.DATA_PROTECTION: ("personal data", "data protection", "gdpr", "process data"),
    ClauseType.NON_COMPETE: ("non-compete", "shall not compete", "restrictive covenant"),
    ClauseType.ASSIGNMENT: ("assign", "assignment", "transfer this agreement"),
}

# Phrases that raise the risk to the receiving party, with the weight they add.
RISK_PHRASES: tuple[tuple[str, int, str], ...] = (
    ("unlimited liability", 3, "exposes the party to unlimited liability"),
    ("sole discretion", 2, "gives the other party sole discretion"),
    ("irrevocable", 2, "grants an irrevocable right"),
    ("perpetual", 2, "creates a perpetual obligation"),
    ("in perpetuity", 2, "creates an obligation in perpetuity"),
    ("waive", 2, "waives a right"),
    ("without limitation", 1, "uses open-ended 'without limitation' language"),
    ("automatically renew", 2, "renews automatically without action"),
    ("auto-renew", 2, "renews automatically without action"),
    ("indemnify", 1, "imposes an indemnification obligation"),
    ("any and all", 1, "uses broad 'any and all' language"),
    ("exclusive", 1, "grants an exclusive right"),
    ("non-refundable", 1, "makes amounts non-refundable"),
    ("penalty", 1, "imposes a penalty"),
)
