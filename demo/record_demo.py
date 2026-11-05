import asyncio
from playwright.async_api import async_playwright

DEMO_MODE_ENV = {"DEMO_MODE": "1"}

# ── Helper: inject CSS to wipe all Streamlit chrome (FIX 2) ──────────
HIDE_STREAMLIT_CSS = """
.stApp { background:#0d1117 !important; }
.stApp * { visibility:hidden !important; }
#demo-left-panel, #demo-panel, #demo-bar, #demo-title-card, [id^="demo-"] { visibility:visible !important; }
[id^="demo-"] * { visibility:visible !important; }
"""

# ── Helper: ripple effect on click ───────────────────────────────────
async def ripple_click(page, x, y):
    await page.evaluate(f"""
        const r = document.createElement('div');
        r.id = 'demo-ripple-' + Date.now();
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
            document.getElementById('demo-title-card')?.remove();
            const d = document.createElement('div');
            d.id = 'demo-title-card';
            d.style.cssText = `
                position:fixed; inset:0; z-index:99998;
                background:#0d1117; display:flex; flex-direction:column;
                align-items:center; justify-content:center;
                font-family:sans-serif; text-align:center;
            `;
            d.innerHTML = `
                <div style="font-size:2.8rem;font-weight:700;color:#58a6ff;text-align:center;max-width:900px;">${l1}</div>
                ${l2 ? `<div style="font-size:1.4rem;color:#8b949e;margin-top:1.2rem;text-align:center;">${l2}</div>` : ''}
                ${l3 ? `<div style="font-size:1.2rem;color:#3fb950;margin-top:0.8rem;font-weight:600;text-align:center;">${l3}</div>` : ''}
            `;
            document.body.appendChild(d);
        }
    """, [line1, line2, line3])
    await asyncio.sleep(duration)
    await page.evaluate("document.getElementById('demo-title-card')?.remove();")

