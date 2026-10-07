# Living Patterns production specification

This document is the production lock for the podcast. Change it deliberately, not incidentally.

## Current sonic baseline

The current baseline is provisional until the remastered pilot episodes are approved by ear.

- Narrator: Kokoro `bm_george`
- Kokoro speed: `0.88`
- Opening ambience: 3.0 seconds
- After “Living Patterns”: 1.25 seconds
- After episode title: 1.8 seconds
- Ordinary paragraph pause: 1.35 seconds
- Major structural pause: 4.5 seconds
- After ending label: 1.6 seconds
- Tail ambience: 4.0 seconds
- Narration normalization: approximately -18 LUFS before mixing
- Final program loudness: -16 LUFS
- True-peak ceiling: -1.5 dBTP
- Target loudness range: 8 LU
- MP3: 44.1 kHz, stereo, 96 kbps
- Music: none by default

The ambience bed should be quiet enough to disappear beneath attentive speech and become perceptible mainly in the breathing spaces. Duck ambience beneath narration rather than competing with it.

## Ambience families

Do not use garden birds as a universal wallpaper. Build a small, licensed library and choose from it sparingly:

1. quiet garden / birds
2. light rain
3. wind through leaves or grass
4. distant urban street
5. sheltered interior room tone
6. workshop / hand tools at a distance
7. water
8. night insects
9. winter exterior
10. near-silence / no added ambience

Silence is a first-class option. Conventional theme music is not part of the baseline.

Every ambience asset must have a source URL, creator, license, and license URL when applicable in the canonical episode data.

## Editorial audio structure

The default spoken structure is:

1. “Living Patterns.”
2. episode title
3. reflection
4. ending label
5. ending

The ending label is not permanently fixed to “A small practice.” See `EDITORIAL_PLAN.md`.

## Acceptance checklist

Before changing the production lock:

- listen in the actual podcast app, not only in a browser;
- compare at least five episodes with different sentence rhythms;
- test phone speaker, headphones, and a normal room speaker;
- confirm that pauses feel intentional rather than stalled;
- confirm that ambience is audible but not attention-seeking;
- confirm that sibilants, plosives, and sentence endings remain natural;
- confirm that loudness is consistent from episode to episode.

Once approved, future episodes should be rendered from this specification rather than hand-tuned individually.
