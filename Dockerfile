FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPACY_MODEL=en_core_web_sm \
    MAX_UPLOAD_BYTES=2097152 \
    SKIP_SPACY=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples

RUN pip install --no-cache-dir -e . \
    && python -m spacy download en_core_web_sm

# Render injects $PORT — do not hardcode 8000
CMD ["sh", "-c", "uvicorn pii_redactor.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
