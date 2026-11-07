## How This Rubric Works
- Location: docs/CODING_RUBRIC.md
- Auto-read by: .github/AGENTS.md at every session start
- Auto-enforced by: .github/workflows/rubric-check.yml
  on every PR
- Updated by: coding agent at end of every session
- Decision trace: docs/decisions/ one file per session

## Version History
| Date | Rule added | Justification | Added by |
|------|-----------|---------------|----------|
| 2026-11-05 | Initial rubric | Project foundation | Jules |

# Sovereign Supply Chain — Coding Rubric

## 1. Before Writing Any Code
- Read the existing file before editing it
- State what you are changing and why in one line
- Never assume a file's contents — always read first
- If a merge conflict exists, resolve it before proceeding
- Never create a new file if the logic belongs in an existing one

## 2. Code Quality Rules
- No dead imports — if a module is not used in UI, remove the import
- No duplicate code — if logic exists elsewhere, call it, don't copy it
- Every new function needs a one-line docstring
- Every API call must have a try/except with a user-friendly error message
- Never hardcode API keys, URLs or credentials — always use os.environ.get()
- Every os.environ.get() must have a sensible default or an explicit None check

## 3. UI Rules
- Never add a UI element without a clear user need
- One status banner maximum at a time — never stack banners
- No popup notifications that push page content down — use Activity Log
- Every interactive feature must have a ? tooltip to its left
- Mobile responsive — test at 768px width mentally before submitting
- No duplicate text — if something appears in header it cannot appear in breadcrumb and sidebar simultaneously
- Minimal is better — when in doubt, remove not add

## 4. Error Handling Rules
- Every module render must be wrapped in render_with_error_boundary()
- Every Meta API call must use @with_rate_limit_retry decorator
- Every file upload must use validate_file_upload() from security.py
- Never let an unhandled exception reach the user as a raw traceback
- Rate limit errors → show "please wait" message, not raw 429
- Auth errors → show "check your API key" message, not raw 401

## 5. Security Rules
- Every user text input must pass through sanitize_text_input() before use
- Every user text input must pass check_xss_patterns() before use
- Every user text input must pass check_prompt_injection() before use
- Never log API keys, user prompts, or PII to console or files
- File uploads must validate magic bytes not just file extension

## 6. Portability Rules
- App must run with ONLY META_API_KEY set as env var
- DEMO_MODE=1 must work with zero other env vars
- All other dependencies (POSTGRES_DB_URI etc) must degrade gracefully with user-friendly fallback message
- Never import a module at the top of app.py unless it is used by all three navigation modules
- Lazy imports for feature-specific modules only

## 7. Testing Rules
- Every new function needs at least one unit test
- Every new API integration needs a mock test
- Tests must not make real API calls — use mocks
- Add pytest.mark.skipif for tests requiring live credentials
- Run existing test suite before submitting any PR

## 8. Git and PR Rules
- One PR per sprint/feature — never bundle unrelated changes
- PR title must state: what changed, which file, why
- Resolve ALL merge conflicts before requesting review
- Never force push to main
- Commit message format:
  "feat|fix|refactor|docs: <what> in <file> — <why>"

## 9. Performance Rules
- No time.sleep() in the main UI thread except in progress indicators with explicit user feedback
- Cache expensive API calls in st.session_state
- Never call the same API twice in one render cycle
- Image uploads must be checked for size before reading bytes

## 10. Documentation Rules
- Every new file needs a module-level docstring explaining its purpose
- Every new env var must be added to .env.example
- Every new feature must be added to README.md
- demo-assets/README_DEMO.md must stay current with any new demo flow changes

# Added 2026-11-06 from UI critique session:
- Input bar must always be single combined row — never split into separate voice and text sections
- HITL approve/reject must appear as chat bubble not separate panel
- Guardrail block message must appear as chat bubble not page-level banner
- No hardcoded environment or version strings in UI — ever
- Guardrail whitelist must be checked before regex injection patterns — supply chain vocabulary never blocked
- ? tooltip must contain all downloadable samples for current module — never link to dead anchors
- Sidebar must contain only nav items — no platform labels, environment text, or navigation headers

## Rubric Checklist (run before every PR)
- [ ] Read every file I edited before editing it
- [ ] No dead imports
- [ ] All API calls have try/except
- [ ] All user inputs sanitized
- [ ] All file uploads validated
- [ ] Error boundary wraps all modules
- [ ] No duplicate UI text
- [ ] No stacked banners
- [ ] New env vars in .env.example
- [ ] Tests written and passing
- [ ] README updated if feature added
- [ ] Merge conflicts resolved
- [ ] Commit message follows format
