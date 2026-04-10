# AGENTS.md -- manufacturing-compliance-dashboard

## Project Overview

BRC/HACCP food safety compliance dashboard for a fish processing facility.
Built on Streamlit with SQLAlchemy ORM and Plotly visualizations. Tracks
temperature monitoring, batch traceability, allergen matrices, shelf life
management, and FEFO (First Expired, First Out) despatch priority.

Live deployment on Streamlit Cloud.

## Architecture

```
app.py                         # Main Streamlit app: all tabs, scoring, sidebar
modules/
  database.py                  # SQLAlchemy engine, ORM models (Product, Batch,
                               #   TemperatureLog, Order), query/scalar helpers
  temperature.py               # Temperature monitoring and excursion detection
  traceability.py              # Batch tracing with input validation
  allergens.py                 # Allergen matrix and cross-reference
  shelf_life.py                # Shelf life calculations and concession logic
  report_generator.py          # PDF audit report generation (fpdf2)
  erp_parser.py                # ERP CSV/Excel import mapping
  excel_parser.py              # Excel file parsing
  ssrs_parser.py               # SSRS report parsing
  timeseries.py                # Time series analysis
config.yaml                    # Facility config: temperature thresholds, shelf
                               #   life rules, allergen list, scoring weights
data/                          # SQLite demo database and seed script
tests/
  test_core_modules.py         # Input validation and error handling tests
```

## Dashboard tabs

1. **FEFO Despatch** -- Pallet-level stock view sorted by expiry. Color-coded
   urgency (RED/AMBER/GREEN). Flags certification mismatches (RSPCA raw
   material on GG production runs).
2. **Traceability** -- Batch lookup by code. Shows production data, linked
   orders, recent production.
3. **Temperature** -- Current readings per zone, excursion log, 7-day trend
   with threshold lines.
4. **Allergens** -- Product-by-allergen cross-reference matrix (EU 14 major
   allergens). Exportable CSV.
5. **Shelf Life** -- Concession tracking (plan use-by vs tag use-by), expiring
   batch alerts.
6. **Audit** -- Generates BRC compliance report with JSON and PDF export.

## Database

- **Default**: SQLite at `data/factory_compliance.db` (demo mode).
- **Production**: Set `COMPLIANCE_DB` env var to a connection string
  (e.g., `mssql+pyodbc://...`).
- **Streamlit Cloud**: Auto-detects read-only filesystem and falls back to
  a temp directory for the SQLite database.
- ORM models in `modules/database.py`: `Product`, `Batch`, `TemperatureLog`,
  `Order`.
- Helper functions: `query(sql, params)` returns a DataFrame,
  `scalar(sql, params)` returns a single value.

## Tests

```bash
python -m pytest tests/ -v
```

Tests validate input handling and error paths without requiring a database
connection. Database-dependent tests use try/except to pass gracefully when
no DB is available.

## Conventions

- **Error handling on all I/O**: Every database query and file read is wrapped
  in try/except. Streamlit `st.error()` or `st.info()` for user-facing errors,
  never raw tracebacks.
- **Parameterized queries**: Use `:param` syntax with SQLAlchemy `text()` for
  user input (e.g., batch code lookups). Never use f-strings for SQL with user
  data.
- **Config-driven thresholds**: Temperature limits, shelf life rules, scoring
  weights, and allergen lists come from `config.yaml`. Do not hardcode these.
- **Dynamic schema handling**: The FEFO tab introspects table columns with
  `PRAGMA table_info` before building queries. This handles schema variations
  between demo and production databases.
- **Batch code format**: `[D|F][YDDD][A-Z]` where D=Defrost, F=Fresh,
  Y=last digit of year, DDD=day of year, suffix=sub-batch.
- **Shelf life tiers**: Normal (+9d), Rubber clock (+10d, packed before 2pm),
  Superchilled (+11d), Superchilled freeze-down (+12d).
- **Scoring**: Temperature and traceability scores weighted equally. Passing
  threshold is 85%.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Key dependencies

- streamlit, pandas, plotly, sqlalchemy, pyyaml, openpyxl, fpdf2
- fastapi + uvicorn (API layer in `api.py`)
