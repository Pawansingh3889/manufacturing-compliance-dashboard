# Changelog

All notable user-facing changes to the Manufacturing Compliance
Dashboard are logged here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The dashboard is continuously deployed from `main` to Streamlit Cloud
and Hugging Face Spaces — there are no tagged releases today, so entries
accumulate under `[Unreleased]` until that changes (see
`GOVERNANCE.md` § Release cadence).

## [Unreleased]

### Added
- **Four Golden Signals `/metrics` endpoint** (`modules/metrics.py`,
  wired via FastAPI middleware) — latency p50/p95/p99, traffic rps,
  5xx error rate + count, best-effort saturation (psutil when
  installed). 10-minute rolling window in-process. 13 tests in
  `tests/test_metrics.py`.
- **ScanAPI integration tests** — `scanapi/scanapi.yaml` drives
  every FastAPI endpoint over real HTTP. Complements the in-process
  TestClient tests. `make scanapi` locally; dedicated CI workflow
  uploads the HTML report as an artefact on every run. Uses ScanAPI
  by Camila Maia and the ScanAPI org (MIT).
- **Scope-and-limitations README section** — explicit "what this does /
  what it does NOT do" lists so users don't form ChatGPT-style
  expectations (Frank Rust & Thomas Prexl pattern, PyCon DE 2026).
- **Governance paperwork** — `GOVERNANCE.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` with anonymisation
  checklist, plus `NOTICE` per Apache 2.0 § 4(d).
- **Contributor-experience automation** — issue templates (bug +
  feature + config), PR template with BRCGS-clause field +
  anonymisation checklist, CODEOWNERS, first-contributor welcome
  workflow, conventional-commit PR-title validator.

### Changed
- **Relicensed from MIT to Apache 2.0.** Solo-authored codebase; Apache
  2.0 adds explicit patent grant + NOTICE convention, which matters for
  enterprise audit. See `NOTICE` for the upstream licence chain.
- **`/health` timestamp** now timezone-aware (`datetime.now(timezone.utc)`)
  so the Python 3.14+ DeprecationWarning on `utcnow()` goes away.
  Still ISO-8601, just with `+00:00` instead of naive.

### Fixed
- **`modules/metrics.py` ruff I001** — extra blank line after import
  block dropped.

---

*Earlier history lives in the git log — `git log --oneline` on any
commit on `main`.*
