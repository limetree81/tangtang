import sys
import os
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

# ✅ 경로 설정 (Game_Play.py 기준 경로 사용)
BACKGROUND_PATH = r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png"
PLAYER_IMG_PATHS = [
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_1.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_2.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_3.png",
]

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Magic Survivor - Start UI")
clock = pygame.time.Clock()

# 폰트 설정
FONT_TITLE = pygame.font.SysFont("malgungothic", 64, bold=True)
FONT_H2 = pygame.font.SysFont("malgungothic", 26, bold=True)
FONT = pygame.font.SysFont("malgungothic", 20)
FONT_SMALL = pygame.font.SysFont("malgungothic", 16)

# -----------------------------
# Helpers
# -----------------------------
def load_image_safe(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        return None

def draw_rounded_rect(surf, rect, color, radius=16, width=0):
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def draw_checkbox(surf, rect, checked=False):
    pygame.draw.rect(surf, (28, 28, 34), rect, border_radius=5)
    pygame.draw.rect(surf, (170, 170, 185), rect, 2, border_radius=5)
    if checked:
        p1 = (rect.x + 3, rect.y + rect.h // 2)
        p2 = (rect.x + rect.w // 2 - 1, rect.y + rect.h - 4)
        p3 = (rect.x + rect.w - 3, rect.y + 4)
        pygame.draw.lines(surf, (120, 240, 160), False, [p1, p2, p3], 3)

# -----------------------------
# UI Components
# -----------------------------
class Button:
    def __init__(self, rect, text, color=GRAY, hover_color=BLUE, text_color=WHITE, radius=18):
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
        label = FONT_H2.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class PlayerCard:
    def __init__(self, rect, player_data, image_surface):
        self.rect = pygame.Rect(rect)
        self.data = player_data
        self.image = image_surface
        self.selected = False
        self.img_rect = pygame.Rect(self.rect.x + 16, self.rect.y + 16, self.rect.w - 32, 210)

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        base_col = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base_col, radius=18)

        if self.selected:
            glow_rect = self.rect.inflate(8, 8)
            draw_rounded_rect(surf, glow_rect, (60, 160, 255), radius=22, width=7)
            draw_rounded_rect(surf, self.rect, BLUE, radius=18, width=6)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=2)

        draw_rounded_rect(surf, self.img_rect, (22, 22, 26), radius=14)
        if self.image:
            surf.blit(self.image, self.img_rect.topleft)

        text_x = self.rect.x + 18
        text_y = self.img_rect.bottom + 16
        name = FONT_H2.render(self.data["name"], True, WHITE)
        surf.blit(name, (text_x, text_y))

        stats_y = text_y + 58
        stats_gap = 32
        surf.blit(FONT_SMALL.render(f"HP    {self.data['HP']}", True, (210, 210, 220)), (text_x, stats_y))
        surf.blit(FONT_SMALL.render(f"SPEED {self.data['SPEED']}", True, (210, 210, 220)), (text_x, stats_y + stats_gap))
        surf.blit(FONT_SMALL.render(f"DMG   {self.data['DAMAGE']}", True, (210, 210, 220)), (text_x, stats_y + stats_gap * 2))

class StageCard:
    def __init__(self, rect, key, title, subtitle):
        self.rect = pygame.Rect(rect)
        self.key = key
        self.title = title
        self.subtitle = subtitle
        self.selected = False

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        base = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base, radius=16)

        if self.selected:
            glow = self.rect.inflate(6, 6)
            draw_rounded_rect(surf, glow, (60, 160, 255), radius=20, width=5)
            draw_rounded_rect(surf, self.rect, (70, 160, 255), radius=16, width=4)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=16, width=2)

        cb_rect = pygame.Rect(self.rect.right - 32, self.rect.y + 16, 18, 18)
        draw_checkbox(surf, cb_rect, checked=self.selected)

        surf.blit(FONT.render(self.title, True, WHITE), (self.rect.x + 18, self.rect.y + 14))
        surf.blit(FONT_SMALL.render(self.subtitle, True, (225, 225, 235)), (self.rect.x + 18, self.rect.y + 46))

