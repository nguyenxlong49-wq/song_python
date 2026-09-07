#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backend phat nhac dung pygame.mixer.music.
Giu logic phat MP3/WAV hien tai, bo sung get_position/duration/seek
de GUI dong bo ma khong dung time.sleep.
"""
import os

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


def _duration_via_mutagen(path):
    try:
        from mutagen.mp3 import MP3
        from mutagen.ogg import OggFileType
        from mutagen.wave import WAVE
        ext = os.path.splitext(path)[1].lower()
        if ext == ".mp3":
            return float(MP3(path).info.length)
        if ext in (".ogg", ".oga"):
            return float(OggFileType(path).info.length)
        if ext == ".wav":
            return float(WAVE(path).info.length)
    except Exception:
        pass
    return 0.0


class MusicPlayer:
    """Wrapper quanh pygame.mixer.music voi audio-clock that."""

    def __init__(self):
        self.audio_path = ""
        self.duration = 0.0
        self._paused_pos = 0.0

    def _ensure_mixer(self):
        if not HAS_PYGAME:
            raise RuntimeError("Can pygame: pip install pygame-ce")
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def load(self, audio_path):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)
        self._ensure_mixer()
        pygame.mixer.music.load(audio_path)
        self.audio_path = audio_path
        self.duration = _duration_via_mutagen(audio_path)
        self._paused_pos = 0.0
        return True

    def play(self, start_sec=0.0):
        self._ensure_mixer()
        if start_sec and start_sec > 0:
            try:
                # pygame ho tro start cho OGG/MP3 tren mot so build
                pygame.mixer.music.play(start=start_sec)
                return
            except Exception:
                pass
        pygame.mixer.music.play()

    def pause(self):
        if HAS_PYGAME and pygame.mixer.get_init():
            try:
                self._paused_pos = self.get_position()
            except Exception:
                pass
            pygame.mixer.music.pause()

    def resume(self):
        if HAS_PYGAME and pygame.mixer.get_init():
            pygame.mixer.music.unpause()

    def stop(self):
        if HAS_PYGAME and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def seek(self, sec):
        """Seek: dung play(start=sec). Tra ve vi tri moi."""
        self._ensure_mixer()
        sec = max(0.0, float(sec))
        if self.duration and sec > self.duration:
            sec = max(0.0, self.duration - 0.5)
        try:
            pygame.mixer.music.play(start=sec)
        except Exception:
            # Fallback: play tu dau neu backend khong ho tro start
            pygame.mixer.music.play()
            return self.get_position()
        return sec

    def get_position(self):
        """Vi tri audio that (giay). Dung de dong bo lyrics/progress/visualizer."""
        if HAS_PYGAME and pygame.mixer.get_init():
            try:
                pos = pygame.mixer.music.get_pos()
                if pos is not None and pos >= 0:
                    return pos / 1000.0
            except Exception:
                pass
        return self._paused_pos

    def is_playing(self):
        if HAS_PYGAME and pygame.mixer.get_init():
            try:
                return bool(pygame.mixer.music.get_busy())
            except Exception:
                return False
        return False

    def get_duration(self):
        return self.duration
