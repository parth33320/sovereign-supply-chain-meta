import asyncio
from playwright.async_api import async_playwright

DEMO_MODE_ENV = {"DEMO_MODE": "1"}

# ── Helper: inject CSS to wipe all Streamlit chrome ──────────────────
HIDE_STREAMLIT_CSS = """
    [data-testid="stSidebar"]          { display:none !important; }
    [data-testid="stHeader"]           { display:none !important; }
    [data-testid="stToolbar"]          { display:none !important; }
    footer                             { display:none !important; }
    #MainMenu                          { display:none !important; }
    .stDeployButton                    { display:none !important; }
    [data-testid="stDecoration"]       { display:none !important; }
    .stApp { background:#0d1117 !important; }
    .main .block-container {
        background:#0d1117 !important;
        padding-top: 2rem !important;
    }
    h1, h2, h3, label, p { color:#c9d1d9 !important; }
    .stSelectbox label { color:#8b949e !important; }
    .stTextInput input, .stSelectbox select {
        background:#161b22 !important;
        color:#c9d1d9 !important;
        border-color:#30363d !important;
    }
"""

# ── Helper: ripple effect on click ───────────────────────────────────
async def ripple_click(page, x, y):
    await page.evaluate(f"""
        const r = document.createElement('div');
        r.style.cssText = `
            position:fixed; left:{x-20}px; top:{y-20}px;
            width:40px; height:40px; border-radius:50%;
            background:rgba(88,166,255,0.5); z-index:99999;
            animation:ripple 0.6s ease-out forwards;
            pointer-events:none;
        `;
        const style = document.createElement('style');
        style.textContent = '@keyframes ripple {{from{{transform:scale(0);opacity:1}}to{{transform:scale(3);opacity:0}}}}';
        document.head.appendChild(style);
        document.body.appendChild(r);
        setTimeout(()=>r.remove(), 700);
    """)
    await page.mouse.click(x, y)
    await asyncio.sleep(0.3)

# ── Helper: full-screen title card ───────────────────────────────────
async def title_card(page, line1, line2="", line3="", duration=4):
    await page.evaluate("""
        ([l1, l2, l3]) => {
            document.getElementById('demo-panel')?.remove();
            const d = document.createElement('div');
            d.id = 'demo-panel';
            d.style.cssText = `
                position:fixed; inset:0; z-index:99998;
                background:#0d1117; display:flex; flex-direction:column;
                align-items:center; justify-content:center;
                font-family:sans-serif;
            `;
            d.innerHTML = `
                <div style="font-size:2.8rem;font-weight:700;color:#58a6ff;text-align:center;max-width:900px;">${l1}</div>
                <div style="font-size:1.4rem;color:#8b949e;margin-top:1.2rem;text-align:center;">${l2}</div>
                <div style="font-size:1.2rem;color:#3fb950;margin-top:0.8rem;font-weight:600;text-align:center;">${l3}</div>
            `;
            document.body.appendChild(d);
        }
    """, [line1, line2, line3])
    await asyncio.sleep(duration)
    await page.evaluate("document.getElementById('demo-panel')?.remove();")

# ── Helper: bottom bar strip ─────────────────────────────────────────
async def bottom_bar(page, text, duration=4):
    await page.evaluate("""
        (t) => {
            document.getElementById('demo-bar')?.remove();
            const b = document.createElement('div');
            b.id = 'demo-bar';
            b.style.cssText = `
                position:fixed; bottom:0; left:0; right:0; z-index:99997;
                background:rgba(13,17,23,0.95); border-top:2px solid #30363d;
                padding:12px 24px; font-family:sans-serif;
                font-size:1.05rem; color:#c9d1d9;
            `;
            b.textContent = t;
            document.body.appendChild(b);
        }
    """, text)
    await asyncio.sleep(duration)
    await page.evaluate("document.getElementById('demo-bar')?.remove();")

