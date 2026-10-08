#!/usr/bin/env python3
"""Create unlisted title-prosody listening samples without changing published episodes."""
from pathlib import Path
import html
import subprocess
import tempfile
import numpy as np
import soundfile as sf
from kokoro import KPipeline

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "auditions"
OUTPUT.mkdir(exist_ok=True)
PIPE = KPipeline(lang_code="b")

TAKES = [
    {
        "slug": "a-current-title",
        "title": "A · Existing style: isolated title",
        "text": "Living Patterns.",
        "voice": "bm_george",
        "note": "Control sample, same wording and voice as the current opening.",
    },
    {
        "slug": "b-declarative-announcement",
        "title": "B · Natural announcement",
        "text": "This is Living Patterns.",
        "voice": "bm_george",
        "note": "Tests a complete declarative phrase that naturally ends on the programme name.",
    },
    {
        "slug": "c-listening-introduction",
        "title": "C · Radio-style introduction",
        "text": "You're listening to Living Patterns.",
        "voice": "bm_george",
        "note": "More radio-like, but should provide a stronger falling cadence at the end.",
    },
    {
        "slug": "d-title-in-context",
        "title": "D · Title with context",
        "text": "Living Patterns. A short reflection on the life of places.",
        "voice": "bm_george",
        "note": "Checks whether providing the following sentence makes the title read more naturally.",
    },
    {
        "slug": "e-other-british-voice",
        "title": "E · Alternative British narrator",
        "text": "Living Patterns.",
        "voice": "bm_fable",
        "note": "Same title, different Kokoro British male voice for comparison.",
    },
]

def audio_for(text, voice):
    parts = []
    for result in PIPE(text, voice=voice, speed=0.88):
        segment = result.audio
        if hasattr(segment, "detach"):
            segment = segment.detach().cpu().numpy()
        parts.append(np.asarray(segment, dtype=np.float32).reshape(-1))
    if not parts:
        raise RuntimeError(f"No narration output for {text!r}")
    return np.concatenate(parts)

for take in TAKES:
    print(f"Rendering {take['slug']}: {take['voice']} {take['text']!r}", flush=True)
    wave = audio_for(take["text"], take["voice"])
    if not 0.75 < len(wave) / 24000 < 15:
        raise RuntimeError(f"Implausible duration: {take['slug']}: {len(wave) / 24000:.2f} s")
    with tempfile.TemporaryDirectory() as tempdir:
        wav = Path(tempdir) / "sample.wav"
        sf.write(wav, wave, 24000)
        mp3 = OUTPUT / (take["slug"] + ".mp3")
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(wav),
                "-af", "highpass=f=70,loudnorm=I=-18:TP=-2:LRA=7",
                "-ar", "44100", "-ac", "1", "-codec:a", "libmp3lame",
                "-b:a", "96k", str(mp3),
            ],
            check=True,
        )
    if mp3.stat().st_size < 3000:
        raise RuntimeError(f"Output too small: {mp3}")
    print(f"Saved {mp3.name} ({mp3.stat().st_size} bytes)", flush=True)

cards = []
for take in TAKES:
    cards.append(
        '<article>'
        f'<h2>{html.escape(take["title"])}</h2>'
        f'<p class="utterance">“{html.escape(take["text"])}”</p>'
        f'<audio controls preload="none" src="{take["slug"]}.mp3"></audio>'
        f'<p>{html.escape(take["note"])}</p>'
        '</article>'
    )

page = '''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Living Patterns · Opening-title voice audition</title>
<meta name="robots" content="noindex,nofollow">
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{font-family:system-ui,Arial,sans-serif;background:#f4eddd;color:#142b3d;margin:0}
main{max-width:850px;margin:auto;padding:32px clamp(20px,5vw,60px) 90px}
header{border-bottom:1px solid #142b3d44;padding-bottom:26px}h1,h2{font-family:Georgia,serif;font-weight:400}
h1{font-size:clamp(2.2rem,5vw,3.8rem);margin-bottom:12px}h2{font-size:1.6rem}
p{line-height:1.6}article{background:#fffaf0;border:1px solid #142b3d33;padding:24px;margin:18px 0}
audio{width:100%;margin:10px 0}.eyebrow{font-size:.75rem;color:#b85c35;letter-spacing:.12em;text-transform:uppercase;font-weight:bold}
.utterance{font-family:Georgia,serif;font-size:1.15rem}
</style></head><body><main><header>
<p class="eyebrow">Unlisted listening test · Not a published episode</p>
<h1>Opening-title prosody audition</h1>
<p>Listen for a natural, downward, finished cadence on “Living Patterns,” particularly on the last word. Different wording can guide text-to-speech prosody without changing the whole episode. These are candidates, not approved replacements.</p>
</header>
''' + "\n".join(cards) + '''
<p>Production baseline: Kokoro, British English, speed 0.88. None of the publicly published episodes have been changed by this test.</p>
</main></body></html>
'''
(OUTPUT / "index.html").write_text(page, encoding="utf-8")
print("Validated all five audition files and generated the listening page.", flush=True)
