# Living Patterns

A short-form podcast of original reflections on living structure, wholeness, centers, repair, participation, and the fit between human life and place.

## Repository model

`data/episodes.json` is the canonical source for published episode text and metadata.  
`data/preview.json` is reserved for pre-launch pilot episodes.  
`data/show.json` contains show-level metadata and source-lineage language.  
`scripts/build.py` deterministically generates `feed.xml`, `preview-feed.xml`, and `index.html`.

Do not hand-edit the generated feed or episode cards. Change the canonical data and rebuild.

## Build

```bash
python3 scripts/build.py
python3 scripts/build.py --check
```

The check mode verifies that generated files match canonical data and catches duplicate GUIDs, episode numbers, broken related-episode references, missing audio files, malformed durations, and ambience-credit contamination.

## Editorial and audio specifications

See `PRODUCTION.md` and `EDITORIAL_PLAN.md`.
