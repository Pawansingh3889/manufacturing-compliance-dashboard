.PHONY: setup test run clean

setup:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v

run:
	streamlit run app.py

clean:
	rm -rf __pycache__
