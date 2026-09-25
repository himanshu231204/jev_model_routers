## Description

A clear and concise description of what this PR does.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Test update
- [ ] CI/CD update

## Related Issues

Closes #(issue_number)

## How Has This Been Tested?

- [ ] `python -m pytest` passes
- [ ] Added/updated tests covering this change
- [ ] Manual testing performed (describe below)

## Checklist

- [ ] Code lands in the right module (see `AGENTS.md`'s module boundaries); no second router, Jev client or proxy
- [ ] Explicit overrides, fresh-turn pinning, and fail-open fallback still hold (if touching routing logic)
- [ ] No secrets or prompt content added to logs/errors
- [ ] `python -m pytest` passes; new tests added for non-trivial changes
- [ ] Behavior change reflected in `ARCHITECTURE.md` (not `docs/*`), per `AGENTS.md`'s Definition of Done

## Additional Notes

Add any other notes about the PR here.
