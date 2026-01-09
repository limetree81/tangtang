import os
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
BLACK = (0, 0, 0)
GRAY = (90, 90, 100)
BLUE = (70, 160, 255)
GREEN = (60, 210, 120)
RED = (235, 80, 80)

# ✅ [수정] 상대 경로 설정을 위한 기준점
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
# ✅ [수정] 이미지 폴더 경로 (사용자 코드의 'iamge' 유지)
IMAGE_DIR = os.path.join(BASE_PATH, "image")
# ✅ [수정] 배경 이미지 경로
BACKGROUND_PATH = os.path.join(IMAGE_DIR, "game_background.png")

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("End UI Only - MAGIC SURVIVOR")
clock = pygame.time.Clock()

FONT_H1 = pygame.font.SysFont("malgungothic", 86)   # GAME OVER
FONT_H2 = pygame.font.SysFont("malgungothic", 36)   # 결과
FONT = pygame.font.SysFont("malgungothic", 26)
FONT_SMALL = pygame.font.SysFont("malgungothic", 22)

# -----------------------------
# Layout Tuning (픽셀 조정용)
# -----------------------------
TITLE_CENTER_Y = 155            # "GAME OVER!" 위치
PANEL_W = 940
PANEL_H = 310                   
PANEL_RADIUS = 26

BTN_W = 435
BTN_H = 90
BTN_GAP = 70

BOTTOM_MARGIN = 60              
PANEL_TO_BTN_GAP = 28           

# 패널 안쪽 패딩
PANEL_PAD_X = 44
PANEL_PAD_TOP = 34

# 내부 구분선/텍스트 간격
LINE_GAP_1 = 50
LINE_GAP_2 = 66
DIVIDER_TOP_GAP = 12
AFTER_DIVIDER_GAP = 20

# -----------------------------
# Helpers
# -----------------------------
def load_image_safe(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception as e:
        print(f"이미지 로드 실패: {path}, 에러: {e}")
        return None

def draw_rounded_rect(surf, rect, color, radius=18, width=0):
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def draw_glass_panel(surf, rect, radius=22, fill_rgba=(30, 30, 36, 145), border_rgba=(230, 230, 235, 255), border_w=2):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, fill_rgba, panel.get_rect(), border_radius=radius)
    surf.blit(panel, (rect.x, rect.y))
    pygame.draw.rect(surf, border_rgba, rect, border_w, border_radius=radius)

def draw_divider(surf, x1, y, x2, alpha=120, thickness=2):
    w = abs(x2 - x1)
    if w <= 0: return
    line = pygame.Surface((w, thickness), pygame.SRCALPHA)
    pygame.draw.rect(line, (230, 230, 235, alpha), (0, 0, w, thickness), border_radius=thickness // 2)
    surf.blit(line, (min(x1, x2), y))

# -----------------------------
# UI Components
# -----------------------------
class Button:
    def __init__(self, rect, text, color=GRAY, hover_color=BLUE, text_color=WHITE, radius=22, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.radius = radius
        self.font = font or pygame.font.SysFont("malgungothic", 34)

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        c = self.hover_color if hover else self.color
        draw_rounded_rect(surf, self.rect, c, radius=self.radius)
        draw_rounded_rect(surf, self.rect, (230, 230, 235), radius=self.radius, width=2)
        label = self.font.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

# -----------------------------
# End UI Scene
# -----------------------------
class EndScene:
    def __init__(self):
        # ✅ [수정] 위에서 설정한 BACKGROUND_PATH 사용 (절대경로 제거)
        self.bg = load_image_safe(BACKGROUND_PATH, size=(WIDTH, HEIGHT))

        # 예시 결과 데이터
        self.success = False
        self.survival_time_sec = 4 * 60 + 47
        self.kill_count = 123
        self.reason = "플레이어 HP가 0이 되었습니다."

        # 레이아웃 계산
        self.btn_y = HEIGHT - BOTTOM_MARGIN - BTN_H
        total_btn_w = BTN_W * 2 + BTN_GAP
        btn_x = (WIDTH - total_btn_w) // 2

        self.btn_restart = Button(
            (btn_x, self.btn_y, BTN_W, BTN_H),
            "다시하기 (Enter)",
            color=BLUE, hover_color=(95, 185, 255)
        )
        self.btn_to_start = Button(
            (btn_x + BTN_W + BTN_GAP, self.btn_y, BTN_W, BTN_H),
            "시작화면 (Esc)",
            color=GREEN, hover_color=(45, 185, 110)
        )

        panel_x = (WIDTH - PANEL_W) // 2
        panel_y = self.btn_y - PANEL_TO_BTN_GAP - PANEL_H
        self.panel_rect = pygame.Rect(panel_x, panel_y, PANEL_W, PANEL_H)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                print("[EndUI] 다시하기")
            elif event.key == pygame.K_ESCAPE:
                print("[EndUI] 시작화면")

        if self.btn_restart.clicked(event):
            print("[EndUI] 다시하기 클릭")
        if self.btn_to_start.clicked(event):
            print("[EndUI] 시작화면 클릭")

    def update(self, dt):
        pass

    def draw(self, surf):
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((12, 12, 18))

        main = "GAME SUCCESS!" if self.success else "GAME OVER!"
        col = GREEN if self.success else RED
        title = FONT_H1.render(main, True, col)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, TITLE_CENTER_Y)))

        draw_glass_panel(surf, self.panel_rect, radius=PANEL_RADIUS)

        px = self.panel_rect.x + PANEL_PAD_X
        py = self.panel_rect.y + PANEL_PAD_TOP

        surf.blit(FONT_H2.render("결과", True, BLACK), (px, py))
        py += 70

        mm = int(self.survival_time_sec // 60)
        ss = int(self.survival_time_sec % 60)
        line1 = f"- 생존 시간 : {mm}:{ss:02d}"
        line2 = f"- 처치한 몬스터 수 : {self.kill_count}"

        surf.blit(FONT.render(line1, True, BLACK), (px, py))
        py += LINE_GAP_1
        surf.blit(FONT.render(line2, True, BLACK), (px, py))
        py += LINE_GAP_2

        y_div = py + DIVIDER_TOP_GAP
        draw_divider(surf, self.panel_rect.x + 85, y_div, self.panel_rect.right - 85, alpha=120, thickness=2)
        py = y_div + AFTER_DIVIDER_GAP

        reason_text = f"종료 사유: {self.reason}"
        surf.blit(FONT_SMALL.render(reason_text, True, BLACK), (px, py))

        mouse = pygame.mouse.get_pos()
        self.btn_restart.draw(surf, mouse)
        self.btn_to_start.draw(surf, mouse)

# -----------------------------
# Main
# -----------------------------
def main():
    scene = EndScene()
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