import os
import glob
from pathlib import Path
from gtts import gTTS
import moviepy
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

NARRATION = [
    (0,   "What if one voice command could save your company $12,000 — today?"),
    (8,   "A warehouse manager says: Emergency. Widget-A is running out. Get me the best price now."),
    (30,  "muse-voice-transcribe-1.0 captures the command. No keyboard. No ticket. AI activates instantly."),
    (47,  "sam-3.1 scans the warehouse shelf. Widget-A is at twelve percent. Critical. Humans hadn't checked yet."),
    (70,  "muse-spark-1.3 forecasts a stockout in fourteen days. Cost of inaction: eight thousand dollars."),
    (93,  "Two AI agents negotiate. Buyer agent versus Supplier agent. muse-spark-1.3 runs both sides. Deal locked: eight dollars twenty per unit."),
    (133, "muse-image-1.0 reads the invoice. AI prepares the purchase order. One human clicks Approve."),
    (157, "Result: twelve thousand two hundred dollars saved in week one. Fourteen hours of procurement work automated."),
    (170, "Four Meta Llama models. One voice command. Zero stockouts. Sovereign Supply Chain AI."),
]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
AUDIO_OUTPUT_DIR = DEMO_DIR / "audio_tracks"
FINAL_VIDEO_PATH = DEMO_DIR / "demo_final.mp4"


def find_recorded_video() -> Path:
    """Finds the webm video recorded by Playwright in demo/."""
    candidates = sorted(
        list(DEMO_DIR.glob("*.webm")) + list(DEMO_DIR.glob("**/*.webm")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not candidates:
        raise FileNotFoundError("No .webm video file found in demo/")
    return candidates[0]


def generate_audio_tracks():
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_clips_meta = []
    for idx, (timestamp, text) in enumerate(NARRATION):
        audio_file = AUDIO_OUTPUT_DIR / f"narrate_{idx}.mp3"
        print(f"Generating TTS for {timestamp}s: '{text[:40]}...'")
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(str(audio_file))
        audio_clips_meta.append((timestamp, str(audio_file)))
    return audio_clips_meta


def assemble_final_video():
    raw_video_path = find_recorded_video()
    print(f"Using raw video from: {raw_video_path}")
    video_clip = VideoFileClip(str(raw_video_path))
    video_duration = video_clip.duration
    print(f"Raw video duration: {video_duration}s")

    audio_meta = generate_audio_tracks()
    audio_clips = []
    for timestamp, audio_file in audio_meta:
        a_clip = AudioFileClip(audio_file)
        if hasattr(a_clip, "with_start"):
            a_clip = a_clip.with_start(timestamp)
        elif hasattr(a_clip, "set_start"):
            a_clip = a_clip.set_start(timestamp)
        audio_clips.append(a_clip)

    print("Compositing audio tracks...")
    composite_audio = CompositeAudioClip(audio_clips)
    if hasattr(composite_audio, "with_duration"):
        composite_audio = composite_audio.with_duration(video_duration)
    elif hasattr(composite_audio, "set_duration"):
        composite_audio = composite_audio.set_duration(video_duration)

    if hasattr(video_clip, "with_audio"):
        final_video = video_clip.with_audio(composite_audio)
    else:
        final_video = video_clip.set_audio(composite_audio)

    print(f"Writing final video to {FINAL_VIDEO_PATH}...")
    final_video.write_videofile(
        str(FINAL_VIDEO_PATH),
        codec="libx264",
        audio_codec="aac",
        bitrate="2500k",
        fps=24,
        logger="bar"
    )

    for clip in audio_clips:
        clip.close()
    composite_audio.close()
    video_clip.close()
    final_video.close()
    print("Narration and assembly complete!")


if __name__ == "__main__":
    assemble_final_video()
