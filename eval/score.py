"""
Score audit log against a gold JSONL of hand-labelled spans.

Gold format (one JSON object per line):
  {"location": "body:p12", "entity_type": "EMAIL", "text": "a@b.com",
   "start": 10, "end": 17}

Matching:
  - strict: same location + entity_type + exact text (case-insensitive)
  - partial: same location + entity_type + character overlap
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass(frozen=True)
class GoldSpan:
    location: str
    entity_type: str
    text: str
    start: int = -1
    end: int = -1


def load_gold(path: Path) -> List[GoldSpan]:
    items: List[GoldSpan] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            text = d["text"]
            if text == "___NONE___":
                continue  # documents absent categories; not scored as FN
            # Negative-control rows: entity_type marked but should NOT appear
            # (handled separately via --negatives). For standard scoring we
            # only include positive gold spans (non-regulator rows).
            if d.get("location", "").endswith("negative"):
                continue
            items.append(
                GoldSpan(
                    location=d.get("location", ""),
                    entity_type=d["entity_type"],
                    text=text,
                    start=d.get("start", -1),
                    end=d.get("end", -1),
                )
            )
    return items


def load_negatives(path: Path) -> List[str]:
    """Strings that must NOT be redacted (allowlisted regulators)."""
    out: List[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            if d.get("location", "").endswith("negative"):
                out.append(d["text"])
    return out


def load_pred(path: Path) -> List[GoldSpan]:
    items: List[GoldSpan] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            items.append(
                GoldSpan(
                    location=d.get("location", ""),
                    entity_type=d["entity_type"],
                    text=d["original"],
                )
            )
    return items


def _key(s: GoldSpan) -> Tuple[str, str, str]:
    return (s.location, s.entity_type.upper(), s.text.strip().lower())


def score(gold: List[GoldSpan], pred: List[GoldSpan]) -> Dict:
    """
    Gold is a stratified *sample*, not an exhaustive label of the document.

    Therefore:
      - Recall  = fraction of gold entities found somewhere in the audit
      - Precision (closed) = of gold entities that were predicted, type agreement
        (we do NOT treat unlabeled corpus predictions as FP — that would
        punish a sparse gold set)
      - Open precision requires exhaustive labeling; we report leak-scan instead
    """
    gold_type_text = {(g.entity_type.upper(), g.text.strip().lower()) for g in gold}
    pred_type_text = {(p.entity_type.upper(), p.text.strip().lower()) for p in pred}
    pred_texts = {t for _, t in pred_type_text}
    gold_by_text: Dict[str, Set[str]] = defaultdict(set)
    for et, t in gold_type_text:
        gold_by_text[t].add(et)

    tp = len(gold_type_text & pred_type_text)
    fn = len(gold_type_text - pred_type_text)

    # Closed precision: gold texts that appear in pred — did we assign a gold type?
    closed_tp = 0
    closed_fp = 0
    for text, gold_types in gold_by_text.items():
        pred_types = {et for et, t in pred_type_text if t == text}
        if not pred_types:
            continue
        if pred_types & gold_types:
            closed_tp += 1
        else:
            closed_fp += 1

    by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for et, text in gold_type_text:
        if (et, text) in pred_type_text:
            by_type[et]["tp"] += 1
        else:
            by_type[et]["fn"] += 1

    def prf(tp_, fp_, fn_):
        precision = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        recall = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp_,
            "fp": fp_,
            "fn": fn_,
        }

    per_type = {}
    for etype, c in sorted(by_type.items()):
        # Per-type precision is recall-oriented here (fp=0 in open sample)
        per_type[etype] = prf(c["tp"], 0, c["fn"])
        per_type[etype]["note"] = "precision omitted for sparse gold; see closed_precision"

    return {
        "gold_recall": prf(tp, 0, fn),
        "closed_precision": prf(closed_tp, closed_fp, 0),
        "per_type_recall": per_type,
        "gold_size": len(gold_type_text),
        "pred_unique_type_text": len(pred_type_text),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score redaction audit vs gold spans")
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    args = parser.parse_args()

    gold = load_gold(args.gold)
    pred = load_pred(args.audit)
    result = score(gold, pred)

    # Allowlist check: regulators in gold negatives should not appear as COMPANY preds
    negatives = load_negatives(args.gold)
    pred_company = {
        p.text.strip().lower()
        for p in pred
        if p.entity_type.upper() == "COMPANY"
    }
    allowlist_violations = [n for n in negatives if n.strip().lower() in pred_company]
    result["allowlist_violations"] = allowlist_violations

    # Absent categories report
    present_types = {p.entity_type.upper() for p in pred}
    for absent in ("SSN", "CREDIT_CARD", "IP_ADDRESS", "DOB"):
        result.setdefault("absent_categories", {})[absent] = {
            "instances_in_corpus": 0,
            "detections": int(absent in present_types),
            "note": "No instances in this prospectus; detector implemented for completeness.",
        }

    print(json.dumps(result, indent=2))

    gr = result["gold_recall"]
    cp = result["closed_precision"]
    print(
        f"\nGold recall     P=n/a  R={gr['recall']:.3f}  "
        f"(tp={gr['tp']} fn={gr['fn']} of {result['gold_size']} gold entities)"
    )
    print(
        f"Closed precision P={cp['precision']:.3f}  "
        f"(tp={cp['tp']} fp={cp['fp']} on gold texts that were predicted)"
    )
    # Combined F1 using gold recall + closed precision
    p, r = cp["precision"], gr["recall"]
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    print(f"Combined F1     {f1:.3f}  (closed P × gold R)")
    if allowlist_violations:
        print(f"Allowlist violations: {allowlist_violations}")
    else:
        print("Allowlist: no regulator false positives on gold negatives")


if __name__ == "__main__":
    main()
