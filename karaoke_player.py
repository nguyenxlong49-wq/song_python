#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Karaoke Player - Phát nhạc và xuất lời bài hát đúng giai điệu
Hỗ trợ 2 chế độ:
1. Phát file nhạc (mp3/wav) + file lời .lrc đồng bộ thời gian
2. Phát giai điệu tự tạo bằng Beep + lời đồng bộ (không cần file nhạc)

Tác giả: Muse Spark
Yêu cầu: pip install pygame colorama
"""

import os
import re
import sys
import time
import math
# Fix Windows console encoding for Vietnamese
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thử import các thư viện tùy chọn
try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False  # Linux/Mac không có winsound

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    class Fore:
        RED = YELLOW = GREEN = CYAN = BLUE = MAGENTA = WHITE = ""
        LIGHTRED_EX = LIGHTYELLOW_EX = LIGHTGREEN_EX = LIGHTCYAN_EX = LIGHTBLUE_EX = LIGHTMAGENTA_EX = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""

# 7 sac cau vong
RAINBOW_COLORS = []
if HAS_COLORAMA:
    RAINBOW_COLORS = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.WHITE]
else:
    RAINBOW_COLORS = [""]

def rainbow_text(text, offset=0):
    """Tra ve text 7 sac cau vong, offset de tao animation chay"""
    if not HAS_COLORAMA or not RAINBOW_COLORS[0]:
        return text
    res=""
    for i,ch in enumerate(text):
        col = RAINBOW_COLORS[(i+offset) % len(RAINBOW_COLORS)]
        res += f"{col}{Style.BRIGHT}{ch}"
    res += Style.RESET_ALL
    return res

def wave_rainbow_text(text, phase=0):
    """Uon song + 7 sac: moi ky tu vua doi mau vua len xuong theo sin"""
    if not text:
        return ["", text, ""]
    # 3 dong de tao song uon
    top = ""; mid = ""; bot = ""
    for i,ch in enumerate(text):
        # Song sin: -1 .. 1
        wave = math.sin(i*0.8 + phase)
        col = RAINBOW_COLORS[(i+int(phase)) % len(RAINBOW_COLORS)] if HAS_COLORAMA and RAINBOW_COLORS[0] else ""
        bright = Style.BRIGHT if HAS_COLORAMA else ""
        reset = Style.RESET_ALL if HAS_COLORAMA else ""
        styled = f"{col}{bright}{ch}{reset}" if HAS_COLORAMA else ch
        if wave > 0.5:
            top += styled
            mid += " "
            bot += " "
        elif wave < -0.5:
            top += " "
            mid += " "
            bot += styled
        else:
            top += " "
            mid += styled
            bot += " "
    return [top, mid, bot]

# 3. Hieu ung karaoke gradient + glow
def karaoke_gradient_text(text, progress):
    """To mau dan tu trai sang phai theo progress 0..1, chuyen mau muot, co glow"""
    if not text:
        return ""
    n = len(text)
    filled = int(n * max(0, min(1, progress)))
    res = ""
    for i,ch in enumerate(text):
        if i < filled:
            # Da hat: mau sang + gradient theo vi tri
            col = RAINBOW_COLORS[i % len(RAINBOW_COLORS)] if HAS_COLORAMA and RAINBOW_COLORS[0] else ""
            res += f"{col}{Style.BRIGHT}{ch}{Style.RESET_ALL}"
        elif i == filled and 0 < progress < 1:
            # Bien gradient muot: mau trung gian sang hon
            res += f"{Fore.YELLOW}{Style.BRIGHT}{ch}{Style.RESET_ALL}" if HAS_COLORAMA else ch
        else:
            # Chua hat: mo
            res += f"{Fore.WHITE}{ch}" if HAS_COLORAMA else ch
    # Glow nhe: them 1 dong mo duoi
    return res

def render_waveform(elapsed, width=42, height=3):
    """4+9. Waveform realtime mo phong (vi pygame.mixer khong cho FFT realtime)
    Tra ve chuoi waveform dang ▂▅█▆▃ voi gradient + glow, chuyen dong lien tuc theo beat
    Giai thich: pygame.mixer.music khong expose raw audio buffer, nen dung mo phong
    sin + random theo beat (BPM ~128) de tranh lag GUI, van dong bo cam giac nhac
    """
    import random
    bars = []
    # Beat ~0.47s (128 BPM), amplitude nhap nhay theo nhac
    beat_phase = elapsed * 2.7
    for i in range(width):
        # Tong hop 2 sin de tao song phuc tap + random nhe
        base = math.sin(i*0.6 + beat_phase) * 0.6 + math.sin(i*1.2 - beat_phase*0.7) * 0.4
        amp = (base + 1) / 2  # 0..1
        # Them chut random de song dong
        amp = max(0, min(1, amp + random.uniform(-0.08, 0.08)))
        # Chon ky tu theo amplitude
        if amp < 0.2:
            ch = "▂"
        elif amp < 0.4:
            ch = "▃"
        elif amp < 0.6:
            ch = "▅"
        elif amp < 0.8:
            ch = "▆"
        else:
            ch = "█"
        # Gradient mau theo vi tri + amplitude
        if HAS_COLORAMA:
            if amp > 0.7:
                col = Fore.MAGENTA
            elif amp > 0.5:
                col = Fore.CYAN
            elif amp > 0.3:
                col = Fore.GREEN
            else:
                col = Fore.BLUE
            # Glow nhe: them BRIGHT khi cao
            style = Style.BRIGHT if amp > 0.6 else ""
            bars.append(f"{col}{style}{ch}{Style.RESET_ALL}")
        else:
            bars.append(ch)
    # Glow them 1 dong mo ben duoi
    return "".join(bars)

# ================== CẤU HÌNH FILE NHẠC CỦA BẠN ==================
# Đổi 2 dòng này thành tên file mp3 + lrc của bạn (đặt cùng thư mục karaoke_player.py)
DEFAULT_AUDIO = "music.mp3"  # ví dụ: "my-song.mp3" hoặc "D:/Nhac/bai-hat.mp3" - doi thanh ten file mp3 cua ban
DEFAULT_LRC   = "music.lrc"  # ví dụ: "my-song.lrc" - để trống "" nếu chỉ muốn phát nhạc không lời
# Tu dong tim file nhac - uu tien thu muc assets/music, ho tro bat ky ten file
import glob as _glob
_found = None
for _cand in ["assets/music/music.mp3", "assets/music/music.wav", "assets/music/music.ogg", "music.mp3", "music.wav"]:
    if os.path.exists(_cand):
        _found = _cand
        break
# neu chua tim thay, scan bat ky mp3/wav trong assets/music
if not _found:
    for _pat in ["assets/music/*.mp3", "assets/music/*.wav", "assets/music/*.ogg", "assets/music/*.m4a"]:
        _lst = _glob.glob(_pat)
        if _lst:
            _found = _lst[0]
            break
if _found:
    DEFAULT_AUDIO = _found
    DEFAULT_LRC = os.path.splitext(_found)[0] + ".lrc"

# Can chinh do lech loi vs giong ca si (giay): + = loi hien muon hon, - = som hon
# Per-song offset: mp3 252.7s vs LRC 227s (love) va 182s vs 174s (super) lech ban thu am
# love cham ~2s -> som 2s; super ve goc API 1.86s
LRC_OFFSET = 0.0
PER_SONG_OFFSET = {
    "love-me-again": -3.0,
    "colors": 0.0,
    "Jason Derulo": 0.0,
    "superhero": 0.0,
    "Unknown Brain": 0.0,
}

# ================== CẤU HÌNH NỐT NHẠC ==================
# Tần số các nốt (Hz) - quãng 4 và 5
NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 'A4': 440, 'B4': 494,
    'C5': 523, 'D5': 587, 'E5': 659, 'F5': 698, 'G5': 784, 'A5': 880, 'B5': 988,
    'REST': 0  # nốt nghỉ
}

# ================== DEMO BÀI HÁT: Happy Birthday (tự tạo giai điệu) ==================
# Mỗi phần tử: (note, duration_ms, lyric)
# duration_ms = thời lượng nốt nhạc, cũng là thời gian hiển thị lyric
DEMO_SONG = [
    ('C4', 500, "Happy"),
    ('C4', 500, "birthday"),
    ('D4', 750, "to"),
    ('C4', 750, "you"),
    ('F4', 750, "Happy"),
    ('E4', 1500, "birthday"),
    ('C4', 500, "Happy"),
    ('C4', 500, "birthday"),
    ('D4', 750, "to"),
    ('C4', 750, "you"),
    ('G4', 750, "Happy"),
    ('F4', 1500, "birthday"),
    ('C4', 500, "Happy"),
    ('C4', 500, "birthday"),
    ('C5', 750, "to"),
    ('A4', 750, "you"),
    ('F4', 750, "Happy"),
    ('E4', 750, "birth-"),
    ('D4', 750, "-day"),
    ('REST', 500, ""),
    ('A4', 500, "Happy"),
    ('A4', 500, "birth-"),
    ('A4', 750, "-day"),
    ('G4', 750, "to"),
    ('F4', 750, "you"),
    ('G4', 1500, "youuu!"),
]

# Demo tiếng Việt: "Chúc Bé Ngủ Ngon" (Twinkle Twinkle) - dễ đồng bộ
DEMO_TWINKLE = [
    ('C4', 500, "Lấp lánh"),
    ('C4', 500, "lấp lánh"),
    ('G4', 500, "ngôi"),
    ('G4', 500, "sao"),
    ('A4', 500, "nhỏ"),
    ('A4', 500, "xinh"),
    ('G4', 1000, "xinh~~"),
    ('F4', 500, "Trên"),
    ('F4', 500, "cao"),
    ('E4', 500, "trên"),
    ('E4', 500, "cao"),
    ('D4', 500, "tít"),
    ('D4', 500, "trên"),
    ('C4', 1000, "cao~~"),
]

# ================== HÀM TIỆN ÍCH ==================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_lrc(lrc_path):
    """
    Parse file .lrc dạng:
    [00:12.00] Lời bài hát
    [00:15.30] Dòng tiếp theo
    [mm:ss.xx] hoac [mm:ss.xxx], ho tro nhieu timestamp tren 1 dong
    Tra ve: list[(time_sec: float, lyric: str)] da sap xep
    karaoke_player.py:85
    """
    # Ho tro [mm:ss.xx] va [mm:ss.xxx], ca [mm:ss] khong co mili
    pattern = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\]')
    lyrics = []
    try:
        with open(lrc_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                # Bo qua tag metadata [ar:], [ti:], [offset:]
                if re.match(r'\[(ar|ti|al|by|offset):', line):
                    continue
                timestamps = pattern.findall(line)
                if not timestamps:
                    continue
                # Lay text sau timestamp cuoi
                last_bracket = line.rfind(']')
                text = line[last_bracket+1:].strip() if last_bracket != -1 else ""
                for minutes, seconds, centis in timestamps:
                    try:
                        m = int(minutes); s = int(seconds)
                        if not (0 <= s < 60):
                            continue
                        if centis:
                            # 2 chu so -> /100, 3 chu so -> /1000
                            div = 10 ** len(centis)
                            # chuan hoa ve giay: 12 -> 0.12, 123 -> 0.123
                            # neu 2 so thi /100, 3 so thi /1000 tu dong qua len
                            c = int(centis) / div if len(centis) <= 2 else int(centis) / 1000
                            # truong hop 2 so nhung doc la 05 -> 0.05 dung
                            if len(centis) == 2:
                                c = int(centis) / 100
                            elif len(centis) == 3:
                                c = int(centis) / 1000
                        else:
                            c = 0
                        time_sec = m * 60 + s + c
                        lyrics.append((time_sec, text))
                    except ValueError:
                        continue
    except FileNotFoundError:
        print(f"[Loi] Khong tim thay file lrc: {lrc_path}")
        return []
    except UnicodeDecodeError as e:
        print(f"[Loi] Doc lrc that bai (encoding): {e}")
        return []
    lyrics.sort(key=lambda x: x[0])
    return lyrics

def play_tone(freq, duration_ms):
    """
    Phát 1 nốt nhạc tần số freq trong duration_ms
    Ưu tiên: winsound (Windows) -> pygame -> print
    karaoke_player.py:102
    """
    if freq == 0:  # REST
        time.sleep(duration_ms / 1000)
        return

    if HAS_WINSOUND and os.name == 'nt':
        try:
            winsound.Beep(freq, duration_ms)
            return
        except Exception:
            pass

    if HAS_PYGAME:
        # Tạo sóng sine bằng pygame nếu không có winsound
        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=44100, size=-16, channels=1)
                except Exception:
                    pygame.mixer.init()
            import numpy as np
            sample_rate = 44100
            n_samples = int(sample_rate * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, n_samples, False)
            wave = (np.sin(2 * np.pi * freq * t) * 32767 * 0.3).astype(np.int16)
            # Chuyển sang stereo nếu cần
            sound = pygame.sndarray.make_sound(wave)
            sound.play()
            time.sleep(duration_ms / 1000)
            return
        except ImportError:
            print("[Canh bao] Thieu numpy, bo qua am thanh sine, chi sleep")
        except Exception as e:
            # print(f"[Canh bao] play_tone pygame loi: {e}")
            pass
        # Fallback pygame không có numpy: dùng delay
        time.sleep(duration_ms / 1000)
        return

    # Fallback cuối: chỉ sleep + in ra
    time.sleep(duration_ms / 1000)


# ================== CHẾ ĐỘ 1: Phát file nhạc + LRC ==================

def play_with_lrc(audio_path, lrc_path):
    """
    Phát file nhạc và hiển thị lời đồng bộ theo timestamp LRC
    karaoke_player.py:145
    """
    if not os.path.exists(audio_path):
        print(f"[Lỗi] Không tìm thấy file nhạc: {audio_path}")
        return
    if not os.path.exists(lrc_path):
        print(f"[Lỗi] Không tìm thấy file lời: {lrc_path}")
        return
    if not HAS_PYGAME:
        print("[Lỗi] Chế độ này cần pygame: pip install pygame")
        return

    lyrics = parse_lrc(lrc_path)
    if not lyrics:
        print("[Lỗi] File LRC rỗng hoặc sai định dạng")
        return
    # Ap dung offset can chinh per-song, clamp >=0 tranh am
    effective_offset = LRC_OFFSET
    low = audio_path.lower()
    for key, val in PER_SONG_OFFSET.items():
        if key.lower() in low:
            effective_offset = val
            break
    if effective_offset != 0:
        lyrics = [(max(0, t + effective_offset), txt) for t, txt in lyrics]
        lyrics.sort(key=lambda x: x[0])
        print(f"[Can chinh] {os.path.basename(audio_path)} OFFSET = {effective_offset:+.2f}s (clamp >=0)")

    # Khoi tao mixer 1 lan, tranh re-init loi
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[Loi] mixer init that bai: {e}")
            return
    try:
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"[Loi] Khong the phat {audio_path}: {e}")
        return

    print(f"{Fore.CYAN}Dang phat: {audio_path}")
    print(f"{Fore.CYAN}Loi tu: {lrc_path}\n")

    # Fix sync: lay moc audio clock ngay sau play, khong sleep 0.5s truoc start
    start_wall = time.time()

    def get_elapsed():
        # Uu tien audio clock tu pygame (khop loi hat), fallback wall clock
        try:
            pos = pygame.mixer.music.get_pos()
            if pos is not None and pos >= 0:
                return pos / 1000.0
        except Exception:
            pass
        return time.time() - start_wall

    idx = 0
    # Tim lyric hien tai dua tren elapsed (audio clock)
    try:
        while pygame.mixer.music.get_busy() or idx < len(lyrics):
            elapsed = get_elapsed()
            # Cap nhat idx: tang khi qua moc tiep theo
            while idx + 1 < len(lyrics) and elapsed >= lyrics[idx+1][0]:
                idx += 1
            # Truong hop chua toi lyric dau
            if idx == 0 and elapsed < lyrics[0][0]:
                # Hien waveform cho intro
                clear_screen()
                print(f"{Fore.YELLOW}♪ Đang phát: {os.path.basename(audio_path)} {Fore.WHITE}[{elapsed:05.2f}s]{Fore.WHITE}\n")
                # 3+9. Waveform realtime mo phong
                wf = render_waveform(elapsed, width=42)
                print(f"{Fore.CYAN}Waveform:{Fore.WHITE} {wf}")
                print(f"{Fore.WHITE}♪ Intro...{Style.RESET_ALL}\n")
                if len(lyrics) > 0:
                    print(f"  {Fore.WHITE}{lyrics[0][1]}")
                print(f"\n{Fore.CYAN}{'-'*40}")
                time.sleep(0.08)
                continue

            # Dam bao idx khong vuot qua
            if idx >= len(lyrics):
                if not pygame.mixer.music.get_busy():
                    break
                time.sleep(0.08)
                continue

            # Tinh progress cho hieu ung karaoke gradient 3.
            cur_t = lyrics[idx][0]
            next_t = lyrics[idx+1][0] if idx+1 < len(lyrics) else cur_t + 3.0
            # Neu elapsed chua toi cur_t (do offset), progress =0
            if elapsed < cur_t:
                progress = 0
            else:
                progress = (elapsed - cur_t) / (next_t - cur_t) if next_t > cur_t else 1
                progress = max(0, min(1, progress))

            # Render 1 frame
            clear_screen()
            print(f"{Fore.YELLOW}♪ Đang phát: {os.path.basename(audio_path)} {Fore.WHITE}[{elapsed:05.2f}s]{Fore.WHITE}\n")
            # 4+9. Waveform realtime phia tren lyrics - gradient + glow, chay lien tuc
            wf = render_waveform(elapsed, width=42)
            # Them glow nhe bang cach in them 1 dong mo
            print(f"{Fore.CYAN}Waveform:{Fore.WHITE} {wf}")
            # Glow them dong duoi mo hon
            wf2 = render_waveform(elapsed+0.3, width=42)
            print(f"         {Fore.WHITE}{Style.DIM}{wf2}{Style.RESET_ALL}\n")

            # Cau truoc -> tro lai trang thai binh thuong (trang mo)
            if idx > 0:
                print(f"  {Fore.WHITE}{Style.DIM}{lyrics[idx-1][1]}{Style.RESET_ALL}")

            # 3. Hieu ung karaoke gradient + glow cho cau hien tai
            # Mau chay trai sang phai theo progress, chuyen mau muot, co glow
            cur_line = lyrics[idx][1] if lyrics[idx][1].strip() else "♪ ♪ ♪"
            grad_text = karaoke_gradient_text(cur_line, progress)
            # Them glow: in them 1 dong duoi mo hon
            print(f"▶ {grad_text}")
            # Glow nhe quanh chu: in them dong duoi voi mau mo
            glow_line = "  " + "".join("·" if i < len(cur_line)*progress else " " for i in range(len(cur_line)))
            if HAS_COLORAMA:
                print(f"  {Fore.MAGENTA}{Style.DIM}{glow_line}{Style.RESET_ALL}")

            # Cau tiep theo mo
            if idx + 1 < len(lyrics):
                print(f"  {Fore.WHITE}{Style.DIM}{lyrics[idx+1][1]}{Style.RESET_ALL}")

            print(f"\n{Fore.CYAN}{'-'*40} {Fore.WHITE}progress {int(progress*100)}%{Fore.CYAN} - {'mo phong' if True else 'realtime FFT'}")
            # Giai thich: pygame.mixer khong expose raw audio nen dung mo phong sin+beat, neu co FFT that se thay the render_waveform bang phan tich that

            time.sleep(0.08)
            # Thoat khi het nhac va het loi
            if idx >= len(lyrics)-1 and elapsed > lyrics[-1][0] + 3 and not pygame.mixer.music.get_busy():
                break
    except KeyboardInterrupt:
        try:
            pygame.mixer.music.stop()
        except:
            pass
        print(f"\n{Fore.YELLOW}Đã dừng (Ctrl+C).")

    print(f"\n{Fore.GREEN}✓ Phát xong!")
    # Ghi chu mo phong vs realtime
    print(f"{Fore.CYAN}Note: Waveform hien tai la mo phong (sin+beat) vi pygame.mixer khong cho FFT realtime.")
    print(f"De co FFT that, thay render_waveform() bang phan tich numpy.fft tu audio buffer (can doc file wav truc tiep).{Style.RESET_ALL}")

def create_sample_lrc(path="sample.lrc"):
    """Tạo file LRC mẫu để test chế độ 1"""
    content = """[00:00.00]Happy birthday to you
