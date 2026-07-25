# Evaluation Report — PII Redactor

**Corpus:** KSH International Limited Red Herring Prospectus (`.docx`, ~1.8 MB, ~61k words)  
**Date:** 2026-07-25  
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

Metrics below were produced on the full assignment prospectus. The raw client
`.docx` is **not** in GitHub (`data/` is gitignored). Reviewers either:

1. **Reproduce from clone alone** (score only — uses committed audit snapshot):

```bash
make eval-from-reports
# same as:
python eval/score.py --audit reports/audit.jsonl --gold eval/gold/gold_spans.jsonl
```

2. **Full re-run + leak scan** (you already have the assignment prospectus):

```bash
mkdir -p data/input data/output
cp "/path/to/Red Herring Prospectus.docx" data/input/prospectus.docx
make setup
make redact    # → data/output/prospectus_redacted.docx + reports/audit.jsonl
make eval      # score + leak_scan on local outputs
```

Committed evidence: [`reports/audit.jsonl`](audit.jsonl), [`reports/score_report.json`](score_report.json).

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

On the complete prospectus the pipeline applied **~3.2k** redactions (~20s on Apple Silicon with `en_core_web_md`), dominated by PERSON and COMPANY from NER + name patterns. Emails: 174 (body + field-code duplicates). DINs: 8. Heading denylist cut ~600 false positives vs the first full run (e.g. “Bid Amount”, “CORPORATE IDENTITY NUMBER”).

## Observed errors

### False negatives (the 2 gold misses)

Likely phone format variants or contact-person names that neither spaCy nor the Title/ALL-CAPS pattern caught. Tracked in the score `fn` count.

### False positives (corpus-level, not gold-closed)

- spaCy ORG still tags some multi-word non-companies; mitigated by corporate-suffix filter and allowlist
- Title/ALL-CAPS name patterns and NER can catch **table headings / financial labels** (e.g. “Bid Amount”, “Total Dues”, “CORPORATE IDENTITY NUMBER”) because they look like proper names or orgs. Mitigated with an expanded financial/heading denylist in `resolve/filters.py` and `recognizers/person_pattern.py`; residual FPs remain when phrasing is novel
- Phone regex is tuned against comma-formatted financials and PIN codes

### Embedded images (e.g. PAN card photos) — not redacted

The pipeline walks **extractable Word text only**: body paragraphs, nested tables, headers/footers, and legacy `<w:instrText>` field codes.

**It does not run OCR.** A PAN / Aadhaar / ID card embedded as a photo is pixels inside the `.docx` ZIP. Recognizers never see that text, so surrogates cannot replace it. Fixing this would need an image extractor + OCR path (out of scope for this 24h build). Treat any scanned ID pages as a known residual leak class.

### Field-code emails

52 mailto addresses live only in legacy `<w:instrText>`. Without the field-code adapter, the document would look redacted on screen while emails remained recoverable via hyperlink hover. The leak scan specifically covers this class.

## Limitations

1. **No OCR on embedded images** — PAN/ID photos and other scanned pages are not redacted (see above).
2. **Table / section headings can be over-redacted** — Title Case and ALL CAPS financial jargon is sometimes tagged PERSON/COMPANY; denylist reduces but does not eliminate this.
3. spaCy `en_core_web_*` is Western-news-biased; Indian names need the pattern fallback (and still miss some).
4. Company redaction is a precision/recall tradeoff; the allowlist (SEBI/BSE/NSE/RBI/…) is the explicit policy.
5. **Demo API (Render free) ≠ full job.** Upload capped (~2 MB) and RAM-limited (512 MB); spaCy is skipped on the free demo (`SKIP_SPACY=1`). Small sample files work in the browser; the full prospectus is meant to be run via **CLI**.
6. Gold set is small; treat closed precision as a lower bound on type-agreement, not open-world precision.

## How a reviewer should run this (CLI)

The GitHub README is the primary path. Cloud URL is an optional smoke demo for a **small** `.docx` only (`examples/sample_small.docx`).

`data/` is gitignored on purpose (client prospectus). After clone:

```bash
git clone https://github.com/Karthik-banglore/pii-redactor
cd pii-redactor
make setup
make test
make eval-from-reports   # score metrics from reports/audit.jsonl — no data/ needed

# Full pipeline + leak scan (place the assignment .docx you already have):
mkdir -p data/input
cp "/path/to/Red Herring Prospectus.docx" data/input/prospectus.docx
make redact
make eval

# or one-shot on any file:
python -m pii_redactor.cli input.docx -o redacted.docx --audit audit.jsonl
python eval/leak_scan.py redacted.docx
```

Local browser demo: `make serve` → http://127.0.0.1:8000 (upload `examples/sample_small.docx`)  
Deployed demo: same small sample only — not the full prospectus.

## Reproducibility

```bash
make setup
make eval-from-reports          # from committed reports/audit.jsonl
# optional full re-run if you have the prospectus:
# make redact && make eval
```

Surrogates are deterministic across process runs for the same `(entity_type, original)` pair.
