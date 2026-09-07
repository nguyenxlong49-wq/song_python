#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AudioVisualizer QWidget ve bang QPainter, khong dung Unicode terminal."""
import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class AudioVisualizer(QWidget):
    """Thanh visualizer 48 cot, gradient + glow, ~30 FPS.

    Giai thich realtime vs mo phong:
    pygame.mixer.music khong expose raw audio buffer de FFT realtime,
    nen visualizer dung ham sin theo position + beat (128 BPM) co smoothing.
    Khong pha he phat nhac, khong tang CPU (chi ve 1 widget, khong tao pixmap moi).
    De co FFT that: chuyen backend sang sounddevice/pyaudio doc file wav
    roi numpy.fft, thay ham _bar_height().
    """

    def __init__(self, bars=48, parent=None):
        super().__init__(parent)
        self.bars = int(bars)
        self.position = 0.0
        self.playing = False
        self._phase = 0.0
        self._smooth = [0.0] * self.bars
        self.setMinimumHeight(90)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, position, playing):
        self.position = float(position)
        self.playing = bool(playing)

    def _tick(self):
        if self.playing:
            self._phase += 0.09
        self.update()

    def _bar_height(self, i, n):
        # Envelop mo phong theo beat, deterministic de khong nhap nhay random
        beat = self.position * 2.7
        base = math.sin(i * 0.55 + beat) * 0.6 + math.sin(i * 1.15 - beat * 0.7) * 0.4
        amp = (base + 1.0) / 2.0
        # Khi pause: giam bien do ve muc nghi
        if not self.playing:
            amp = amp * 0.25 + 0.08
        target = max(0.05, min(1.0, amp))
        # Smoothing de muot, tranh nhay dot ngot
        prev = self._smooth[i] if i < len(self._smooth) else target
        val = prev + (target - prev) * 0.35
        if i < len(self._smooth):
            self._smooth[i] = val
        return val

    def _bar_color(self, amp):
        if amp > 0.75:
            return QColor(255, 77, 255)
        if amp > 0.55:
            return QColor(64, 224, 255)
        if amp > 0.35:
            return QColor(87, 255, 164)
        return QColor(70, 130, 255)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(10, 12, 24, 0))
        n = self.bars
        w = self.width()
        h = self.height()
        gap = 4
        bw = max(2.0, (w - gap * (n - 1)) / n)
        for i in range(n):
            amp = self._bar_height(i, n)
            bh = max(3.0, amp * (h - 12))
            x = i * (bw + gap)
            y = h - 6 - bh
            color = self._bar_color(amp)
            # Glow: ve rect mo rong hon phia sau
            glow = QColor(color)
            glow.setAlpha(60)
            painter.fillRect(int(x - 1), int(y - 2), int(bw + 2), int(bh + 4), glow)
            grad = QLinearGradient(0, y, 0, y + bh)
            top = QColor(color)
            bottom = QColor(color)
            bottom.setAlpha(120)
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, bottom)
            painter.fillRect(int(x), int(y), int(bw), int(bh), grad)
            # Diem sang tren dinh
            painter.setPen(QPen(QColor(255, 255, 255, 140)))
            painter.drawLine(int(x), int(y), int(x + bw), int(y))
        painter.end()
