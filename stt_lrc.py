#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STT -> LRC: speech-to-text co timestamp tu dong.
Dung faster-whisper neu co (nhe, chay local). Chua cai thi bao loi ro.
Tra ve chuoi LRC dang [mm:ss.xx] moi segment 1 dong.
"""
import os


def backend():
    try:
        import faster_whisper  # noqa
        return "faster-whisper"
    except ImportError:
        pass
    try:
        import whisper  # noqa
        return "whisper"
    except ImportError:
        pass
    return ""


def transcribe_to_lrc(audio_path, model="tiny", language=None, progress_cb=None):
    """Nhan audio -> chuoi LRC. progress_cb(frac, text) goi theo tien do."""
    be = backend()
    if not be:
        raise RuntimeError("Chua cai STT. Chay: pip install faster-whisper")
    if be == "faster-whisper":
        from faster_whisper import WhisperModel
        # tiny: nhanh, base/small: chuan hon (can RAM/VRAM hon)
        m = WhisperModel(model, device="auto", compute_type="auto")
        segments, _info = m.transcribe(audio_path, language=language, vad_filter=True)
        out = []
        total = 0.0
        try:
            from mutagen.mp3 import MP3
            total = float(MP3(audio_path).info.length) or 1.0
        except Exception:
            total = 1.0
        for seg in segments:
            t = max(0.0, float(seg.start))
            txt = (seg.text or "").strip()
            if not txt:
                continue
            out.append(f"[{int(t//60):02d}:{t%60:05.2f}]{txt}")
            if progress_cb:
                try:
                    progress_cb(min(0.99, t / total), txt)
                except Exception:
                    pass
        return "\n".join(out) + "\n"
    # whisper goc (openai-whisper)
    import whisper as _w
    m = _w.load_model(model)
    res = m.transcribe(audio_path, language=language)
    out = []
    for seg in res.get("segments", []):
        t = max(0.0, float(seg.get("start", 0)))
        txt = (seg.get("text") or "").strip()
        if txt:
            out.append(f"[{int(t//60):02d}:{t%60:05.2f}]{txt}")
    return "\n".join(out) + "\n"


def save_lrc(audio_path, lrc_text):
    out = os.path.splitext(audio_path)[0] + ".lrc"
    with open(out, "w", encoding="utf-8") as f:
        f.write(lrc_text)
    return out
