"""Allowlist and context filters."""

from __future__ import annotations

import re
from typing import List, Sequence, Set

from pii_redactor.domain.policy import DEFAULT_ALLOWLIST, is_allowlisted
from pii_redactor.domain.span import EntityType, Span

_CORP_SUFFIX = re.compile(
    r"\b(Limited|Ltd\.?|Private|Pvt\.?|LLP|Bank|Securities|Capital|"
    r"Management|Advisors?|Associates|Hospital|Technologies|Solutions|"
    r"Industries|International|Corporation|Inc\.?|LLC|PLC|Company)\b",
    re.I,
)

# Exact phrases that look like PERSON/ORG to NER but are prospectus headings / labels.
_HEADING_EXACT: Set[str] = {
    "bid amount",
    "bid amounts",
    "blocked amount",
    "offered shares",
    "total dues",
    "total income",
    "total chakan unit",
    "proposed capital expenditure",
    "capital employed",
    "capital market division",
    "corporate identity number",
    "authorised share capital",
    "authorized share capital",
    "promoter selling shareholder",
    "promoter selling shareholders",
    "the promoter selling shareholder",
    "the promoter selling shareholders",
    "aggregate amount of",
    "post-offer equity share",
    "this red herring prospectus",
    "red herring prospectus",
    "face value",
    "offer price",
    "issue size",
    "net proceeds",
    "objects of the offer",
    "risk factors",
    "forward looking statements",
    "financial information",
    "capital structure",
    "our management",
    "our promoter",
    "our business",
    "legal proceedings",
    "other information",
    "declaration",
    "particulars",
    "description",
    "amount",
    "total",
}

# Substrings: if the whole span is mostly this jargon, drop it.
_HEADING_SUBSTR: tuple[str, ...] = (
    "selling shareholder",
    "bid amount",
    "blocked amount",
    "offered share",
    "capital expenditure",
    "share capital",
    "identity number",
    "exchange board of india",
    "issue of capital",
    "disclosure requ",
    "venture capital",
    "equity share",
    "face value",
    "net worth",
    "working capital",
    "fixed asset",
    "current asset",
    "current liabilit",
    "profit after tax",
    "profit before tax",
    "earnings per share",
    "book value",
    "debt equity",
)

_NOISE_EXACT: Set[str] = {
    "company",
    "our company",
    "the company",
    "the offer",
    "bidder",
    "bidders",
    "india",
    "maharashtra",
    "mumbai",
    "pune",
    "delhi",
    "fiscal",
    "offer",
    "equity",
    "shares",
    "prospectus",
    "amount",
    "total",
    "particulars",
    "description",
    "remarks",
    "notes",
    "note",
    "sr no",
    "s no",
    "sl no",
}


def _is_heading_noise(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", text.strip().lower())
    # Strip trailing footnote markers like (1
    lowered = re.sub(r"[\s\(\[]+\d+[\)\]]?$", "", lowered).strip(" ,.-")
    if not lowered:
        return True
    if lowered in _HEADING_EXACT or lowered in _NOISE_EXACT:
        return True
    if any(s in lowered for s in _HEADING_SUBSTR):
        # Keep real company names that merely mention "capital" via corp suffix
        # only if they also look corporate AND are longer than a label.
        if _CORP_SUFFIX.search(text) and text.count(" ") >= 2 and len(lowered) > 40:
            return False
        return True
    # ALL-CAPS short financial headers (2–4 tokens, no person-like shape)
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if (
        2 <= len(words) <= 5
        and all(re.fullmatch(r"[A-Z0-9/()'&\-.,]+", w) for w in words)
        and not any(re.search(r"[a-z]", w) for w in words)
    ):
        finance = {
            "AMOUNT",
            "TOTAL",
            "SHARE",
            "SHARES",
            "CAPITAL",
            "EQUITY",
            "OFFER",
            "BID",
            "VALUE",
            "INCOME",
            "DUES",
            "BOARD",
            "ISSUE",
            "NUMBER",
            "IDENTITY",
            "CORPORATE",
            "AUTHORISED",
            "AUTHORIZED",
            "AGGREGATE",
            "PROPOSED",
            "EXPENDITURE",
            "PROCEEDS",
            "PARTICULARS",
            "DESCRIPTION",
        }
        if sum(1 for w in words if w.strip("().,") in finance) >= 1:
            return True
    return False


def apply_filters(spans: Sequence[Span]) -> List[Span]:
    """Drop allowlisted companies/names and other non-PII noise."""
    kept: List[Span] = []
    for span in spans:
        if span.entity_type == EntityType.COMPANY.value and is_allowlisted(
            span.text, DEFAULT_ALLOWLIST
        ):
            continue
        if span.entity_type == EntityType.PERSON.value and is_allowlisted(
            span.text, DEFAULT_ALLOWLIST
        ):
            continue
        if span.entity_type in {
            EntityType.PERSON.value,
            EntityType.COMPANY.value,
            EntityType.ADDRESS.value,
        } and _is_heading_noise(span.text):
            continue
        # spaCy ORG: keep only if it looks corporate (suffix or multi-word 3+)
        if span.entity_type == EntityType.COMPANY.value and span.source == "spacy_ner":
            text = span.text.strip()
            if not _CORP_SUFFIX.search(text) and text.count(" ") < 2:
                continue
        kept.append(span)
    return kept
