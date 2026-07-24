"""spaCy NER recognizer for PERSON / COMPANY / ADDRESS."""

from __future__ import annotations

import os
from typing import List, Optional

from pii_redactor.domain.span import Context, EntityType, Span

_NLP = None


def get_nlp(model: Optional[str] = None):
    """Load spaCy model once (module-level cache)."""
    global _NLP
    if _NLP is not None:
        return _NLP
    import spacy

    name = model or os.environ.get("SPACY_MODEL", "en_core_web_md")
    try:
        _NLP = spacy.load(name, disable=["lemmatizer", "textcat"])
    except OSError:
        # Fallback to blank English if model missing (tests / CI)
        _NLP = spacy.blank("en")
    return _NLP


# spaCy label → our entity type
_LABEL_MAP = {
    "PERSON": EntityType.PERSON.value,
    "ORG": EntityType.COMPANY.value,
    "GPE": EntityType.ADDRESS.value,
    "LOC": EntityType.ADDRESS.value,
    "FAC": EntityType.ADDRESS.value,
}


class SpacyNERRecognizer:
    """Detects PERSON, COMPANY, ADDRESS via spaCy NER."""

    entity_type = "NER"  # multi-type

    def __init__(self, model: Optional[str] = None) -> None:
        self._model_name = model
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = get_nlp(self._model_name)
        return self._nlp

    def detect(self, text: str, ctx: Context) -> List[Span]:
        if not text or not text.strip():
            return []
        # Skip very long segments in chunks to avoid memory spikes
        if len(text) > 100_000:
            text = text[:100_000]
        doc = self.nlp(text)
        spans: List[Span] = []
        for ent in doc.ents:
            etype = _LABEL_MAP.get(ent.label_)
            if not etype:
                continue
            # Drop tiny ORG tokens that are just common words
            if etype == EntityType.COMPANY.value and len(ent.text.strip()) < 3:
                continue
            spans.append(
                Span(
                    start=ent.start_char,
                    end=ent.end_char,
                    entity_type=etype,
                    text=ent.text,
                    score=0.75,
                    source="spacy_ner",
                )
            )
        return spans

    def detect_batch(self, texts: List[str]) -> List[List[Span]]:
        """Batch NER via nlp.pipe for performance on large documents."""
        results: List[List[Span]] = []
        for doc in self.nlp.pipe(texts, batch_size=32):
            spans: List[Span] = []
            for ent in doc.ents:
                etype = _LABEL_MAP.get(ent.label_)
                if not etype:
                    continue
                if etype == EntityType.COMPANY.value and len(ent.text.strip()) < 3:
                    continue
                spans.append(
                    Span(
                        start=ent.start_char,
                        end=ent.end_char,
                        entity_type=etype,
                        text=ent.text,
                        score=0.75,
                        source="spacy_ner",
                    )
                )
            results.append(spans)
        return results
