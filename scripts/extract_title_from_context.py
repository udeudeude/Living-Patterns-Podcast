#!/usr/bin/env python3
"""Isolate the title from speech generated with natural declarative context.

The existing Kokoro voice is preserved. No resynthesis, new voice or
post-hoc pitch alteration is performed. Word-level timestamps find the
start of 'Living', then the prefix is removed with a tiny fade-in.
"""
from __future__ import annotations

import html
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "auditions" / "context"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {
        "id": "b-title-only",
        "source": "b-declarative-announcement.mp3",
        "title": "B · Title isolated from the preferred take",
        "full": "This is Living Patterns.",
        "detail": "The extra words have been cut away. The original title inflection is untouched.",
    },
    {
        "id": "c-title-only",
        "source": "c-listening-introduction.mp3",
        "title": "C · Title isolated from the radio-style take",
        "full": "You're listening to Living Patterns.",
        "detail": "A second natural falling cadence from the same approved narrator.",
    },
]

def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)

def words_from_audio(model, path):
    segments, _ = model.transcribe(
        str(path),
        language="en",
        word_timestamps=True,
        beam_size=5,
        condition_on_previous_text=False,
        vad_filter=False,
        initial_prompt="This is Living Patterns. You're listening to Living Patterns.",
    )
    words = []
    for segment in segments:
        for word in segment.words or []:
            token = re.sub(r"[^a-z]+", "", word.word.lower())
            if token:
                words.append((token, float(word.start), float(word.end)))
    return words

model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

cards = []
for item in SOURCES:
    src = ROOT / "auditions" / item["source"]
    if not src.is_file():
        raise SystemExit(f"Missing existing reference recording: {src}")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        wav = work / "input.wav"
        ffmpeg("-i", str(src), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav))

        aligned = words_from_audio(model, wav)
        print(f'{item["id"]} aligned words: {aligned}', flush=True)

        starts = [
            start for n, (token, start, end) in enumerate(aligned[:-1])
            if token == "living" and aligned[n+1][0] == "patterns"
        ]
        if len(starts) != 1:
            raise RuntimeError(
                f"Could not establish a unique 'Living Patterns' word boundary in "
                f"{item['source']}: {aligned}"
            )

        y, sr = sf.read(wav, dtype="float32")
        assert y.ndim == 1
        start = max(0.0, starts[0] - 0.040)
        if start < 0.3 or start > 1.9:
            raise RuntimeError(f"Unexpected aligned title onset: {start:.2f}")

        audio = np.array(y[int(start * sr):], copy=True)
        if not 1.0 < len(audio)/sr < 3.0:
            raise RuntimeError(f"Trimmed sample has implausible length {len(audio)/sr:.2f}s")
        fade_samples = min(round(sr * 0.008), len(audio) // 10)
        audio[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)

        clipped_wav = work / "clipped.wav"
        sf.write(clipped_wav, audio, sr)

        # Independently check the spoken words after editing.
        spoken = words_from_audio(model, clipped_wav)
        print(f'{item["id"]}: cut {start:.3f}s; trimmed duration {len(audio)/sr:.2f}s; words {spoken}', flush=True)
        target = [token for token, _, _ in spoken]
        if not any(target[i:i+2] == ["living", "patterns"] for i in range(len(target)-1)):
            raise RuntimeError(f"Trimmed audio is not recognized as Living Patterns: {spoken}")
        if any(token in {"this", "is", "youre", "listening", "to"} for token in target):
            raise RuntimeError(f"Trimmed audio appears to retain intro words: {spoken}")

        result = OUT / (item["id"] + ".mp3")
        ffmpeg("-i", str(clipped_wav), "-ar", "44100", "-ac", "1",
               "-codec:a", "libmp3lame", "-b:a", "96k", str(result))
        if result.stat().st_size < 10000:
            raise RuntimeError(f"Too-small output: {result}")

    cards.append(
        f'<article><h2>{html.escape(item["title"])}</h2>'
        f'<p>“Living Patterns.”</p><audio controls preload="none" src="{item["id"]}.mp3"></audio>'
        f'<p>{html.escape(item["detail"])}</p></article>'
    )

(OUT / "index.html").write_text(
    """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Living Patterns · Natural title inflection</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4eddd;color:#142b3d;font-family:Arial,sans-serif}
main{max-width:830px;margin:auto;padding:36px clamp(20px,5vw,60px) 84px}
h1,h2{font-family:Georgia,serif;font-weight:400}h1{font-size:clamp(2.2rem,5vw,3.7rem);line-height:1.1}
h2{font-size:1.5rem}p{line-height:1.55}
article{background:#fffaf0;border:1px solid #142b3d33;padding:26px;margin:22px 0}
audio{display:block;width:100%;margin:16px 0}.eyebrow{font-size:.75rem;letter-spacing:.13em;color:#b85c35;font-weight:bold;text-transform:uppercase}
</style></head><body><main>
<p class="eyebrow">Same narrator · Same words · No pitch-shifting</p>
<h1>Let the title have its natural ending.</h1>
<p>Both clips say only “Living Patterns.” They were spoken as the end of a
complete sentence, then the preceding words were removed. This tests an
actual change in delivery rather than an artificially lowered final note.</p>
""" + "\n".join(cards) +
    """<p>Unlisted listening test. The published podcast episodes are unchanged.</p>
</main></body></html>
""",
    encoding="utf-8",
)
print("Generated two contextual title extracts and their listening page.", flush=True)
