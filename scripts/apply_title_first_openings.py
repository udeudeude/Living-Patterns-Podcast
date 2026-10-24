#!/usr/bin/env python3
"""Create title-first masters from existing, voice-approved episode recordings.

The cut points below were measured separately for every published episode.
No speech synthesis or voice selection occurs. All original files are retained.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scan_intros import duration, speech_bands

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "episodes.json"

# seconds from the beginning of the source recording.
# onset is the first audible syllable of the *episode title*.
# cut leaves ~170ms of pre-title margin and was matched to the
# listener-approved 53-second audition for episode 1.
ONSET = {
    1: (6.53, 6.72),
    2: (6.55, 6.72),
    3: (1.33, 1.50),
    4: (1.29, 1.46),
    5: (1.17, 1.34),
    6: (1.43, 1.60),
}


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
                          check=True)


def title_start_present(groups, onset):
    return any(abs(a - onset) <= 0.13 for a, b in groups)


def original_announcement_present(groups, onset, number):
    # For remasters, the audible show name begins after a 3-second ambience
    # lead-in. Older masters begin with the show name immediately.
    initial = 3.30 if number in (1, 2) else 0.04
    return any(abs(a - initial) < 0.18 and b < onset for a, b in groups)


def fmt_duration(seconds):
    n = int(seconds + 0.5)
    return f"{n//60}:{n%60:02d}"


def main():
    episodes = json.loads(DATA.read_text(encoding="utf-8"))
    if {e["number"] for e in episodes if e["status"] == "published"} != set(ONSET):
        raise RuntimeError("Published episode inventory changed; re-audit before cutting")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    changes = []

    for e in episodes:
        if e["status"] != "published":
            continue
        number = e["number"]
        cut, onset = ONSET[number]
        old = ROOT / e["audio"]
        if not old.is_file():
            raise RuntimeError(f"Missing source audio: {old}")
        if old.stem.endswith("-title-first"):
            raise RuntimeError(f"Episode {number} already has a title-first filename")

        original_length = duration(old)
        if not 95 < original_length < 180:
            raise RuntimeError(f"Episode {number}: unexpected master length")

        scan = speech_bands(old, seconds=23)
        groups = scan["groups"]
        if not title_start_present(groups, onset):
            raise RuntimeError(f"Episode {number}: episode-title onset could not be verified: {groups}")
        if not original_announcement_present(groups, onset, number):
            raise RuntimeError(f"Episode {number}: opening show-name announcement not detected: {groups}")

        target_name = old.stem + "-title-first.mp3"
        target = ROOT / target_name
        if target.exists():
            raise RuntimeError(f"Would overwrite an existing audio file: {target}")

        # Match the accepted listening demo's 0.08s fade-in.
        # No loudness, equalization, pitch or time manipulation is applied.
        ffmpeg(
            "-ss", f"{cut:.3f}",
            "-i", str(old),
            "-af", "afade=t=in:st=0:d=0.08",
            "-ar", "44100", "-ac", "2",
            "-codec:a", "libmp3lame", "-b:a", "96k",
            str(target),
        )

        new_length = duration(target)
        if abs(new_length - (original_length - cut)) > 0.10:
            raise RuntimeError(f"Episode {number}: incorrect clipped duration")
        if target.stat().st_size < 300000:
            raise RuntimeError(f"Episode {number}: output unexpectedly small")

        # The new beginning should match the title onset that was previously
        # cut to around 0.17s into the new audio, not the show-name intro.
        new_scan = speech_bands(target, seconds=6)
        first = new_scan["groups"][0][0] if new_scan["groups"] else -1
        if not 0.04 <= first <= 0.45:
            raise RuntimeError(f"Episode {number}: title start seems clipped: {new_scan['groups']}")

        e["audio"] = target_name
        e["duration"] = fmt_duration(new_length)
        e["updated_at"] = now

        changes.append({
            "episode": number,
            "old": old.name,
            "new": target_name,
            "old_sec": round(original_length, 2),
            "cut_sec": cut,
            "new_sec": round(new_length, 2),
            "duration": e["duration"],
            "start_first_group": first,
            "new_size": target.stat().st_size,
        })
        print(json.dumps(changes[-1]), flush=True)

    DATA.write_text(json.dumps(episodes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Published {len(changes)} title-first masters. Build the feed and site using scripts/build.py.", flush=True)


if __name__ == "__main__":
    main()
