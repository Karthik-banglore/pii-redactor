# Submission checklist

## Links

| Field | Value |
|-------|-------|
| Assignment name | PII Redaction Tool |
| Github Link | https://github.com/Karthik-banglore/pii-redactor |
| Cloud service | `https://pii-redactor-1-guhx.onrender.com` |
| Evaluation doc | Upload [`reports/EVALUATION.md`](reports/EVALUATION.md) to Drive/Docs and share |
| Output docx | Local `data/output/prospectus_redacted.docx` → Drive, **Anyone with the link can view** |

## Deploy to Render (≈10 min)

1. Open https://dashboard.render.com → **New** → **Web Service**
2. Connect GitHub repo `Karthik-banglore/pii-redactor`
3. Runtime: **Docker** (uses `Dockerfile`)
4. Plan: **Free**
5. Health check path: `/health`
6. Env vars (optional; defaults exist in Dockerfile):
   - `SPACY_MODEL=en_core_web_sm`
   - `MAX_UPLOAD_BYTES=2097152`
7. Deploy. First build downloads spaCy and takes several minutes.
8. Smoke test: open `/`, upload `examples/sample_small.docx`, or hit `/docs`
9. **Before submitting the form**, open `/health` once to wake the free-tier service (cold start 30–60s)

## Drive uploads

1. Upload `data/output/prospectus_redacted.docx` (local only — not on GitHub)
2. Share → General access → **Anyone with the link** → Viewer
3. Verify in an incognito window
4. Upload `reports/EVALUATION.md` (or paste into a Google Doc) the same way

## Results snapshot (for the form / README)

- Gold recall: **0.941** (32/34)
- Closed precision: **1.000**
- Combined F1: **0.970**
- Leak scan: **PASSED**
- Allowlist violations: **0**
- Full-run redactions: **~3.2k** (heading denylist applied)
- Committed for reviewers: `reports/audit.jsonl` → `make eval-from-reports` (no `data/` needed)

## Known gaps (also in EVALUATION.md)

- **No OCR** — embedded PAN/ID photos are not redacted
- Residual table-heading FPs possible; common financial labels are denylisted
- Cloud demo: small files only (`examples/sample_small.docx`); full prospectus = CLI
- Client `.docx` is gitignored under `data/` — graders place their copy then `make redact && make eval`

## Local verification already done

```text
23 passed
make redact            → ~3.2k redactions
make eval-from-reports → metrics from reports/audit.jsonl
TestClient POST /redact → 200
```
