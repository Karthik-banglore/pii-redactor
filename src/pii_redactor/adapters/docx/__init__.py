from pii_redactor.adapters.docx.loader import DocxAdapter, extract_all_text
from pii_redactor.adapters.docx.segments import ParagraphView
from pii_redactor.adapters.docx.writer import apply_spans_to_paragraph, paragraph_text

__all__ = [
    "DocxAdapter",
    "ParagraphView",
    "apply_spans_to_paragraph",
    "extract_all_text",
    "paragraph_text",
]