# ── Helper: inject a fixed dark panel (top-right) ────────────────────
async def inject_panel(page, header, model_badge, content_lines, panel_id="demo-panel", width=460):
    await page.evaluate(f"document.getElementById('{panel_id}')?.remove();")
    lines_html = "".join(f"<div style='margin:4px 0;'>{l}</div>" for l in content_lines)
    await page.evaluate("""
        ([pId, w, hdr, badge, bodyHtml]) => {
            const p = document.createElement('div');
            p.id = pId;
            p.style.cssText = `
                position:fixed; top:60px; right:30px; z-index:9997;
                width:${w}px; max-height:420px; overflow:hidden;
                background:#161b22; border:1px solid #30363d; border-radius:8px;
                font-family:monospace; font-size:0.82rem; color:#c9d1d9;
                padding:14px 16px;
            `;
            p.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;
                            border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:10px;">
                    <span style="font-weight:700;color:#58a6ff;">${hdr}</span>
                    <span style="color:#8b949e;font-size:0.75rem;">🦙 ${badge}</span>
                </div>
                <div id="${pId}-body" style="line-height:1.6;">${bodyHtml}</div>
            `;
            document.body.appendChild(p);
        }
    """, [panel_id, width, header, model_badge, lines_html])


async def run_demo():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            record_video_dir="demo/",
            record_video_size={"width": 1280, "height": 1080},
            viewport={"width": 1280, "height": 1080}
        )
        page = await context.new_page()
        await page.goto("http://localhost:8501", wait_until="networkidle")
        await asyncio.sleep(3)

        # Inject CSS to hide all Streamlit chrome
        await page.add_style_tag(content=HIDE_STREAMLIT_CSS)
        await asyncio.sleep(1)

        # ── ACT 1: Opening title card ─────────────────────────────
        await title_card(page,
            "Sovereign Supply Chain AI",
            "One voice command. 4 Meta Llama models. Zero stockouts.",
            "Watch $12,200 get saved in 3 minutes.",
            duration=8
        )

        # ── ACT 2 TITLE CARD ──────────────────────────────────────
        # Target timestamp: 8s
        await title_card(page,
            "Step 1 of 5 — Voice Command",
            "A warehouse manager speaks one sentence.",
            "muse-voice-transcribe-1.0 hears it. AI takes over.",
            duration=4
        )

        # ── ACT 2: Voice command transcription ───────────────────
        await inject_panel(page,
            "🎙 Voice Input",
            "muse-voice-transcribe-1.0",
            [
                "<span style='color:#58a6ff;font-style:italic;'>Transcribing audio stream...</span>",
                "",
                "<span style='color:#c9d1d9;'>\"Emergency — Widget-A is running out.</span>",
                "<span style='color:#c9d1d9;'>Get me the best price now.\"</span>",
            ]
        )
        await asyncio.sleep(4)
        # Simulate ripple click on voice input area
        await ripple_click(page, 640, 400)
        await asyncio.sleep(4)
        await bottom_bar(page, "Step 1 of 5 — Voice received. AI takes over.", duration=8)

        # ── ACT 3 TITLE CARD ──────────────────────────────────────
        # Target timestamp: 28s - 45s
        await title_card(page,
            "Step 2 of 5 — Warehouse Vision",
            "AI scans physical shelf using computer vision.",
            "sam-3.1 confirms: Widget-A is 12% — CRITICAL",
            duration=4
        )

        # ── ACT 3: SAM shelf scan ─────────────────────────────────
        # Target timestamp: 45s - 68s
        await inject_panel(page,
            "📦 Shelf Scan",
            "sam-3.1",
            [
                "<div style='background:#0d1117;padding:6px;border-radius:4px;text-align:center;color:#8b949e;margin-bottom:8px;'>[ Warehouse Aisle 4 — Shelf Cam ]</div>",
                "<span style='color:#f85149;'>■</span> <b>Widget-A</b> <span style='color:#f85149;'>████░░░░░░ 12% — CRITICAL</span>",
                "<span style='color:#e3b341;'>■</span> <b>Widget-B</b> <span style='color:#e3b341;'>█████░░░░░ 58% — OK</span>",
                "<span style='color:#3fb950;'>■</span> <b>Widget-C</b> <span style='color:#3fb950;'>████████░░ 82% — OK</span>",
            ]
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "Step 2 of 5 — Humans hadn't checked yet. sam-3.1 caught it.", duration=13)

        # ── ACT 4 TITLE CARD ──────────────────────────────────────
        await title_card(page,
            "Step 3 of 5 — Demand Forecast",
            "muse-spark-1.3 predicts: stockout in 14 days.",
            "Cost of inaction: $8,000 in emergency fees.",
            duration=4
        )

        # ── ACT 4: Demand forecast ────────────────────────────────
        # Target timestamp: 68s - 90s
        await inject_panel(page,
            "📊 Demand Forecast",
            "muse-spark-1.3",
            [
                "Widget-A: stockout in <span style='color:#e3b341;font-weight:700;'>14 days</span> ⚠ HIGH confidence",
                "",
                "Recommended reorder: <b>500 units</b> by Nov 17",
                "Cost of inaction: <span style='color:#f85149;font-weight:700;'>$8,000</span> in emergency procurement fees",
                "",
                "<div style='border-top:1px solid #30363d;margin-top:6px;padding-top:6px;color:#3fb950;'>✓ Forecast locked. Initiating supplier negotiation.</div>",
            ]
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "Step 3 of 5 — $8,000 saved if we act now. Agents negotiating.", duration=12)

        # ── ACT 5 TITLE CARD ──────────────────────────────────────
        # Target timestamp: 90s
        await title_card(page,
            "Step 4 of 5 — Agent Negotiation",
            "Two AI agents negotiate price. No human involved.",
            "muse-spark-1.3 × muse-spark-1.3",
            duration=4
        )

        # ── ACT 5: A2A negotiation (CENTERPIECE) ─────────────────
        # Inject header panel first
        await page.evaluate("""
            document.getElementById('demo-panel')?.remove();
            const p = document.createElement('div');
            p.id = 'demo-panel';
            p.style.cssText = `
                position:fixed; top:60px; right:30px; z-index:9997;
                width:520px; background:#161b22;
                border:1px solid #30363d; border-radius:8px;
                font-family:monospace; font-size:0.82rem; color:#c9d1d9;
                padding:14px 16px;
            `;
            p.innerHTML = `
                <div style="display:flex;justify-content:space-between;border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:10px;">
                    <div><span style="color:#58a6ff;font-weight:700;">🤖 BUYER AGENT</span><br><span style="color:#8b949e;font-size:0.72rem;">🦙 muse-spark-1.3</span></div>
                    <div style="text-align:right"><span style="color:#f85149;font-weight:700;">🏭 SUPPLIER B AGENT</span><br><span style="color:#8b949e;font-size:0.72rem;">🦙 muse-spark-1.3</span></div>
                </div>
                <div id="a2a-body" style="line-height:1.9;min-height:120px;"></div>
            `;
            document.body.appendChild(p);
        """)

        a2a_lines = [
            "→ RFQ: 500 units Widget-A, need by Nov 17",
            "← Quote: $8.40/unit | Total: $4,200 | Terms: NET-30",
            "→ Counter: $8.20/unit, can you do NET-15?",
            "← <span style='color:#3fb950;'>Accepted: $8.20/unit, NET-15 confirmed ✓</span>",
            "✅ <b>Deal locked.</b> <span style='color:#3fb950;'>Saving $100 vs opening offer.</span>",
        ]
        for line in a2a_lines:
            await page.evaluate("(l) => { document.getElementById('a2a-body').innerHTML += l + '<br>'; }", line)
            await asyncio.sleep(4.0)

        await asyncio.sleep(4)
        await bottom_bar(page, "Step 4 of 5 — Negotiated. No human needed until approval.", duration=8)

        # ── ACT 6 TITLE CARD ──────────────────────────────────────
        # Target timestamp: 130s
        await title_card(page,
            "Step 5 of 5 — Human Approval",
            "AI processes invoice. Human makes final call.",
            "muse-image-1.0 reads the document.",
            duration=4
        )

        # ── ACT 6: Invoice + HITL ─────────────────────────────────
        await inject_panel(page,
            "🧾 Invoice Processed",
            "muse-image-1.0",
            [
                "Supplier: <b>Supplier B Inc.</b>",
                "PO #: <b>PO-2024-0099</b>",
                "Item: Widget-A × 500 units @ $8.20",
                "Total: <b>$4,100.00</b> | Due: NET-15",
                "<div style='border-top:1px solid #30363d;margin-top:8px;padding-top:8px;'>",
                "  <span style='background:#e3b341;color:#0d1117;padding:2px 8px;border-radius:3px;font-weight:700;'>⚠ Human Review Required</span>",
                "  <div style='margin-top:8px;color:#8b949e;'>PO-2024-0099 | $4,100 | Supplier B</div>",
                "  <div style='display:flex;gap:10px;margin-top:10px;'>",
                "    <span style='background:#238636;color:#fff;padding:4px 16px;border-radius:4px;cursor:pointer;'>✓ APPROVE</span>",
                "    <span style='background:#da3633;color:#fff;padding:4px 16px;border-radius:4px;cursor:pointer;'>✗ REJECT</span>",
                "  </div>",
                "</div>",
            ]
        )
        await asyncio.sleep(5)

        # Ripple on APPROVE button, then flip to APPROVED
        await ripple_click(page, 920, 420)
        await page.evaluate("""
            const body = document.getElementById('demo-panel-body');
            if(body) {
                const btns = body.querySelector('div[style*="display:flex"]');
                if(btns) btns.innerHTML = '<span style="background:#238636;color:#fff;padding:4px 16px;border-radius:4px;font-weight:700;">✓ APPROVED</span>';
            }
        """)
        await asyncio.sleep(2)  # 2s pause on APPROVED ✓
        await bottom_bar(page, "Human makes the call. PO executed. AI handles the rest.", duration=8)

        # ── ACT 7: ROI dashboard ──────────────────────────────────
        # Target timestamp: 155s
        await title_card(page,
            "Results — Week 1",
            "",
            "",
            duration=4
        )

        await inject_panel(page,
            "🏆 Q4 Initiative — Week 1 Results",
            "Sovereign Supply Chain AI",
            [
                "💰 Total savings: <span style='color:#3fb950;font-size:1.05em;font-weight:700;'>$12,200</span>",
                "🚫 Stockouts prevented: <b>1</b> (avoided $8,000 emergency cost)",
                "💼 Supplier savings: <b>$4,200</b> (negotiated $100 below ask)",
                "⏱ Hours automated: <b>14 hrs</b>",
                "📈 On track for <b>$50,000 Q4 target</b>",
                "",
                "<div style='border-top:1px solid #30363d;margin-top:6px;padding-top:6px;color:#58a6ff;font-weight:700;'>4 Meta Llama models. 1 voice command. 3 minutes.</div>",
            ]
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "One voice command. $12,200 saved. Fully auditable.", duration=5)

        # ── ACT 8: Closing title card ─────────────────────────────
        # Target timestamp: 168s - 176s
        await title_card(page,
            "Sovereign Supply Chain AI",
            "muse-spark-1.3  ·  muse-voice-transcribe-1.0  ·  muse-image-1.0  ·  sam-3.1",
            "github.com/parth33320/sovereign-supply-chain-meta  |  sovereign-supply-chain-meta.onrender.com",
            duration=12
        )

        await context.close()
        await browser.close()

asyncio.run(run_demo())
