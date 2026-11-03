"""
Automated Demo Video Production - Narration and Video Assembly
=============================================================
Generates TTS audio clips for narration timestamps using gTTS,
merges audio and video using MoviePy into demo/demo_final.mp4.
"""

import os
from pathlib import Path
from gtts import gTTS

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
RAW_VIDEO_PATH = DEMO_DIR / "raw_recording.webm"
FINAL_VIDEO_PATH = DEMO_DIR / "demo_final.mp4"
AUDIO_OUTPUT_DIR = DEMO_DIR / "audio_tracks"

# NARRATION script with timestamps and text
# Timestamps: 0:00, 0:08, 0:28, 0:55, 1:20, 2:00, 2:15, 2:30, 2:45
NARRATION = [
    (0.0, "What if one voice command could save your company twelve thousand dollars?"),
    (8.0, "Watch. A supply chain manager speaks — and four Meta Llama models go to work."),
    (28.0, "The AI scans the warehouse shelf. Widget-A is at twelve percent. That's a crisis in fourteen days."),
    (55.0, "Meta's forecasting model confirms it. Without action: eight thousand dollars in emergency orders. The AI flags it now."),
    (80.0, "Here's where it gets interesting. Two AI agents negotiate a purchase order. Buyer agent sends the quote request. Supplier agent responds. They go back and forth — and close the deal for a hundred dollars less than the opening offer."),
    (120.0, "The invoice is scanned automatically. All the data extracted in two seconds. Then the AI stops and waits for a human to approve."),
    (135.0, "Because AI should do the work. Humans should make the call."),
    (150.0, "Final result: twelve thousand two hundred dollars saved. One stockout prevented. Fourteen hours of manual work, gone."),
    (165.0, "Built on Meta Llama. Open source. Deployable today.")
]


def generate_audio_tracks():
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_meta = []
    for idx, (timestamp, text) in enumerate(NARRATION):
        mp3_path = AUDIO_OUTPUT_DIR / f"track_{idx}.mp3"
        print(f"Generating TTS [{timestamp}s]: '{text}'")
        tts = gTTS(text=text, lang="en", tld="com", slow=False)
        tts.save(str(mp3_path))
        audio_meta.append({"start_sec": timestamp, "audio_path": str(mp3_path)})
    return audio_meta


def assemble_final_video(video_path: Path, audio_meta, output_path: Path):
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

    print(f"Loading raw video from {video_path}...")
    video_clip = VideoFileClip(str(video_path))
    video_duration = video_clip.duration
    print(f"Raw video duration: {video_duration:.2f} seconds")

    audio_clips = []
    for item in audio_meta:
        start_time = item["start_sec"]
        if start_time < video_duration:
            a_clip = AudioFileClip(item["audio_path"])
            if hasattr(a_clip, "with_start"):
                a_clip = a_clip.with_start(start_time)
            elif hasattr(a_clip, "set_start"):
                a_clip = a_clip.set_start(start_time)
            audio_clips.append(a_clip)

    composite_audio = CompositeAudioClip(audio_clips)
    if hasattr(composite_audio, "with_duration"):
        composite_audio = composite_audio.with_duration(video_duration)
    elif hasattr(composite_audio, "set_duration"):
        composite_audio = composite_audio.set_duration(video_duration)

    if hasattr(video_clip, "with_audio"):
        final_video = video_clip.with_audio(composite_audio)
    else:
        final_video = video_clip.set_audio(composite_audio)

    print(f"Rendering {output_path} (H.264 + AAC)...")
    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=24,
        bitrate="2000k",
        logger="bar"
    )

    for a in audio_clips:
        a.close()
    composite_audio.close()
    video_clip.close()
    final_video.close()
    print(f"Render complete: {output_path}")


def main():
    if not RAW_VIDEO_PATH.exists():
        raise FileNotFoundError(f"Raw video recording not found at {RAW_VIDEO_PATH}")

    audio_meta = generate_audio_tracks()
    assemble_final_video(RAW_VIDEO_PATH, audio_meta, FINAL_VIDEO_PATH)


if __name__ == "__main__":
    main()
