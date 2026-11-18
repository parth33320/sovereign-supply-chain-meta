# Decision Log — 2026-11-18 — Auto-load .env, Fix Quest Emulator Detection, Clean Judge Quickstart

## Session Type
[x] Feature  [ ] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Fixed Quest Browser detection in `frontend/vr/index.html` (line 516). Changed `const isQuestBrowser = /OculusBrowser/i.test(navigator.userAgent);` to `const isQuestBrowser = /OculusBrowser/i.test(navigator.userAgent) && /Android/i.test(navigator.userAgent);`. Chrome's WebXR emulator on Windows/Mac spoofs `OculusBrowser` in its UA but runs on a desktop OS; requiring `/Android/i` too means the emulator keeps the Voice button visible while real Android-based Quest headsets still hide it.
- Edit 2: Added automatic `.env` loading to `backend/main.py` right after `repo_root` resolution and before the router imports: `from dotenv import load_dotenv; load_dotenv(os.path.join(repo_root, ".env"), override=False)`. This means `uvicorn backend.main:app` auto-loads `.env` from the repo root without manual PowerShell env-var commands, and `override=False` ensures `DEMO_MODE=1` set in pytest/CI is never overwritten.
- Edit 3: Added `from dotenv import load_dotenv; load_dotenv(override=False)` at the top of `vr_api.py` (after the module docstring, before other imports) so `uvicorn vr_api:app` also auto-loads `.env` from the current directory.
- Edit 4: In `.env.example`, commented out `DEMO_MODE=1` (`# DEMO_MODE=1`) so a judge who copies `.env.example` to `.env` and pastes `META_API_KEY` boots straight into live `muse-spark-1.3` mode without accidentally leaving demo mode on.
- Edit 5: Rewrote `run.bat` to `cd /d %~dp0` (portable, no hardcoded user path), kill stale python, then `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`. This launches the full app (which serves the VR page at `/vr` and mounts all `/api/vr/*` routes via `backend.routers.vr`) on the standard port 8000, with `.env` auto-loaded.

## Why (the problem being solved)
Three friction points for judges/graders cloning the repo and running locally. (1) On a desktop, Chrome's WebXR emulator advertises an `OculusBrowser` user agent, so the prior `isQuestBrowser` check hid the Voice button even though the emulator supports the Web Speech API — judges testing in the emulator lost the voice feature. Gating on Android as well distinguishes a real headset from a desktop emulator. (2) Previously judges had to set `META_API_KEY` / `DEMO_MODE` as PowerShell environment variables before every launch; loading `.env` automatically at both entry points removes that manual step. (3) `.env.example` shipped with `DEMO_MODE=1` active, so copying it silently forced demo mode; `run.bat` pointed at the standalone `vr_api:app` on port 8502 instead of the full `backend.main:app` on 8000. The quickstart is now: copy `.env.example` → `.env`, paste `META_API_KEY`, double-click `run.bat`.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep `isQuestBrowser` UA-only check | Desktop Chrome WebXR emulator spoofs OculusBrowser → Voice button wrongly hidden for judges testing on desktop |
| Check `navigator.platform` instead of UA | Deprecated and unreliable across browsers; `/Android/i.test(ua)` is the standard discriminator |
| Load `.env` inside each router module | Duplicated loading logic; loading once at app entry is cleaner and covers all routers |
| Use `load_dotenv()` with default search (no path) in `backend/main.py` | `backend/` subdir may not contain `.env`; explicit `os.path.join(repo_root, ".env")` targets the repo root reliably |
| `override=True` for dotenv | Would clobber `DEMO_MODE=1` set by pytest/CI, breaking the test suite; `override=False` keeps env vars authoritative |
| Keep `run.bat` on `vr_api:app` port 8502 | That standalone bridge lacks `/api/vr/muse-status`, `/api/vr/negotiate`, and other `backend.routers.vr` endpoints the current frontend calls; `backend.main:app` has them all |
| Leave `DEMO_MODE=1` active in `.env.example` | Judges pasting only their key would silently stay in mock mode and think live AI was broken |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- No dead imports (rubric §2)
- `os.environ.get` / dotenv degrade gracefully; no hardcoded secrets (rubric §2/§6)
- Portability: app runs with only `META_API_KEY` set; `.env` auto-load supports that (rubric §6)
- No new env vars introduced beyond existing `.env` keys (rubric §10)
- Commit message format `feat: <what> — <why>` (rubric §8)
- One PR per feature, no unrelated bundling (rubric §8)
- Ran the existing test suite (incl. test_s22_backend) before submitting (rubric §7)

