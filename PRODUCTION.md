# Living Patterns production specification

This document is the production lock for the podcast. Change it deliberately, not incidentally.

## Current sonic baseline

The narrator is the approved Kokoro `bm_george` voice and is not open for voice auditions. The title-first opening is approved by listening. Other sonic parameters remain provisional until the pilot episodes are reviewed.

- Narrator: Kokoro `bm_george`
- Kokoro speed: `0.88`
- Opening ambience: a brief margin before the spoken episode title; the 3.0-second original preroll is not a requirement for a title-first opening
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

1. episode title
2. reflection
3. ending label
4. ending

**Approved opening decision:** Do not announce “Living Patterns” at the start of each episode. The show name remains visible in podcast apps and artwork; the spoken programme begins directly with the individual episode title. Keep the established narrator, and review awkward inflections in individual sentences rather than changing voice or adding an introductory formula.

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