# ── Helper: bottom bar strip (FIX 6: text-align:center) ──────────────
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
                font-size:1.05rem; color:#c9d1d9; text-align:center;
            `;
            b.textContent = t;
            document.body.appendChild(b);
        }
    """, text)
    await asyncio.sleep(duration)
    await page.evaluate("document.getElementById('demo-bar')?.remove();")

# ── Helper: inject persistent left panel ─────────────────────────────
# Left panel geometry: left:30px, top:140px, width:540px
async def inject_left_panel(page, initial_lines, status="● RUNNING", tenant="Tenant-A"):
    await page.evaluate("document.getElementById('demo-left-panel')?.remove();")
    lines_html = "".join(f"<div style='margin:4px 0;'>{l}</div>" for l in initial_lines)
    await page.evaluate("""
        ([lines, status, tenant]) => {
            const p = document.createElement('div');
            p.id = 'demo-left-panel';
            p.style.cssText = `
                position:fixed; top:140px; left:30px; z-index:9997;
                width:540px; height:420px; box-sizing:border-box;
                background:#161b22; border:1px solid #30363d; border-radius:8px;
                font-family:monospace; font-size:0.82rem; color:#c9d1d9;
                padding:14px 16px; display:flex; flex-direction:column; justify-content:space-between;
            `;
            p.innerHTML = `
                <div>
                    <div style="border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:10px;">
                        <span style="font-weight:700;color:#58a6ff;">🤖 AGENT ACTIVITY LOG</span>
                    </div>
                    <div id="demo-left-panel-body" style="line-height:1.6;">${lines}</div>
                </div>
                <div id="demo-left-panel-footer" style="border-top:1px solid #30363d;padding-top:8px;margin-top:10px;display:flex;justify-content:space-between;color:#8b949e;font-size:0.75rem;">
                    <span id="demo-left-status">STATUS: <span style="color:#3fb950;font-weight:700;">${status}</span></span>
                    <span>Tenant: ${tenant}</span>
                </div>
            `;
            document.body.appendChild(p);
        }
    """, [lines_html, status, tenant])

# ── Helper: append lines to left panel ───────────────────────────────
async def append_left_panel(page, new_lines, update_status=None):
    for line in new_lines:
        await page.evaluate("""
            (l) => {
                const b = document.getElementById('demo-left-panel-body');
                if (b) {
                    const row = document.createElement('div');
                    row.style.margin = '4px 0';
                    row.innerHTML = l;
                    b.appendChild(row);
                }
            }
        """, line)
    if update_status:
        await page.evaluate("""
            (s) => {
                const st = document.getElementById('demo-left-status');
                if (st) {
                    st.innerHTML = `STATUS: <span style="color:#3fb950;font-weight:700;">${s}</span>`;
                }
            }
        """, update_status)

# ── Helper: inject right stage panel (FIX 4: width=540, right:30px, top:140px) ─
async def inject_panel(page, header, model_badge, content_lines, panel_id="demo-panel", width=540):
    await page.evaluate(f"document.getElementById('{panel_id}')?.remove();")
    lines_html = "".join(f"<div style='margin:4px 0;'>{l}</div>" for l in content_lines)
    badge_html = f"<span style='color:#8b949e;font-size:0.75rem;'>🦙 {model_badge}</span>" if model_badge else ""
    await page.evaluate("""
        ([pId, w, hdr, badgeHtml, bodyHtml]) => {
            const p = document.createElement('div');
            p.id = pId;
            p.style.cssText = `
                position:fixed; top:140px; right:30px; z-index:9997;
                width:${w}px; height:420px; box-sizing:border-box; overflow:hidden;
                background:#161b22; border:1px solid #30363d; border-radius:8px;
                font-family:monospace; font-size:0.82rem; color:#c9d1d9;
                padding:14px 16px;
            `;
            p.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;
                            border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:10px;">
                    <span style="font-weight:700;color:#58a6ff;">${hdr}</span>
                    ${badgeHtml}
                </div>
                <div id="${pId}-body" style="line-height:1.6;">${bodyHtml}</div>
            `;
            document.body.appendChild(p);
        }
    """, [panel_id, width, header, badge_html, lines_html])


async def run_demo():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        # FIX 5: Viewport 1280x720
        context = await browser.new_context(
            record_video_dir="demo/",
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        # FIX 7: Sequence must be EXACTLY: goto -> add_style_tag -> title_card (zero sleep between goto and add_style_tag)
        await page.goto("http://localhost:8501", wait_until="networkidle")
        await page.add_style_tag(content=HIDE_STREAMLIT_CSS)

        # ── ACT 0: Opening title card (0s – 8s, 8s) ───────────────
        await title_card(page,
            "Sovereign Supply Chain AI",
            "One voice command. 4 Meta Llama models. Zero stockouts.",
            "Watch $12,200 get saved in 3 minutes.",
            duration=8
        )

        # ── ACT 1: Voice Command (8s – 28s) ───────────────────────
        # Title card 4s (8s - 12s)
        await title_card(page,
            "Step 1 of 5 — Voice Command",
            "A warehouse manager speaks one sentence.",
            "muse-voice-transcribe-1.0 hears it. AI takes over.",
            duration=4
        )

        # Inject left panel once (persists for all demo)
        await inject_left_panel(page, [
            "[12:03:01] muse-voice-transcribe-1.0 → LISTENING",
            "[12:03:04] Voice captured: 1 utterance, 14 tokens"
        ])

        # Inject right panel (Voice Input, width=540)
        # State 1 (2s): Waveform animation
        wave_style = """
            <style>
                @keyframes wave {
                    from { height: 4px; }
                    to { height: 24px; }
                }
                .wave-bar {
                    display: inline-block;
                    width: 6px;
                    margin: 0 2px;
                    background: #58a6ff;
                    border-radius: 2px;
                    animation: wave 0.6s ease-in-out infinite alternate;
                }
            </style>
        """
        bars_html = "".join([f'<span class="wave-bar" style="animation-delay: {i*80}ms;"></span>' for i in range(12)])
        initial_voice_content = [
            wave_style,
            "<span style='color:#58a6ff;font-style:italic;'>▶ Capturing voice input...</span>",
            "<div style='height:40px;display:flex;align-items:center;margin:12px 0;'>" + bars_html + "</div>"
        ]
        await inject_panel(page,
            "🎙 Voice Input",
            "muse-voice-transcribe-1.0",
            initial_voice_content,
            width=540
        )

        # FIX 1: Ripple on mic emoji at (730, 190) fires at same moment waveform starts
        await ripple_click(page, 730, 190)
        await asyncio.sleep(2)

        # State 2 (6s): Replace waveform content via JS innerHTML with transcribed text
        await page.evaluate("""
            () => {
                const body = document.getElementById('demo-panel-body');
                if (body) {
                    body.innerHTML = `
                        <div style="margin:4px 0;color:#58a6ff;font-style:italic;">▶ Transcribing audio stream...</div>
                        <div style="margin:12px 0;"></div>
                        <div style="margin:4px 0;color:#c9d1d9;">"Emergency — Widget-A is running out.</div>
                        <div style="margin:4px 0;color:#c9d1d9;">Get me the best price now."</div>
                    `;
                }
            }
        """)
        await asyncio.sleep(6)
        await bottom_bar(page, "Voice received by muse-voice-transcribe-1.0 — AI activates instantly.", duration=8)

        # ── ACT 2: Warehouse Vision (28s – 51s) ────────────────────
        # Title card 4s (28s - 32s)
        await title_card(page,
            "Step 2 of 5 — Warehouse Vision",
            "AI scans physical shelf using computer vision.",
            "sam-3.1 confirms: Widget-A is 12% — CRITICAL",
            duration=4
        )

        # Append to left panel
        await append_left_panel(page, [
            "[12:03:08] sam-3.1 → SCANNING Aisle 4, Shelf 3",
            "[12:03:09] Visual bbox detected: Widget-A stock 12%"
        ])

        # Inject right panel (Shelf Scan, width=540)
        await inject_panel(page,
            "📦 Shelf Scan",
            "sam-3.1",
            [
                "<div style='background:#0d1117;padding:6px;border-radius:4px;text-align:center;color:#8b949e;margin-bottom:8px;'>[ Warehouse Aisle 4 — Shelf Cam ]</div>",
                "<div style='margin:8px 0;'><span style='color:#f85149;'>■</span> <b>Widget-A</b> <span style='color:#f85149;'>████░░░░░░ 12% — CRITICAL</span></div>",
                "<div style='margin:8px 0;'><span style='color:#e3b341;'>■</span> <b>Widget-B</b> <span style='color:#e3b341;'>█████░░░░░ 58% — OK</span></div>",
                "<div style='margin:8px 0;'><span style='color:#3fb950;'>■</span> <b>Widget-C</b> <span style='color:#3fb950;'>████████░░ 82% — OK</span></div>",
            ],
            width=540
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "Humans hadn't checked yet. sam-3.1 caught it at 12%.", duration=13)

        # ── ACT 3: Demand Forecast (51s – 73s) ────────────────────
        # Title card 4s (51s - 55s)
        await title_card(page,
            "Step 3 of 5 — Demand Forecast",
            "muse-spark-1.3 predicts: stockout in 14 days.",
            "Cost of inaction: $8,000 in emergency fees.",
            duration=4
        )

        # Append to left panel
        await append_left_panel(page, [
            "[12:03:10] muse-spark-1.3 → ANALYZING demand",
            "[12:03:11] Burn rate: 35.7 u/day; delta: 500"
        ])

        # Inject right panel (Demand Forecast, width=540)
        await inject_panel(page,
            "📊 Demand Forecast",
            "muse-spark-1.3",
            [
                "Widget-A: stockout in <span style='color:#e3b341;font-weight:700;'>14 days</span> ⚠ HIGH",
                "",
                "Recommended reorder: <b>500 units</b> by Nov 17",
                "Cost of inaction: <span style='color:#f85149;font-weight:700;'>$8,000</span> emergency fees",
                "<div style='border-top:1px solid #30363d;margin:10px 0;'></div>",
                "<span style='color:#3fb950;'>✓ Forecast locked. Initiating negotiation.</span>"
            ],
            width=540
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "$8,000 saved if we act now. AI agents negotiating.", duration=12)

        # ── ACT 4: Agent Negotiation (73s – 109s) ─────────────────
        # Title card 4s (73s - 77s)
        await title_card(page,
            "Step 4 of 5 — Agent Negotiation",
            "Two AI agents negotiate price. No human involved.",
            "muse-spark-1.3 × muse-spark-1.3",
            duration=4
        )

        # Inject A2A panel (FIX 4: width=540, no 520px exception)
        await page.evaluate("""
            document.getElementById('demo-panel')?.remove();
            const p = document.createElement('div');
            p.id = 'demo-panel';
            p.style.cssText = `
                position:fixed; top:140px; right:30px; z-index:9997;
                width:540px; height:420px; box-sizing:border-box; overflow:hidden;
                background:#161b22; border:1px solid #30363d; border-radius:8px;
                font-family:monospace; font-size:0.82rem; color:#c9d1d9;
                padding:14px 16px;
            `;
            p.innerHTML = `
                <div style="display:flex;justify-content:space-between;border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:10px;">
                    <div><span style="color:#58a6ff;font-weight:700;">🤖 BUYER AGENT</span> <span style="color:#8b949e;font-size:0.75rem;">🦙 muse-spark-1.3</span></div>
                    <div style="text-align:right"><span style="color:#f85149;font-weight:700;">🏭 SUPPLIER B</span> <span style="color:#8b949e;font-size:0.75rem;">🦙 muse-spark-1.3</span></div>
                </div>
                <div id="a2a-body" style="line-height:1.9;min-height:120px;"></div>
            `;
            document.body.appendChild(p);
        """)

        # Exchanges in sync between left panel and A2A panel
        a2a_exchanges = [
            (
                "[12:03:12] A2A Buyer Agent dispatching RFQ",
                "→ RFQ: 500 units Widget-A, Nov 17"
            ),
            (
                "[12:03:16] Supplier B Agent returned initial quote",
                "← Quote: $8.40/unit | Total: $4,200"
            ),
            (
                "[12:03:20] Buyer counter-proposal submitted",
                "→ Counter: $8.20/unit, NET-15?"
            ),
            (
                "[12:03:24] Supplier B accepted $8.20 NET-15",
                "← <span style='color:#3fb950;'>Accepted: $8.20/unit, NET-15 conf ✓</span><br><b>✅ Deal locked. Saving $100 vs opening offer.</b>"
            )
        ]

        for left_line, right_html in a2a_exchanges:
            await append_left_panel(page, [left_line])
            await page.evaluate("(l) => { document.getElementById('a2a-body').innerHTML += '<div style=\"margin:4px 0;\">' + l + '</div>'; }", right_html)
            await asyncio.sleep(4.0)

        await asyncio.sleep(4)  # after last line
        await bottom_bar(page, "Negotiated by AI. No human needed until final approval.", duration=8)

        # ── ACT 5: Human Approval (109s – 128s) ───────────────────
        # Title card 4s (109s - 113s)
        await title_card(page,
            "Step 5 of 5 — Human Approval",
            "AI processes invoice. Human makes final call.",
            "muse-image-1.0 reads the document.",
            duration=4
        )

        # Append to left panel
        await append_left_panel(page, [
            "[12:03:26] muse-image-1.0 → READING invoice 0099",
            "[12:03:28] OCR extraction verified 100% matched",
            "[12:03:29] HITL checkpoint → Awaiting human approval"
        ])

        # Inject right panel (Invoice, width=540)
        # Pre-flip: Both [✓ APPROVE] (#btn-approve) and [✗ REJECT] buttons are visible
        await inject_panel(page,
            "🧾 Invoice Processed",
            "muse-image-1.0",
            [
                "Supplier: <b>Supplier B Inc.</b>",
                "PO #: <b>PO-2024-0099</b>",
                "Item: Widget-A × 500 units @ $8.20",
                "Total: <b>$4,100.00</b> | Due: NET-15",
                "<div style='border-top:1px solid #30363d;margin:10px 0;'></div>",
                "<span style='background:#e3b341;color:#0d1117;padding:2px 8px;border-radius:3px;font-weight:700;'>⚠ Human Review Required</span>",
                "<div style='margin-top:8px;color:#8b949e;'>PO-2024-0099 | $4,100 | Supplier B</div>",
                "<div id='hitl-btns' style='display:flex;gap:10px;margin-top:10px;'>",
                "  <span id='btn-approve' style='background:#238636;color:#fff;padding:4px 16px;border-radius:4px;cursor:pointer;font-weight:700;'>✓ APPROVE</span>",
                "  <span style='background:#da3633;color:#fff;padding:4px 16px;border-radius:4px;cursor:pointer;'>✗ REJECT</span>",
                "</div>"
            ],
            width=540
        )
        await asyncio.sleep(5)

        # Ripple on APPROVE using getBoundingClientRect
        btn_coords = await page.evaluate("""
            () => {
                const btn = document.getElementById('btn-approve');
                if (!btn) return {x:870, y:400};
                const r = btn.getBoundingClientRect();
                return {x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};
            }
        """)
        await ripple_click(page, btn_coords['x'], btn_coords['y'])

        # Flip to APPROVED — target by ID not by style selector
        await page.evaluate("""
            () => {
                const d = document.getElementById('hitl-btns');
                if (d) d.innerHTML = '<span style="background:#238636;color:#fff;padding:4px 16px;border-radius:4px;font-weight:700;">✓ APPROVED</span>';
            }
        """)

        await append_left_panel(page, [
            "[12:03:34] Human APPROVE action confirmed"
        ])
        await asyncio.sleep(2)  # pause on APPROVED state
        await bottom_bar(page, "Human makes the call. PO executed. AI handles the rest.", duration=8)

        # ── ACT 6: Results (128s – 143s) ──────────────────────────
        # Title card 4s (128s - 132s)
        await title_card(page,
            "Results — Week 1",
            "$12,200 saved. 14 hours automated. Zero stockouts.",
            duration=4
        )

        # Append to left panel and update status to ● COMPLETED
        await append_left_panel(page, [
            "[12:03:35] ERP webhook dispatched: PO-2024-0099",
            "[12:03:36] ✅ All agents complete. Audit log saved"
        ], update_status="● COMPLETED")

        # Inject right panel (Results, width=540)
        await inject_panel(page,
            "🏆 Q4 Initiative — Week 1 Results",
            "",
            [
                "<div style='color:#8b949e;margin-bottom:8px;font-size:0.75rem;'>Sovereign Supply Chain AI</div>",
                "<div style='font-size:1.15rem;font-weight:700;color:#3fb950;margin:6px 0;'>💰 Total savings: $12,200</div>",
                "<div style='margin:4px 0;'>🚫 Stockouts prevented: <b>1</b></div>",
                "<div style='margin:4px 0;'>💼 Supplier savings: <b>$4,200</b></div>",
                "<div style='margin:4px 0;'>⏱ Hours automated: <b>14 hrs</b></div>",
                "<div style='margin:4px 0;'>📈 On track for <b>$50,000 Q4 target</b></div>",
                "<div style='border-top:1px solid #30363d;margin:10px 0;'></div>",
                "<div style='color:#58a6ff;font-weight:700;'>4 Meta Llama models. 1 voice command.</div>"
            ],
            width=540
        )
        await asyncio.sleep(6)
        await bottom_bar(page, "One voice command. $12,200 saved. Fully auditable.", duration=5)

        # ── ACT 7: Closing title card (143s – 155s / 12s duration) ─
        # Full screen #0d1117: Line 1, Line 2, Line 3
        await title_card(page,
            "Sovereign Supply Chain AI",
            "muse-spark-1.3 · muse-voice-transcribe-1.0 · muse-image-1.0 · sam-3.1",
            "github.com/parth33320/sovereign-supply-chain-meta",
            duration=12
        )

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_demo())
