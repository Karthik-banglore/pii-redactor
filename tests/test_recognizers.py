"""Unit tests for pattern recognizers."""

from pii_redactor.domain.span import Context
from pii_redactor.recognizers.indian import CINRecognizer, DINRecognizer, PANRecognizer
from pii_redactor.recognizers.patterns import (
    CreditCardRecognizer,
    EmailRecognizer,
    PhoneRecognizer,
    SSNRecognizer,
)
from pii_redactor.resolve.overlap import resolve_overlaps
from pii_redactor.domain.span import Span


def test_email_detect():
    r = EmailRecognizer()
    spans = r.detect("Write to rajesh.hegde@ksh.com for details", Context())
    assert len(spans) == 1
    assert spans[0].text == "rajesh.hegde@ksh.com"


def test_phone_with_plus91():
    r = PhoneRecognizer()
    text = "Telephone: +91 22 40094400 Email: x@y.com"
    spans = r.detect(text, Context())
    assert any("40094400" in s.text or "2240094400" in s.text.replace(" ", "") for s in spans)


def test_phone_rejects_financial():
    r = PhoneRecognizer()
    text = "Revenue was 1,234,567.89 in Fiscal 2025"
    spans = r.detect(text, Context())
    assert spans == []


def test_ssn():
    r = SSNRecognizer()
    spans = r.detect("SSN 123-45-6789 on file", Context())
    assert len(spans) == 1


def test_credit_card_luhn():
    r = CreditCardRecognizer()
    # Valid Visa test number
    spans = r.detect("Card 4111 1111 1111 1111", Context())
    assert len(spans) == 1
    # Invalid Luhn
    bad = r.detect("Card 4111 1111 1111 1112", Context())
    assert bad == []


def test_din_labeled():
    r = DINRecognizer()
    spans = r.detect("DIN: 00135070", Context())
    assert len(spans) == 1
    assert spans[0].text == "00135070"


def test_pan():
    r = PANRecognizer()
    spans = r.detect("PAN ABCDE1234F filed", Context())
    assert len(spans) == 1


def test_cin():
    r = CINRecognizer()
    spans = r.detect("CIN U28129PN1979PLC141032", Context())
    assert len(spans) == 1


def test_overlap_email_beats_person():
    email = Span(9, 30, "EMAIL", "rajesh.hegde@ksh.com", 0.99, "regex_email")
    person = Span(9, 21, "PERSON", "rajesh.hegde", 0.8, "spacy_ner")
    resolved = resolve_overlaps([email, person])
    assert len(resolved) == 1
    assert resolved[0].entity_type == "EMAIL"
