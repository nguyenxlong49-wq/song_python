#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool can chinh LRC khop giong ca si
Chay: python calibrate_lrc.py
- Phat mp3
- Hien tung dong loi, ban nhan Enter dung luc ca si hat dong do
- Tu dong ghi timestamp chinh xac vao file moi
"""
import os, sys, time
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except: pass

try:
    import pygame
except ImportError:
    print("Can pygame: pip install pygame")
    sys.exit(1)

AUDIO = "assets/music/love-me-again.mp3"
# Lay loi tu file cu (bo timestamp)
SRC_LRC = "assets/music/love-me-again.lrc"
OUT_LRC = "assets/music/love-me-again_synced.lrc"

def load_lyrics_no_time(path):
    lyrics=[]
    with open(path, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            # bo [00:00.00]
            if line.startswith("["):
                idx=line.find("]")
                if idx!=-1:
                    line=line[idx+1:].strip()
            if line:
                lyrics.append(line)
    return lyrics

lyrics = load_lyrics_no_time(SRC_LRC)
print(f"Tim thay {len(lyrics)} dong loi tu {SRC_LRC}")
for i,l in enumerate(lyrics[:5]):
    print(f"  {i+1}. {l}")
print("  ...")
input("\nNhan Enter de bat dau phat nhac va can chinh (se phat mp3)...")

pygame.mixer.init()
pygame.mixer.music.load(AUDIO)
pygame.mixer.music.play()
start = time.time()
print("\n=== DANG PHAT - NHAN ENTER DUNG NHIP CA SI HAT ===")
print("Moi dong loi se hien, ban nhan Enter khi ca si bat dau hat dong do")
print("Nhan Ctrl+C de ket thuc som\n")

timestamps=[]
try:
    for i, line in enumerate(lyrics):
        print(f"\n[{i+1}/{len(lyrics)}] CHUAN BI: {line}")
        input("  -> Nhan Enter NGAY KHI ca si hat dong nay... ")
        t = time.time() - start
        timestamps.append((t, line))
        print(f"     Da ghi [{int(t//60):02d}:{t%60:05.2f}] {line}")
    pygame.mixer.music.stop()
except KeyboardInterrupt:
    pygame.mixer.music.stop()
    print("\nDa dung can chinh.")

# Ghi file mới
with open(OUT_LRC, "w", encoding="utf-8") as f:
    for t, line in timestamps:
        m = int(t//60); s = t%60
        f.write(f"[{m:02d}:{s:05.2f}]{line}\n")
print(f"\nDa ghi file chinh xac: {OUT_LRC}")
print("Chay thu: python karaoke_player.py --audio assets/music/love-me-again.mp3 --lrc assets/music/love-me-again_synced.lrc")

# Tu dong cap nhat DEFAULT de lan sau chay la khop
# Copy de thanh file chinh
import shutil
shutil.copy(OUT_LRC, SRC_LRC)
print(f"Da cap nhat {SRC_LRC} de lan sau python karaoke_player.py chay khop luon.")