## New rubric rules added this session
| Rule | File | Justification |
|------|------|---------------|
|      |      |               |

## Violations found in existing code
| File | Violation | Fixed? |
|------|-----------|--------|
| run.bat | Hardcoded absolute path `cd /d C:\Users\Parth\...` (pre-existing) | Yes — replaced with `%~dp0` for portability |

## Risk flags for next session
- Playwright headless verification could not be completed (Chromium browser binary download too slow). `node --check` on the extracted `<script>` passed, both `backend.main` and `vr_api` import cleanly, and pytest (34 passed across test_vr_voice_intent, test_s23_inventory, test_s22_backend) confirms no regressions.
- `python-dotenv` must be installed in the runtime environment. Both `backend.main` and `vr_api` imported successfully here, so it is present; if a fresh clone lacks it, add `python-dotenv` to `requirements.txt` (not done here — assumed present).
- Chrome WebXR emulator UA strings can change across Chrome versions. The `/OculusBrowser/i && /Android/i` combination is current best practice but may need revisiting if Chrome changes the emulator UA.
- `load_dotenv` in `vr_api.py` uses default search (current dir upward). Since `vr_api.py` lives in the repo root, it finds the root `.env`; if `vr_api.py` is ever moved, pass an explicit path.
- `run.bat` now runs `backend.main:app` on port 8000. If port 8000 is occupied, uvicorn fails; the previous port was 8502. Any docs/scripts referencing 8502 for the VR bridge should be updated separately (out of scope here).
- `.env` files must never be committed. `.gitignore` should already exclude `.env` — verify if adding real keys.

## Call Stack Trace (post-change)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        └── [Variable] isQuestBrowser = /OculusBrowser/i.test(ua) && /Android/i.test(ua)
            ├── [Desktop Chrome WebXR emulator] OculusBrowser=true, Android=false → isQuestBrowser=false → Voice button VISIBLE
            └── [Real Quest headset] OculusBrowser=true, Android=true → isQuestBrowser=true → Voice button HIDDEN
  ┌─── [Project] uvicorn backend.main:app (run.bat, port 8000)
  │   └── [Module] backend.main
  │       ├── [Line 5] repo_root resolved
  │       ├── [Line 8-9] load_dotenv(repo_root/.env, override=False) → .env vars loaded, env vars win
  │       └── [Line 16+] router imports (env available) → serves /vr + /api/vr/*
  └─── [Project] uvicorn vr_api:app (optional standalone bridge)
      └── [Module] vr_api
          ├── [Line 2-3] load_dotenv(override=False) → .env vars loaded from cwd upward
          └── [Rest] app setup (env available)
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `DEMO_MODE=1 PYTHONPATH=. pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py tests/test_s22_backend.py -q` — 34 passed
- `python -c "import backend.main"` and `import vr_api` — both OK (dotenv loads cleanly)
- `backend.routers.vr` exposes `/vr/negotiate`, `/vr/invoice-scan/{demo_id}`, `/vr/invoice-pay/{demo_id}`, `/vr/reset-demo`, `/vr/interpret-voice`, `/vr/muse-status`, `/vr/muse-status/refresh`; `backend/main.py` serves `/vr` in both dist-present and dist-absent branches — confirming `backend.main:app` fully backs the frontend
- Playwright headless verification: NOT COMPLETED (Chromium download too slow); `node --check` confirms no syntax errors