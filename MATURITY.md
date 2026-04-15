# Data Maturity Scorecard

Self-assessment against the Data Pipeline Operations Maturity Model (PyCon DE 2026, Akif Cakir).

## Scoring: 5 Levels

1. **Struggling** — Manual processes, no monitoring
2. **Basic** — Some automation, ad-hoc checks
3. **Decent** — Declarative validation, defined SLOs
4. **Strong** — Anomaly detection, automated alerting
5. **Mastery** — Self-healing, error budgets, continuous improvement

---

## Pillar 1: Data Collection — Level 3

| Evidence | Where |
|---|---|
| 6 temperature zones monitored | config.yaml, temp_logs table |
| ERP auto-import with column mapping | modules/erp_parser.py (100+ aliases) |
| SSRS format detection | modules/ssrs_parser.py |
| 60 days of seeded demo data | data/seed_demo.py |

**Gap to Level 4:** No real-time sensor integration. Temperature readings are periodic, not streaming.

## Pillar 2: Data Quality — Level 3

| Evidence | Where |
|---|---|
| Declarative validation rules | modules/validation.py |
| Z-score anomaly detection | modules/timeseries.py |
| Batch code format validation | regex ^[DF]\d{4}[A-Z]$ |
| Allergen set validation | 14 EU allergens enforced |

**Gap to Level 4:** Validation is advisory, not blocking. No automated data profiling or drift detection.

## Pillar 3: Data Timeliness — Level 2

| Evidence | Where |
|---|---|
| Streamlit dashboard with 5-min cache | app.py (@st.cache_data ttl=300) |
| FastAPI for programmatic access | api.py |

**Gap to Level 3:** No freshness SLOs. No alerting when data goes stale.

## Pillar 4: Data Completeness — Level 3

| Evidence | Where |
|---|---|
| Traceability scoring (% with raw material link) | modules/traceability.py |
| SLO target: 90% traceability | modules/slo.py |
| Batch-to-order linkage tracking | Audit report tab |

**Gap to Level 4:** No automated backfill for missing traceability links.

## Summary

| Pillar | Level | Next Step |
|---|---|---|
| Data Collection | 3 | Real-time sensor integration |
| Data Quality | 3 | Blocking validation, drift detection |
| Data Timeliness | 2 | Freshness SLOs with alerting |
| Data Completeness | 3 | Automated backfill for gaps |

**Overall: Level 3 (Decent)**
