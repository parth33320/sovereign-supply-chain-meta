# Decision Log — 2026-11-10 — Clean Up Legacy Streamlit UI Tests

## Session Type
[ ] Feature  [ ] Bug fix  [x] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Deleted legacy Streamlit UI test files:
  - `tests/test_warehouse_vision_ui.py`
  - `tests/test_document_vision_ui.py`
  - `tests/test_voice_ui_e2e.py`
  - `tests/test_sync_graph_invocation.py`

## Why (the problem being solved)
- The application UI was migrated from Streamlit to a React frontend (`frontend/`) served via FastAPI (`backend/`).
- These tests relied on `streamlit.testing.v1.AppTest` and asserted on Streamlit-specific widgets (`file_uploader`, `audio_input`, session state) that are no longer part of the application.
- UI testing is now conducted via React component tests and Playwright against the FastAPI backend endpoints.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Retain tests with skips | Tests target completely deleted UI architecture and Streamlit widgets |
| Rewrite tests against Streamlit | App is now React + FastAPI, obsolete Streamlit UI tests are unmaintained |

## Rubric rules applied this session
- Cleaned up obsolete tests without leaving dead code or failing assertions.
- Maintained test suite relevance after architecture migration.

## New rubric rules added this session
None.

## Violations found in existing code
None.

## Risk flags for next session
None.
