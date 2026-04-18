# Compliance Dashboard governance

Who decides what, and what contributors can expect. Short by design —
this is a focused food-safety dashboard, not a platform.

## Roles

### Maintainer

Currently: **[@Pawansingh3889](https://github.com/Pawansingh3889)**.

The maintainer decides on:

- merges to `main`
- deployments to Streamlit Cloud and Hugging Face Spaces
- scope changes that affect the BRCGS compliance story
- this governance document

The maintainer commits to:

- replying to issues and PRs within **7 calendar days**
- merging green, in-scope PRs within **14 calendar days** of the last
  review comment being addressed
- giving first-time contributors a clear "go ahead" before they invest
  serious time

### Triage collaborator

Granted to contributors with three merged, in-scope PRs. Can label,
assign, and close off-topic issues. Cannot merge or change repository
settings.

### Contributor

Anyone who files an issue or opens a PR. No paperwork.

## Decisions

Small changes (docs, tests, bug fixes, single-module refactors) — one
maintainer approval on the PR.

Larger changes — new modules, new dependencies, API shape changes,
deployment targets — start as an **issue with a proposal** before any
code is written. Proposal template:

1. what compliance problem it solves (bonus: BRCGS clause reference)
2. the change in bullet form
3. alternatives considered
4. what anonymisation rule it affects, if any

### Architecture Decision Records (ADRs)

Proposals that change *how* the dashboard is built (new vector
backend, new auth model, new SLO definition, migration off Streamlit
Cloud) are labelled **`ADR`** on the issue so they stay easy to find.
Pattern from Camila Maia's ScanAPI talk (PyCon DE 2026). Follow-up
issues reference the ADR by number; the ADR issue stays open in an
archived state as the record of the decision.

## Issue assignment (first-PR-wins)

1. Comment "I'd like to work on this" — earns a 7-day soft claim.
2. Expire silently after 7 days if no PR opens; anyone may pick up.
3. If two PRs land, the first to pass CI and request review wins.
4. The maintainer will not hold a claim open for absent contributors.

## Scope discipline

The four lines that will not move on this project:

- **No real PII.** Ever. The synthetic seed in `scripts/seed_demo_db.py`
  is the only permissible data in fixtures, tests, or screenshots.
  See CONTRIBUTING.md § Anonymisation checklist.
- **Read-only to source ERPs.** Every deployed connection is read-only
  at the driver level; the dashboard surfaces data, it does not correct
  it.
- **No unverified BRCGS claims.** A PR that adds a "covers clause X"
  claim must either cite the clause in the relevant module docstring
  or explicitly say what is left to the ERP.
- **No multi-tenant expansion.** This is a factory-local dashboard,
  single-tenant by design. RBAC belongs behind an identity-aware
  proxy, not inside the app.

## Release cadence

Continuous deployment to Streamlit Cloud and Hugging Face Spaces from
`main`. There are no tagged releases today. If that changes:

- SemVer starting at 0.x
- breaking changes get one minor version of deprecation notice
- `CHANGELOG.md` will land before the first non-zero release

## Security

See `SECURITY.md`. Security issues route via private advisory, not
public issues.

## Changes to this document

Via PR from the maintainer. Community input welcome in issues.
