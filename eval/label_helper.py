"""
Dump candidate PII spans from a document to help build a gold set.

Usage:
  python eval/label_helper.py data/input/prospectus.docx -o eval/gold/candidates.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pii_redactor.adapters.docx.loader import DocxAdapter
from pii_redactor.domain.span import Context
from pii_redactor.recognizers import build_default_registry
from pii_redactor.resolve.filters import apply_filters
from pii_redactor.resolve.overlap import resolve_overlaps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    adapter = DocxAdapter()
    adapter.load(args.input)
    registry = build_default_registry()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(args.output, "w", encoding="utf-8") as fh:
        for segment in adapter.iter_segments():
            if not segment.text.strip():
                continue
            # Prefer PII-dense locations
            loc = segment.location
            spans = registry.detect_all(segment.text, Context(location=loc))
            spans = resolve_overlaps(apply_filters(spans))
            for span in spans:
                rec = {
                    "location": loc,
                    "entity_type": span.entity_type,
                    "text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "source": span.source,
                    "score": span.score,
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                count += 1
                if count >= args.limit:
                    print(f"Wrote {count} candidates to {args.output}")
                    return
    print(f"Wrote {count} candidates to {args.output}")


if __name__ == "__main__":
    main()
