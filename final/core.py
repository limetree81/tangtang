import os
import pygame
from config import ASSET_DIR, DATA_DIR, WHITE

# -----------------------------
# 1. BGM Manager
# -----------------------------
class BGMManager:
    """배경 음악 재생 및 일시정지를 관리하는 클래스"""
    def __init__(self):
        self.current_track = None
        self.paused = False

    def play(self, filename, loop=-1):
        """새로운 트랙을 재생합니다. 이미 재생 중인 트랙이면 무시합니다."""
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
                print(f"BGM 재생 오류 ({filename}): {e}")
        else:
            print(f"BGM 파일을 찾을 수 없습니다: {path}")

    def pause(self):
        """재생 중인 음악을 일시정지합니다."""
        if not self.paused:
            pygame.mixer.music.pause()
            self.paused = True

    def unpause(self):
        """일시정지된 음악을 다시 재생합니다."""
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

    def stop(self):
        """음악 재생을 완전히 중지합니다."""
        pygame.mixer.music.stop()
        self.current_track = None
        self.paused = False

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
        if cache_key in self.images:
            return self.images[cache_key]
        
        search_paths = [os.path.join(ASSET_DIR, file_name), name]
        for path in search_paths:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    if size:
                        img = pygame.transform.smoothscale(img, size)
                    self.images[cache_key] = img
                    return img
                except: pass
        
        # 대체 이미지 생성
        surf = pygame.Surface(size if size else (64, 64), pygame.SRCALPHA)
        surf.fill((*color, 255))
        pygame.draw.rect(surf, (160, 160, 170), surf.get_rect(), 3)
        try:
            f = pygame.font.SysFont("malgungothic", 14)
            t = f.render("NO IMG", True, (230, 230, 240))
            surf.blit(t, t.get_rect(center=surf.get_rect().center))
        except: pass
        self.images[cache_key] = surf
        return surf

# -----------------------------
# 3. Screen Manager
# -----------------------------
class ScreenManager:
    def __init__(self):
        self.current = None

    def set(self, screen_obj):
        self.current = screen_obj

    def handle_event(self, event):
        if self.current: self.current.handle_event(event)

    def update(self, dt):
        if self.current: self.current.update(dt)

    def draw(self, surf):
        if self.current: self.current.draw(surf)

# -----------------------------
# 4. UI Elements
# -----------------------------
class Button:
    def __init__(self, rect, text, color, hover, font, text_color=WHITE, radius=14):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover = hover
        self.font = font
        self.text_color = text_color
        self.radius = radius

    def draw(self, surf, mouse_pos):
        c = self.hover if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=self.radius)
        pygame.draw.rect(surf, (220, 220, 230), self.rect, 2, border_radius=self.radius)
        label = self.font.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

def draw_panel(surf, rect, title, title_font, body_bg=(35, 35, 42), border=(120, 120, 135)):
    pygame.draw.rect(surf, body_bg, rect, border_radius=18)
    pygame.draw.rect(surf, border, rect, 2, border_radius=18)
    if title:
        t = title_font.render(title, True, WHITE)
        surf.blit(t, (rect.x + 18, rect.y + 16))