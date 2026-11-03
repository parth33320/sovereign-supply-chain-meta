import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
FINAL_VIDEO_PATH = DEMO_DIR / "demo_final.mp4"
RUN_DEMO_SH_PATH = DEMO_DIR / "run_demo.sh"


def test_video_duration():
    """Open demo/demo_final.mp4 with moviepy VideoFileClip. Assert duration >= 150 seconds."""
    assert FINAL_VIDEO_PATH.exists(), f"{FINAL_VIDEO_PATH} does not exist"
    from moviepy import VideoFileClip

    clip = VideoFileClip(str(FINAL_VIDEO_PATH))
    try:
        assert clip.duration >= 150.0, f"Expected duration >= 150s, got {clip.duration}s"
    finally:
        clip.close()


def test_video_exists_and_large():
    """Assert os.path.getsize('demo/demo_final.mp4') > 5_000_000 (5MB)."""
    assert FINAL_VIDEO_PATH.exists(), f"{FINAL_VIDEO_PATH} does not exist"
    size = os.path.getsize(str(FINAL_VIDEO_PATH))
    assert size > 5_000_000, f"Expected size > 5,000,000 bytes, got {size} bytes"


def test_narration_script_has_seven_lines():
    """Count lines in NARRATION list in narrate_demo.py. Assert len >= 7."""
    import demo.narrate_demo as narrate_module

    assert hasattr(narrate_module, "NARRATION"), "narrate_demo.py does not define NARRATION"
    assert isinstance(narrate_module.NARRATION, list), "NARRATION must be a list"
    assert len(narrate_module.NARRATION) >= 7, f"Expected len(NARRATION) >= 7, got {len(narrate_module.NARRATION)}"


def test_run_demo_sh_exists():
    """Assert os.path.exists('demo/run_demo.sh')."""
    assert os.path.exists(str(RUN_DEMO_SH_PATH)), f"{RUN_DEMO_SH_PATH} does not exist"
