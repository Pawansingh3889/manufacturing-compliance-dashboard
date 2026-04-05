# Manufacturing Compliance Dashboard

BRC/HACCP food safety compliance — batch traceability, temperature monitoring, allergen matrix, shelf life risk scoring.

Built by someone who works on the factory floor.

\`\`\`
stack = ["Streamlit", "FastAPI", "PySpark", "Databricks", "SQLite", "Plotly", "Docker"]
data  = "674 batches, 8640 temperature logs, 271 orders, 16 products"
\`\`\`

[Live Dashboard](https://manufacturing-compliance-dashboard-mjappkncanejzlfr5ngghik.streamlit.app)

---

## What it does

**Dashboard (Streamlit)** — batch traceability, FEFO despatch, temperature monitoring, allergen matrix, shelf life concessions, PDF audit reports

**REST API (FastAPI)** — JSON endpoints for batches, temperature logs, shelf life risk, yield summaries

**Batch Analytics (PySpark / Databricks)** — yield analysis, temperature excursion rates, shelf life risk scoring, daily OEE

**Time-Series Anomaly Detection** — rolling z-score, excursion duration tracking, trend forecasting on sensor data

---

## Quick start

\`\`\`bash
pip install -r requirements.txt
python data/seed_demo.py
streamlit run app.py
\`\`\`
