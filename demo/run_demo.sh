#!/usr/bin/env bash
set -e

# Kill any existing streamlit server on port 8501
fuser -k 8501/tcp 2>/dev/null || true
pkill -f "streamlit run" 2>/dev/null || true

# Start Streamlit in background with DEMO_MODE=1
echo "Starting Streamlit on port 8501 in DEMO_MODE=1..."
DEMO_MODE=1 streamlit run app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!

cleanup() {
    echo "Stopping Streamlit server (PID: $STREAMLIT_PID)..."
    kill $STREAMLIT_PID 2>/dev/null || true
    fuser -k 8501/tcp 2>/dev/null || true
}
trap cleanup EXIT

# Wait for server ready
echo "Waiting for Streamlit server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8501/_stcore/health >/dev/null 2>&1 || curl -s http://localhost:8501 >/dev/null 2>&1; then
        echo "Streamlit is ready!"
        break
    fi
    sleep 1
done

# Run Playwright screen recording
echo "Recording demo walkthrough..."
python demo/record_demo.py

# Run narration generation and video assembly
echo "Narrating and assembling final video..."
python demo/narrate_demo.py

echo "Demo generation complete: demo/demo_final.mp4"
