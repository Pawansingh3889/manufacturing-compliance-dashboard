.PHONY: setup setup-dev test run clean lint format typecheck api scanapi

setup:
	pip install -r requirements.txt

# Full dev environment — runtime deps + test tooling (pytest, ruff, scanapi).
setup-dev:
	pip install -r requirements-dev.txt

test:
	python -m pytest tests/ -v

run:
	streamlit run app.py

# Start the FastAPI service on http://localhost:8000 (Swagger at /docs).
api:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check .

format:
	ruff format .

typecheck:
	ty check modules/

# ScanAPI integration tests — boots uvicorn in the background, waits for
# /health to respond, runs the spec, tears down cleanly. Report lands in
# scanapi-report/ (gitignored; open scanapi-report/scanapi-report.html).
#
# Override BASE_URL to target a staging or production deploy instead:
#   make scanapi BASE_URL=https://staging.example.com
scanapi:
	@echo "Starting uvicorn in the background..."
	@python -m uvicorn api:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 & echo $$! > /tmp/uvicorn.pid
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
	  curl -fsS http://127.0.0.1:8000/health > /dev/null && break || sleep 1; \
	done
	@BASE_URL=$${BASE_URL:-http://127.0.0.1:8000} scanapi run scanapi/scanapi.yaml -o scanapi-report/scanapi-report.html; \
	  SCANAPI_EXIT=$$?; \
	  kill $$(cat /tmp/uvicorn.pid) 2>/dev/null || true; \
	  rm -f /tmp/uvicorn.pid; \
	  exit $$SCANAPI_EXIT

clean:
	rm -rf __pycache__ scanapi-report scanapi-report.html
