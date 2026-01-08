# 완료! (요구사항 반영 버전)
# 1) 체크박스 제거 + "플레이어를 선택하세요..." 문구 삭제
# 2) 게임 명을 크고 굵게
# 3) 선택(파란) 테두리를 더 굵고 잘 보이게
# 4) HP / SPEED / DAMAGE 줄 간격 띄우기

import sys
import pygame

pygame.init()
pygame.font.init()

# -----------------------------
# Config
# -----------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GRAY = (90, 90, 100)
BLUE = (70, 160, 255)
GREEN = (60, 210, 120)
RED = (235, 80, 80)

# ✅ 배경 이미지 경로 (본인 경로로 수정)
BACKGROUND_PATH = r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Start UI - Player Cards (Team C)")
clock = pygame.time.Clock()

# ✅ 타이틀을 더 크고 굵게
FONT_TITLE = pygame.font.SysFont("malgungothic", 64, bold=True)
FONT_H2 = pygame.font.SysFont("malgungothic", 26, bold=True)
FONT = pygame.font.SysFont("malgungothic", 20)
FONT_SMALL = pygame.font.SysFont("malgungothic", 16)

# -----------------------------
# Helpers
# -----------------------------
def load_image_safe(path):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

def load_background_scaled(path):
    img = load_image_safe(path)
    if img is None:
        return None
    return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))

def draw_rounded_rect(surf, rect, color, radius=16, width=0):
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def fit_text_ellipsis(font, text, max_w):
    if font.size(text)[0] <= max_w:
        return text
    ell = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        t = text[:mid] + ell
        if font.size(t)[0] <= max_w:
            lo = mid + 1
        else:
            hi = mid
    return text[:max(0, lo - 1)] + ell

