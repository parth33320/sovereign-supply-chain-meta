"""
Automated Demo Video Production - Narration and Video Assembly (S14)
===================================================================
1. Reads narration script matching video timestamps from demo/timestamps.json.
2. Uses gTTS to generate MP3 narration audio clips.
3. Uses MoviePy to composite audio clips at timestamps and merge with raw_recording.webm
   into demo/demo_final.mp4 (H.264 video + AAC audio).
"""

import json
import os
import sys
from pathlib import Path
from gtts import gTTS

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
RAW_VIDEO_PATH = DEMO_DIR / "raw_recording.webm"
TIMESTAMPS_PATH = DEMO_DIR / "timestamps.json"
FINAL_VIDEO_PATH = DEMO_DIR / "demo_final.mp4"
AUDIO_OUTPUT_DIR = DEMO_DIR / "audio_tracks"

# Narration scripts designed to fit within the timestamp durations of each phase
NARRATION_SCRIPTS = {
    1: "First, we submit a logistics command to the multi-agent orchestrator, generating a rebalancing plan.",
    2: "Next, we trigger a chaos load test with 1,000 edge cases, verifying resilience and automatic recovery.",
    3: "Now, uploading a warehouse shelf image triggers SAM computer vision for automated inventory segmentation.",
    4: "Here, our Buyer and Supplier agents execute an autonomous A2A negotiation and draft a purchase order.",
    5: "The human-in-the-loop governance checkpoint allows instant review and formal plan execution.",
    6: "Finally, zero-trust semantic guardrails intercept and neutralize a prompt injection attack."
}


def generate_narration_audio_clips(phases_info):
    """
    Generates MP3 audio files using gTTS for each phase.
    Returns list of dicts with phase, audio_path, start_sec, end_sec.
    """
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_clips_meta = []

    for phase_data in phases_info:
        phase_num = phase_data["phase"]
        start_sec = phase_data["start_sec"]
        end_sec = phase_data["end_sec"]
        text = NARRATION_SCRIPTS.get(phase_num, f"Executing demonstration step {phase_num}.")

        mp3_path = AUDIO_OUTPUT_DIR / f"phase_{phase_num}.mp3"
        print(f"Generating TTS for Phase {phase_num}: '{text}'...")
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(str(mp3_path))

        audio_clips_meta.append({
            "phase": phase_num,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "audio_path": str(mp3_path)
        })

    return audio_clips_meta


def assemble_video(video_path: Path, audio_clips_meta, output_path: Path):
    """
    Composites the audio tracks onto the video at their corresponding timestamps
    using MoviePy and exports the final MP4.
    """
    # MoviePy 2.x imports
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

    print(f"Loading video from {video_path}...")
    video_clip = VideoFileClip(str(video_path))
    video_duration = video_clip.duration

    audio_clips = []
    for meta in audio_clips_meta:
        audio_file = meta["audio_path"]
        start_time = meta["start_sec"]
        a_clip = AudioFileClip(audio_file)

        # Set audio clip start time in the composition
        # In moviepy 2.x, with_start or start handles timing
        if hasattr(a_clip, "with_start"):
            a_clip = a_clip.with_start(start_time)
        elif hasattr(a_clip, "set_start"):
            a_clip = a_clip.set_start(start_time)
        audio_clips.append(a_clip)

    print("Compositing audio track onto video...")
    composite_audio = CompositeAudioClip(audio_clips)
    if hasattr(composite_audio, "with_duration"):
        composite_audio = composite_audio.with_duration(video_duration)
    elif hasattr(composite_audio, "set_duration"):
        composite_audio = composite_audio.set_duration(video_duration)

    if hasattr(video_clip, "with_audio"):
        final_video = video_clip.with_audio(composite_audio)
    else:
        final_video = video_clip.set_audio(composite_audio)

    print(f"Writing output video to {output_path}...")
    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=24,
        logger="bar"
    )

    # Close clips
    for a in audio_clips:
        a.close()
    composite_audio.close()
    video_clip.close()
    final_video.close()
    print(f"Video assembly complete! Saved to {output_path}")


def main():
    if not TIMESTAMPS_PATH.exists():
        raise FileNotFoundError(f"Timestamps file not found at {TIMESTAMPS_PATH}. Run demo/record_demo.py first.")

    if not RAW_VIDEO_PATH.exists():
        raise FileNotFoundError(f"Raw video recording not found at {RAW_VIDEO_PATH}. Run demo/record_demo.py first.")

    with open(TIMESTAMPS_PATH, "r") as f:
        timestamps_data = json.load(f)

    phases_info = timestamps_data.get("phases", [])
    if not phases_info:
        raise ValueError("No phases found in timestamps.json")

    print(f"Found {len(phases_info)} phases in {TIMESTAMPS_PATH}")
    audio_clips_meta = generate_narration_audio_clips(phases_info)
    assemble_video(RAW_VIDEO_PATH, audio_clips_meta, FINAL_VIDEO_PATH)


if __name__ == "__main__":
    main()
