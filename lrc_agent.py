#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI agent: xac nhan bai hat -> lay API -> xuat LRC.
1. Doc metadata tag (title/artist) -> filename -> LRCLIB search cham diem duration
2. .lrc cung ten co san -> dung ngay
3. Co loi tho -> rai timestamp
4. Khong co gi -> placeholder
"""
import os
import urllib.parse
import urllib.request

UA = "song_python-agent/1.0"


def read_tags(audio_path):
    """Doc title/artist/album tu metadata. Tra ve dict."""
    info = {"title": "", "artist": "", "album": ""}
    try:
        from mutagen import File
        audio = File(audio_path)
        if audio is None:
            return info
        def first(keys):
            for k in keys:
                if k in audio:
                    v = audio[k]
                    if isinstance(v, list) and v:
                        return str(v[0]).strip()
                    return str(v).strip()
            return ""
        info["title"] = first(["TIT2", "title", "\xa9nam", "TITLE"])
        info["artist"] = first(["TPE1", "artist", "\xa9ART", "ARTIST"])
        info["album"] = first(["TALB", "album", "\xa9alb", "ALBUM"])
    except Exception as e:
        print(f"[Agent tags] {e}")
    return info


def clean_suffix(text):
    """Cat hau to YouTube/NCS: [Official...], (Official...), Future Bass, NCS, Copyright Free Music, HD..."""
    import re
    t = text
    t = re.sub(r"\[.*?Official.*?\]", "", t, flags=re.I)
    t = re.sub(r"\(.*?Official.*?\)", "", t, flags=re.I)
    for pat in [r"Future Bass", r"\bNCS\b", r"Copyright Free Music", r"Copyright Free", r"\bHD\b",
                r"Official Music Video", r"Official Video", r"Official Audio", r"Lyrics? Video",
                r"Coca-Cola.*", r"FIFA World Cup.*"]:
        t = re.sub(pat, "", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip(" -_()[]")
    return t.strip()


def guess_info(audio_path):
    tags = read_tags(audio_path)
    if tags["title"]:
        return clean_suffix(tags["title"]), clean_suffix(tags["artist"])
    base = os.path.splitext(os.path.basename(audio_path))[0]
    if " - " in base:
        artist, track = base.split(" - ", 1)
        return clean_suffix(track), clean_suffix(artist)
    return clean_suffix(base), ""


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


def identify_song(audio_path):
    """Xac nhan bai: tag -> filename -> duration. Tra ve dict."""
    track, artist = guess_info(audio_path)
    dur = duration_of(audio_path)
    tags = read_tags(audio_path)
    src = "tags" if tags["title"] else "filename"
    result = {"track": track, "artist": artist, "duration": dur, "source": src}
    print(f"[Agent identify] {artist} - {track} ({dur:.1f}s) via {src}")
    return result


def search_lrclib(track, artist=""):
    try:
        q = f"{artist} {track}".strip() or track
        url = "https://lrclib.net/api/search?q=" + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Agent search] {e}")
        return []


def fetch_best(track, artist, duration=0.0):
    """Task lay API: search -> cham diem (co synced + duration gan nhat) -> tra LRC."""
    # 1. Thu get chinh xac truoc
    try:
        qs = {"track_name": track, "artist_name": artist}
        if duration:
            qs["duration"] = str(int(duration))
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(qs)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            if data.get("syncedLyrics"):
                print(f"[Agent] get chinh xac id={data.get('id')}")
                return data["syncedLyrics"], data.get("id")
    except Exception as e:
        print(f"[Agent get] {e} -> chuyen search")
    # 2. Search + cham diem
    cands = search_lrclib(track, artist)
    best, best_score = None, None
    for rec in cands:
        if not rec.get("syncedLyrics"):
            continue
        dd = abs((rec.get("duration") or 0) - (duration or 0)) if duration else 0
        # Uu tien artist khop + duration gan
        artist_ok = (artist.lower() in (rec.get("artistName") or "").lower()) if artist else True
        score = (0 if artist_ok else 1000) + dd
        if best_score is None or score < best_score:
            best_score, best = score, rec
    if best:
        print(f"[Agent] search chon id={best.get('id')} {best.get('artistName')}-{best.get('trackName')} dd={best_score:.1f}s")
        return best["syncedLyrics"], best.get("id")
    return "", None


def fetch_synced(track, artist, duration=0.0):
    text, _id = fetch_best(track, artist, duration)
    return text


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
    """Tra ve (lrc_path, nguon). Nguon: local/lrclib/plain/placeholder."""
    guess = os.path.splitext(audio_path)[0] + ".lrc"
    if os.path.exists(guess):
        return guess, "local"
    ident = identify_song(audio_path)
    synced, _id = fetch_best(ident["track"], ident["artist"], ident["duration"])
    if synced:
        with open(guess, "w", encoding="utf-8") as f:
            f.write(synced)
        print(f"[Agent] LRCLIB co loi ({ident['artist']}-{ident['track']}): {guess}")
        return guess, "lrclib"
    if plain_text.strip():
        dist = distribute_plain(plain_text, ident["duration"] or 180.0)
        if dist:
            with open(guess, "w", encoding="utf-8") as f:
                f.write(dist)
            print(f"[Agent] rai loi tho: {guess}")
            return guess, "plain"
    # Khong tu tao placeholder gia nua: tra ve rong de GUI bao ro
    print(f"[Agent] khong tim thay LRC that cho {ident['artist']} - {ident['track']}")
    return "", "none"
