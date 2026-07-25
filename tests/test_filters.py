"""Heading / financial-label noise filters."""

from pii_redactor.domain.span import Span
from pii_redactor.resolve.filters import apply_filters


def _span(text: str, etype: str = "PERSON", source: str = "regex_person_name") -> Span:
    return Span(
        start=0,
        end=len(text),
        entity_type=etype,
        text=text,
        score=0.8,
        source=source,
    )


def test_drops_table_headings():
    noisy = [
        _span("CORPORATE IDENTITY NUMBER"),
        _span("Bid Amount", "COMPANY", "spacy_ner"),
        _span("Total Dues", "COMPANY", "spacy_ner"),
        _span("Promoter Selling Shareholders", "COMPANY", "spacy_ner"),
        _span("this Red Herring Prospectus", "COMPANY", "spacy_ner"),
    ]
    kept = apply_filters(noisy)
    assert kept == []


def test_keeps_real_person_and_company():
    good = [
        _span("Rashi Patil"),
        _span("Acme Private Limited", "COMPANY", "spacy_ner"),
    ]
    kept = apply_filters(good)
    assert [s.text for s in kept] == ["Rashi Patil", "Acme Private Limited"]
