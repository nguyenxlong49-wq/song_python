#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KARAOKE PLAYER GUI - PySide6. Chay: python main.py"""
import glob
import os
import sys
import urllib.parse
import urllib.request

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

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
QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,40); border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; background: #50dcff; }
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

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.slider.sliderReleased.connect(self._do_seek)
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
        self.b_play = QPushButton("▶")
        self.b_stop = QPushButton("⏹")
        self.b_next = QPushButton("⏭")
        self.b_prev.clicked.connect(self.prev_song)
        self.b_play.clicked.connect(self.toggle)
        self.b_stop.clicked.connect(self.stop_song)
        self.b_next.clicked.connect(self.next_song)
        btn_row.addWidget(self.b_prev)
        btn_row.addWidget(self.b_play)
        btn_row.addWidget(self.b_stop)
        btn_row.addWidget(self.b_next)
        lay.addLayout(btn_row)

        ctl_row = QHBoxLayout()
        self.offset_box = QSpinBox()
        self.offset_box.setRange(-100, 100)
        self.offset_box.setSingleStep(1)
        self.offset_box.setPrefix("offset ds: ")
        self.offset_box.valueChanged.connect(self._offset_changed)
        self.b_file = QPushButton("Mo file LRC")
        self.b_file.clicked.connect(self.choose_lrc)
        self.b_fetch = QPushButton("Lay LRC (LRCLIB)")
        self.b_fetch.clicked.connect(self.fetch_current)
        ctl_row.addWidget(self.offset_box)
        ctl_row.addWidget(self.b_file)
        ctl_row.addWidget(self.b_fetch)
        lay.addLayout(ctl_row)

        self.songs = QListWidget()
        self.songs.itemDoubleClicked.connect(lambda _i: self.load_selected())
        lay.addWidget(self.songs, 1)
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

    def load_selected(self):
        path = self.current_path()
        if not path:
            return
        lrc = os.path.splitext(path)[0] + ".lrc"
        self.load_song(path, lrc if os.path.exists(lrc) else "")

    def load_song(self, audio, lrc):
        try:
            self.player.stop()
            self.player.load(audio)
        except Exception as e:
            print(f"[Loi load] {e}")
            QMessageBox.warning(self, "Loi", f"Khong mo duoc:\n{audio}\n{e}")
            return
        print(f"[Load] audio={audio}")
        self.lyrics = []
        if lrc and os.path.exists(lrc):
            try:
                raw = parse_lrc(lrc)
                self.lyrics = apply_offset(raw, self.offset)
                print(f"[Load] lrc={lrc} lines={len(self.lyrics)} offset={self.offset:+.1f}s")
            except Exception as e:
                print(f"[Loi LRC] {e}")
        else:
            print("[LRC] khong co file local, co the dung 'Lay LRC (LRCLIB)'")
        self.lyrics_view.set_lyrics(self.lyrics)
        self.lyrics_view.set_position(0.0)
        self.slider.setValue(0)
        self.song_label.setText(os.path.basename(audio))
        self.player.play()
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

    def prev_song(self):
        if not self._paths:
            return
        r = (self.songs.currentRow() - 1) % len(self._paths)
        self.songs.setCurrentRow(r)
        self.load_selected()

    def next_song(self):
        if not self._paths:
            return
        r = (self.songs.currentRow() + 1) % len(self._paths)
        self.songs.setCurrentRow(r)
        self.load_selected()

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

    def _do_seek(self):
        self._seeking = False
        dur = self.player.get_duration()
        if dur > 0:
            sec = self.slider.value() / 1000.0 * dur
            self.player.seek(sec)
            # Cap nhat lyrics + progress ngay lap tuc
            self.update_player(force=True)

    def update_player(self, force=False):
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
