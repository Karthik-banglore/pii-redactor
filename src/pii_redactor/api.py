"""FastAPI demo surface — thin wrapper over the shared pipeline."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from pii_redactor.pipeline import build_pipeline


def _cleanup(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 2 * 1024 * 1024))  # 2 MB
SPACY_MODEL = os.environ.get("SPACY_MODEL", "en_core_web_sm")

app = FastAPI(
    title="PII Redactor",
    description=(
        "Upload a .docx to detect and pseudonymise PII. "
        "Demo instance is size-capped; use the CLI for large documents."
    ),
    version="0.1.0",
)

# Load pipeline (and spaCy model) once at startup — cold start pays once.
PIPELINE = build_pipeline(spacy_model=SPACY_MODEL)

UPLOAD_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>PII Redactor</title>
  <style>
    body { font-family: Georgia, serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem;
           background: #f7f4ef; color: #1a1a1a; }
    h1 { font-size: 1.75rem; }
    .card { background: #fff; border: 1px solid #ddd; padding: 1.5rem; }
    input[type=file] { margin: 1rem 0; }
    button { background: #1a1a1a; color: #fff; border: 0; padding: 0.6rem 1.2rem; cursor: pointer; }
    .note { color: #555; font-size: 0.9rem; margin-top: 1rem; }
  </style>
</head>
<body>
  <h1>PII Redactor</h1>
  <p>Upload a Word document. Detected PII is replaced with deterministic fake values.</p>
  <div class="card">
    <form action="/redact" method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".docx" required />
      <div><button type="submit">Redact</button></div>
    </form>
    <p class="note">Max upload: 2&nbsp;MB on this demo. Full prospectus: use the CLI.
    Interactive API docs: <a href="/docs">/docs</a></p>
  </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return UPLOAD_FORM


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": SPACY_MODEL}


async def _read_upload(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are accepted")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large ({len(data)} bytes). "
                f"Demo cap is {MAX_UPLOAD_BYTES} bytes. "
                "Use the CLI for the full prospectus."
            ),
        )
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    return data


@app.post("/redact")
async def redact(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    data = await _read_upload(file)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inp = tmp_path / "input.docx"
        out = tmp_path / "redacted.docx"
        audit = tmp_path / "audit.jsonl"
        inp.write_bytes(data)
        PIPELINE.redact(inp, out, audit_path=audit)
        final = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        final.write(out.read_bytes())
        final.close()
    if background_tasks is not None:
        background_tasks.add_task(_cleanup, final.name)
    return FileResponse(
        final.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="redacted.docx",
    )


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await _read_upload(file)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inp = tmp_path / "input.docx"
        out = tmp_path / "redacted.docx"
        audit_path = tmp_path / "audit.jsonl"
        inp.write_bytes(data)
        audit = PIPELINE.redact(inp, out, audit_path=audit_path)
        return JSONResponse(
            {
                "count": len(audit.records),
                "records": [
                    {
                        "location": r.location,
                        "entity_type": r.entity_type,
                        "original": r.original,
                        "replacement": r.replacement,
                        "source": r.source,
                        "score": r.score,
                    }
                    for r in audit.records
                ],
            }
        )
