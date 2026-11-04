#!/bin/bash
set -e
DEMO_MODE=1 streamlit run app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!
sleep 6
python demo/record_demo.py
python demo/narrate_demo.py
kill $STREAMLIT_PID 2>/dev/null || true
echo "Done. Output: demo/demo_final.mp4"
