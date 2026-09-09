#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LyricsWidget: hien 3 dong, highlight dong hien tai, karaoke fill trai->phai."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from lrc_parser import estimate_progress, find_index


class LyricsWidget(QWidget):
    """Khong tao lai widget moi frame, chi ve lai text can thiet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lyrics = []
        self.position = 0.0
        self.idx = -1
        self.progress = 0.0
        self.setMinimumHeight(170)

    def set_lyrics(self, lyrics):
        self.lyrics = list(lyrics)
        self.position = 0.0
        self.idx = -1
        self.progress = 0.0
        self.update()

    def set_position(self, elapsed):
        self.position = float(elapsed)
        if not self.lyrics:
            return
        new_idx = find_index(self.lyrics, self.position)
        new_prog = estimate_progress(self.lyrics, new_idx, self.position)
        self.idx = new_idx
        self.progress = new_prog
        self.update()

    def _rainbow_gradient(self, x, width):
        grad = QLinearGradient(x, 0, x + max(1.0, width), 0)
        grad.setColorAt(0.0, QColor(255, 90, 90))
        grad.setColorAt(0.17, QColor(255, 210, 90))
        grad.setColorAt(0.34, QColor(110, 255, 150))
        grad.setColorAt(0.51, QColor(80, 220, 255))
        grad.setColorAt(0.68, QColor(110, 140, 255))
        grad.setColorAt(0.85, QColor(220, 120, 255))
        grad.setColorAt(1.0, QColor(255, 255, 255))
        return grad

    def _draw_centered(self, painter, y, text, font, base_color, karaoke=False, progress=0.0, glow=False):
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text)
        x = (self.width() - tw) / 2.0
        if glow:
            painter.setPen(QPen(QColor(255, 80, 220, 70)))
            painter.drawText(int(x + 1), int(y + 2), text)
        # Nen mo
        painter.setPen(QPen(base_color))
        painter.drawText(int(x), int(y), text)
        if karaoke and text.strip() and progress > 0.0:
            fill_w = tw * max(0.0, min(1.0, progress))
            painter.save()
            painter.setClipRect(int(x), 0, int(fill_w), self.height())
            grad = self._rainbow_gradient(x, tw)
            painter.setPen(QPen(grad, 1))
            # Ve lai voi font dam hon de noi bat
            painter.drawText(int(x), int(y), text)
            painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        if not self.lyrics:
            painter.setPen(QPen(QColor(150, 160, 190)))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "Chua co lyrics - chon bai hat")
            painter.end()
            return
        idx = self.idx
        # Truoc intro: hien dong dau mo
        if idx < 0:
            f_next = QFont("Segoe UI", 11)
            painter.setPen(QPen(QColor(140, 150, 180)))
            painter.setFont(f_next)
            fm = painter.fontMetrics()
            t0 = self.lyrics[0][1] if self.lyrics[0][1].strip() else "..."
            painter.drawText(self.rect().adjusted(0, 110, 0, -20), Qt.AlignHCenter | Qt.AlignTop, t0)
            painter.setPen(QPen(QColor(120, 130, 160)))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect().adjusted(0, 20, 0, 0), Qt.AlignHCenter | Qt.AlignTop, "♪ Intro...")
            painter.end()
            return
        prev_text = self.lyrics[idx - 1][1] if idx - 1 >= 0 else ""
        cur_text = self.lyrics[idx][1] if self.lyrics[idx][1].strip() else "♪ ♪ ♪"
        next_text = self.lyrics[idx + 1][1] if idx + 1 < len(self.lyrics) else ""
        # Dong truoc: nho + mo
        if prev_text:
            self._draw_centered(painter, 38, prev_text, QFont("Segoe UI", 11), QColor(130, 140, 170, 160))
        # Dong hien tai: lon + karaoke gradient + glow
        self._draw_centered(painter, 92, cur_text, QFont("Segoe UI", 20, QFont.Bold), QColor(225, 230, 245), karaoke=True, progress=self.progress, glow=True)
        # Thanh tien trinh nho duoi cau hat
        bar_w = min(self.width() - 80, 420)
        bar_x = (self.width() - bar_w) / 2.0
        bar_y = 108
        painter.fillRect(int(bar_x), int(bar_y), int(bar_w), 3, QColor(255, 255, 255, 40))
        painter.fillRect(int(bar_x), int(bar_y), int(bar_w * self.progress), 3, QColor(80, 220, 255, 200))
        # Dong sau: nho + mo
        if next_text:
            self._draw_centered(painter, 148, next_text, QFont("Segoe UI", 11), QColor(130, 140, 170, 150))
        painter.end()
