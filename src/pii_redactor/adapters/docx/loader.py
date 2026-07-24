"""Walk a .docx: body paragraphs, nested tables, headers, footers, field codes."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree

from pii_redactor.adapters.base import DocumentAdapter, TextSegment
from pii_redactor.adapters.docx.fields import (
    FieldTextTarget,
    apply_email_replacements,
    find_field_targets,
)
from pii_redactor.adapters.docx.segments import ParagraphView
from pii_redactor.domain.span import ResolvedSpan


class DocxAdapter(DocumentAdapter):
    """OOXML adapter. Detection layers never see this class's internals."""

    def __init__(self) -> None:
        self._doc: Optional[Document] = None
        self._path: Optional[Path] = None
        self._field_targets: List[FieldTextTarget] = []
        self._email_surrogates: dict = {}

    def load(self, path: Path) -> None:
        self._path = Path(path)
        self._doc = Document(str(path))
        self._field_targets = []
        self._collect_field_targets()

    def save(self, path: Path) -> None:
        if self._doc is None:
            raise RuntimeError("No document loaded")
        # Apply pending field-code email replacements before save
        if self._email_surrogates:
            apply_email_replacements(self._field_targets, self._email_surrogates)
            self._email_surrogates = {}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._doc.save(str(path))

    def register_email_surrogate(self, original: str, replacement: str) -> None:
        """Queue a field-code email replacement (applied on save)."""
        self._email_surrogates[original.lower()] = replacement

    def iter_segments(self) -> Iterator[TextSegment]:
        if self._doc is None:
            raise RuntimeError("No document loaded")

        # Body paragraphs (top-level only — tables handled separately)
        for i, para in enumerate(self._doc.paragraphs):
            yield self._para_segment(para, f"body:p{i}")

        # Tables (recursive); python-docx document.paragraphs skips these
        for t_idx, table in enumerate(self._doc.tables):
            yield from self._iter_table(table, f"tbl{t_idx}")

        # Headers / footers
        for s_idx, section in enumerate(self._doc.sections):
            for kind, part in (
                ("header", section.header),
                ("footer", section.footer),
            ):
                if part is None:
                    continue
                for p_idx, para in enumerate(part.paragraphs):
                    yield self._para_segment(para, f"section{s_idx}:{kind}:p{p_idx}")
                for t_idx, table in enumerate(part.tables):
                    yield from self._iter_table(
                        table, f"section{s_idx}:{kind}:tbl{t_idx}"
                    )

        # Field-code text as segments (instr + display) for detection
        for target in self._field_targets:
            yield self._field_segment(target)

    # ------------------------------------------------------------------
    def _para_segment(self, paragraph: Paragraph, location: str) -> TextSegment:
        view = ParagraphView(paragraph)

        def _apply(spans: Sequence[ResolvedSpan]) -> None:
            view.apply(spans)

        return TextSegment(text=view.text, location=location, _apply_fn=_apply)

    def _field_segment(self, target: FieldTextTarget) -> TextSegment:
        def _apply(spans: Sequence[ResolvedSpan]) -> None:
            if not spans:
                return
            # Apply right-to-left on the raw element text
            text = target.text
            ordered = sorted(spans, key=lambda s: s.start, reverse=True)
            for span in ordered:
                if span.start < 0 or span.end > len(text):
                    continue
                text = text[: span.start] + span.replacement + text[span.end :]
                # Also register for mailto pairing if EMAIL
                if span.entity_type == "EMAIL":
                    self.register_email_surrogate(span.original, span.replacement)
            target.text = text

        return TextSegment(
            text=target.text, location=target.location, _apply_fn=_apply
        )

    def _iter_table(self, table: Table, prefix: str) -> Iterator[TextSegment]:
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                for p_idx, para in enumerate(cell.paragraphs):
                    yield self._para_segment(
                        para, f"{prefix}:r{r_idx}c{c_idx}:p{p_idx}"
                    )
                # Nested tables
                for nt_idx, nested in enumerate(cell.tables):
                    yield from self._iter_table(
                        nested, f"{prefix}:r{r_idx}c{c_idx}:nt{nt_idx}"
                    )

    def _collect_field_targets(self) -> None:
        assert self._doc is not None
        # Body
        body = self._doc.element.body
        self._field_targets.extend(find_field_targets(body, "field:body"))

        # Headers / footers via section part XML
        for s_idx, section in enumerate(self._doc.sections):
            for kind, header_footer in (
                ("header", section.header),
                ("footer", section.footer),
            ):
                if header_footer is None:
                    continue
                root = header_footer._element
                self._field_targets.extend(
                    find_field_targets(root, f"field:section{s_idx}:{kind}")
                )


def extract_all_text(path: Path) -> str:
    """Extract every character from body, tables, headers, footers, instrText."""
    adapter = DocxAdapter()
    adapter.load(path)
    parts = [seg.text for seg in adapter.iter_segments()]
    return "\n".join(parts)
