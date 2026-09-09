#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI agent xu ly LRC: mp3 -> LRC dong bo.
1. .lrc cung ten co san -> dung ngay
2. LRCLIB theo ten file + duration -> luu
3. Co loi tho (plain text) -> rai timestamp deu theo duration
4. Khong co gi -> tao placeholder instrumental de nhac van co loi chay
"""
import os
import urllib.parse
import urllib.request


def guess_info(audio_path):
    base = os.path.splitext(os.path.basename(audio_path))[0]
    if " - " in base:
        artist, track = base.split(" - ", 1)
        return track.strip(), artist.strip()
    return base.strip(), ""


def duration_of(audio_path):
    try:
        from mutagen.mp3 import MP3
        return float(MP3(audio_path).info.length)
    except Exception:
        pass
    try:
        from mutagen.wave import WAVE
        return float(WAVE(audio_path).info.length)
    except Exception:
        return 0.0


def fetch_synced(track, artist, duration=0.0):
    try:
        qs = {"track_name": track, "artist_name": artist}
        if duration:
            qs["duration"] = str(int(duration))
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(qs)
        req = urllib.request.Request(url, headers={"User-Agent": "song_python-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            return data.get("syncedLyrics") or ""
    except Exception as e:
        print(f"[Agent LRCLIB] {e}")
        return ""


def distribute_plain(plain_text, duration):
    """Rai loi tho thanh LRC: bo intro 5s, outro 5s, chia deu."""
    lines = [l.strip() for l in plain_text.splitlines() if l.strip()]
    if not lines or duration <= 12:
        return ""
    start, end = 5.0, max(10.0, duration - 5.0)
    step = (end - start) / len(lines)
    out = []
    for i, line in enumerate(lines):
        t = start + i * step
        out.append(f"[{int(t//60):02d}:{t%60:05.2f}]{line}")
    return "\n".join(out) + "\n"


def placeholder(duration):
    """LRC tam khi chua co loi that: moi 10s mot moc instrumental."""
    if duration <= 0:
        duration = 180.0
    out = ["[00:00.00]♪ Intro..."]
    t = 10.0
    while t < duration - 5:
        out.append(f"[{int(t//60):02d}:{t%60:05.2f}]♪ ...")
        t += 10.0
    return "\n".join(out) + "\n"


def ensure_lrc(audio_path, plain_text=""):
    """Tra ve (lrc_path, nguon). Nguon: local/lrclib/plain/placeholder/none."""
    guess = os.path.splitext(audio_path)[0] + ".lrc"
    if os.path.exists(guess):
        return guess, "local"
    track, artist = guess_info(audio_path)
    dur = duration_of(audio_path)
    synced = fetch_synced(track, artist, dur) if track else ""
    if synced:
        with open(guess, "w", encoding="utf-8") as f:
            f.write(synced)
        print(f"[Agent] LRCLIB co loi: {guess}")
        return guess, "lrclib"
    if plain_text.strip():
        dist = distribute_plain(plain_text, dur or 180.0)
        if dist:
            with open(guess, "w", encoding="utf-8") as f:
                f.write(dist)
            print(f"[Agent] rai loi tho: {guess}")
            return guess, "plain"
    with open(guess, "w", encoding="utf-8") as f:
        f.write(placeholder(dur or 180.0))
    print(f"[Agent] tao placeholder: {guess} (sua file nay hoac dung Calibrate)")
    return guess, "placeholder"
