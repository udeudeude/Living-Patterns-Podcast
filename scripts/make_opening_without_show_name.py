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
    # In this mix the first two spoken blocks are the programme name
    # and the episode title, with a deliberate 1.25-second pause between.
    # Detect the speech envelope rather than relying on a speech recognizer
    # that ignored both short title phrases in the first attempt.
    voice_band = Path(tmp) / "voice-band.wav"
    ffmpeg(
        "-i", str(wav),
        "-af", "highpass=f=180,lowpass=f=1800",
        "-ar", "16000", "-ac", "1", voice_band,
    )
    filtered, rate = sf.read(voice_band, dtype="float32")
    samples_per_frame = 320  # 20 milliseconds
    count = len(filtered) // samples_per_frame
    frames = filtered[:count * samples_per_frame].reshape(count, samples_per_frame)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    # Smooth the envelope to avoid mistaking syllabic gaps for silence.
    smooth = np.convolve(rms, np.ones(7) / 7, mode="same")
    floor = float(np.median(smooth[:110])) # first 2.2s: just ambience
    threshold = max(0.012, floor * 3.2)
    speech = smooth > threshold

    # Merge pauses under .24 seconds, but not the intentional title pause.
    groups = []
    active = np.flatnonzero(speech)
    if len(active):
        a = int(active[0])
        b = a
        for i in active[1:]:
            i = int(i)
            if i - b <= 12:
                b = i
            else:
                if b - a >= 12:
                    groups.append((a * .02, (b + 1) * .02))
                a = b = i
        if b - a >= 12:
            groups.append((a * .02, (b + 1) * .02))
    print(f"Speech bands: floor={floor:.4f} threshold={threshold:.4f} groups={groups}", flush=True)

    # The first word of the episode title is expected after the title
    # announcement and before the reflection proper.
    candidates = [
        a for a, b in groups
        if 5.0 <= a <= 10.0 and b - a >= 0.35
    ]
    if not candidates:
        raise RuntimeError(f"Could not isolate episode-title onset: {groups}")
    # The title itself can have several speech bands separated by a
    # brief pause. The FIRST band after the long programme-name pause
    # is the beginning of the episode title, not an ambiguity.
    onset = min(candidates)
    preceding = [b for a, b in groups if 2.5 < a < 5.0]
    if len(preceding) != 1 or onset - preceding[0] < 0.85:
        raise RuntimeError(f"Missing clear gap after spoken programme name: {groups}")
    # Retain a short lead-in of ambience ahead of the first syllable.
    cut = onset - 0.17

    ffmpeg(
        "-ss", f"{cut:.3f}", "-i", str(SOURCE),
        "-t", "53",
        "-af", "afade=t=in:st=0:d=0.08",
        "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "96k",
        str(OUT),
    )
    if OUT.stat().st_size < 150000:
        raise RuntimeError(f"Sample too small: {OUT.stat().st_size}")
    print(f"Edited starting at {cut:.3f}s; episode-title voice onset {onset:.3f}s", flush=True)

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
