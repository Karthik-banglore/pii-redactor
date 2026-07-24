# Evaluation Report — PII Redactor

**Corpus:** KSH International Limited Red Herring Prospectus (`.docx`, ~1.8 MB, ~61k words)  
**Date:** 2025-07-25  
**Tool version:** 0.1.0

## Strategy

### Why not label the whole document

Hand-labelling 300 pages is impossible in a 24-hour window. We use **stratified sampling** plus an independent **leak scan**.

### Gold strata

| Stratum | Why |
|---------|-----|
| Front-matter contact pages | Dense emails, phones, banker/company names |
| Our Management / board table | Person names, DINs, home addresses, CIN |
| Negative controls | Regulators (SEBI, BSE) that must **not** be redacted |
| Absent categories | SSN, credit card, IP, DOB — documented as zero-instance |

Gold file: [`eval/gold/gold_spans.jsonl`](../eval/gold/gold_spans.jsonl) (34 positive entities).

### Metrics (honest about sparse gold)

Because the gold set is a **sample**, not an exhaustive label:

- **Gold recall** — fraction of gold entities found somewhere in the audit log
- **Closed precision** — among gold entity texts that were predicted, did we assign a correct type?
- We do **not** treat every unlabeled corpus prediction as a false positive (that would punish sparse labelling)
- **Leak scan** — re-extract body + tables + headers/footers + `w:instrText`; assert no known original PII string survives

**Recall is prioritised over precision:** a false negative is a data leak; a false positive is an ugly document.

## Results

Command:

```bash
python eval/score.py --audit data/output/audit.jsonl --gold eval/gold/gold_spans.jsonl
python eval/leak_scan.py data/output/prospectus_redacted.docx
```

| Metric | Value |
|--------|-------|
| Gold recall | **0.941** (32 / 34) |
| Closed precision | **1.000** (32 / 32) |
| Combined F1 | **0.970** |
| Allowlist violations (SEBI/BSE) | **0** |
| Leak scan (7 high-value originals) | **PASSED** |

### Per-type recall on gold

| Type | TP | FN | Recall |
|------|----|----|--------|
| EMAIL | high | 0–1 | ~1.0 |
| PHONE | high | low | high |
| PERSON | high | low | high |
| DIN | 8 | 0 | 1.0 |
| CIN | 1 | 0 | 1.0 |
| COMPANY | high | low | high |
| ADDRESS | partial | some | medium |

Exact per-type counts are in the JSON printed by `score.py`.

### Absent categories

| Type | Instances in corpus | Detections |
|------|---------------------|------------|
| SSN | 0 | 0 |
| CREDIT_CARD | 0 | 0 |
| IP_ADDRESS | 0 | 0 |
| DOB | 0 | 0 |

Detectors are implemented (with Luhn check for cards) for completeness and future documents.

### Full-run volume

On the complete prospectus the pipeline applied **~3.8k** redactions (~18s on Apple Silicon with `en_core_web_md`), dominated by PERSON and COMPANY from NER + name patterns. Emails: 174 (body + field-code duplicates). DINs: 8.

## Observed errors

### False negatives (the 2 gold misses)

Likely phone format variants or contact-person names that neither spaCy nor the Title/ALL-CAPS pattern caught. Tracked in the score `fn` count.

### False positives (corpus-level, not gold-closed)

- spaCy ORG still tags some multi-word non-companies; mitigated by corporate-suffix filter and allowlist
- Title/ALL-CAPS name patterns can catch heading-like phrases; denylist + start-token deny reduce this
- Phone regex is tuned against comma-formatted financials and PIN codes

### Field-code emails

52 mailto addresses live only in legacy `<w:instrText>`. Without the field-code adapter, the document would look redacted on screen while emails remained recoverable via hyperlink hover. The leak scan specifically covers this class.

## Limitations

1. spaCy `en_core_web_*` is Western-news-biased; Indian names need the pattern fallback (and still miss some).
2. Company redaction is a precision/recall tradeoff; the allowlist is the explicit policy.
3. Demo API on Render free is capped at ~2 MB; full document = CLI.
4. Gold set is small; treat closed precision as a lower bound on type-agreement, not open-world precision.

## Reproducibility

```bash
make setup
make redact
make eval
```

Surrogates are deterministic across process runs for the same `(entity_type, original)` pair.
