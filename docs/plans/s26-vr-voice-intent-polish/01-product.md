# Product: S26 — VR Voice Intent + Demo Polish

## Problem
The Quest/AR walk cannot be driven reliably: the A2A result panel is a full-width bottom sheet that hides the shelf and invoice, the invoice is only reachable through a nav tab (un-AR-native), voice commands only understand "restock", and the in-progress attempt crashes the page before anything renders.

## Success metric
A judge can complete the whole loop hands-free: **pinch Widget-A → watch A2A negotiate → approve by voice → pinch Widget-A again → invoice appears → pay by voice → stock updates**, with the shelf never ambiguously covered and every command acknowledged on screen.

## Announcement — the blog post before the feature
The AR walk now behaves like a warehouse tool instead of a web page. There are no tabs: you pinch the shelf, the negotiation card floats in front of you, and the supplier invoice appears exactly when it should — after the PO is approved. Say "approve", "reject", "pay invoice" or "show invoice" and the card tells you what it heard and what it did. Every pinch now answers with a glow and a haptic tick, so you never wonder whether the headset caught your hand.

## Screens
- `frontend/vr/index.html` — shelf scene, invoice scene, floating A2A/result card, voice feedback toast (single-file WebXR app)