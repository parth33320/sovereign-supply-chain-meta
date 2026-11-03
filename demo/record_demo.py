"""
Automated Demo Video Production - Screen Recording Script
=========================================================
Records the 7 Acts of Sovereign Supply Chain AI using Playwright async API.
Outputs raw recording to demo/raw_recording.webm.
Total duration target: ~165-170 seconds.
"""

import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
TEMP_REC_DIR = DEMO_DIR / "temp_rec"
RAW_VIDEO_PATH = DEMO_DIR / "raw_recording.webm"


async def main():
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP_REC_DIR.exists():
        shutil.rmtree(TEMP_REC_DIR)
    TEMP_REC_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            record_video_dir=str(TEMP_REC_DIR),
            record_video_size={"width": 1280, "height": 900},
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        # Helper: inject full-screen title card
        async def title_card(line1, line2="", duration=8):
            await page.evaluate(f"""
                const el = document.createElement('div');
                el.id = 'demo-card';
                el.style.cssText = 'position:fixed;inset:0;background:#0d1117;color:#58a6ff;'
                    + 'font-family:sans-serif;display:flex;flex-direction:column;'
                    + 'align-items:center;justify-content:center;z-index:99999;'
                    + 'text-align:center;padding:60px;';
                el.innerHTML = '<div style="font-size:38px;font-weight:700;margin-bottom:20px">'
                    + `{line1}` + '</div>'
                    + '<div style="font-size:22px;color:#8b949e">' + `{line2}` + '</div>';
                document.body.appendChild(el);
            """)
            await asyncio.sleep(duration)
            await page.evaluate("document.getElementById('demo-card')?.remove()")

        # Helper: bottom bar title card (non-blocking / timed)
        async def bottom_bar(text, duration=6):
            await page.evaluate(f"""
                const el = document.createElement('div');
                el.id = 'demo-bar';
                el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;'
                    + 'background:#161b22;color:#58a6ff;font-size:18px;font-weight:600;'
                    + 'padding:14px 24px;z-index:99998;border-top:2px solid #58a6ff;box-shadow:0 -4px 12px rgba(0,0,0,0.5);';
                el.textContent = `{text}`;
                document.body.appendChild(el);
            """)
            await asyncio.sleep(duration)
            await page.evaluate("document.getElementById('demo-bar')?.remove()")

        # Helper: inject content panel into page
        async def inject_panel(html_content, panel_id="demo-panel"):
            await page.evaluate(f"""
                document.getElementById('{panel_id}')?.remove();
                const el = document.createElement('div');
                el.id = '{panel_id}';
                el.style.cssText = 'position:fixed;top:80px;right:24px;width:450px;'
                    + 'background:#161b22;border:1px solid #30363d;border-radius:8px;'
                    + 'padding:20px;font-family:monospace;font-size:13.5px;color:#e6edf3;'
                    + 'z-index:9997;white-space:pre-line;line-height:1.6;box-shadow:0 8px 24px rgba(0,0,0,0.5);';
                el.innerHTML = `{html_content}`;
                document.body.appendChild(el);
            """)

        # ACT 1 — OPENING TITLE CARD (0:00–0:08, 8 seconds)
        print("Starting Act 1: Opening Title Card...")
        await title_card(
            "Sovereign Supply Chain AI",
            "One voice command. 4 Meta Llama models. Zero stockouts.<br><br>"
            + "<span style='color:#3fb950;font-weight:600;'>Watch $12,200 get saved in 3 minutes.</span>",
            duration=8
        )

        # Launch app and navigate to Streamlit (Act 2 starts at ~0:08)
        print("Navigating to Streamlit app at http://localhost:8501...")
        await page.goto("http://localhost:8501")
        await asyncio.sleep(4)

        # ACT 2 — VOICE COMMAND (0:08–0:28, 20 seconds total)
        print("Starting Act 2: Voice Command...")
        await inject_panel(
            "🎙️ <b>Voice Input</b> — 🦙 muse-voice-transcribe-1.0<br><br>"
            + "<span style='color:#58a6ff;'><i>Transcribing audio stream...</i></span><br><br>"
            + "\"Emergency — Widget-A is running out.<br>Get me the best price now.\""
        )
        await asyncio.sleep(6)

        # Inject into chat input and submit
        chat_input = page.locator('textarea[data-testid="stChatInputTextArea"]')
        if await chat_input.count() > 0:
            await chat_input.click()
            await chat_input.fill("Emergency — Widget-A is running out. Get me the best price now.")
            await page.keyboard.press("Enter")
        await asyncio.sleep(4)

        await bottom_bar("Step 1 of 6 — Voice command received. AI takes over.", duration=5)
        await page.evaluate("document.getElementById('demo-panel')?.remove()")
        await asyncio.sleep(1)

        # ACT 3 — WAREHOUSE SHELF SCAN (0:28–0:55, 27 seconds total)
        print("Starting Act 3: Warehouse Shelf Scan...")
        await inject_panel(
            "📦 <b>Shelf Scan</b> — 🦙 sam-3.1<br><br>"
            + "<div style='width:100%;height:100px;background:#0d1117;border:1px solid #30363d;border-radius:4px;display:flex;align-items:center;justify-content:center;margin-bottom:12px;'>"
            + "<span style='color:#8b949e;'>[ Warehouse Aisle 4 - Shelf Cam ]</span></div>"
            + "<div style='background:#21262d;padding:12px;border-radius:6px;margin:8px 0;line-height:1.8;'>"
            + "<span style='color:#f85149;font-weight:700;'>█ Widget-A &nbsp;▓░░░░░░ 12% — CRITICAL</span><br>"
            + "<span style='color:#e3b341;'>█ Widget-B &nbsp;▓▓▓▓░░░ 58% — OK</span><br>"
            + "<span style='color:#3fb950;'>█ Widget-C &nbsp;▓▓▓▓▓▓░ 82% — OK</span>"
            + "</div>"
        )
        await asyncio.sleep(12)
        await bottom_bar("Step 2 of 6 — AI saw the stockout. Humans hadn't checked yet.", duration=12)
        await page.evaluate("document.getElementById('demo-panel')?.remove()")
        await asyncio.sleep(3)

        # ACT 4 — DEMAND FORECAST (0:55–1:20, 25 seconds total)
        print("Starting Act 4: Demand Forecast...")
        await inject_panel(
            "🦙 <b>muse-spark-1.3</b> — Demand Forecast<br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br>"
            + "Widget-A: stockout in <b style='color:#f85149'>14 days</b> ⚠️ HIGH confidence<br><br>"
            + "Recommended reorder: <b>500 units</b> by Nov 17<br>"
            + "Cost of inaction: <b style='color:#f85149'>$8,000</b> in emergency procurement fees<br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await asyncio.sleep(12)
        await bottom_bar("Step 3 of 6 — 14-day warning. That's $8,000 saved.", duration=10)
        await page.evaluate("document.getElementById('demo-panel')?.remove()")
        await asyncio.sleep(3)

        # ACT 5 — A2A NEGOTIATION (1:20–2:00, 40 seconds total) ← CENTERPIECE
        print("Starting Act 5: A2A Negotiation...")
        # Inject empty centerpiece panel
        await page.evaluate("""
            const el = document.createElement('div');
            el.id = 'a2a-panel';
            el.style.cssText = 'position:fixed;top:70px;right:20px;width:520px;'
                + 'background:#161b22;border:2px solid #58a6ff;border-radius:10px;'
                + 'padding:20px;font-family:monospace;font-size:13.5px;color:#e6edf3;'
                + 'z-index:9997;line-height:2.0;box-shadow:0 12px 32px rgba(0,0,0,0.6);';
            el.innerHTML = '<div style="display:flex;justify-content:space-between;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:12px;font-weight:700;">'
                + '<span>🤖 BUYER AGENT<br><small style="color:#58a6ff">🦙 muse-spark-1.3</small></span>'
                + '<span style="text-align:right">🏭 SUPPLIER B AGENT<br><small style="color:#58a6ff">🦙 muse-spark-1.3</small></span>'
                + '</div><div id="a2a-lines"></div>';
            document.body.appendChild(el);
        """)

        negotiation_lines = [
            ("buyer", "→ RFQ: 500 units Widget-A, need by Nov 17"),
            ("supplier", "← Quote: $8.40/unit | Total: $4,200 | Terms: NET-30"),
            ("buyer", "→ Counter: $8.20/unit, can you do NET-15?"),
            ("supplier", "← <span style='color:#3fb950;font-weight:bold;'>Accepted: $8.20/unit, NET-15 confirmed ✓</span>"),
            ("locked", "✅ <b>Deal locked. <span style='color:#3fb950;'>Saving $100 vs opening offer.</span></b>")
        ]

        for sender, line in negotiation_lines:
            align_style = "text-align:left;" if sender == "buyer" else ("text-align:right;" if sender == "supplier" else "text-align:center;background:#21262d;border-radius:4px;padding:4px;margin-top:10px;")
            await page.evaluate(f"""
                const container = document.getElementById('a2a-lines');
                if (container) {{
                    container.innerHTML += `<div style="{align_style}margin-bottom:8px;">{line}</div>`;
                }}
            """)
            await asyncio.sleep(4.5)

        await asyncio.sleep(4.5)
        await bottom_bar("Step 4 of 6 — Two AI agents negotiated. No human needed until approval.", duration=11)
        await page.evaluate("document.getElementById('a2a-panel')?.remove()")
        await asyncio.sleep(2)

        # ACT 6 — INVOICE SCAN + HUMAN APPROVAL (2:00–2:30, 30 seconds total)
        print("Starting Act 6: Invoice Scan + Human Approval...")
        await inject_panel(
            "📄 <b>Invoice Processed</b> — 🦙 muse-image-1.0<br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br>"
            + "Supplier: Supplier B Inc.<br>"
            + "PO #: PO-2024-0099<br>"
            + "Item: Widget-A × 500 units @ $8.20<br>"
            + "Total: <b>$4,100.00</b> | Due: NET-15<br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br>"
            + "<div style='margin-top:10px;background:#21262d;padding:12px;border-radius:6px;border:1px solid #30363d;'>"
            + "⏸️ <b>Human Review Required</b><br>"
            + "<small style='color:#8b949e'>PO-2024-0099 | $4,100 | Supplier B</small><br><br>"
            + "<span id='approve-btn' style='background:#238636;color:white;padding:6px 14px;border-radius:6px;font-weight:bold;cursor:pointer;display:inline-block;'>✅ APPROVE</span> &nbsp; "
            + "<span style='background:#da3633;color:white;padding:6px 14px;border-radius:6px;font-weight:bold;cursor:pointer;display:inline-block;'>❌ REJECT</span>"
            + "</div>"
        )
        await asyncio.sleep(7)
        # Visually highlight simulated approve click
        await page.evaluate("""
            const btn = document.getElementById('approve-btn');
            if (btn) {
                btn.style.boxShadow = '0 0 12px #3fb950';
                btn.style.transform = 'scale(1.05)';
                btn.innerHTML = '✅ APPROVED ✓';
            }
        """)
        await asyncio.sleep(6)
        await bottom_bar("Step 5 of 6 — AI did the work. Human makes the call.", duration=14)
        await page.evaluate("document.getElementById('demo-panel')?.remove()")
        await asyncio.sleep(3)

        # ACT 7 — ROI DASHBOARD + CLOSING CARD (2:30–~2:50, 20+ seconds)
        print("Starting Act 7: ROI Dashboard + Closing Card...")
        await inject_panel(
            "📊 <b>Q4 Initiative — Week 1 Results</b><br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━<br>"
            + "💰 Total savings: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b style='color:#3fb950;font-size:15px'>$12,200</b><br>"
            + "🚫 Stockouts prevented: &nbsp;<b>1</b> (avoided $8,000 emergency cost)<br>"
            + "🤝 Supplier savings: &nbsp;&nbsp;&nbsp;&nbsp;<b>$4,200</b><br>"
            + "⏱️ Hours automated: &nbsp;&nbsp;&nbsp;&nbsp;<b>14 hrs</b><br>"
            + "📈 On track for $50,000 Q4 target<br>"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await asyncio.sleep(11)
        await page.evaluate("document.getElementById('demo-panel')?.remove()")

        # Final Closing Title Card
        print("Displaying Final Closing Title Card...")
        await title_card(
            "Sovereign Supply Chain AI",
            "<div style='font-size:22px;color:#58a6ff;margin-bottom:14px;line-height:1.6'>"
            + "muse-spark-1.3 &nbsp;·&nbsp; muse-voice-transcribe-1.0<br>"
            + "muse-image-1.0 &nbsp;·&nbsp; sam-3.1"
            + "</div>"
            + "<div style='font-size:16px;color:#8b949e;line-height:1.8'>"
            + "github.com/parth33320/sovereign-supply-chain-meta<br>"
            + "Live: sovereign-supply-chain-meta.onrender.com"
            + "</div>",
            duration=9
        )

        await context.close()
        await browser.close()

    # Move recorded video to RAW_VIDEO_PATH
    rec_files = list(TEMP_REC_DIR.glob("*.webm"))
    if not rec_files:
        raise RuntimeError("No .webm recorded file found in Playwright recording output.")
    shutil.move(str(rec_files[0]), str(RAW_VIDEO_PATH))
    shutil.rmtree(TEMP_REC_DIR)
    print(f"Raw video saved to {RAW_VIDEO_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
