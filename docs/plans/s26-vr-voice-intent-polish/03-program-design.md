# Program Design: S26 — VR Voice Intent + Demo Polish

## Files
- `frontend/vr/index.html` — whole VR client; rewritten around one card system, no inline styles, no nav bar.
- `vr_api.py` — one new endpoint + two module-level helpers; duplicate `import os` and inline `import httpx` removed.
- `tests/test_vr_voice_intent.py` — new: parser + endpoint tests with mocked HTTP.
- `.env.example` — document `MUSE_API_KEY` / `MUSE_BASE_URL` aliases.
- `README.md` — S26 bullet + env var rows.
- `docs/decisions/2026-11-16-s26-vr-voice-intent-polish.md` — rubric violations found in the abandoned attempt.

## Types & signatures
```python
class VoiceIntentPayload(BaseModel):
    transcript: str = ""

def _parse_intent_json(content: str | dict | None) -> dict:
    """Return {"intent": <allowed intent>, "item": <str|None>} from an LLM reply."""

@app.post("/api/vr/interpret-voice")
async def interpret_voice(payload: VoiceIntentPayload) -> dict:
    """Classify a voice transcript; never raises, always returns a valid intent object."""
```
```js
function openPanel(html, accent)      // accent: "info" | "ok" | "warn" | "danger" | "accent"
function closePanel()
function resolveIntent(transcript)    // → Promise<intent>
function fallbackIntent(transcript)   // → intent
function handleIntent(intent, transcript)
function showVoiceFeedback(transcript, intent, intentLabel)
function clearVoiceFeedback()
function resetMicBtn(clearFeedback)
function setPinchVisual(hand, active)
function pulseHaptic(src)
```

## Call stack
See `02-architecture.md`.

## Test plan
- `test_interpret_voice_happy_path` — mocked httpx returns fenced JSON → endpoint returns `approve_po`.
- `test_interpret_voice_rejects_unknown_intent` — LLM returns `"launch_missiles"` → coerced to `unknown`.
- `test_interpret_voice_no_api_key` — env cleared → `unknown`, no HTTP call.
- `test_interpret_voice_upstream_error` — mocked client raises → `unknown` (no 500).
- `test_parse_intent_json_plain_fenced_prose_garbage` — four parser branches.
- `test_frontend_has_no_inline_style_attributes` — regex guard over generated-markup section.

## Least confident decisions
1. Keeping Widget-A DB seed at 50 (required by `tests/test_s23_inventory.py`) while the shelf overlay starts at 0 for the stockout narrative.
2. Voice feedback placement: top-centre under the status pill rather than inside `#ar-panel`, because every panel render replaces `innerHTML` and the panel starts hidden.
3. Dimming the scene (`body.panel-open`) instead of resizing the panel: keeps spatial context without the card appearing to "cover" content.