"""Handle legacy Word field codes (w:instrText) that python-docx cannot see."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence
from xml.etree import ElementTree as ET  # noqa: F401 — typing only

from lxml import etree

from pii_redactor.domain.span import ResolvedSpan

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}


def _qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


@dataclass
class FieldTextTarget:
    """A mutable text node inside a field code or its visible display text."""

    element: etree._Element
    kind: str  # "instr" | "display"
    location: str

    @property
    def text(self) -> str:
        return self.element.text or ""

    @text.setter
    def text(self, value: str) -> None:
        self.element.text = value


def find_field_targets(root: etree._Element, location_prefix: str) -> List[FieldTextTarget]:
    """
    Collect instrText nodes and the visible <w:t> between fldChar separate/end
    for every field in *root*.
    """
    targets: List[FieldTextTarget] = []
    # Clark notation — works on both lxml and python-docx oxml elements
    instr_nodes = root.findall(f".//{{{W_NS}}}instrText")
    for i, instr in enumerate(instr_nodes):
        loc = f"{location_prefix}:instr:{i}"
        targets.append(FieldTextTarget(element=instr, kind="instr", location=loc))

        display = _find_display_text_after(instr)
        if display is not None:
            targets.append(
                FieldTextTarget(
                    element=display,
                    kind="display",
                    location=f"{location_prefix}:display:{i}",
                )
            )
    return targets


def _find_display_text_after(instr: etree._Element) -> Optional[etree._Element]:
    """Locate the first <w:t> between separate and end fldChar after *instr*."""
    # instrText lives inside a <w:r>. Field structure:
    #   r[fldChar begin] … r[instrText] … r[fldChar separate] … r[w:t] … r[fldChar end]
    parent_run = instr.getparent()
    if parent_run is None:
        return None
    container = parent_run.getparent()
    if container is None:
        return None

    children = list(container)
    try:
        start_idx = children.index(parent_run)
    except ValueError:
        return None

    seen_separate = False
    for sibling in children[start_idx + 1 :]:
        if sibling.tag != _qn("r"):
            continue
        fld = sibling.find(_qn("fldChar"))
        if fld is not None:
            ftype = fld.get(_qn("fldCharType"))
            if ftype == "separate":
                seen_separate = True
                continue
            if ftype == "end":
                return None
        if seen_separate:
            t_el = sibling.find(_qn("t"))
            if t_el is not None:
                return t_el
    return None


_EMAIL_IN_INSTR = re.compile(
    r"(mailto:)?([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})",
    re.IGNORECASE,
)


def apply_email_replacements(
    targets: Sequence[FieldTextTarget],
    mapping: dict,
) -> List[ResolvedSpan]:
    """
    Replace email addresses inside field targets using *mapping*
    (original_lower -> replacement). Returns synthetic ResolvedSpans for audit.
    """
    applied: List[ResolvedSpan] = []
    for target in targets:
        original = target.text
        if not original:
            continue
        new_text = original
        for match in list(_EMAIL_IN_INSTR.finditer(original)):
            email = match.group(2)
            key = email.lower()
            if key not in mapping:
                continue
            replacement = mapping[key]
            # Preserve mailto: prefix if present
            full = match.group(0)
            if match.group(1):
                repl_full = f"mailto:{replacement}"
            else:
                repl_full = replacement
            new_text = new_text.replace(full, repl_full, 1)
            applied.append(
                ResolvedSpan(
                    start=match.start(2),
                    end=match.end(2),
                    entity_type="EMAIL",
                    original=email,
                    replacement=replacement,
                    score=1.0,
                    source="field_code",
                )
            )
        if new_text != original:
            target.text = new_text
    return applied
