# Product: AR Walk — Demo Improvements

## Problem
The Meta Quest / browser AR Walk demo (`frontend/vr/index.html`) exposes Invoice, Guide, and Disruption paths from load, lets "Listening..." flash when the mic is idle, has no demo reset, and treats invoice approval as a second PO gate. Judges cannot cleanly rerun the full flow in one session.

## Solution
Progressive-disclosure AR Walk: Invoice tab locked until PO approved, mic-driven voice-command tooltip replaces the Guide button, "Listening..." only shows while recording, invoice scene becomes "Verify & Release Payment" / "Flag Discrepancy" with a pre-filled supplier dispute draft, real DB-backed Widget-A restock on payment release, a top-right Reset Demo button, terminal-state PO rejection, and disruption removed entirely.

## User Stories
1. As a demo judge, I start with Invoice locked so the story is pinch/voice → PO → approve → invoice → restock.
2. As a judge, I hover the mic to discover the available voice commands.
3. As a judge, I only see "Listening..." while the mic is actively recording.
4. As a judge, I verify invoice amounts match the approved PO and release payment, which increments Widget-A stock in the DB and refreshes the shelf.
5. As a judge, I can flag a discrepancy and see a dismissible supplier-dispute draft plus a "Pending supplier response" state (demo does not lock up).
6. As a judge, I can reset the demo from a top-right corner button at any time and rerun the full flow.
7. As a judge, rejecting the PO shows a terminal "PO rejected — restock paused" state (no loop), and I use Reset to try approval.

## Out of Scope
- React `frontend/src/` dashboard (Orchestrator/ManagerApprovals/Analytics).
- Real WebXR hand-tracking beyond optional pinch-to-speak if the simulator exposes it.
- Live Meta API key path (demo endpoints remain hardcoded fallback); invoice-scan uses demo data.

## Success Metric
A judge can run voice-or-pinch → PO → approve → invoice → verify → restock → reset → repeat, end-to-end in one browser session, with no "Listening..." flash, no second approval gate, and no disruption workflow.
