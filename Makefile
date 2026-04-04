.PHONY: setup run seed clean help

setup: ## Install dependencies and seed demo data
	pip install -r requirements.txt
	python data/seed_demo.py

run: ## Start the dashboard
	streamlit run app.py

seed: ## Regenerate demo database
	python data/seed_demo.py

clean: ## Remove database
	rm -f data/compliance.db

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
