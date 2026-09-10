#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KARAOKE PLAYER GUI - PySide6. Chay: python main.py"""
import glob
import os
import sys
import urllib.parse
import urllib.request

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)


class SttWorker(QThread):
    progress = Signal(float, str)
    done = Signal(str)
    error = Signal(str)

    def __init__(self, audio, model="tiny"):
        super().__init__()
        self.audio = audio
        self.model = model

    def run(self):
        try:
            import stt_lrc
            def cb(frac, text):
                self.progress.emit(float(frac), text)
            lrc_text = stt_lrc.transcribe_to_lrc(self.audio, model=self.model, progress_cb=cb)
            out = stt_lrc.save_lrc(self.audio, lrc_text)
            self.done.emit(out)
        except Exception as e:
            self.error.emit(str(e))


class SeekSlider(QSlider):
    """Slider kieu YouTube: bam chuot vao bat ky dau de tua ngay."""
    clicked_seek = Signal(int)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / max(1, self.width())
            self.setValue(int(val))
            self.clicked_seek.emit(int(val))
            event.accept()
            return
        super().mousePressEvent(event)

from lrc_parser import apply_offset, parse_lrc
from lyrics_widget import LyricsWidget
from music_player import MusicPlayer
from visualizer import AudioVisualizer

APP_STYLE = """
QMainWindow { background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #0b1020, stop:1 #141b34); }
QWidget { color: #e6eaf5; font-family: 'Segoe UI'; font-size: 13px; }
QLabel#Title { font-size: 22px; font-weight: 800; color: #ffffff; }
QLabel#Song { font-size: 14px; font-weight: 600; color: #9be7ff; }
QListWidget { background: rgba(255,255,255,14); border: 1px solid rgba(120,180,255,60); border-radius: 12px; padding: 6px; }
QPushButton { background: rgba(90,140,255,40); border: 1px solid rgba(120,180,255,80); border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { background: rgba(90,140,255,80); }
QSlider::groove:horizontal { height: 8px; background: rgba(255,255,255,35); border-radius: 4px; }
QSlider::sub-page:horizontal { height: 8px; background: #2196F3; border-radius: 4px; }
QSlider::add-page:horizontal { height: 8px; background: rgba(255,255,255,35); border-radius: 4px; }
QSlider::handle:horizontal { width: 16px; margin: -5px 0; border-radius: 8px; background: #fff; border: 2px solid #2196F3; }
QSlider::handle:horizontal:hover { background: #2196F3; }
"""


def scan_songs():
    songs = []
    for pat in ("assets/music/*.mp3", "assets/music/*.wav", "assets/music/*.ogg", "*.mp3", "*.wav"):
        songs.extend(glob.glob(pat))
    return sorted(set(songs))


