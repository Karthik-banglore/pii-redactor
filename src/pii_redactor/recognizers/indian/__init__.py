"""Indian identifier recognizers (DIN, PAN, CIN, Aadhaar, GST)."""

from __future__ import annotations

import re
from typing import List

from pii_redactor.domain.span import Context, EntityType, Span


class DINRecognizer:
    entity_type = EntityType.DIN.value
    # 8-digit DIN, optionally preceded by "DIN"
    _LABELED = re.compile(r"\bDIN\s*[:\-]?\s*(\d{8})\b", re.IGNORECASE)
    _BARE = re.compile(r"^\s*(\d{8})\s*$")
    _BARE_INLINE = re.compile(r"\b(\d{8})\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        spans: List[Span] = []
        covered = set()
        for m in self._LABELED.finditer(text):
            spans.append(
                Span(
                    start=m.start(1),
                    end=m.end(1),
                    entity_type=self.entity_type,
                    text=m.group(1),
                    score=0.99,
                    source="regex_din",
                )
            )
            covered.add((m.start(1), m.end(1)))

        # Table cells that are exactly an 8-digit DIN (board tables)
        loc = (ctx.location or "").lower()
        if "tbl" in loc or "din" in loc:
            for m in self._BARE.finditer(text):
                key = (m.start(1), m.end(1))
                if key in covered:
                    continue
                spans.append(
                    Span(
                        start=m.start(1),
                        end=m.end(1),
                        entity_type=self.entity_type,
                        text=m.group(1),
                        score=0.95,
                        source="regex_din_cell",
                    )
                )
                covered.add(key)

        window_hint = (ctx.preceding_text + " " + text[:80]).lower()
        if "din" in window_hint:
            for m in self._BARE_INLINE.finditer(text):
                key = (m.start(1), m.end(1))
                if key in covered:
                    continue
                spans.append(
                    Span(
                        start=m.start(1),
                        end=m.end(1),
                        entity_type=self.entity_type,
                        text=m.group(1),
                        score=0.85,
                        source="regex_din_context",
                    )
                )
        return spans


class PANRecognizer:
    entity_type = EntityType.PAN.value
    _PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return [
            Span(
                start=m.start(),
                end=m.end(),
                entity_type=self.entity_type,
                text=m.group(0),
                score=0.95,
                source="regex_pan",
            )
            for m in self._PATTERN.finditer(text)
        ]


class CINRecognizer:
    entity_type = EntityType.CIN.value
    # Corporate Identity Number: L/U + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits
    _PATTERN = re.compile(r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return [
            Span(
                start=m.start(),
                end=m.end(),
                entity_type=self.entity_type,
                text=m.group(0),
                score=0.99,
                source="regex_cin",
            )
            for m in self._PATTERN.finditer(text)
        ]


class AadhaarRecognizer:
    entity_type = EntityType.AADHAAR.value
    _PATTERN = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")

    def detect(self, text: str, ctx: Context) -> List[Span]:
        spans = []
        for m in self._PATTERN.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if len(digits) != 12:
                continue
            spans.append(
                Span(
                    start=m.start(),
                    end=m.end(),
                    entity_type=self.entity_type,
                    text=m.group(0),
                    score=0.9,
                    source="regex_aadhaar",
                )
            )
        return spans


class GSTRecognizer:
    entity_type = EntityType.GST.value
    _PATTERN = re.compile(
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b"
    )

    def detect(self, text: str, ctx: Context) -> List[Span]:
        return [
            Span(
                start=m.start(),
                end=m.end(),
                entity_type=self.entity_type,
                text=m.group(0),
                score=0.95,
                source="regex_gst",
            )
            for m in self._PATTERN.finditer(text)
        ]
