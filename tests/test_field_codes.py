"""Field-code (w:instrText) email handling tests."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from docx import Document
from lxml import etree

from pii_redactor.adapters.docx.fields import apply_email_replacements, find_field_targets
from pii_redactor.adapters.docx.loader import DocxAdapter, extract_all_text


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _add_mailto_field(paragraph, email: str):
    """Inject a legacy HYPERLINK field into a paragraph's XML."""
    p = paragraph._p
    # Clear existing runs
    for child in list(p):
        if child.tag.endswith("}r"):
            p.remove(child)

    def run_with(*children):
        r = etree.SubElement(p, f"{{{W}}}r")
        for c in children:
            r.append(c)
        return r

    # begin
    fld_begin = etree.Element(f"{{{W}}}fldChar")
    fld_begin.set(f"{{{W}}}fldCharType", "begin")
    run_with(fld_begin)

    # instrText
    instr = etree.Element(f"{{{W}}}instrText")
    instr.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instr.text = f' HYPERLINK "mailto:{email}" '
    run_with(instr)

    # separate
    fld_sep = etree.Element(f"{{{W}}}fldChar")
    fld_sep.set(f"{{{W}}}fldCharType", "separate")
    run_with(fld_sep)

    # display text
    t = etree.Element(f"{{{W}}}t")
    t.text = email
    run_with(t)

    # end
    fld_end = etree.Element(f"{{{W}}}fldChar")
    fld_end.set(f"{{{W}}}fldCharType", "end")
    run_with(fld_end)


def test_find_and_replace_field_email(tmp_path: Path):
    doc = Document()
    para = doc.add_paragraph()
    _add_mailto_field(para, "sarthak@ksh.com")
    path = tmp_path / "field.docx"
    doc.save(path)

    adapter = DocxAdapter()
    adapter.load(path)
    assert any("sarthak@ksh.com" in t.text for t in adapter._field_targets)

    apply_email_replacements(
        adapter._field_targets, {"sarthak@ksh.com": "alice@example.com"}
    )
    out = tmp_path / "out.docx"
    adapter.save(out)

    # Re-read raw XML
    with ZipFile(out) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    assert "sarthak@ksh.com" not in xml
    assert "alice@example.com" in xml