# -----------------------------
# Scene Class
# -----------------------------
class StartScene:
    def __init__(self):
        # 배경 로드
        self.bg = load_image_safe(BACKGROUND_PATH, (WIDTH, HEIGHT))
        
        # 플레이어 데이터 및 이미지
        self.PLAYERS = [
            {"id": "tank",   "name": "플레이어 1", "HP":" : 150", "SPEED":" : 240", "DAMAGE":" : x 1.0"},
            {"id": "speed",  "name": "플레이어 2", "HP":" : 100", "SPEED":" : 360", "DAMAGE":" : x 1.0"},
            {"id": "damage", "name": "플레이어 3", "HP":" : 100", "SPEED":" : 240", "DAMAGE":" : x 1.5"},
        ]
        
        # 레이아웃 설정
        self.card_w, self.card_h = 250, 410
        self.gap = 30
        self.y_cards = 170
        total_w = self.card_w * 4 + self.gap * 3
        self.start_x = (WIDTH - total_w) // 2

        # 캐릭터 카드 생성 (이미지 포함)
        self.cards = []
        for i in range(3):
            img = load_image_safe(PLAYER_IMG_PATHS[i], (self.card_w - 32, 210))
            rect = (self.start_x + i * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
            self.cards.append(PlayerCard(rect, self.PLAYERS[i], img))
        self.selected_idx = 0

        # 스테이지 카드 생성 (도움말 위치)
        self.stage_panel_rect = pygame.Rect(self.start_x + 3 * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
        stage_defs = [("easy", "쉬움", "보스 HP/속도 낮음"), ("normal", "보통", "현재 스테이지(기존)"), ("hard", "어려움", "보스 2마리 + 강화")]
        self.stage_cards = []
        for i, (key, title, sub) in enumerate(stage_defs):
            r = pygame.Rect(self.stage_panel_rect.x + 16, self.stage_panel_rect.y + 78 + i * 112, self.card_w - 32, 96)
            self.stage_cards.append(StageCard(r, key, title, sub))
        self.stage_idx = 1

        # 하단 버튼
        btn_y = HEIGHT - 100
        btn_w, btn_h = 510, 60
        btn_gap = 60
        btn_x_start = (WIDTH - (btn_w * 2 + btn_gap)) // 2
        self.btn_exit = Button((btn_x_start, btn_y, btn_w, btn_h), "종료 (Esc)", RED)
        self.btn_start = Button((btn_x_start + btn_w + btn_gap, btn_y, btn_w, btn_h), "시작하기 (Enter)", GREEN)

        self._sync()

    def _sync(self):
        for i, c in enumerate(self.cards): c.selected = (i == self.selected_idx)
        for i, s in enumerate(self.stage_cards): s.selected = (i == self.stage_idx)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.selected_idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]
            if event.key in (pygame.K_4, pygame.K_5, pygame.K_6):
                self.stage_idx = {pygame.K_4: 0, pygame.K_5: 1, pygame.K_6: 2}[event.key]
            if event.key == pygame.K_RETURN: self.start_game()
            self._sync()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, card in enumerate(self.cards):
                if card.rect.collidepoint(event.pos): self.selected_idx = i
            for i, sc in enumerate(self.stage_cards):
                if sc.rect.collidepoint(event.pos): self.stage_idx = i
            self._sync()

        if self.btn_exit.clicked(event): pygame.quit(); sys.exit()
        if self.btn_start.clicked(event): self.start_game()

    def start_game(self):
        print(f"시작! 플레이어: {self.PLAYERS[self.selected_idx]['name']}, 난이도: {self.stage_cards[self.stage_idx].key}")

    def draw(self, surf):
        if self.bg: surf.blit(self.bg, (0, 0))
        else: surf.fill((18, 18, 24))

        mouse = pygame.mouse.get_pos()
        # 타이틀
        t_shadow = FONT_TITLE.render("MAGIC SURVIVOR", True, (0, 0, 0))
        t_main = FONT_TITLE.render("MAGIC SURVIVOR", True, WHITE)
        surf.blit(t_shadow, (82, 74)); surf.blit(t_main, (80, 72))

        # 캐릭터 카드
        for c in self.cards: c.draw(surf, mouse)

        # 스테이지 패널
        draw_rounded_rect(surf, self.stage_panel_rect, (35, 35, 42), radius=18)
        draw_rounded_rect(surf, self.stage_panel_rect, (120, 120, 135), radius=18, width=2)
        surf.blit(FONT_H2.render("스테이지", True, WHITE), (self.stage_panel_rect.x + 18, self.stage_panel_rect.y + 16))
        for sc in self.stage_cards: sc.draw(surf, mouse)

        # 하단 바 디자인 (Game_Start.py 형식 - 삭제)
        # bar_h = 130
        # panel = pygame.Surface((WIDTH, bar_h), pygame.SRCALPHA)
        # panel.fill((0, 0, 0, 80))
        # surf.blit(panel, (0, HEIGHT - bar_h))
        # pygame.draw.line(surf, (90, 90, 110), (0, HEIGHT - bar_h), (WIDTH, HEIGHT - bar_h), 2)

        self.btn_exit.draw(surf, mouse)
        self.btn_start.draw(surf, mouse)

# -----------------------------
# Main Loop
# -----------------------------
def main():
    scene = StartScene()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            scene.handle_event(event)
        scene.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()