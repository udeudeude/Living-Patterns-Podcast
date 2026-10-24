#!/usr/bin/env python3
"""Read-only inventory of opening speech bands for all published episodes."""
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def speech_bands(filename, seconds=23):
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(filename),
            "-t", str(seconds), "-af", "highpass=f=180,lowpass=f=1800",
            "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1",
        ],
        capture_output=True, check=True,
    )
    y = np.frombuffer(proc.stdout, dtype="<f4")
    width = 320
    frame_count = len(y) // width
    frames = y[:frame_count*width].reshape(frame_count,width)
    rms = np.sqrt(np.mean(frames*frames,axis=1))
    envelope = np.convolve(rms, np.ones(7)/7, mode="same")
    background = float(np.percentile(envelope,10))
    loud = float(np.percentile(envelope,96))
    threshold = max(background*3, loud*0.19, 0.002)
    flagged = np.flatnonzero(envelope>threshold)
    groups = []
    if len(flagged):
        st=pr=int(flagged[0])
        for k in flagged[1:]:
            k=int(k)
            if k-pr<=12:
                pr=k
            else:
                if pr-st>=11: groups.append([round(st*.02,2),round((pr+1)*.02,2)])
                st=pr=k
        if pr-st>=11: groups.append([round(st*.02,2),round((pr+1)*.02,2)])
    return {
        "background":round(background,5),
        "loud":round(loud,5),
        "threshold":round(threshold,5),
        "groups":groups,
    }


def duration(path):
    proc=subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=nokey=1:noprint_wrappers=1",str(path)],
        capture_output=True,text=True,check=True,
    )
    return float(proc.stdout.strip())


def main():
    ep=json.loads((ROOT/"data/episodes.json").read_text())
    for e in ep:
        f=ROOT/e["audio"]
        print(json.dumps({
            "number":e["number"],"title":e["title"],
            "audio":e["audio"],"seconds":round(duration(f),2),
            **speech_bands(f)
        }), flush=True)


if __name__=="__main__":
    main()
