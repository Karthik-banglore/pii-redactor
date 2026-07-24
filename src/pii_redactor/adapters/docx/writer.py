"""Apply resolved spans onto paragraph runs (thin wrapper around ParagraphView)."""

from __future__ import annotations

from typing import Sequence

from docx.text.paragraph import Paragraph

from pii_redactor.adapters.docx.segments import ParagraphView
from pii_redactor.domain.span import ResolvedSpan


def apply_spans_to_paragraph(paragraph: Paragraph, spans: Sequence[ResolvedSpan]) -> None:
    """Apply *spans* to *paragraph*, preserving first-run formatting."""
    view = ParagraphView(paragraph)
    view.apply(spans)


def paragraph_text(paragraph: Paragraph) -> str:
    """Joined human-readable text for a paragraph."""
    return ParagraphView(paragraph).text
