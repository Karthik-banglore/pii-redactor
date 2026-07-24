"""Join fragmented Word runs into readable text with an offset→run map."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from docx.text.paragraph import Paragraph
from docx.text.run import Run

from pii_redactor.domain.span import ResolvedSpan


@dataclass
class RunSlice:
    """Maps a character range in joined text back to a single run."""

    run_index: int
    start: int  # inclusive, in joined text
    end: int  # exclusive
    run: Run


@dataclass
class ParagraphView:
    """
    Reconstructs logical paragraph text from fragmented runs and maps
    character offsets back onto those runs for write-back.
    """

    paragraph: Paragraph
    text: str = ""
    run_map: List[RunSlice] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.text and not self.run_map:
            self._build()

    def _build(self) -> None:
        pieces: List[str] = []
        mapping: List[RunSlice] = []
        cursor = 0
        for idx, run in enumerate(self.paragraph.runs):
            # run.text already maps <w:tab/> → \t and <w:br/> → \n
            chunk = run.text or ""
            start = cursor
            end = start + len(chunk)
            mapping.append(RunSlice(run_index=idx, start=start, end=end, run=run))
            pieces.append(chunk)
            cursor = end
        self.text = "".join(pieces)
        self.run_map = mapping

    def apply(self, spans: Sequence[ResolvedSpan]) -> None:
        """Rewrite runs so each resolved span becomes its replacement text.

        Spans are applied right-to-left so earlier character offsets stay valid.
        Formatting of the first overlapped run is preserved.
        """
        if not spans:
            return
        ordered = sorted(spans, key=lambda s: s.start, reverse=True)
        for span in ordered:
            self._apply_one(span.start, span.end, span.replacement)
        # Rebuild map so subsequent applies see fresh offsets
        self._build()

    def _apply_one(self, start: int, end: int, replacement: str) -> None:
        if start < 0 or end > len(self.text) or start > end:
            raise ValueError(
                f"Span [{start}, {end}) out of bounds for text length {len(self.text)}"
            )
        if start == end and not replacement:
            return

        overlapped = [rs for rs in self.run_map if rs.end > start and rs.start < end]
        if not overlapped:
            # Empty paragraph / empty span edge case
            if self.run_map and start == end == 0 and replacement:
                self.run_map[0].run.text = replacement + (self.run_map[0].run.text or "")
            return

        first = overlapped[0]
        last = overlapped[-1]

        prefix = (first.run.text or "")[: max(0, start - first.start)]
        suffix = (last.run.text or "")[max(0, end - last.start) :]

        first.run.text = prefix + replacement + (suffix if first is last else "")
        if first is not last:
            last.run.text = suffix
            for mid in overlapped[1:-1]:
                mid.run.text = ""
            # If first != last we already put suffix on last; clear any leftover
            # on first beyond prefix+replacement (already done above).
        # Blank any fully-covered middle runs already handled; if only one run,
        # prefix+replacement+suffix is complete.
