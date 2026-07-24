"""Redaction policy: allowlists and entity-type configuration."""

from __future__ import annotations

import re
from typing import FrozenSet

# Statutory / market infrastructure — preserve, do not redact.
DEFAULT_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        "SEBI",
        "BSE",
        "NSE",
        "RBI",
        "NCLT",
        "NCLAT",
        "MCA",
        "ROC",
        "CDSL",
        "NSDL",
        "Depositories Act",
        "Companies Act",
        "Securities Act",
        "Registrar of Companies",
        "Ministry of Corporate Affairs",
        "Securities and Exchange Board of India",
        "Reserve Bank of India",
        "Bombay Stock Exchange",
        "National Stock Exchange",
        "BSE Limited",
        "National Stock Exchange of India Limited",
        "Government of India",
        "Government of Maharashtra",
        "Stock Exchanges",
        "Stock Exchange",
    }
)


def is_allowlisted(text: str, allowlist: FrozenSet[str] = DEFAULT_ALLOWLIST) -> bool:
    """Return True if *text* matches an allowlisted name (case-insensitive)."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return False
    lower = cleaned.lower()
    for item in allowlist:
        if lower == item.lower():
            return True
        # Exact token match for short acronyms
        if len(item) <= 5 and re.search(rf"\b{re.escape(item)}\b", cleaned, re.I):
            return True
    return False
