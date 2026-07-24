"""CLI entry point — what graders will actually run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pii_redactor.pipeline import build_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect PII in a .docx and write a pseudonymised copy."
    )
    parser.add_argument("input", type=Path, help="Input .docx path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output redacted .docx path",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=None,
        help="Optional JSONL audit log path",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="spaCy model name (default: SPACY_MODEL env or en_core_web_md)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 1

    pipeline = build_pipeline(spacy_model=args.model)
    audit = pipeline.redact(args.input, args.output, audit_path=args.audit)
    print(f"Wrote {args.output}")
    print(f"Redactions applied: {len(audit.records)}")
    if args.audit:
        print(f"Audit log: {args.audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
