import os, pytest
from demo.narrate_demo import NARRATION

def test_video_exists_and_large():
    assert os.path.exists("demo/demo_final.mp4")
    assert os.path.getsize("demo/demo_final.mp4") > 5_000_000

def test_video_duration():
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        from moviepy import VideoFileClip
    clip = VideoFileClip("demo/demo_final.mp4")
    assert clip.duration >= 150
    clip.close()

def test_narration_has_seven_entries():
    assert len(NARRATION) >= 7

def test_narration_first_line_has_dollar():
    assert "$" in NARRATION[0][1]

def test_run_demo_sh_exists():
    assert os.path.exists("demo/run_demo.sh")
