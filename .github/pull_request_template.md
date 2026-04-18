<!--
Thanks for contributing to the Manufacturing Compliance Dashboard!
One-line docs fixes can skip most sections; anything touching
validation, SLOs, or compliance scoring should fill everything.
-->

## What changed

<!-- One or two sentences explaining the *why*, not just the *what*. -->

## Related issue

<!-- "Closes #123" or "Relates to #123". -->

## BRCGS clause(s) this touches (if any)

<!-- e.g. 3.9 (Traceability), 3.11 (Product Release), 8.5.1 (Electronic
     Records). Leave blank if not compliance-related. -->

## Tests

- [ ] `make test` passes locally
- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] New tests cover the behaviour change (file under `tests/` named after the module)

## Anonymisation checklist

- [ ] No real employee names
- [ ] No real customer names (retailer brand names etc.)
- [ ] No real batch code formats
- [ ] No real factory zone names or exact temperature thresholds
- [ ] No real vessel registration numbers or supplier names
- [ ] No real sandbox or production passwords

## Contributor checklist

- [ ] One logical change per commit, conventional commit style (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`, `style:`)
- [ ] `CHANGELOG.md` entry under `[Unreleased]` if user-facing
- [ ] Docstrings updated on any public function whose signature changed

## Anything else reviewers should know
