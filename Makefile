.PHONY: setup test redact eval eval-from-reports serve tunnel clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

setup:
	git config core.hooksPath .githooks
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(PYTHON) -m spacy download en_core_web_md

test:
	$(PYTHON) -m pytest -v

# Requires the assignment prospectus at data/input/prospectus.docx (gitignored).
redact:
	@test -f data/input/prospectus.docx || (echo "Missing data/input/prospectus.docx — copy the assignment .docx there first." && exit 1)
	mkdir -p data/output
	$(PYTHON) -m pii_redactor.cli \
		data/input/prospectus.docx \
		-o data/output/prospectus_redacted.docx \
		--audit data/output/audit.jsonl
	cp data/output/audit.jsonl reports/audit.jsonl

# Full eval after make redact (needs local data/output).
eval:
	@test -f data/output/audit.jsonl || (echo "Run make redact first, or use: make eval-from-reports" && exit 1)
	$(PYTHON) eval/score.py \
		--audit data/output/audit.jsonl \
		--gold eval/gold/gold_spans.jsonl
	$(PYTHON) eval/leak_scan.py data/output/prospectus_redacted.docx

# Clone-only: score against the committed audit snapshot (no data/ folder needed).
eval-from-reports:
	$(PYTHON) eval/score.py \
		--audit reports/audit.jsonl \
		--gold eval/gold/gold_spans.jsonl
	@echo ""
	@echo "Note: leak_scan needs the redacted .docx."
	@echo "  Reviewers: copy the assignment prospectus → data/input/prospectus.docx,"
	@echo "  then run: make redact && make eval"
	@echo "  Or leak-scan your own CLI output:"
	@echo "    python eval/leak_scan.py path/to/redacted.docx"

serve:
	$(PYTHON) -m uvicorn pii_redactor.api:app --reload --host 0.0.0.0 --port 8000

tunnel:
	cloudflared tunnel --url http://localhost:8000

clean:
	rm -rf .pytest_cache **/__pycache__ *.egg-info
