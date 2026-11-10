# Decision Log — 2026-11-07 — Pytest Timeout Version Pinning

## Session Type
[ ] Feature  [x] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Added `pytest-timeout==2.4.0` to `requirements.txt`.
- Verified execution of pytest runner with `--timeout=30` flag in Python 3.12.

## Why (the problem being solved)
- Python 3.12 completely removed the deprecated `distutils` standard library module.
- `pytest-timeout==1.4.2` attempts to import `LooseVersion` from `distutils.version`, throwing `ModuleNotFoundError: No module named 'distutils'` during pytest collection.
- Pinning `pytest-timeout==2.4.0` provides test timeout handling natively compatible with Python 3.12 without requiring extra shims or dependencies.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| `pytest-timeout==1.4.2` with `setuptools` | Unnecessarily pulls in `setuptools` solely as a `distutils` compatibility shim |
| Unpinned `pytest-timeout` | Pinned versions guarantee reproducible test executions across CI and environments |

## Rubric rules applied this session
- Tested and verified execution under Python 3.12.
- Kept requirements clean and free of unnecessary dependencies.

## New rubric rules added this session
None.

## Violations found in existing code
None.

## Risk flags for next session
None.
