# Decision Log — 2026-11-06 — UI Cleanup and Guardrail Fix

## Session Type
[x] Feature  [x] Bug fix  [x] Refactor  [x] Docs  [x] Security

## What was built or changed
1. **Supply Chain Vocabulary Whitelist in Guardrails**:
   - Implemented `is_whitelisted_supply_chain_input` in `guardrails.py` running before regex pattern checks.
   - Evaluates prompts against domain vocabulary whitelist, filtering common stopwords. Safe supply chain inputs pass immediately.
   - Added `tests/test_guardrails_whitelist.py` asserting all 20 gold-standard voice inputs and full test dataset pass without false positives while blocking injection attempts.
2. **Sidebar Clutter Elimination**:
   - Removed PLATFORM label, Sovereign Tower title text, Navigation label, and fake `Environment: Meta Foundation Cloud v1.6.0-enterprise` caption.
   - Sidebar contains only `🛡️ **Sovereign**`.
3. **Claude-Style Combined Input Row**:
   - Replaced separate voice and text sections with a unified row `st.columns([0.05, 0.05, 0.05, 0.75, 0.1])` containing `[ ? ]`, `[ 📎 ]`, `[ 🎙️ ]`, `st.text_input`, and `[ ➔ ]`.
   - Native drawers for file upload and voice recording render inside the chat container boundary with explicit pointer rewinds and md5 deduplication.
4. **Action Slot & HITL Inline Interaction**:
   - HITL operator approval buttons `[ ✅ APPROVE ]` and `[ ❌ REJECT ]` sit in the dedicated Action Slot between the chat container and the input row to prevent scroll jumping.
   - Removed standalone HITL side panels and orange warning boxes.
5. **No Hardcoded Environment Strings & Rubric Grep Enforcement**:
   - Removed all hardcoded environment strings from the UI.
   - Updated `.github/workflows/rubric-check.yml` with CI checks enforcing zero popups, zero hardcoded environment strings, and zero sidebar navigation labels.

## Why this approach
- Eliminates false positive guardrail blocks on valid logistics instructions.
- Modernizes UI into a unified conversational experience matching modern frontier AI interfaces (Claude/ChatGPT).
- Prevents Streamlit scroll jumps during operator decision-making.

## Trade-offs and Alternatives Considered
- *Popovers vs Inline*: Popovers create floating overlay artifacts that clash on mobile. Replaced with assistant help bubble and Action Slot sample downloads.
- *Fixed Pixel Container vs Responsive*: Container with clean vertical block constraints allows drawers to expand naturally without overflowing mobile viewports.
