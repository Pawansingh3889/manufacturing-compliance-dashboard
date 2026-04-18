# Security policy

The Compliance Dashboard touches regulated data (BRC/HACCP), runs on
public hosting (Streamlit Cloud + Hugging Face Spaces), and exposes an
API + MCP surface that consumes natural-language input. This document
sets out the supported versions, the threat model, and how to report a
vulnerability.

## Supported versions

Continuous deployment from `main`. The supported version is always the
latest commit on `main`. If you are running an older commit, upgrade
first.

## Threat model

| Surface | Protection | Where |
| --- | --- | --- |
| FastAPI REST layer (`api.py`) | Read-only query patterns; SQL is parameterised; `/metrics` + structured exceptions | `api.py`, `tests/test_api.py` |
| MCP server (`mcp_server.py`) | FastMCP tool schema; each tool routes to a single module function with validated inputs | `mcp_server.py`, `tests/test_mcp_server.py` |
| NL query module (`modules/nl_query.py`) | Regex pattern matching; questions outside the coded set return "not supported" rather than reaching the database | `modules/nl_query.py`, `tests/test_api.py` |
| Demo data (`scripts/seed_demo_db.py`) | Synthetic only. No real PII or customer data | Anonymisation rule in `CONTRIBUTING.md` |
| Observability (`/metrics`) | Four Golden Signals, bounded window, no log body inspection | `modules/metrics.py`, `tests/test_metrics.py` |

Known gaps tracked publicly:

- Single-tenant authentication via Streamlit secrets (no RBAC). If you
  need multi-tenant isolation, put the app behind an identity-aware
  proxy. Documented in README § Scope and limitations.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security problem.**

Report privately via the GitHub security advisory form:

<https://github.com/Pawansingh3889/manufacturing-compliance-dashboard/security/advisories/new>

A good report has:

1. **What you found** — one-sentence description.
2. **Reproduction** — the exact request, query, or configuration that
   triggers it.
3. **Impact** — what an attacker could do.
4. **Suggested fix** — optional. A patch or test case is gold.

## What to expect

| Severity | Initial response | Fix target |
| --- | --- | --- |
| Critical | within 48 hours | within 7 days |
| High | within 5 days | within 14 days |
| Medium | within 7 days | next minor cycle |
| Low / info | within 14 days | when scoped |

Response times are honest estimates, not legal commitments. The
maintainer works alongside a factory-floor day job.

## Coordinated disclosure

Default: **90 days** from report to public disclosure. Sooner if the
fix is deployed and you agree; longer if the fix needs upstream
changes (e.g. in FastAPI, Streamlit, or fastmcp).

## Scope

**In scope:**

- `api.py`, `app.py`, `mcp_server.py`
- `modules/` — every file
- `scripts/seed_demo_db.py`
- Configuration parsing (`config.yaml`, env vars)
- Docker setup (`Dockerfile`, `docker-compose.yml`)

**Out of scope:**

- Upstream dependency CVEs (report those to the upstream; link the
  advisory here so we can pin the fix)
- Issues requiring local shell, `sudo`, or the ability to edit
  configuration at runtime
- Social engineering of the maintainer or contributors
- Streamlit Cloud / Hugging Face platform issues

## Previous advisories

None.
