"""FastAPI demo surface — thin wrapper over the shared pipeline."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from pii_redactor.pipeline import Pipeline, build_pipeline

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 2 * 1024 * 1024))  # 2 MB
SPACY_MODEL = os.environ.get("SPACY_MODEL", "en_core_web_sm")
# Free-tier Render is 512 MB — skip spaCy in the web demo unless explicitly enabled.
SKIP_SPACY = os.environ.get("SKIP_SPACY", "1").lower() in {"1", "true", "yes"}

app = FastAPI(
    title="PII Redactor",
    description=(
        "Upload a .docx to detect and pseudonymise PII. "
        "Demo instance is size-capped; use the CLI for large documents."
    ),
    version="0.1.0",
)

_PIPELINE: Optional[Pipeline] = None


def get_pipeline() -> Pipeline:
    """Lazy-load so / and /health stay up even if the model is heavy."""
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = build_pipeline(
            spacy_model=None if SKIP_SPACY else SPACY_MODEL,
            use_spacy=not SKIP_SPACY,
        )
    return _PIPELINE


def _cleanup(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def _repo_root() -> Path:
    # src/pii_redactor/api.py → project root (local + Docker /app)
    return Path(__file__).resolve().parents[2]


def _sample_path() -> Path:
    return _repo_root() / "examples" / "sample_small.docx"


UPLOAD_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>PII Redactor — Demo</title>
  <style>
    body { font-family: Georgia, serif; max-width: 42rem; margin: 3rem auto; padding: 0 1rem;
           background: #f7f4ef; color: #1a1a1a; line-height: 1.45; }
    h1 { font-size: 1.75rem; margin-bottom: 0.35rem; }
    h2 { font-size: 1.1rem; margin: 0 0 0.75rem; }
    .card { background: #fff; border: 1px solid #ddd; padding: 1.5rem; margin: 1rem 0; }
    .steps { margin: 0; padding-left: 1.25rem; }
    .steps li { margin: 0.4rem 0; }
    input[type=file] { margin: 1rem 0; display: block; }
    button, .btn {
      display: inline-block; background: #1a1a1a; color: #fff; border: 0;
      padding: 0.65rem 1.2rem; cursor: pointer; text-decoration: none; font: inherit;
    }
    .btn.secondary { background: #fff; color: #1a1a1a; border: 1px solid #1a1a1a; margin-right: 0.5rem; }
    .warn { background: #fff8e6; border: 1px solid #e6d9a8; padding: 0.85rem 1rem; margin: 1rem 0; }
    .note { color: #555; font-size: 0.9rem; margin-top: 1rem; }
    code { font-size: 0.9em; }
  </style>
</head>
<body>
  <h1>PII Redactor</h1>
  <p>Cloud demo (size-capped). Detected PII is replaced with deterministic fake values.</p>

  <div class="warn">
    <strong>Do not upload the full prospectus here.</strong>
    This free demo accepts <strong>.docx files up to 2&nbsp;MB</strong> and runs a light regex path.
    Use the sample below (~36&nbsp;KB), or run the full document via the
    <a href="https://github.com/Karthik-banglore/pii-redactor#quick-start">CLI on GitHub</a>.
  </div>

  <div class="card">
    <h2>Try the demo (3 steps)</h2>
    <ol class="steps">
      <li>
        <a class="btn secondary" href="/sample">Download sample_small.docx</a>
        (also on GitHub:
        <a href="https://github.com/Karthik-banglore/pii-redactor/raw/main/examples/sample_small.docx">examples/sample_small.docx</a>)
      </li>
      <li>Upload that file with the form below.</li>
      <li>Click <strong>Redact</strong> — your browser downloads <code>redacted.docx</code>.</li>
    </ol>
  </div>

  <div class="card">
    <h2>Upload</h2>
    <form action="/redact" method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required />
      <div><button type="submit">Redact</button></div>
    </form>
    <p class="note">
      Max upload: 2&nbsp;MB · API docs: <a href="/docs">/docs</a> · Health: <a href="/health">/health</a><br/>
      Source / full CLI: <a href="https://github.com/Karthik-banglore/pii-redactor">github.com/Karthik-banglore/pii-redactor</a>
    </p>
  </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return UPLOAD_FORM


@app.get("/sample")
def download_sample():
    """Serve the bundled small .docx so reviewers need not dig through GitHub first."""
    path = _sample_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Sample file missing on this deploy. "
                "Download from GitHub: "
                "https://github.com/Karthik-banglore/pii-redactor/raw/main/examples/sample_small.docx"
            ),
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="sample_small.docx",
    )


@app.get("/redact")
def redact_get() -> RedirectResponse:
    """Browsers hitting /redact directly should land on the upload form."""
    return RedirectResponse(url="/", status_code=302)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": "regex-only" if SKIP_SPACY else SPACY_MODEL,
        "skip_spacy": SKIP_SPACY,
        "sample": "/sample",
    }


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
async def redact(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    data = await _read_upload(file)
    pipeline = get_pipeline()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inp = tmp_path / "input.docx"
        out = tmp_path / "redacted.docx"
        audit = tmp_path / "audit.jsonl"
        inp.write_bytes(data)
        pipeline.redact(inp, out, audit_path=audit)
        final = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        final.write(out.read_bytes())
        final.close()
    background_tasks.add_task(_cleanup, final.name)
    return FileResponse(
        final.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="redacted.docx",
    )


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await _read_upload(file)
    pipeline = get_pipeline()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inp = tmp_path / "input.docx"
        out = tmp_path / "redacted.docx"
        audit_path = tmp_path / "audit.jsonl"
        inp.write_bytes(data)
        audit = pipeline.redact(inp, out, audit_path=audit_path)
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
