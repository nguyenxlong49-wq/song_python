#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LRC parser - giu nguyen logic tot tu karaoke_player.py parse_lrc."""
import re


def parse_lrc(lrc_path):
    """Parse [mm:ss.xx] / [mm:ss.xxx] / [mm:ss], ho tro nhieu timestamp 1 dong.
    Tra ve list[(time_sec, lyric)] da sap xep. Bo qua tag [ar:]/[ti:]/[offset:].
    """
    pattern = re.compile(r"\[(\d+):(\d+)(?:\.(\d+))?\]")
    lyrics = []
    with open(lrc_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if re.match(r"\[(ar|ti|al|by|offset):", line):
                continue
            timestamps = pattern.findall(line)
            if not timestamps:
                continue
            last_bracket = line.rfind("]")
            text = line[last_bracket + 1:].strip() if last_bracket != -1 else ""
            for minutes, seconds, centis in timestamps:
                try:
                    m = int(minutes)
                    s = int(seconds)
                    if not (0 <= s < 60):
                        continue
                    if centis:
                        if len(centis) == 2:
                            c = int(centis) / 100.0
                        elif len(centis) == 3:
                            c = int(centis) / 1000.0
                        else:
                            c = int(centis) / (10 ** len(centis))
                    else:
                        c = 0.0
                    lyrics.append((m * 60 + s + c, text))
                except ValueError:
                    continue
    lyrics.sort(key=lambda x: x[0])
    return lyrics


def apply_offset(lyrics, offset_sec):
    """Cong offset giay vao moi moc, clamp >= 0."""
    if not offset_sec:
        return list(lyrics)
    shifted = [(max(0.0, t + offset_sec), txt) for t, txt in lyrics]
    shifted.sort(key=lambda x: x[0])
    return shifted


def find_index(lyrics, elapsed):
    """Tim index dong dang hat: dong cuoi co time <= elapsed. -1 neu chua toi."""
    idx = -1
    for i, (t, _txt) in enumerate(lyrics):
        if elapsed >= t:
            idx = i
        else:
            break
    return idx


def estimate_progress(lyrics, idx, elapsed):
    """Uoc luong progress 0..1 cua dong idx.
    LRC chi co timestamp dau dong nen dung (next_time - cur_time).
    Giai thich: day la uoc luong, khong phai timestamp tung tu.
    """
    if idx < 0 or idx >= len(lyrics):
        return 0.0
    cur_t = lyrics[idx][0]
    if idx + 1 < len(lyrics):
        next_t = lyrics[idx + 1][0]
    else:
        next_t = cur_t + 3.0
    if elapsed <= cur_t:
        return 0.0
    if next_t <= cur_t:
        return 1.0
    p = (elapsed - cur_t) / (next_t - cur_t)
    if p < 0.0:
        return 0.0
    if p > 1.0:
        return 1.0
    return p
