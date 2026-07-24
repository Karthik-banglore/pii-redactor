"""Regex recognizers for structured PII."""

from __future__ import annotations

import re
from typing import List

from pii_redactor.domain.span import Context, EntityType, Span


def _spans_from_pattern(
    text: str,
    pattern: re.Pattern,
    entity_type: str,
    source: str,
    score: float = 0.99,
    group: int = 0,
) -> List[Span]:
    out: List[Span] = []
    for m in pattern.finditer(text):
        out.append(
            Span(
                start=m.start(group),
                end=m.end(group),
                entity_type=entity_type,
                text=m.group(group),
                score=score,
                source=source,
            )
        )
    return out


class EmailRecognizer:
    entity_type = EntityType.EMAIL.value
    _PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    )

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return _spans_from_pattern(
            text, self._PATTERN, self.entity_type, "regex_email"
        )


class PhoneRecognizer:
    """Indian phone variants seen in the prospectus corpus."""

    entity_type = EntityType.PHONE.value
    # +91 / + 91 / 91- with flexible spacing; also bare 10-digit mobiles near Telephone:
    _PATTERN = re.compile(
        r"(?:(?:\+|00)\s*91[\s\-]*)?(?:\(?0?\d{2,4}\)?[\s\-]*)?\d{3,5}[\s\-]?\d{3,5}"
        r"|\b[6-9]\d{9}\b"
    )
    # Reject comma-formatted financials and PIN-like 6-digit with internal space only
    _FINANCIAL = re.compile(r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?")
    _PIN = re.compile(r"\b[1-9]\d{2}\s?\d{3}\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        spans: List[Span] = []
        financial_ranges = [(m.start(), m.end()) for m in self._FINANCIAL.finditer(text)]
        for m in self._PATTERN.finditer(text):
            candidate = m.group(0)
            digits = re.sub(r"\D", "", candidate)
            # Need a plausible phone length
            if len(digits) < 10 or len(digits) > 13:
                continue
            # Skip if entirely inside a financial figure
            if any(fs <= m.start() and m.end() <= fe for fs, fe in financial_ranges):
                continue
            # Bare 6-digit PIN codes should not match; pattern requires 10+ digits usually
            if self._PIN.fullmatch(candidate.strip()) and len(digits) == 6:
                continue
            score = 0.95
            # Context boost near Telephone / Tel / Mobile / Contact
            window = text[max(0, m.start() - 40) : m.start()].lower()
            if any(k in window for k in ("telephone", "tel:", "mobile", "phone", "contact")):
                score = 0.99
            # Prefer numbers that look international / landline with +91
            if "+91" in candidate.replace(" ", "") or "+ 91" in candidate:
                score = max(score, 0.98)
            elif len(digits) == 10 and not digits.startswith(("6", "7", "8", "9")):
                # 10-digit non-mobile without context — likely noise
                if score < 0.98:
                    continue
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    entity_type=self.entity_type,
                    text=candidate,
                    score=score,
                    source="regex_phone",
                )
            )
        return spans


class SSNRecognizer:
    entity_type = EntityType.SSN.value
    _PATTERN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return _spans_from_pattern(text, self._PATTERN, self.entity_type, "regex_ssn")


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class CreditCardRecognizer:
    entity_type = EntityType.CREDIT_CARD.value
    _PATTERN = re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        spans: List[Span] = []
        for m in self._PATTERN.finditer(text):
            raw = m.group(0)
            if _luhn_ok(raw):
                spans.append(
                    Span(
                        start=m.start(),
                        end=m.end(),
                        entity_type=self.entity_type,
                        text=raw,
                        score=0.99,
                        source="regex_credit_card",
                    )
                )
        return spans


class IPAddressRecognizer:
    entity_type = EntityType.IP_ADDRESS.value
    _PATTERN = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    )

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return _spans_from_pattern(
            text, self._PATTERN, self.entity_type, "regex_ip"
        )


class DOBRecognizer:
    entity_type = EntityType.DOB.value
    _PATTERN = re.compile(
        r"\b(?:date of birth|d\.?o\.?b\.?|born on|birth date)\s*[:\-]?\s*"
        r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
        re.IGNORECASE,
    )

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return _spans_from_pattern(
            text, self._PATTERN, self.entity_type, "regex_dob", group=1
        )
