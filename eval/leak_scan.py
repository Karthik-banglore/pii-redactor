"""
Re-extract every character from a redacted .docx (body, tables, headers,
footers, instrText) and assert that known original PII strings are gone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pii_redactor.adapters.docx.loader import extract_all_text
from pii_redactor.audit import AuditLog


def leak_scan(output_docx: Path, originals: list[str]) -> list[str]:
    blob = extract_all_text(output_docx)
    blob_lower = blob.lower()
    leaks = []
    for original in originals:
        o = original.strip()
        if len(o) < 4:
            continue
        if o.lower() in blob_lower:
            leaks.append(o)
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan redacted docx for leftover PII")
    parser.add_argument("output_docx", type=Path)
    parser.add_argument(
        "--audit",
        type=Path,
        default=None,
        help="Audit JSONL — originals taken from here if provided",
    )
    parser.add_argument(
        "--known",
        type=Path,
        default=None,
        help="Optional JSON list of known original strings",
    )
    args = parser.parse_args()

    originals: list[str] = []
    if args.audit and args.audit.exists():
        for rec in AuditLog.load(args.audit):
            originals.append(rec.original)
    if args.known and args.known.exists():
        originals.extend(json.loads(args.known.read_text()))

    if not originals:
        # Default high-value strings from the prospectus analysis
        originals = [
            "Sarthak.malvadkar@kshinterantional.com",
            "ksh.ipo@nuvama.com",
            "Kushal Subbayya Hegde",
            "Rajesh Kushal Hegde",
            "Rohit Kushal Hegde",
            "00135070",
            "00114193",
        ]

    # Unique
    originals = sorted(set(originals))
    leaks = leak_scan(args.output_docx, originals)
    if leaks:
        print(f"LEAK SCAN FAILED — {len(leaks)} original string(s) still present:")
        for leak in leaks[:50]:
            print(f"  - {leak}")
        if len(leaks) > 50:
            print(f"  ... and {len(leaks) - 50} more")
        return 1

    print(f"LEAK SCAN PASSED — checked {len(originals)} originals, none found in output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
