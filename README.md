# Karaoke Python - Phát nhạc + Lời đồng bộ 7 sắc cầu vồng

Phát file `mp3/wav` và hiển thị lời `.lrc` đồng bộ theo giai điệu, hỗ trợ API `lrclib.net`.

## Tính năng
- Phát nhạc qua `pygame.mixer` + lời đồng bộ `time.time()` + `LRC_OFFSET` per-song
- Lời animation 7 sắc cầu vồng `rainbow_text()` thay vì xanh
- Menu chọn bài tự động quét `assets/music/*.mp3`
- Lấy LRC chuẩn từ API `https://lrclib.net/api/get` (Jason Derulo - Colors, Unknown Brain - Superhero, John Newman - Love Me Again)
- Hỗ trợ `colorama`, `numpy`, `mutagen`

## Cài đặt
```bash
pip install -r requirements.txt
```

## Chạy
```bash
# Menu chọn bài
python karaoke_player.py

# Phát trực tiếp
python karaoke_player.py --audio assets/music/love-me-again.mp3 --lrc assets/music/love-me-again.lrc

# Preview 16s
python preview.py

# Căn chỉnh LRC khớp ca sĩ (gõ Enter theo nhịp)
python calibrate_lrc.py
```

## Cấu trúc
```
karaoke-python/
├── karaoke_player.py
├── requirements.txt
├── preview.py
├── calibrate_lrc.py
└── assets/music/
    ├── love-me-again.mp3/.lrc
    ├── Jason Derulo - Colors [...].mp3/.lrc
    └── Unknown Brain - Superhero [...].mp3/.lrc
```

## Yêu cầu
- Python 3.10+
- pygame-ce, colorama, numpy, mutagen
