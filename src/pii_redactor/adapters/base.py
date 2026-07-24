"""Document adapter protocol and text segment interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from pii_redactor.domain.span import ResolvedSpan


@dataclass
class TextSegment:
    """A contiguous piece of document text with apply-back capability."""

    text: str
    location: str
    _apply_fn: Callable[[Sequence[ResolvedSpan]], None] = field(repr=False, compare=False)

    def apply(self, spans: Sequence[ResolvedSpan]) -> None:
        self._apply_fn(list(spans))


class DocumentAdapter(ABC):
    """Knows OOXML (or another format); never knows what PII is."""

    @abstractmethod
    def load(self, path: Path) -> None:
        ...

    @abstractmethod
    def iter_segments(self) -> Iterable[TextSegment]:
        ...

    @abstractmethod
    def save(self, path: Path) -> None:
        ...
