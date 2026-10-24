#!/usr/bin/env python3
"""Create pitch-contour auditions using ONLY the approved Living Patterns narrator.

No text-to-speech resynthesis, wording change, or voice change occurs here.
All new samples originate from the same approved "Living Patterns." take.
"""
from pathlib import Path
import html
import math
import subprocess
import tempfile

import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "auditions" / "a-current-title.mp3"
DEST = ROOT / "auditions" / "inflection"
DEST.mkdir(parents=True, exist_ok=True)

if not SOURCE.is_file():
    raise SystemExit(f"Missing baseline voice sample: {SOURCE}")

def run_ffmpeg(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)

with tempfile.TemporaryDirectory() as td:
    directory = Path(td)
    wav = directory / "source.wav"
    run_ffmpeg(["-i", str(SOURCE), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    source = parselmouth.Sound(str(wav))
    if source.get_total_duration() < 1.1:
        raise RuntimeError("Baseline title unexpectedly short")

    manipulation = call(source, "To Manipulation", 0.01, 65, 450)
    baseline_tier = call(manipulation, "Extract pitch tier")
    count = int(call(baseline_tier, "Get number of points"))
    if count < 35:
        raise RuntimeError(f"Could not reliably find baseline voiced pitch: {count} frames")

    pitch_times = np.array([float(call(baseline_tier, "Get time from index", i)) for i in range(1, count + 1)])
    pitch_vals = np.array([float(call(baseline_tier, "Get value at index", i)) for i in range(1, count + 1)])
    first, last = float(pitch_times[0]), float(pitch_times[-1])
    length = last - first
    if length < 0.7:
        raise RuntimeError(f"Voiced span too short to shape reliably: {length:.3f} seconds")

    # Shape approximately the final word, not the whole sentence.
    # Retain the exact original first word, timing, timbre and voice.
    pivot_time = last - (0.43 * length)
    pivot_pitch = float(np.median(pitch_vals[
        (pitch_times >= pivot_time - 0.09) & (pitch_times <= pivot_time + 0.09)
    ]))
    if not 65 < pivot_pitch < 450:
        raise RuntimeError(f"Unreliable pitch at pivot: {pivot_pitch}")

    print(f"Baseline duration {source.get_total_duration():.2f}s; voiced {first:.2f}-{last:.2f}s; "
          f"fall starts at {pivot_time:.2f}s from {pivot_pitch:.1f} Hz", flush=True)

    takes = [
        ("00-original", "0 · Original inflection", None, "The current, rising title for comparison."),
        ("01-gentle-fall", "1 · Gentle downward finish", 0.13,
         "Original voice and wording, with a small downward pitch contour on “Patterns.”"),
        ("02-natural-fall", "2 · Clear downward finish", 0.21,
         "Original voice and wording, with a measured downward pitch contour on “Patterns.”"),
        ("03-deeper-fall", "3 · Deeper downward finish", 0.29,
         "Original voice and wording, with a stronger downward pitch contour on “Patterns.”"),
    ]

    def encode(take_sound, slug):
        tmp = directory / (slug + ".wav")
        filename = DEST / (slug + ".mp3")
        take_sound.save(str(tmp), "WAV")
        run_ffmpeg(["-i", str(tmp), "-ar", "44100", "-ac", "1",
                    "-c:a", "libmp3lame", "-b:a", "96k", str(filename)])
        if filename.stat().st_size < 5000:
            raise RuntimeError(f"Encoded MP3 suspiciously small: {filename}")
        return filename

    for slug, title, depth, description in takes:
        if depth is None:
            sound = source
        else:
            m = call(source, "To Manipulation", 0.01, 65, 450)
            tier = call(m, "Extract pitch tier")
            call(tier, "Remove points between", pivot_time, last + 0.06)
            # A continuous smooth fall; preserve the original initial
            # part of the sample, including the first word's inflection.
            for fraction in np.linspace(0, 1, 22):
                t = pivot_time + fraction * (last - pivot_time)
                smooth = (1 - math.cos(math.pi * fraction)) / 2
                hz = pivot_pitch * (1 - depth * smooth)
                call(tier, "Add point", float(t), float(hz))
            call([tier, m], "Replace pitch tier")
            sound = call(m, "Get resynthesis (overlap-add)")
            if abs(sound.get_total_duration() - source.get_total_duration()) > 0.04:
                raise RuntimeError(f"Unexpected duration change for {slug}")
        filename = encode(sound, slug)
        print(f"{slug}: {filename.stat().st_size} bytes", flush=True)

    cards = []
    for slug, title, depth, description in takes:
        cards.append(
            f'<article><h2>{html.escape(title)}</h2>'
            f'<p>“Living Patterns.”</p>'
            f'<audio controls preload="none" src="{slug}.mp3"></audio>'
            f'<p class="description">{html.escape(description)}</p></article>'
        )

    htmlpage = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Living Patterns · Inflection auditions</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f4eddd;color:#142b3d;font-family:Arial,sans-serif}
main{max-width:800px;margin:0 auto;padding:30px clamp(18px,5vw,52px) 80px}
h1,h2{font-family:Georgia,serif;font-weight:400}
h1{font-size:clamp(2.2rem,5vw,3.5rem)}
h2{font-size:1.6rem;margin:0 0 12px}
header{border-bottom:1px solid #142b3d44;margin-bottom:24px;padding-bottom:24px}
article{border:1px solid #142b3d33;background:#fffaf0;margin:20px 0;padding:24px}
audio{display:block;width:100%;margin-top:16px}
p{line-height:1.6}
.description{font-size:.9rem}
.eyebrow{color:#b85c35;font-size:.75rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase}
</style></head><body><main>
<header>
<p class="eyebrow">Voice fixed · Wording fixed · Inflection variable</p>
<h1>Does the title finally sound finished?</h1>
<p>All four samples say exactly “Living Patterns.” in the same narrator’s voice.
Only the final pitch contour changes. Compare the downward endings, not the phrasing.</p>
</header>
""" + "\n".join(cards) + """
<footer><p>Unlisted test. These are candidates, not replacements for published episodes.
Pitch-shaping can sometimes introduce artifacts; the best choice must sound natural, not just fall in pitch.</p></footer>
</main></body></html>
"""
    (DEST / "index.html").write_text(htmlpage, encoding="utf-8")
    print("Inflection listening page and all four audio clips generated successfully.", flush=True)
