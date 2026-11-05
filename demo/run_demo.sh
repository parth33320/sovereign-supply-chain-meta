#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== PHASE 1: Recording ==="
DEMO_MODE=1 streamlit run app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
sleep 8

python demo/record_demo.py

WEBM=$(ls -t demo/*.webm 2>/dev/null | head -1)
if [ -z "$WEBM" ]; then
    echo "ERROR: no .webm found"
    kill $STREAMLIT_PID
    exit 1
fi

ffmpeg -y -i "$WEBM" -vf "fps=5,scale=800:-1" -t 50 demo/preview.gif

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║ CHECKPOINT — REVIEW preview.gif NOW          ║"
echo "║ Kill this script if video looks wrong.       ║"
echo "║ Waiting 10 seconds then starting Phase 2.    ║"
echo "╚══════════════════════════════════════════════╝"
sleep 10

echo "=== PHASE 2: Narration ==="
python demo/narrate_demo.py

kill $STREAMLIT_PID 2>/dev/null || true
echo "Done. Output: demo/demo_final.mp4"
