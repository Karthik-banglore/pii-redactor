"""End-to-end redaction pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pii_redactor.adapters.docx.loader import DocxAdapter
from pii_redactor.audit import AuditLog, AuditRecord
from pii_redactor.domain.span import Context, ResolvedSpan
from pii_redactor.recognizers import build_default_registry
from pii_redactor.recognizers.ner import SpacyNERRecognizer
from pii_redactor.resolve.filters import apply_filters
from pii_redactor.resolve.overlap import resolve_overlaps
from pii_redactor.surrogate.provider import SurrogateProvider


class Pipeline:
    def __init__(
        self,
        spacy_model: Optional[str] = None,
        surrogate: Optional[SurrogateProvider] = None,
        use_spacy: bool = True,
    ) -> None:
        model = spacy_model or os.environ.get("SPACY_MODEL", "en_core_web_md")
        self.registry = build_default_registry(
            spacy_model=model if use_spacy else None,
            use_spacy=use_spacy,
        )
        self.surrogate = surrogate or SurrogateProvider()
        self._ner = next(
            (r for r in self.registry if isinstance(r, SpacyNERRecognizer)), None
        )

    def redact(
        self,
        input_path: Path,
        output_path: Path,
        audit_path: Optional[Path] = None,
    ) -> AuditLog:
        adapter = DocxAdapter()
        adapter.load(input_path)
        audit = AuditLog(audit_path)

        segments = list(adapter.iter_segments())

        ner_by_index: List[list] = [[] for _ in segments]
        if self._ner is not None:
            texts = [s.text for s in segments]
            nonempty_idx = [i for i, t in enumerate(texts) if t and t.strip()]
            batch_texts = [texts[i] for i in nonempty_idx]
            if batch_texts:
                batch_results = self._ner.detect_batch(batch_texts)
                for i, spans in zip(nonempty_idx, batch_results):
                    ner_by_index[i] = spans

        for idx, segment in enumerate(segments):
            if not segment.text or not segment.text.strip():
                continue
            ctx = Context(location=segment.location)
            spans = []
            for recognizer in self.registry:
                if isinstance(recognizer, SpacyNERRecognizer):
                    continue
                spans.extend(recognizer.detect(segment.text, ctx))
            spans.extend(ner_by_index[idx])
            spans = apply_filters(spans)
            spans = resolve_overlaps(spans)

            resolved: List[ResolvedSpan] = []
            for span in spans:
                replacement = self.surrogate.fake_for(span.entity_type, span.text)
                resolved.append(
                    ResolvedSpan(
                        start=span.start,
                        end=span.end,
                        entity_type=span.entity_type,
                        original=span.text,
                        replacement=replacement,
                        score=span.score,
                        source=span.source,
                    )
                )
                audit.add(
                    AuditRecord(
                        location=segment.location,
                        entity_type=span.entity_type,
                        original=span.text,
                        replacement=replacement,
                        source=span.source,
                        score=span.score,
                    )
                )
                if span.entity_type == "EMAIL":
                    adapter.register_email_surrogate(span.text, replacement)

            if resolved:
                segment.apply(resolved)

        adapter.save(output_path)
        audit.close()
        return audit


def build_pipeline(
    spacy_model: Optional[str] = None,
    use_spacy: bool = True,
) -> Pipeline:
    return Pipeline(spacy_model=spacy_model, use_spacy=use_spacy)