# -----------------------------
# UI Components
# -----------------------------
class Button:
    def __init__(self, rect, text, color=GRAY, hover_color=BLUE, text_color=WHITE, radius=14):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.radius = radius

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        c = self.hover_color if hover else self.color
        draw_rounded_rect(surf, self.rect, c, radius=self.radius)
        draw_rounded_rect(surf, self.rect, (255, 255, 255), radius=self.radius, width=2)
        label = FONT.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class PlayerCard:
    def __init__(self, rect, player_data, image_surface):
        self.rect = pygame.Rect(rect)
        self.data = player_data
        self.image = image_surface
        self.selected = False

        self.img_rect = pygame.Rect(self.rect.x + 14, self.rect.y + 14, self.rect.w - 28, 240)
        self.text_x = self.rect.x + 14
        self.text_y = self.img_rect.bottom + 14

        self._scaled_cache = None
        self._scaled_cache_size = None

    def _get_scaled_image(self):
        if self.image is None:
            return None
        size = (self.img_rect.w, self.img_rect.h)
        if self._scaled_cache is None or self._scaled_cache_size != size:
            self._scaled_cache = pygame.transform.smoothscale(self.image, size)
            self._scaled_cache_size = size
        return self._scaled_cache

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)

        # 배경
        base_col = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base_col, radius=18)

        # ✅ 선택 테두리: 더 굵게 + 바깥 글로우 느낌(2겹)
        if self.selected:
            # 바깥(글로우)
            glow_rect = self.rect.inflate(6, 6)
            draw_rounded_rect(surf, glow_rect, (60, 160, 255), radius=22, width=6)
            # 안쪽(메인)
            draw_rounded_rect(surf, self.rect, BLUE, radius=18, width=5)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=2)

        # image frame
        draw_rounded_rect(surf, self.img_rect, (22, 22, 26), radius=14)
        draw_rounded_rect(surf, self.img_rect, (110, 110, 130), radius=14, width=2)

        img = self._get_scaled_image()
        if img:
            surf.blit(img, self.img_rect.topleft)
        else:
            ph = FONT.render("이미지 없음", True, (220, 220, 230))
            surf.blit(ph, ph.get_rect(center=self.img_rect.center))

        # Title
        name = FONT_H2.render(self.data["name"], True, WHITE)
        surf.blit(name, (self.text_x, self.text_y))

        max_w = self.rect.w - 28

        # ✅ 스탯 줄 간격 띄우기 (더 여유 있게)
        hp_line = f"HP {self.data['HP']}"
        vel_line = f"SPEED {self.data['SPEED']}"
        dmg_line = f"DAMAGE {self.data['DAMAGE']}"

        stats_y0 = self.text_y + 52     # 이름 아래 첫 줄 시작점
        stats_gap = 22                  # ✅ 줄 간격(여기 더 키우면 더 띄엄띄엄)

        surf.blit(FONT_SMALL.render(fit_text_ellipsis(FONT_SMALL, hp_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 0))
        surf.blit(FONT_SMALL.render(fit_text_ellipsis(FONT_SMALL, vel_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 1))
        surf.blit(FONT_SMALL.render(fit_text_ellipsis(FONT_SMALL, dmg_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 2))

        # ✅ 체크박스/선택됨 문구 제거 (아예 안 그림)

    def hit_test(self, pos):
        return self.rect.collidepoint(pos)

class HelpPanel:
    def __init__(self, rect, help_lines):
        self.rect = pygame.Rect(rect)
        self.lines = help_lines

    def draw(self, surf):
        draw_rounded_rect(surf, self.rect, (42, 42, 50), radius=18)
        draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=3)

        title = FONT_H2.render("도움말", True, WHITE)
        surf.blit(title, (self.rect.x + 16, self.rect.y + 16))

        y = self.rect.y + 56
        x = self.rect.x + 14
        max_w = self.rect.w - 28

        for ln in self.lines:
            txt = fit_text_ellipsis(FONT_SMALL, ln, max_w)
            surf.blit(FONT_SMALL.render(txt, True, (230, 230, 240)), (x, y))
            y += 22
            if y > self.rect.bottom - 20:
                break

# -----------------------------
# Data
# -----------------------------
PLAYERS = [
    {"id": "tank",   "name": "플레이어 1", "HP":" : 150", "SPEED":" : 240", "DAMAGE":" : x 1.0"},
    {"id": "speed",  "name": "플레이어 2", "HP":" : 100", "SPEED":" : 360", "DAMAGE":" : x 1.0"},
    {"id": "damage", "name": "플레이어 3", "HP":" : 100", "SPEED":" : 240", "DAMAGE":" : x 1.5"},
]

IMAGE_PATHS = [
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_1.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_2.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_3.png"
]

HELP_TEXT = [
    "",
    "[플레이어 특징]",
    "P1: HP 높음",
    "P2: 이동속도(VEL) 높음",
    "P3: 공격력(DMG) 높음",
    "",
    "[인게임 규칙]",
    "레벨업: EXP 100마다",
    "레벨업 시 스킬 선택",
    "",
    "[조작 방법]",
    "이동: WASD / 방향키",
    "스킬 선택: 1/2/3",
]

# -----------------------------
# Scene: Start only
# -----------------------------
class StartScene:
    def __init__(self):
        self.selected_idx = 0
        self.player_images = [load_image_safe(p) for p in IMAGE_PATHS]

        self.bg = load_background_scaled(BACKGROUND_PATH)

        # 레이아웃
        self.card_w, self.card_h = 245, 400
        self.gap = 30
        self.y_cards = 160

        total_w = self.card_w * 4 + self.gap * 3
        self.start_x = (WIDTH - total_w) // 2

        self.cards = []
        for i in range(3):
            rect = (self.start_x + i * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
            self.cards.append(PlayerCard(rect, PLAYERS[i], self.player_images[i]))

        help_rect = (self.start_x + 3 * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
        self.help_panel = HelpPanel(help_rect, HELP_TEXT)

        self._sync_selected()

        # Bottom Buttons
        btn_y = HEIGHT - 100
        btn_w, btn_h = 505, 60
        btn_gap = 60
        total_btn = btn_w * 2 + btn_gap
        btn_x = (WIDTH - total_btn) // 2

        self.btn_exit = Button(
            (btn_x, btn_y, btn_w, btn_h),
            "종료 (Esc)", color=RED, hover_color=(180, 50, 50), radius=18
        )
        self.btn_start = Button(
            (btn_x + btn_w + btn_gap, btn_y, btn_w, btn_h),
            "시작하기 (Enter)", color=GREEN, hover_color=(40, 170, 90), radius=18
        )

    def _sync_selected(self):
        for i, c in enumerate(self.cards):
            c.selected = (i == self.selected_idx)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.selected_idx = 0; self._sync_selected()
            elif event.key == pygame.K_2:
                self.selected_idx = 1; self._sync_selected()
            elif event.key == pygame.K_3:
                self.selected_idx = 2; self._sync_selected()
            elif event.key == pygame.K_RETURN:
                print(f"[Start only] selected: {PLAYERS[self.selected_idx]['name']}")

        if self.btn_exit.clicked(event):
            pygame.quit()
            sys.exit()

        if self.btn_start.clicked(event):
            print(f"[Start only] selected: {PLAYERS[self.selected_idx]['name']}")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, card in enumerate(self.cards):
                if card.hit_test(event.pos):
                    self.selected_idx = i
                    self._sync_selected()
                    break

    def update(self, dt):
        pass

    def draw(self, surf):
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((18, 18, 24))

        mouse = pygame.mouse.get_pos()

        # ✅ 타이틀(그림자 + 본문)
        t_shadow = FONT_TITLE.render("MAGIC SURVIVOR - START", True, (0, 0, 0))
        t_main = FONT_TITLE.render("MAGIC SURVIVOR - START", True, WHITE)
        surf.blit(t_shadow, (102, 77))
        surf.blit(t_main, (100, 75))

        for c in self.cards:
            c.draw(surf, mouse)
        self.help_panel.draw(surf)

        # 하단 바 (반투명)
        bar_h = 130
        bar_rect = pygame.Rect(0, HEIGHT - bar_h, WIDTH, bar_h)

        panel = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        surf.blit(panel, bar_rect.topleft)

        pygame.draw.line(surf, (0, 0, 0), (0, HEIGHT - bar_h), (WIDTH, HEIGHT - bar_h), 2)

        self.btn_exit.draw(surf, mouse)
        self.btn_start.draw(surf, mouse)

# -----------------------------
# Main loop: Start only
# -----------------------------
def main():
    scene = StartScene()
    while True:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            scene.handle_event(event)

        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()