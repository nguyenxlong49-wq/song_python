import time, threading, karaoke_player
audio="assets/music/love-me-again.mp3"
lrc="assets/music/love-me-again.lrc"
def run():
    karaoke_player.play_with_lrc(audio,lrc)
t=threading.Thread(target=run,daemon=True)
t.start()
time.sleep(16)
import pygame
pygame.mixer.music.stop()
print("\n--- Da dung sau 16s demo ---")
