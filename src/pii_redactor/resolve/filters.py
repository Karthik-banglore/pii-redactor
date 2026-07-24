"""Allowlist and context filters."""

from __future__ import annotations

from typing import List, Sequence

from pii_redactor.domain.policy import DEFAULT_ALLOWLIST, is_allowlisted
from pii_redactor.domain.span import EntityType, Span
import re

_CORP_SUFFIX = re.compile(
    r"\b(Limited|Ltd\.?|Private|Pvt\.?|LLP|Bank|Securities|Capital|"
    r"Management|Advisors?|Associates|Hospital|Technologies|Solutions|"
    r"Industries|International|Corporation|Inc\.?|LLC|PLC|Company)\b",
    re.I,
)


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
        lowered = span.text.strip().lower()
        noise = {
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
        }
        if lowered in noise:
            continue
        # spaCy ORG: keep only if it looks corporate (suffix or multi-word 3+)
        if span.entity_type == EntityType.COMPANY.value and span.source == "spacy_ner":
            text = span.text.strip()
            if not _CORP_SUFFIX.search(text) and text.count(" ") < 2:
                continue
        kept.append(span)
    return kept
