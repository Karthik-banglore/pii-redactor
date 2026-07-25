"""Conservative Title-Case person-name pattern (helps when spaCy misses Indian names)."""

from __future__ import annotations

import re
from typing import List, Set

from pii_redactor.domain.span import Context, EntityType, Span

_DENY: Set[str] = {
    "red herring",
    "prospectus",
    "book built",
    "offer document",
    "equity shares",
    "face value",
    "risk factors",
    "forward looking",
    "financial statements",
    "board of directors",
    "managing director",
    "independent director",
    "executive director",
    "whole time",
    "company secretary",
    "compliance officer",
    "lead managers",
    "registrar to",
    "stock exchange",
    "government of",
    "state of",
    "union of",
    "dated",
    "page",
    "section",
    "chapter",
    "table of",
    "as on",
    "for the",
    "in the",
    "of the",
    "and the",
    "fiscal year",
    "three month",
    "power sector",
    "raw materials",
    "magnet winding",
    "our promoter",
    "our management",
    "promoter group",
    "group entities",
    "capital structure",
    "equity share",
    "infra park",
    "parents branch",
    "rajesh branch",
    "sangeeta branch",
    "rakhi branch",
    "rohit branch",
    "individual promoters",
    "waterloo industrial",
    "kushal motors",
    # Table / financial headings mistaken for person names
    "corporate identity",
    "identity number",
    "bid amount",
    "blocked amount",
    "offered shares",
    "total dues",
    "total income",
    "capital employed",
    "capital expenditure",
    "share capital",
    "selling shareholder",
    "aggregate amount",
    "authorised share",
    "authorized share",
    "net proceeds",
    "issue size",
    "offer price",
    "working capital",
    "fixed assets",
    "current assets",
    "profit after",
    "profit before",
    "earnings per",
    "book value",
}

_START_DENY: Set[str] = {
    "individual",
    "promoters",
    "promoter",
    "our",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "such",
    "under",
    "above",
    "below",
    "chapter",
    "section",
    "table",
    "form",
    "annexure",
    "schedule",
    "clause",
    "article",
    "regulation",
    "company",
    "board",
    "director",
    "directors",
    "equity",
    "share",
    "shares",
    "capital",
    "structure",
    "group",
    "entities",
    "branch",
    "parents",
    "waterloo",
    "industrial",
    "park",
    "infra",
    "motors",
    "management",
    "certain",
    "further",
    "details",
    "corporate",
    "authorised",
    "authorized",
    "aggregate",
    "proposed",
    "blocked",
    "offered",
    "total",
    "bid",
    "net",
    "face",
    "issue",
    "particulars",
    "description",
    "amount",
}

_SUFFIX_DENY = re.compile(
    r"\b(Limited|Ltd|Private|Pvt|LLP|Bank|Securities|Hospital|University|"
    r"College|School|Society|Trust|Fund|Committee|Commission|Ministry|"
    r"Department|Authority|Exchange|Corporation|Inc|LLC|PLC|Promoters?|"
    r"Branch|Park|Structure|Entities|Management|Director|Directors)\b",
    re.I,
)

# Prefer 2–3 word Title Case names; allow optional middle initial
_NAME = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-z]+){1,2})\b"
)
# ALL CAPS person names (common in prospectus tables / offer summaries)
_NAME_CAPS = re.compile(
    r"\b([A-Z]{2,}(?:\s+[A-Z]\.)?(?:\s+[A-Z]{2,}){1,2})\b"
)


class PersonNameRecognizer:
    entity_type = EntityType.PERSON.value

    def detect(self, text: str, ctx: Context) -> List[Span]:
        spans: List[Span] = []
        spans.extend(self._match(text, _NAME))
        spans.extend(self._match(text, _NAME_CAPS))
        return spans

    def _match(self, text: str, pattern: re.Pattern) -> List[Span]:
        spans: List[Span] = []
        for m in pattern.finditer(text):
            candidate = m.group(1).strip()
            lower = candidate.lower()
            if any(d in lower for d in _DENY):
                continue
            if _SUFFIX_DENY.search(candidate):
                continue
            words = candidate.split()
            if len(words) < 2 or len(words) > 3:
                continue
            first = words[0].lower().rstrip(".")
            if first in _START_DENY:
                continue
            if all(len(w.rstrip(".")) <= 2 for w in words):
                continue
            # Skip ALL CAPS that look like section / table headers
            if candidate.isupper() and any(w in {
                "VALUE", "EACH", "FACE", "OFFER", "EQUITY", "SHARE", "SHARES",
                "RISK", "FACTORS", "BOARD", "DIRECTORS", "LIMITED", "PRIVATE",
                "AMOUNT", "TOTAL", "BID", "BLOCKED", "CAPITAL", "INCOME",
                "DUES", "IDENTITY", "NUMBER", "CORPORATE", "AUTHORISED",
                "AUTHORIZED", "AGGREGATE", "PROPOSED", "EXPENDITURE",
                "PARTICULARS", "DESCRIPTION", "PROCEEDS", "ISSUE",
            } for w in words):
                continue
            spans.append(
                Span(
                    start=m.start(1),
                    end=m.end(1),
                    entity_type=self.entity_type,
                    text=candidate,
                    score=0.72,
                    source="regex_person_name",
                )
            )
        return spans
