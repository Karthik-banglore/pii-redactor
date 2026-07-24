"""Core domain types shared across adapters and recognizers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EntityType(str, Enum):
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    COMPANY = "COMPANY"
    ADDRESS = "ADDRESS"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    DOB = "DOB"
    IP_ADDRESS = "IP_ADDRESS"
    DIN = "DIN"
    PAN = "PAN"
    CIN = "CIN"
    AADHAAR = "AADHAAR"
    GST = "GST"


@dataclass(frozen=True)
class Span:
    """A detected PII span in joined, human-readable text."""

    start: int
    end: int
    entity_type: str
    text: str
    score: float
    source: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid span bounds: [{self.start}, {self.end})")

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class ResolvedSpan:
    """Span after overlap resolution and surrogate assignment."""

    start: int
    end: int
    entity_type: str
    original: str
    replacement: str
    score: float
    source: str


@dataclass
class Context:
    """Optional detection context (surrounding labels, location hints)."""

    location: str = ""
    preceding_text: str = ""
    following_text: str = ""