[00:03.00]Happy birthday to you
[00:06.00]Happy birthday, happy birthday
[00:09.00]Happy birthday to you
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Đã tạo {path}")

# ================== CHẾ ĐỘ 2: Phát giai điệu tự tạo + lời (không cần file) ==================

def play_melody_with_lyrics(song_data, title="Demo"):
    """
    Phát giai điệu từ danh sách (note, duration_ms, lyric)
    Hiển thị lyric đúng nhịp nốt nhạc
    karaoke_player.py:207
    """
    clear_screen()
    print(f"{Fore.MAGENTA}{Style.BRIGHT}╔{'═'*40}╗")
    print(f"║ {title.center(38)} ║")
    print(f"╚{'═'*40}╝{Style.RESET_ALL}\n")

    # In toàn bộ lời mờ trước
    all_lyrics = " ".join([l for _, _, l in song_data if l])
    print(f"{Fore.WHITE}Lời: {all_lyrics}\n")
    print(f"{Fore.CYAN}Nhấn Ctrl+C để dừng\n")
    time.sleep(1)

    try:
        for i, (note, duration, lyric) in enumerate(song_data):
            freq = NOTES.get(note, 0)

            # Hiển thị
            # Xóa dòng cũ và in dòng mới với highlight karaoke
            lyric_display = lyric if lyric else "♪"
            progress = f"[{i+1}/{len(song_data)}]"

            if HAS_COLORAMA:
                print(f"{Fore.YELLOW}{progress} {Fore.WHITE}{Style.BRIGHT}▶ {lyric_display}{Style.RESET_ALL} {Fore.CYAN}({note} {freq}Hz - {duration}ms){Style.RESET_ALL}")
            else:
                print(f"{progress} ▶ {lyric_display} ({note} {duration}ms)")

            # Phát nốt nhạc (blocking đúng duration) - chay song song hieu ung
            play_tone(freq, duration)

        print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Hoàn thành bài: {title}!")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Đã dừng.")


