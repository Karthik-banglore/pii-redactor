"""Overlap / conflict resolution for competing spans."""

from __future__ import annotations

from typing import List, Sequence

from pii_redactor.domain.span import Span

# Prefer regex sources over NER when scores tie
_REGEX_PREFIXES = ("regex_", "field_code")


def _is_regex(source: str) -> bool:
    return any(source.startswith(p) for p in _REGEX_PREFIXES)


def resolve_overlaps(spans: Sequence[Span]) -> List[Span]:
    """
    Resolve overlapping spans.

    Rules (in order):
      1. Longest span wins
      2. Higher score wins
      3. Regex beats NER
    """
    if not spans:
        return []

    # Sort: longer first, then higher score, then regex preferred
    ordered = sorted(
        spans,
        key=lambda s: (
            s.length,
            s.score,
            1 if _is_regex(s.source) else 0,
        ),
        reverse=True,
    )

    accepted: List[Span] = []
    for candidate in ordered:
        conflict = False
        for kept in accepted:
            if _overlaps(candidate, kept):
                conflict = True
                break
        if not conflict:
            accepted.append(candidate)

    # Return in document order
    return sorted(accepted, key=lambda s: (s.start, s.end))


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end
