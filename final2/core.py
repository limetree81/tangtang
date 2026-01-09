import os
import pygame
from config import ASSET_DIR, DATA_DIR, WHITE

# -----------------------------
# 1. Audio Manager (BGM & SFX)
# -----------------------------
class AudioManager:
    """배경 음악 및 단발성 효과음을 통합 관리합니다."""
    def __init__(self):
        self.current_track = None
        self.paused = False
        self.sfx_cache = {}

    # --- BGM 로직 ---
    def play_bgm(self, filename, loop=-1):
        """배경 음악을 재생합니다. 동일 곡이면 무시합니다."""
        if self.current_track == filename:
            return
        
        path = os.path.join(ASSET_DIR, filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(loop)
                self.current_track = filename
                self.paused = False
            except Exception as e:
                print(f"BGM 재생 오류: {e}")

    # ✅ 호환성 유지: 기존 screens.py에서 .play()를 호출하므로 별칭 추가
    def play(self, filename, loop=-1):
        """기존 play() 호출을 play_bgm()으로 연결합니다."""
        self.play_bgm(filename, loop)

    def pause_bgm(self):
        if not self.paused:
            pygame.mixer.music.pause()
            self.paused = True

    # ✅ 호환성 유지: 기존 screens.py에서 .pause()를 호출할 수 있으므로 추가
    def pause(self):
        self.pause_bgm()

    def unpause_bgm(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

    # ✅ 호환성 유지: 기존 screens.py에서 .unpause()를 호출할 수 있으므로 추가
    def unpause(self):
        self.unpause_bgm()

    def stop_bgm(self):
        pygame.mixer.music.stop()
        self.current_track = None
        self.paused = False

    # ✅ 호환성 유지
    def stop(self):
        self.stop_bgm()

    # --- SFX 로직 ---
    def play_sfx(self, filename):
        """단발성 효과음을 1회 재생합니다."""
        if filename not in self.sfx_cache:
            path = os.path.join(ASSET_DIR, filename)
            if os.path.exists(path):
                try:
                    self.sfx_cache[filename] = pygame.mixer.Sound(path)
                except:
                    return
            else:
                return
        
        self.sfx_cache[filename].play()

# -----------------------------
# 2. ResourceManager
# -----------------------------
class ResourceManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
        self.images = {}

    def get_image(self, name, size, color=(70, 70, 80)):
        file_name = os.path.basename(name)
        cache_key = f"{file_name}_{size}"
        if cache_key in self.images: return self.images[cache_key]
        search_paths = [os.path.join(ASSET_DIR, file_name), name]
        for path in search_paths:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    if size: img = pygame.transform.smoothscale(img, size)
                    self.images[cache_key] = img
                    return img
                except: pass
        surf = pygame.Surface(size if size else (64, 64), pygame.SRCALPHA)
        surf.fill((*color, 255))
        pygame.draw.rect(surf, (160, 160, 170), surf.get_rect(), 3)
        self.images[cache_key] = surf
        return surf

# -----------------------------
# 3. ScreenManager
# -----------------------------
class ScreenManager:
    def __init__(self): self.current = None
    def set(self, screen_obj): self.current = screen_obj
    def handle_event(self, event):
        if self.current: self.current.handle_event(event)
    def update(self, dt):
        if self.current: self.current.update(dt)
    def draw(self, surf):
        if self.current: self.current.draw(surf)

# -----------------------------
# 4. Button & UI Helpers
# -----------------------------
class Button:
    def __init__(self, rect, text, color, hover, font, text_color=WHITE, radius=14):
        self.rect = pygame.Rect(rect); self.text = text; self.color = color; self.hover = hover; self.font = font; self.text_color = text_color; self.radius = radius
    def draw(self, surf, mouse_pos):
        c = self.hover if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=self.radius); pygame.draw.rect(surf, (220, 220, 230), self.rect, 2, border_radius=self.radius)
        l = self.font.render(self.text, True, self.text_color); surf.blit(l, l.get_rect(center=self.rect.center))
    def clicked(self, event): return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

def draw_panel(surf, rect, title, title_font, body_bg=(35, 35, 42), border=(120, 120, 135)):
    pygame.draw.rect(surf, body_bg, rect, border_radius=18); pygame.draw.rect(surf, border, rect, 2, border_radius=18)
    if title: surf.blit(title_font.render(title, True, WHITE), (rect.x + 18, rect.y + 16))