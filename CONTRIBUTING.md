# Contributing to the Manufacturing Compliance Dashboard

This dashboard covers a regulated domain (BRC / HACCP food safety) and
runs on public hosting (Streamlit Cloud + Hugging Face Spaces). The bar
for contributions is therefore higher than a generic side project:
correctness matters, anonymity is mandatory, and scope creep hurts the
audit story.

## The Prime Directive

**No real PII. Ever.** Employee names, customer identifiers, real batch
codes, vessel registration numbers, supplier names, factory zone names
with their real thresholds — none of those ever land in this repo. The
anonymised synthetic data in `scripts/seed_demo_db.py` is the only
example you may use in fixtures, tests, or screenshots. Production
deployments that point at the real ERP keep the real data there, not in
code.

If you're unsure whether a string is "real", assume it is and use a
placeholder.

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/manufacturing-compliance-dashboard.git
cd manufacturing-compliance-dashboard
make setup       # install dependencies
make test        # run pytest
make run         # start Streamlit on http://localhost:8501
```

The FastAPI layer runs separately:

```bash
uvicorn api:app --reload   # http://localhost:8000/docs
```

## How to Contribute

1. **Find or open an issue.** Watch for `good first issue`, `help wanted`,
   and `compliance` labels.
2. **Fork and branch.** `feature/<short-name>` or `bugfix/<short-name>`.
3. **Code, commit small.** One logical change per commit; conventional
   commit style (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`).
4. **Test before you push.**
   - `make lint` — ruff must pass
   - `make typecheck` — ty must pass
   - `make test` — pytest must pass
5. **Pull request.** Explain *what*, *why*, and *how you tested it*.
   Reference the issue number. Anything that touches validation, SLOs,
   compliance scoring, or the anonymisation contract needs a full
   description and passing tests.

## What belongs in each directory

| Path | What lands here |
|---|---|
| `app.py` | Streamlit UI. Tabs and widgets only; domain logic lives in `modules/`. |
| `api.py` | FastAPI endpoints. One endpoint calls into one module function. |
| `mcp_server.py` | FastMCP tools exposing the same domain logic to LLM agents. |
| `modules/` | One file per concern: `compliance`, `traceability`, `allergens`, `temperature`, `shelf_life`, `slo`, `validation`, `metrics`, `nl_query`, `rag`, `chart_style`, `database`. |
| `tests/` | `test_<module>.py` — one file per module it covers. Keep fixtures small and synthetic. |
| `docs/` | Supporting markdown for the dashboard, landing page assets. |
| `scripts/` | Seed scripts and one-off helpers. Never commit real data. |
| `spark/` | Opt-in PySpark batch-analytics jobs. Not required for the Streamlit Cloud deploy. |

## Code Standards

- Python 3.11+.
- Ruff + ty must pass (see `pyproject.toml`).
- Type hints on every public function.
- Docstrings on every module and public function.
- New modules get a matching `tests/test_<module>.py`. The existing
  `test_metrics.py`, `test_slo.py`, `test_validation.py` are good
  templates — one `TestClass` per concern inside the module.
- Dependencies stay minimal. Before adding to `requirements.txt`, check
  whether stdlib or an already-installed package covers it.

## Compliance rules

The dashboard is built against BRCGS Issue 9. The clauses most often
touched are:

| Clause | What it requires | Where we cover it |
|---|---|---|
| 3.9 Traceability | Forward and backward tracing, mass-balance test | `modules/traceability.py`, `api.py::/batches/{code}/trace` |
| 3.11 Product Release | Void / return records | Indirectly via the trace chain; no automated release decision |
| 8.5.1 Electronic Records | Audit trail, access controls, tamper-evident storage | Out of scope — this dashboard is a read path, not a system of record |

A contribution that claims BRCGS coverage must either cite the clause it
implements or explicitly say what it leaves to the ERP. Don't overstate.

## Observability

`GET /metrics` exposes the Four Golden Signals (latency, traffic, errors,
saturation) over a 10-minute rolling window. New endpoints get metrics
for free via the middleware in `api.py`; no extra wiring needed.

SLOs live in `modules/slo.py`. A new SLO is defined by its success
criterion (e.g. `temperature compliance >= 95 %`), its measurement window,
and a test in `tests/test_slo.py`.

## Anonymisation checklist (pre-commit)

Before opening a PR, search your diff for:

- Real employee names (first + surname)
- Customer names (e.g. real retailer brands)
- Real batch code formats (the synthetic format is `X1234A` / `Y5678B`)
- Real factory zone names or exact temperature thresholds
- Vessel registration numbers
- Supplier names
- Sandbox or real passwords

If any of those land in a file, replace them with the synthetic forms
used elsewhere in the repo before pushing. When in doubt, ask in the PR.

## Reporting bugs

Open an issue with:

- Steps to reproduce.
- Expected vs actual.
- Which surface: Streamlit UI, REST API endpoint, MCP tool, or CLI.
- Python version, OS, deploy target (local / Streamlit Cloud / HF Space).
- A redacted traceback. **Never paste real data.**

## Feature requests

Open an issue describing:

- The compliance problem it solves (bonus points for a BRCGS clause
  reference).
- Which module it affects.
- Whether it needs a new dependency (default answer: no).

## Recognition

Merged PRs land in the commit history permanently. Substantial
contributions are acknowledged in the README when appropriate.