# ================== MAIN ==================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Karaoke Player - Phat nhac + loi dong bo")
    parser.add_argument("--audio", help="Duong dan file nhac mp3/wav")
    parser.add_argument("--lrc", help="Duong dan file loi .lrc")
    parser.add_argument("--demo", choices=["birthday", "twinkle"], default="birthday", help="Chon demo giai dieu tu tao")
    parser.add_argument("--create-lrc", action="store_true", help="Tao file sample.lrc mau")
    parser.add_argument("--offset", type=float, default=None, help="Can chinh lech giay: + muon hon, - som hon. Vd --offset -0.5")
    args = parser.parse_args()
    # --offset uu tien cao nhat, override per-song
    if args.offset is not None:
        globals()["LRC_OFFSET"] = args.offset
        for k in list(globals().get("PER_SONG_OFFSET", {}).keys()):
            globals()["PER_SONG_OFFSET"][k] = args.offset

    if args.create_lrc:
        create_sample_lrc()

    # Nếu có audio + lrc -> chế độ 1
    elif args.audio and args.lrc:
        play_with_lrc(args.audio, args.lrc)

    # Nếu chỉ có audio mà không có lrc -> AI agent tu xu ly LRC roi phat
    elif args.audio and not args.lrc:
        # Tự đoán file lrc cùng tên: nhac.mp3 -> nhac.lrc
        guess_lrc = os.path.splitext(args.audio)[0] + ".lrc"
        if os.path.exists(guess_lrc):
            print(f"Tim thay LRC cung ten: {guess_lrc}")
            play_with_lrc(args.audio, guess_lrc)
        else:
            try:
                from lrc_agent import ensure_lrc
                guess_lrc, src = ensure_lrc(args.audio)
                print(f"[AI Agent] nguon LRC: {src} -> {guess_lrc}")
                if guess_lrc and os.path.exists(guess_lrc):
                    play_with_lrc(args.audio, guess_lrc)
                    # return de khong roi xuong branch phat khong loi ben duoi
                    import sys as _sys
                    _sys.exit(0)
                print("[AI Agent] khong co LRC that, phat nhac khong loi")
            except SystemExit:
                raise
            except Exception as e:
                print(f"[AI Agent loi] {e}")
            if not os.path.exists(args.audio):
                print(f"[Loi] Khong tim thay file nhac: {args.audio}")
            elif HAS_PYGAME:
                if not pygame.mixer.get_init():
                    try:
                        pygame.mixer.init()
                    except Exception as e:
                        print(f"[Loi] mixer init that bai: {e}")
                        sys.exit(1)
                try:
                    pygame.mixer.music.load(args.audio)
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"[Loi] Khong the phat {args.audio}: {e}")
                    sys.exit(1)
                print(f"Dang phat (khong loi): {args.audio}")
                print("De co loi dong bo, tao file .lrc cung ten hoac dung --lrc")
                try:
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    pygame.mixer.music.stop()
                    print("\nDa dung.")
                print("Phat xong!")
            else:
                print("Can pygame de phat mp3/wav: pip install pygame")
                print("Vi du file .lrc:")
                print("  [00:01.00] Dong loi 1")
                print("  [00:05.50] Dong loi 2")
                print("Dung --create-lrc de tao file mau")

    # Mặc định: Menu lua chon bai hat - VONG LAP de nghe bai khac
    else:
        # Tim tat ca bai hat co san
        def get_available_songs():
            songs=[]
            for pat in ["assets/music/*.mp3","assets/music/*.wav","assets/music/*.ogg","assets/music/*.m4a","*.mp3","*.wav"]:
                songs.extend(_glob.glob(pat))
            # Loai trung va sap xep
            songs = sorted(set(songs))
            return songs

        # Vong lap chinh de chon va nghe lien tuc
        while True:
            songs = get_available_songs()
            has_songs = len(songs) > 0

            # Neu co nhieu bai -> hien menu
            if has_songs:
                print(f"\n{Fore.CYAN}{Style.BRIGHT}=== LUA CHON BAI HAT (vong lap) ==={Style.RESET_ALL}")
                for i, s in enumerate(songs, 1):
                    base = os.path.basename(s)
                    has_lrc = os.path.exists(os.path.splitext(s)[0]+".lrc")
                    tag = f"{Fore.GREEN}co loi{Fore.WHITE}" if has_lrc else f"{Fore.YELLOW}khong loi{Fore.WHITE}"
                    print(f"  {Fore.YELLOW}{i}.{Fore.WHITE} {base} [{tag}]")
                print(f"  {Fore.MAGENTA}{len(songs)+1}. Happy Birthday (demo Beep){Fore.WHITE}")
                print(f"  {Fore.MAGENTA}{len(songs)+2}. Twinkle Twinkle (demo Beep){Fore.WHITE}")
                print(f"  {Fore.CYAN}{len(songs)+3}. Phat tat ca (playlist loop){Fore.WHITE}")
                print(f"  {Fore.CYAN}0. Thoat{Fore.WHITE}")
                try:
                    choice = input(f"\n{Fore.CYAN}Nhap so (1-{len(songs)+3}, 0 thoat): {Style.RESET_ALL}").strip()
                    if not choice.isdigit():
                        print("Thoat.")
                        break
                    choice = int(choice)
                except (KeyboardInterrupt, EOFError):
                    print("\nThoat.")
                    break

                if choice == 0:
                    print("Tam biet!")
                    break
                elif 1 <= choice <= len(songs):
                    sel = songs[choice-1]
                    guess = os.path.splitext(sel)[0]+".lrc"
                    if os.path.exists(guess):
                        play_with_lrc(sel, guess)
                    else:
                        if HAS_PYGAME:
                            if not pygame.mixer.get_init():
                                try:
                                    pygame.mixer.init()
                                except Exception as e:
                                    print(f"[Loi] mixer init that bai: {e}")
                                    continue
                            try:
                                pygame.mixer.music.load(sel)
                                pygame.mixer.music.play()
                            except Exception as e:
                                print(f"[Loi] Khong the phat {sel}: {e}")
                                continue
                            print(f"Dang phat (khong loi): {sel}")
                            print(f"Tao file {guess} de co loi dong bo")
                            try:
                                while pygame.mixer.music.get_busy():
                                    time.sleep(0.1)
                            except KeyboardInterrupt:
                                pygame.mixer.music.stop()
                                print("\nDa dung.")
                            print("Phat xong!")
                        else:
                            print("Can pygame de phat mp3/wav: pip install pygame")
                elif choice == len(songs)+1:
                    play_melody_with_lyrics(DEMO_SONG, title="Happy Birthday - Demo Karaoke")
                elif choice == len(songs)+2:
                    play_melody_with_lyrics(DEMO_TWINKLE, title="Lap Lanh Sao - Twinkle Twinkle")
                elif choice == len(songs)+3:
                    print(f"{Fore.CYAN}Phat playlist loop {len(songs)} bai... Ctrl+C de dung{Fore.WHITE}")
                    try:
                        while True:
                            for s in songs:
                                guess = os.path.splitext(s)[0]+".lrc"
                                if os.path.exists(guess):
                                    play_with_lrc(s, guess)
                                else:
                                    if HAS_PYGAME:
                                        if not pygame.mixer.get_init():
                                            pygame.mixer.init()
                                        pygame.mixer.music.load(s)
                                        pygame.mixer.music.play()
                                        while pygame.mixer.music.get_busy():
                                            time.sleep(0.1)
                                time.sleep(0.5)
                    except KeyboardInterrupt:
                        if HAS_PYGAME and pygame.mixer.get_init():
                            pygame.mixer.music.stop()
                        print(f"\n{Fore.YELLOW}Da dung playlist.")
                else:
                    print("Lua chon khong hop le.")
                # Sau khi phat 1 bai, quay lai menu
                print(f"{Fore.CYAN}--- Quay lai menu chon bai khac ---\n{Fore.WHITE}")
            else:
                # Khong co file nhac nao -> chay demo roi thoat loop
                if not HAS_WINSOUND and not HAS_PYGAME:
                    print("Canh bao: Khong co winsound/pygame, chi chay gia lap (sleep) + hien thi loi")
                    print("Cai pygame de co am thanh: pip install pygame\n")
                if args.demo == "twinkle":
                    play_melody_with_lyrics(DEMO_TWINKLE, title="Lap Lanh Sao - Twinkle Twinkle")
                else:
                    play_melody_with_lyrics(DEMO_SONG, title="Happy Birthday - Demo Karaoke")
                break

    # Hướng dẫn sử dụng in cuối
    if not args.audio:
        print(f"""
{Fore.CYAN}Cách dùng:
  1. Demo không cần file (mặc định):
     python karaoke_player.py
     python karaoke_player.py --demo twinkle

  2. Phát file thật + LRC:
     python karaoke_player.py --audio nhac.mp3 --lrc loi.lrc
     # Tạo LRC mẫu: python karaoke_player.py --create-lrc
""")
