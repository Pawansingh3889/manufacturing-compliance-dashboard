.PHONY: setup test run clean lint format typecheck

setup:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

run:
	streamlit run app.py

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy modules/

clean:
	rm -rf __pycache__
