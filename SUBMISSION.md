# Submission checklist

## Links

| Field | Value |
|-------|-------|
| Assignment name | PII Redaction Tool |
| Github Link | https://github.com/Karthik-banglore/pii-redactor |
| Cloud service | Deploy on Render (see below) — then paste the `*.onrender.com` URL |
| Evaluation doc | Upload [`reports/EVALUATION.md`](reports/EVALUATION.md) to Drive/Docs and share |
| Output docx | [`data/output/prospectus_redacted.docx`](../data/output/prospectus_redacted.docx) — upload to Drive, set **Anyone with the link can view** |

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
8. Smoke test: open `/`, upload `data/output/sample_small.docx` (create via tests), or hit `/docs`
9. **Before submitting the form**, open `/health` once to wake the free-tier service (cold start 30–60s)

## Drive uploads

1. Upload `data/output/prospectus_redacted.docx`
2. Share → General access → **Anyone with the link** → Viewer
3. Verify in an incognito window
4. Upload `reports/EVALUATION.md` (or paste into a Google Doc) the same way

## Results snapshot (for the form / README)

- Gold recall: **0.941** (32/34)
- Closed precision: **1.000**
- Combined F1: **0.970**
- Leak scan: **PASSED**
- Allowlist violations: **0**

## Local verification already done

```text
21 passed
make redact  → ~3.8k redactions in ~18s
make eval    → metrics above
TestClient POST /redact → 200
```
