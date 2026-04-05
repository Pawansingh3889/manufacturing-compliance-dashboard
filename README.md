<div align="center">

# Manufacturing Compliance Dashboard

**BRC/HACCP compliance for food manufacturing**

Batch traceability, temperature monitoring, and allergen matrix in one Streamlit dashboard.
Built by someone who works on the factory floor.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)]()

</div>

---


## Batch Analytics (PySpark)

The spark/ module provides batch-level analytics using PySpark, designed for processing large volumes of compliance data:

| Output | What it computes |
|---|---|
| yield_analysis/ | Yield %, waste % by shift and production line |
| temperature_report/ | Excursion rates, avg/min/max temp by location |
| shelf_life_risk/ | Batches approaching or exceeding shelf life (EXPIRED/CRITICAL/WARNING) |
| daily_production/ | Daily throughput, quality rate, alert counts per line |

```bash
pip install pyspark>=3.5
python spark/batch_analytics.py
```


## What It Does

A ready-to-deploy Streamlit dashboard for food manufacturing compliance. Replaces Excel spreadsheets with a real-time compliance monitoring system.

| Feature | What You Get |
|---|---|
| **Batch Traceability** | Trace any batch from raw material intake through production to customer dispatch. Traceability score shows % of batches with complete chains. |
| **Temperature Monitoring** | Live readings by location, colour-coded (green/red). Excursion detection with configurable thresholds. 30-day trend charts. |
| **Allergen Matrix** | Product x allergen cross-reference grid. Filter by category. Export to CSV. BRC Section 5 compliant. |
| **Compliance Score** | Sidebar KPIs: Temperature Control %, Traceability %, Overall %. PASS/FAIL indicator. |
| **Excel Upload** | Drag-and-drop your existing Excel/CSV data. Validates columns automatically. |
| **Audit Report** | One-click compliance report with scores, excursions, and allergen matrix. JSON export (free), PDF/Excel export (premium). |

## Quick Start

```bash
git clone https://github.com/Pawansingh3889/manufacturing-compliance-dashboard.git
cd manufacturing-compliance-dashboard
make setup    # Install deps + seed 60 days of demo data
make run      # Open dashboard at localhost:8501
```

Or manually:

```bash
pip install -r requirements.txt
python data/seed_demo.py
streamlit run app.py
```

## Demo Data

Ships with 60 days of realistic manufacturing data:

| Table | Records | Content |
|---|---|---|
| Products | 10 | Fish products with allergen data |
| Raw Materials | ~200 | Supplier deliveries with batch codes |
| Production | ~500 | Daily runs with yield, waste, shift data |
| Orders | ~270 | Customer orders linked to production batches |
| Temperature Logs | ~19,000 | 5 locations, 8 readings/day |

## Configuration

Edit `config.yaml` to match your facility:

```yaml
temperature:
  locations:
    Cold Room 1:
      min: -2.0
      max: 5.0
    Freezer 1:
      min: -25.0
      max: -15.0
```

## Free vs Premium

| Feature | Free (GitHub) | Premium (Gumroad) |
|---|---|---|
| Batch traceability | Yes | Yes |
| Temperature monitoring | Yes | Yes |
| Allergen matrix | Yes | Yes |
| Compliance scoring | Yes | Yes |
| Single Excel upload | Yes | Yes |
| Multi-file historical import | | Yes |
| PDF audit report export | | Yes |
| Excel audit report export | | Yes |
| Docker deployment | | Yes |
| Multi-site support | | Yes |

**[Get Premium Version](https://pawankapko.gumroad.com/)**

## Tech Stack

| Component | Tool |
|---|---|
| UI | Streamlit |
| Charts | Plotly |
| Database | SQLite (demo) / PostgreSQL (production) |
| Data | pandas, SQLAlchemy |
| Config | YAML |

## Project Structure

```
manufacturing-compliance-dashboard/
├── app.py                    # Streamlit dashboard (4 tabs)
├── config.yaml               # Facility config (thresholds, allergens)
├── modules/
│   ├── traceability.py       # Batch tracing + traceability score
│   ├── temperature.py        # Monitoring + excursion detection
│   ├── allergens.py          # Allergen matrix generation
│   ├── excel_parser.py       # Excel/CSV upload + validation
│   ├── report_generator.py   # Audit report (JSON free, PDF/Excel premium)
│   └── database.py           # SQLite/PostgreSQL connection
├── data/
│   └── seed_demo.py          # 60-day demo data generator
├── Dockerfile                # Docker deployment (premium)
├── docker-compose.yml        # Docker Compose (premium)
├── Makefile                  # setup, run, seed, clean
├── requirements.txt
└── LICENSE
```

## Who This Is For

- Quality managers at food manufacturing sites
- BRC/HACCP auditors preparing for inspections
- Operations teams replacing Excel-based compliance tracking
- Anyone managing temperature monitoring, batch traceability, or allergen documentation

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) if applicable.

---

<div align="center">

**Built by [Pawan Singh Kapkoti](https://pawansingh3889.github.io)**

Data & Analytics Engineer | Food Manufacturing Domain Expert

[![Hire Me](https://img.shields.io/badge/Hire_Me-22c55e?style=for-the-badge)](mailto:pawankapkoti3889@gmail.com) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/pawan-singh-kapkoti-100176347)

</div>
