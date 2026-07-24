# PII Redactor

Detect personally identifiable information in Word (`.docx`) documents and replace it with **deterministic fake surrogates** so the document stays readable.

Built for a take-home assignment against a ~300-page Indian IPO Red Herring Prospectus.

## Quick start

```bash
make setup          # venv + deps + spaCy en_core_web_md
make test           # 21 unit tests
make redact         # redact data/input/prospectus.docx → data/output/
make eval           # precision/recall + leak scan
make serve          # local FastAPI demo on :8000
```

CLI:

```bash
python -m pii_redactor.cli input.docx -o redacted.docx --audit audit.jsonl
```

## Architecture

Modular monolith. One library, two thin entry points (CLI + FastAPI).

```
.docx ──► DocxAdapter ──► TextSegments (joined runs + offset map)
                │
                ▼
         RecognizerRegistry  (regex + Indian IDs + spaCy NER + name patterns)
                │
                ▼
         Filters (allowlist) → Overlap resolution → SurrogateProvider
                │
                ▼
         Write-back to runs + field codes ──► redacted.docx + audit.jsonl
```

**Why we built our own offset map.** A `.docx` is a ZIP of XML. This prospectus stores ~1 word per `<w:t>` run (75k runs). Naïve `run.text = re.sub(...)` misses multi-word names. We join runs, detect on the joined string, then map character offsets back onto the fragmented runs.

**Why python-docx alone is not enough.**

| Gap | What we do |
|-----|------------|
| `document.paragraphs` skips tables (63% of text here) | Recursive table walker |
| Zero `<w:hyperlink>` elements; 52 mailto addresses hide in legacy `<w:instrText>` | lxml field-code handler |
| Run fragmentation | `ParagraphView` offset map |

## Detection

| Type | Method |
|------|--------|
| EMAIL, PHONE, SSN, CREDIT_CARD, IP, DOB | Regex (+ Luhn for cards) |
| DIN, PAN, CIN, Aadhaar, GST | Indian ID regex |
| PERSON | spaCy NER + Title/ALL-CAPS name patterns |
| COMPANY, ADDRESS | spaCy NER (ORG / GPE / LOC / FAC) with corporate-suffix filter |

**Allowlist policy.** Regulators and market infrastructure are preserved: SEBI, BSE, NSE, RBI, Registrar of Companies, Ministry of Corporate Affairs, etc. Redacting them gains no privacy and destroys meaning. Documented judgment call, not a bug.

**Surrogates.** `Faker` seeded by `sha256(entity_type + normalized_original)` so the same person always becomes the same fake name across 20+ occurrences.

**Absent categories.** This prospectus contains **zero** SSNs, credit cards, IP addresses, or dates of birth. Detectors are still implemented; evaluation reports them as absent.

## Demo API (Render)

The deployed service is a **size-capped demo** (~2 MB upload). Render free tier is 512 MB RAM / 0.1 CPU and sleeps after 15 minutes idle. The full prospectus is processed by the CLI.

```
GET  /         upload form
POST /redact   → redacted .docx
POST /analyze  → JSON audit
GET  /health
GET  /docs     interactive Swagger UI
```

Env: `SPACY_MODEL` (default `en_core_web_sm` in Docker), `MAX_UPLOAD_BYTES`.

## Alternatives considered

- **Presidio** — strong detectors, no `.docx` write-back; we'd still own the hard part.
- **Railway trial** — better RAM / no cold start, but expires and has trial-network caveats.
- **Cloudflare Tunnel** — great for live demos from a laptop; unsuitable as a submission URL (ephemeral hostname).
- **Hugging Face Spaces** — Docker/Gradio now behind PRO (Jul 2026).

## Project layout

```
src/pii_redactor/   core library + cli + api
eval/               gold set, score.py, leak_scan.py
tests/              offset map, recognizers, surrogates, field codes
reports/            EVALUATION.md
Dockerfile          Render / any container host
Makefile            setup test redact eval serve tunnel
```

## Extending

Add a new PII type by implementing one class:

```python
class Recognizer(Protocol):
    entity_type: str
    def detect(self, text: str, ctx: Context) -> list[Span]: ...
```

Register it in `build_default_registry()`. No other file changes.

## License

Assignment / portfolio use.
