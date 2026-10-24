#!/usr/bin/env python3
"""Make a short unlisted episode opening with only the show-name phrase omitted.

This edits existing episode audio, preserves the established narrator and
original title/words, and leaves the public podcast feed untouched.
"""
from pathlib import Path
import html
import json
import re
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "2026-08-18-begin-with-the-place-that-already-works-remastered.mp3"
DEST = ROOT / "auditions" / "without-show-name"
DEST.mkdir(parents=True, exist_ok=True)
OUT = DEST / "episode-1-opening.mp3"

def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        check=True,
    )

with tempfile.TemporaryDirectory() as tmp:
    wav = Path(tmp) / "beginning.wav"
    ffmpeg(
        "-i", str(SOURCE),
        "-t", "27",
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le", str(wav),
    )
    audio, sample_rate = sf.read(wav, dtype="float32")
    if sample_rate != 16000 or audio.ndim != 1:
        raise RuntimeError("Unexpected input format")
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        np.asarray(audio, dtype=np.float32),
        beam_size=5,
        language="en",
        word_timestamps=True,
        vad_filter=False,
        initial_prompt=(
            "Living Patterns. Begin with the place that already works. "
            "We often think improvement begins with a plan."
        ),
    )
    words = []
    for segment in segments:
        for word in segment.words or []:
            token = re.sub("[^a-z]+", "", word.word.lower())
            if token:
                words.append((token, round(float(word.start), 3), round(float(word.end), 3)))
    print("Recognized opening words:", words[:36], flush=True)

    # Anchor the edit to the actual start of the episode title, rather than
    # guessing the duration of the show-name announcement.
    candidates = []
    for i, (token, start, _) in enumerate(words[:-1]):
        if token == "begin" and words[i + 1][0] == "with":
            candidates.append(start)
    if len(candidates) != 1:
        raise RuntimeError(f"Could not uniquely locate opening of episode title: {words}")

    title_onset = candidates[0]
    if not 2.0 < title_onset < 16.0:
        raise RuntimeError(f"Title start is outside expected range: {title_onset}")

    # Include 150ms of the silent/ambience margin before the title so the
    # beginning is not clipped; retain the original narrator and ambience.
    cut = max(0.0, title_onset - 0.15)
    ffmpeg(
        "-ss", f"{cut:.3f}", "-i", str(SOURCE),
        "-t", "53",
        "-af", "afade=t=in:st=0:d=0.08",
        "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "96k",
        str(OUT),
    )
    if OUT.stat().st_size < 150000:
        raise RuntimeError(f"Sample too small: {OUT.stat().st_size}")

    # Verify the output opens with the intended episode title, not the show name.
    check_file = Path(tmp) / "check.wav"
    ffmpeg("-i", str(OUT), "-t", "12", "-ar", "16000", "-ac", "1", str(check_file))
    checked, _ = sf.read(check_file, dtype="float32")
    segments, _ = model.transcribe(
        np.asarray(checked, dtype=np.float32),
        language="en",
        beam_size=5,
        initial_prompt="Begin with the place that already works.",
    )
    recognized = " ".join(s.text.strip() for s in segments).lower()
    print(f"Cut at {cut:.3f}s (title onset {title_onset:.3f}s). Verified sample: {recognized}", flush=True)
    if "begin" not in recognized or "place" not in recognized:
        raise RuntimeError(f"Wrong narration at cut: {recognized}")
    if recognized.strip().startswith("living patterns"):
        raise RuntimeError("Show-name introduction was not removed")

page = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Living Patterns · Opening without show-name announcement</title>
<style>
*{box-sizing:border-box}body{background:#f4eddd;color:#142b3d;margin:0;font-family:Arial,sans-serif}
main{max-width:770px;margin:0 auto;padding:40px clamp(20px,5vw,65px) 80px}
h1{font:normal clamp(2.3rem,6vw,4rem)/1.1 Georgia,serif;margin:12px 0}
p{line-height:1.6}.eyebrow{font-size:.75rem;text-transform:uppercase;color:#b85c35;letter-spacing:.15em;font-weight:700}
.card{background:#fffaf0;border:1px solid #142b3d33;padding:26px;margin-top:30px}
audio{display:block;width:100%;margin:20px 0}
</style></head><body><main>
<p class="eyebrow">Unlisted demonstration · Episode 1</p>
<h1>Begin with the place that already works</h1>
<p>This is the existing episode recording, but with the spoken
“Living Patterns” introduction removed. It opens with the episode
title, followed by the same narration, pacing and ambience.
No narrator or voice settings have been changed.</p>
<div class="card">
<audio controls preload="metadata" src="episode-1-opening.mp3"></audio>
<p>Listen to the first 53 seconds, beginning with the episode title.</p>
</div>
<p>For comparison: <a href="../../2026-08-18-begin-with-the-place-that-already-works-remastered.mp3">original episode, with spoken show-name introduction</a>.</p>
<p>Neither the published episode nor the podcast feed has been changed.</p>
</main></body></html>
"""
(DEST / "index.html").write_text(page, encoding="utf-8")
print(f"Generated {OUT}, {OUT.stat().st_size} bytes, and listening page.", flush=True)