def fetch_lrclib(track, artist, duration=0):
    """Lay syncedLyrics tu LRCLIB, tra ve chuoi LRC hoac ''. Khong hard-code lyrics."""
    try:
        qs = {"track_name": track, "artist_name": artist}
        if duration:
            qs["duration"] = str(int(duration))
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(qs)
        req = urllib.request.Request(url, headers={"User-Agent": "song_python-gui/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            return data.get("syncedLyrics") or ""
    except Exception as e:
        print(f"[LRCLIB loi] {e}")
        return ""


def fmt(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KARAOKE PLAYER")
        self.resize(560, 760)
        self.player = MusicPlayer()
        self.lyrics = []
        self.offset = 0.0
        self._seeking = False

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)

        title = QLabel("KARAOKE PLAYER")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        self.art = QLabel("[ ALBUM ART ]")
        self.art.setAlignment(Qt.AlignCenter)
        self.art.setMinimumHeight(86)
        self.art.setStyleSheet("background: rgba(255,255,255,16); border-radius: 14px; color:#8b93b0; font-weight:700;")
        lay.addWidget(self.art)

        self.song_label = QLabel("Chua chon bai")
        self.song_label.setObjectName("Song")
        self.song_label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.song_label)

        self.visual = AudioVisualizer(bars=48)
        lay.addWidget(self.visual)

        self.lyrics_view = LyricsWidget()
        lay.addWidget(self.lyrics_view)

        self.slider = SeekSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.slider.sliderReleased.connect(self._do_seek)
        self.slider.clicked_seek.connect(self._click_seek)
        lay.addWidget(self.slider)

        time_row = QHBoxLayout()
        self.t_cur = QLabel("00:00")
        self.t_end = QLabel("00:00")
        self.t_end.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_row.addWidget(self.t_cur)
        time_row.addWidget(self.t_end)
        lay.addLayout(time_row)

        btn_row = QHBoxLayout()
        self.b_prev = QPushButton("⏮")
        self.b_rw = QPushButton("⏪ 10s")
        self.b_play = QPushButton("▶")
        self.b_stop = QPushButton("⏹")
        self.b_ff = QPushButton("10s ⏩")
        self.b_next = QPushButton("⏭")
        self.b_prev.clicked.connect(self.prev_song)
        self.b_rw.clicked.connect(lambda: self.seek_relative(-10))
        self.b_play.clicked.connect(self.toggle)
        self.b_stop.clicked.connect(self.stop_song)
        self.b_ff.clicked.connect(lambda: self.seek_relative(10))
        self.b_next.clicked.connect(self.next_song)
        btn_row.addWidget(self.b_prev)
        btn_row.addWidget(self.b_rw)
        btn_row.addWidget(self.b_play)
        btn_row.addWidget(self.b_stop)
        btn_row.addWidget(self.b_ff)
        btn_row.addWidget(self.b_next)
        lay.addLayout(btn_row)

        ctl_row = QHBoxLayout()
        self.offset_box = QSpinBox()
        self.offset_box.setRange(-100, 100)
        self.offset_box.setSingleStep(1)
        self.offset_box.setPrefix("offset ds: ")
        self.offset_box.valueChanged.connect(self._offset_changed)
        self.b_audio = QPushButton("Mo nhac MP3")
        self.b_audio.clicked.connect(self.choose_audio)
        self.b_file = QPushButton("Mo file LRC")
        self.b_file.clicked.connect(self.choose_lrc)
        self.b_fetch = QPushButton("Lay LRC (LRCLIB)")
        self.b_fetch.clicked.connect(self.fetch_current)
        self.b_paste = QPushButton("Dan loi -> Agent")
        self.b_paste.clicked.connect(self.paste_lyrics_agent)
        self.b_stt = QPushButton("STT -> LRC")
        self.b_stt.clicked.connect(self.stt_current)
        self.stt_model = QComboBox()
        self.stt_model.addItems(["tiny", "base", "small"])
        ctl_row.addWidget(self.offset_box)
        ctl_row.addWidget(self.b_audio)
        ctl_row.addWidget(self.b_file)
        ctl_row.addWidget(self.b_fetch)
        ctl_row.addWidget(self.b_paste)
        ctl_row.addWidget(self.b_stt)
        ctl_row.addWidget(self.stt_model)
        lay.addLayout(ctl_row)

        self.songs = QListWidget()
        self.songs.itemDoubleClicked.connect(lambda _i: self.load_selected())
        # Click trai 1 cai la phat ngay (fix click chon bai)
        self.songs.itemClicked.connect(lambda _i: self.load_selected())
        self.songs.itemSelectionChanged.connect(self._preview_select)
        # Chi chuot phai moi mo bang nho Phat/Xoa
        self.songs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.songs.customContextMenuRequested.connect(self._song_menu_at)
        lay.addWidget(self.songs, 1)

        # Volume kieu YouTube
        vol_row = QHBoxLayout()
        self.b_mute = QPushButton("🔊")
        self.b_mute.setFixedWidth(48)
        self.b_mute.setToolTip("Click: thanh volume nho | Double-click/M: mute")
        self.b_mute.clicked.connect(self._toggle_vol_popup)
        self.b_mute.installEventFilter(self)
        from PySide6.QtWidgets import QSlider as _QS, QFrame as _QFrame, QVBoxLayout as _QVL
        # Popup thanh doc nho hien khi click icon (kieu YouTube)
        self.vol_popup = _QFrame(self, Qt.Popup)
        self.vol_popup.setStyleSheet("QFrame{background:#1a2138;border:1px solid rgba(120,180,255,90);border-radius:10px;}")
        _pvl = _QVL(self.vol_popup)
        _pvl.setContentsMargins(8, 8, 8, 8)
        self.vol = _QS(Qt.Vertical)
        self.vol.setRange(0, 100)
        self.vol.setValue(80)
        self.vol.setMinimumHeight(120)
        self.vol.valueChanged.connect(self._vol_changed)
        _pvl.addWidget(self.vol)
        vol_row.addWidget(self.b_mute)
        vol_row.addStretch(1)
        lay.addLayout(vol_row)
        self._muted = False
        self._vol_before_mute = 80
        try:
            import pygame as _pg
            if _pg.mixer.get_init():
                _pg.mixer.music.set_volume(0.8)
        except Exception:
            pass
        self.refresh_list()

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.update_player)
        self.tick.start(40)
        self.setStyleSheet(APP_STYLE)

    def refresh_list(self):
        self.songs.clear()
        self._paths = scan_songs()
        for p in self._paths:
            base = os.path.basename(p)
            has = os.path.exists(os.path.splitext(p)[0] + ".lrc")
            self.songs.addItem(f"{base} {'[co loi]' if has else '[khong loi]'}")
        if self._paths:
            self.songs.setCurrentRow(0)

    def current_path(self):
        row = self.songs.currentRow()
        if 0 <= row < len(self._paths):
            return self._paths[row]
        return self._paths[0] if self._paths else ""

    def _song_popup(self, item):
        # Click trai vao bai -> bang nho ngay con tro
        from PySide6.QtGui import QCursor
        self._song_menu_at(QCursor.pos(), global_pos=True)

    def _song_menu_at(self, pos, global_pos=False):
        from PySide6.QtWidgets import QMenu
        path = self.current_path()
        if not path:
            return
        menu = QMenu(self)
        act_play = menu.addAction("▶ Phat bai nay")
        act_del = menu.addAction("Xoa bai hat")
        if global_pos:
            action = menu.exec(pos)
        else:
            action = menu.exec(self.songs.mapToGlobal(pos))
        if action == act_play:
            self.load_selected()
        elif action == act_del:
            self.delete_selected()

    def delete_selected(self):
        from PySide6.QtWidgets import QMessageBox
        path = self.current_path()
        if not path:
            return
        base = os.path.basename(path)
        lrc = os.path.splitext(path)[0] + ".lrc"
        ret = QMessageBox.question(self, "Xoa bai", f"Xoa khoi he thong?\n{base}\n(Kem file .lrc cung ten neu co)")
        if ret != QMessageBox.Yes:
            return
        # Neu dang phat bai nay thi dung truoc
        if self.player.audio_path and os.path.abspath(self.player.audio_path) == os.path.abspath(path):
            self.player.stop()
            self.lyrics = []
            self.lyrics_view.set_lyrics([])
            self.b_play.setText("▶")
            self.song_label.setText("Chua chon bai")
        try:
            os.remove(path)
            print(f"[System] da xoa nhac: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Xoa", f"Khong xoa duoc:\n{e}")
            return
        if os.path.exists(lrc):
            try:
                os.remove(lrc)
                print(f"[System] da xoa loi: {lrc}")
            except Exception as e:
                print(f"[System] khong xoa duoc lrc: {e}")
        self.refresh_list()

    def load_selected(self):
        path = self.current_path()
        if not path:
            return
        lrc = os.path.splitext(path)[0] + ".lrc"
        if os.path.exists(lrc):
            self.load_song(path, lrc)
        else:
            # Click bai chua co LRC -> AI agent tu tao roi phat (giu selection)
            try:
                from lrc_agent import ensure_lrc
                guess, src = ensure_lrc(path)
                print(f"[Auto LRC] {src} -> {guess}")
                self.load_song(path, guess if guess and os.path.exists(guess) else "")
            except Exception as e:
                print(f"[Auto LRC loi] {e}")
                self.load_song(path, "")

    def _preview_select(self):
        # Hien ten bai dang chon ngay ca khi chua phat
        p = self.current_path()
        if p and not self.player.audio_path:
            self.song_label.setText(os.path.basename(p) + " (chon de phat)")

    def _default_offset(self, audio):
        low = audio.lower()
        if "love-me-again" in low:
            return -3.0
        return 0.0

    def load_song(self, audio, lrc):
        try:
            self.player.stop()
            self.player.load(audio)
        except Exception as e:
            print(f"[Loi load] {e}")
            QMessageBox.warning(self, "Loi", f"Khong mo duoc:\n{audio}\n{e}")
            return
        # Tu dong gan offset rieng tung bai (love cham ~2s)
        self.offset = self._default_offset(audio)
        try:
            self.offset_box.blockSignals(True)
            self.offset_box.setValue(int(round(self.offset * 10)))
            self.offset_box.blockSignals(False)
        except Exception:
            pass
        print(f"[Load] audio={audio}")
        self.lyrics = []
        if lrc and os.path.exists(lrc):
            try:
                raw = parse_lrc(lrc)
                print(f"[LRC] raw lines={len(raw)} first={raw[0] if raw else 'EMPTY'}")
                self.lyrics = apply_offset(raw, self.offset)
                print(f"[Load] lrc={lrc} lines={len(self.lyrics)} offset={self.offset:+.1f}s")
                if not self.lyrics:
                    QMessageBox.warning(self, "LRC", f"File LRC rong/khong parse duoc:\n{lrc}")
            except Exception as e:
                print(f"[Loi LRC] {e}")
                QMessageBox.warning(self, "LRC", f"Loi doc LRC:\n{e}")
        else:
            print(f"[LRC] khong thay file: {lrc}, co the dung 'Lay LRC (LRCLIB)'")
            QMessageBox.information(self, "LRC", f"Khong thay file loi:\n{lrc}\nChon 'Mo file LRC' hoac 'Lay LRC (LRCLIB)'.")
        self.lyrics_view.set_lyrics(self.lyrics)
        self.lyrics_view.set_position(0.0)
        self.slider.setValue(0)
        self.song_label.setText(os.path.basename(audio))
        self.player.play()
        try:
            import pygame as _pg
            if _pg.mixer.get_init():
                _pg.mixer.music.set_volume(self.vol.value() / 100.0)
        except Exception:
            pass
        self.b_play.setText("⏸")

    def toggle(self):
        # Dung is_paused rieng vi get_busy() van True khi pause
        if self.player.is_paused():
            self.player.resume()
            self.b_play.setText("⏸")
            return
        if self.player.is_playing():
            self.player.pause()
            self.b_play.setText("▶")
            return
        # Neu chua load gi thi load bai dang chon
        if not self.player.audio_path:
            self.load_selected()
            return
        # Da stop -> play lai tu dau
        self.player.play()
        self.b_play.setText("⏸")

    def stop_song(self):
        self.player.stop()
        self.lyrics_view.set_position(0.0)
        self.slider.setValue(0)
        self.t_cur.setText("00:00")
        self.b_play.setText("▶")
        print("[Stop] da dung")

    def _goto(self, r):
        # Chuyen bai an toan: chan index, giu selection, log ro
        if not getattr(self, "_paths", None):
            print("[Next/Prev] chua co danh sach nhac")
            return
        n = len(self._paths)
        r = r % n
        try:
            self.songs.blockSignals(True)
            self.songs.setCurrentRow(r)
            self.songs.blockSignals(False)
        except Exception:
            pass
        try:
            print(f"[Next/Prev] -> [{r+1}/{n}] {os.path.basename(self._paths[r])}")
            self.load_selected()
        except Exception as e:
            print(f"[Next/Prev loi] {e}")
            QMessageBox.warning(self, "Next/Prev", str(e))

    def prev_song(self):
        if not getattr(self, "_paths", None):
            return
        cur = self.songs.currentRow()
        if cur < 0:
            cur = 0
        self._goto(cur - 1)

    def next_song(self):
        if not getattr(self, "_paths", None):
            return
        cur = self.songs.currentRow()
        if cur < 0:
            cur = -1
        self._goto(cur + 1)

    def _offset_changed(self, v):
        # QSpinBox ds (deci-giay) de chinh 0.1s
        self.offset = v / 10.0
        # Apply lai offset cho lyrics hien tai neu co goc
        path = self.player.audio_path
        if path:
            lrc = os.path.splitext(path)[0] + ".lrc"
            if os.path.exists(lrc):
                self.lyrics = apply_offset(parse_lrc(lrc), self.offset)
                self.lyrics_view.set_lyrics(self.lyrics)

    def choose_audio(self):
        # Chon mp3 -> luu vao assets/music -> AI agent tu xu ly LRC
        import shutil
        from lrc_agent import ensure_lrc
        f, _x = QFileDialog.getOpenFileName(self, "Chon file nhac", "", "Audio (*.mp3 *.wav *.ogg *.m4a)")
        if not f:
            return
        # Luu nhac vao he thong assets/music
        music_dir = "assets/music"
        os.makedirs(music_dir, exist_ok=True)
        dest = os.path.join(music_dir, os.path.basename(f))
        try:
            # Chi copy neu khac file (tranh ghi de chinh no)
            if os.path.abspath(f) != os.path.abspath(dest):
                shutil.copy2(f, dest)
                print(f"[System] da luu nhac: {dest}")
            # Copy kem .lrc cung ten neu co
            src_lrc = os.path.splitext(f)[0] + ".lrc"
            dest_lrc = os.path.splitext(dest)[0] + ".lrc"
            if os.path.exists(src_lrc) and os.path.abspath(src_lrc) != os.path.abspath(dest_lrc):
                shutil.copy2(src_lrc, dest_lrc)
                print(f"[System] da luu loi kem: {dest_lrc}")
        except Exception as e:
            QMessageBox.warning(self, "Luu nhac", f"Khong luu duoc vao {dest}:\n{e}")
            dest = f
        guess, src = ensure_lrc(dest)
        if src == "local":
            print(f"[Auto LRC] tim thay: {guess}")
        elif src == "lrclib":
            QMessageBox.information(self, "AI Agent", f"Da lay loi tu LRCLIB:\n{guess}")
        elif src == "none":
            QMessageBox.information(self, "AI Agent", "Khong tim thay LRC that.\nDung 'Dan loi -> Agent' hoac 'Lay LRC (LRCLIB)'.")
        self.load_song(dest, guess if guess and os.path.exists(guess) else "")
        self.refresh_list()

    def paste_lyrics_agent(self):
        # Dan loi tho -> agent rai timestamp theo duration
        from PySide6.QtWidgets import QInputDialog
        from lrc_agent import distribute_plain
        if not self.player.audio_path:
            QMessageBox.warning(self, "Agent", "Chon bai hat truoc.")
            return
        text, ok = QInputDialog.getMultiLineText(self, "AI Agent", "Dan loi tho (moi dong 1 cau):")
        if not ok or not text.strip():
            return
        dur = self.player.get_duration() or 180.0
        lrc_text = distribute_plain(text, dur)
        out = os.path.splitext(self.player.audio_path)[0] + ".lrc"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(lrc_text)
        self.lyrics = apply_offset(parse_lrc(out), self.offset)
        self.lyrics_view.set_lyrics(self.lyrics)
        print(f"[Agent] da rai loi tho: {out}")

    def stt_current(self):
        # STT bai dang phat/chon -> LRC tu dong can gio
        import stt_lrc
        if not stt_lrc.backend():
            QMessageBox.warning(self, "STT", "Chua cai STT.\nChay:\npip install faster-whisper")
            return
        path = self.player.audio_path or self.current_path()
        if not path:
            return
        model = self.stt_model.currentText() if hasattr(self, "stt_model") else "tiny"
        self.b_stt.setEnabled(False)
        self.song_label.setText(f"Dang STT ({model}): {os.path.basename(path)}...")
        self._stt = SttWorker(path, model)
        self._stt.progress.connect(lambda frac, txt: self.song_label.setText(f"STT {int(frac*100)}%: {txt[:40]}"))
        def _done(out):
            self.b_stt.setEnabled(True)
            try:
                self.lyrics = apply_offset(parse_lrc(out), self.offset)
                self.lyrics_view.set_lyrics(self.lyrics)
                self.refresh_list()
                QMessageBox.information(self, "STT", f"Da tao LRC tu audio:\n{out}\nMo lai bai de nghe + sua offset neu can.")
                print(f"[STT] xong: {out}")
            except Exception as e:
                QMessageBox.warning(self, "STT", str(e))
        def _err(msg):
            self.b_stt.setEnabled(True)
            QMessageBox.warning(self, "STT", f"Loi STT:\n{msg}")
        self._stt.done.connect(_done)
        self._stt.error.connect(_err)
        self._stt.start()

    def choose_lrc(self):
        f, _x = QFileDialog.getOpenFileName(self, "Chon file LRC", "assets/music", "LRC (*.lrc)")
        if f:
            try:
                self.lyrics = apply_offset(parse_lrc(f), self.offset)
                self.lyrics_view.set_lyrics(self.lyrics)
                print(f"[Load] lrc thu cong: {f}")
            except Exception as e:
                QMessageBox.warning(self, "Loi", str(e))

    def fetch_current(self):
        path = self.player.audio_path or self.current_path()
        if not path:
            return
        base = os.path.splitext(os.path.basename(path))[0]
        # Doan "Artist - Title" neu co, nguoc lai dung base lam track
        if " - " in base:
            artist, track = base.split(" - ", 1)
        else:
            artist, track = "", base
        dur = self.player.get_duration()
        lrc_text = fetch_lrclib(track.strip(), artist.strip(), dur)
        if not lrc_text:
            QMessageBox.information(self, "LRCLIB", "API khong tra lyrics. Hay chon file .lrc local.")
            return
        out = os.path.splitext(path)[0] + ".lrc"
        with open(out, "w", encoding="utf-8") as f:
            f.write(lrc_text)
        self.lyrics = apply_offset(parse_lrc(out), self.offset)
        self.lyrics_view.set_lyrics(self.lyrics)
        self.refresh_list()
        print(f"[LRCLIB] da luu {out}")

    def _apply_seek(self, sec):
        # Ham chung: tua + khoa update 0.6s de audio kip bat kip, tranh reset
        import time as _time
        dur = self.player.get_duration()
        if dur <= 0 or not self.player.audio_path:
            return
        sec = max(0.0, min(dur - 0.2, float(sec)))
        self._seeking = False
        self._last_seek_t = _time.time()
        self._last_seek_sec = sec
        self.player.seek(sec)
        # Hien ngay loi + thanh xanh tai vi tri moi, khong doi audio
        self.lyrics_view.set_position(sec)
        self.slider.blockSignals(True)
        self.slider.setValue(int(sec / dur * 1000))
        self.slider.blockSignals(False)
        self.t_cur.setText(fmt(sec))
        self.visual.set_state(sec, True)

    def _do_seek(self):
        import time as _time
        # Bo qua neu vua click-seek (<0.6s) de tranh seek kep gay reset
        if _time.time() - getattr(self, "_last_seek_t", 0) < 0.6:
            self._seeking = False
            return
        self._seeking = False
        dur = self.player.get_duration()
        if dur > 0:
            sec = self.slider.value() / 1000.0 * dur
            self._apply_seek(sec)

    def _click_seek(self, value):
        # Bam chuot vao thanh -> tua ngay kieu YouTube
        dur = self.player.get_duration()
        if dur > 0 and self.player.audio_path:
            sec = value / 1000.0 * dur
            self._apply_seek(sec)

    def seek_relative(self, delta):
        # Tua +-giay
        if not self.player.audio_path:
            return
        pos = self.player.get_position()
        dur = self.player.get_duration()
        new = max(0.0, pos + delta)
        if dur > 0:
            new = min(dur - 0.5, new)
        self.player.seek(new)
        self.update_player(force=True)
        print(f"[Seek] {pos:.1f}s -> {new:.1f}s")

    def _vol_changed(self, v):
        # Keo thanh volume kieu YouTube
        self._muted = (v == 0)
        self.b_mute.setText("🔇" if self._muted else "🔊")
        try:
            import pygame as _pg
            if _pg.mixer.get_init():
                _pg.mixer.music.set_volume(v / 100.0)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is getattr(self, "b_mute", None) and event.type() == QEvent.MouseButtonDblClick:
            self.toggle_mute()
            return True
        return super().eventFilter(obj, event)

    def _toggle_vol_popup(self):
        # Click icon loa -> hien thanh doc nho ngay tren nut
        if self.vol_popup.isVisible():
            self.vol_popup.hide()
            return
        pos = self.b_mute.mapToGlobal(self.b_mute.rect().topLeft())
        self.vol_popup.setGeometry(pos.x() - 6, pos.y() - 160, 52, 150)
        self.vol_popup.show()

    def toggle_mute(self):
        if getattr(self, "_muted", False):
            self.vol.setValue(getattr(self, "_vol_before_mute", 80) or 80)
        else:
            self._vol_before_mute = self.vol.value() or 80
            self.vol.setValue(0)

    def volume_step(self, delta):
        self.vol.setValue(max(0, min(100, self.vol.value() + delta)))

    def keyPressEvent(self, event):
        # Space: play/pause, <-/->: tua 5s, J/L: tua 10s, Up/Down volume, M mute (YouTube)
        k = event.key()
        if k == Qt.Key_Space:
            self.toggle()
        elif k == Qt.Key_Right:
            self.seek_relative(5)
        elif k == Qt.Key_Left:
            self.seek_relative(-5)
        elif k == Qt.Key_L:
            self.seek_relative(10)
        elif k == Qt.Key_J:
            self.seek_relative(-10)
        elif k == Qt.Key_Up:
            self.volume_step(5)
        elif k == Qt.Key_Down:
            self.volume_step(-5)
        elif k == Qt.Key_M:
            self.toggle_mute()
        else:
            super().keyPressEvent(event)

    def update_player(self, force=False):
        import time as _time
        # Khoa 0.6s sau seek: giu thanh xanh + loi o vi tri moi, khong de get_pos cu reset
        if _time.time() - getattr(self, "_last_seek_t", 0) < 0.6 and not force:
            sec = getattr(self, "_last_seek_sec", 0.0)
            self.visual.set_state(sec, True)
            return
        pos = self.player.get_position()
        playing = self.player.is_playing()
        dur = self.player.get_duration()
        self.visual.set_state(pos, playing)
        self.lyrics_view.set_position(pos)
        if not self._seeking and dur > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(int(pos / dur * 1000))
            self.slider.blockSignals(False)
        self.t_cur.setText(fmt(pos))
        self.t_end.setText(fmt(dur))


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
