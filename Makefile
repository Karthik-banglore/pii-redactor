.PHONY: setup test redact eval serve tunnel clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(PYTHON) -m spacy download en_core_web_md

test:
	$(PYTHON) -m pytest -v

redact:
	$(PYTHON) -m pii_redactor.cli \
		data/input/prospectus.docx \
		-o data/output/prospectus_redacted.docx \
		--audit data/output/audit.jsonl

eval:
	$(PYTHON) eval/score.py \
		--audit data/output/audit.jsonl \
		--gold eval/gold/gold_spans.jsonl
	$(PYTHON) eval/leak_scan.py data/output/prospectus_redacted.docx

serve:
	$(PYTHON) -m uvicorn pii_redactor.api:app --reload --host 0.0.0.0 --port 8000

tunnel:
	cloudflared tunnel --url http://localhost:8000

clean:
	rm -rf .pytest_cache **/__pycache__ *.egg-info
