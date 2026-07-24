"""Recognizer protocol and registry."""

from __future__ import annotations

from typing import Iterable, List, Protocol, Sequence

from pii_redactor.domain.span import Context, Span


class Recognizer(Protocol):
    entity_type: str

    def detect(self, text: str, ctx: Context) -> List[Span]:
        ...


class RecognizerRegistry:
    def __init__(self, recognizers: Sequence[Recognizer] | None = None) -> None:
        self._recognizers: List[Recognizer] = list(recognizers or [])

    def register(self, recognizer: Recognizer) -> None:
        self._recognizers.append(recognizer)

    def detect_all(self, text: str, ctx: Context | None = None) -> List[Span]:
        ctx = ctx or Context()
        spans: List[Span] = []
        for recognizer in self._recognizers:
            spans.extend(recognizer.detect(text, ctx))
        return spans

    def __iter__(self) -> Iterable[Recognizer]:
        return iter(self._recognizers)

    def __len__(self) -> int:
        return len(self._recognizers)
