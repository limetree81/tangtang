import os
import sys
import random
import pygame

pygame.init()
pygame.font.init()

# -----------------------------
# Config
# -----------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

WHITE = (245, 245, 245)
BLACK = (12, 12, 15)
BLUE = (70, 160, 255)
RED = (235, 80, 80)

# ✅ 여기만 네 환경에 맞게 바꿔줘
ASSET = {
    "bg": r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png",
    "player": r"C:\Users\KDT43\Project1\tangtang\KHG\player_1.png",
    "spider": r"C:\Users\KDT43\Project1\tangtang\KHG\monster_spider.png",
    "skull": r"C:\Users\KDT43\Project1\tangtang\KHG\monster_bone.png",
    "midboss": r"C:\Users\KDT43\Project1\tangtang\KHG\middle_boss_dimenter.png",
    "finalboss": r"C:\Users\KDT43\Project1\tangtang\KHG\final_boss_pumpkin.png",
}

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("InGame UI + Images (Team C)")
clock = pygame.time.Clock()


# -----------------------------
# Helpers
# -----------------------------
def load_image(path: str, size=None):
    """이미지 로드(실패하면 투명 플레이스홀더)."""
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        if size is None:
            size = (64, 64)
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (160, 160, 175), surf.get_rect(), 3, border_radius=10)
        try:
            f = pygame.font.SysFont("malgungothic", 14)
            t = f.render("NO IMG", True, (230, 230, 240))
            surf.blit(t, t.get_rect(center=surf.get_rect().center))
        except Exception:
            pass
        return surf


def load_background_scaled(path: str):
    img = load_image(path)
    return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))


# -----------------------------
# UI Components
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
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos))


class PauseOverlay:
    def __init__(self, ui):
        self.ui = ui
        self.active = True
        self.font_h = pygame.font.SysFont("malgungothic", 64)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.btn_resume = Button(
            (WIDTH // 2 - 200, HEIGHT // 2 + 40, 400, 70),
            "계속하기 (P)", (70, 160, 255), (95, 185, 255),
            pygame.font.SysFont("malgungothic", 28)
        )

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            self.active = False
            self.ui.paused = False
        if self.btn_resume.clicked(event):
            self.active = False
            self.ui.paused = False

    def draw(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        title = self.font_h.render("PAUSED", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        tip = self.font.render("게임이 일시정지되었습니다. P 또는 버튼으로 재개할 수 있습니다.", True, (220, 220, 230))
        surf.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))

        self.btn_resume.draw(surf, pygame.mouse.get_pos())


# -----------------------------
# Dummy Entities (UI 전시용)
# -----------------------------
class DummyPlayer:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.radius = 18
        self.hp = 85
        self.max_hp = 130


class DummyEnemy:
    def __init__(self, kind, pos, img, radius=18):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.img = img
        self.radius = radius


# -----------------------------
# InGame UI + Images
# -----------------------------
class InGameUIOnly:
    def __init__(self):
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.font_small = pygame.font.SysFont("malgungothic", 18)

        # ✅ 배경/이미지 로드
        self.bg = load_background_scaled(ASSET["bg"])
        self.player_img = load_image(ASSET["player"], size=(100, 100))

        self.img_spider = load_image(ASSET["spider"], size=(40, 40))
        self.img_skull = load_image(ASSET["skull"], size=(40, 40))
        self.img_midboss = load_image(ASSET["midboss"], size=(100, 100))
        self.img_finalboss = load_image(ASSET["finalboss"], size=(120, 120))

        # 더미 플레이어
        self.player = DummyPlayer((WIDTH * 0.5, HEIGHT * 0.55))

        # 더미 적들(화면에 보이기만 하게 배치)
        self.enemies = []
        self._spawn_demo_enemies()

        # HUD 더미 데이터
        self.total_time = 300.0
        self.elapsed = 123.4
        self.level = 3
        self.exp = 40
        self.exp_need = 100
        self.kills = 12

        # 보스 배너(원하면 켜기)
        self.boss_deadline = self.elapsed + 25.0
        self.active_boss_kind = "midboss"  # "midboss" or "finalboss"

        # buttons
        self.btn_to_start = Button((WIDTH - 290, 14, 130, 40), "나가기", (235, 80, 80), (180, 55, 55), pygame.font.SysFont("malgungothic", 22))
        self.btn_pause = Button((WIDTH - 150, 14, 130, 40), "Pause (P)", (90, 90, 110), (120, 120, 140), pygame.font.SysFont("malgungothic", 22))

        # pause
        self.paused = False
        self.pause_overlay = None

    def _spawn_demo_enemies(self):
        arena = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 90)
        for _ in range(7):
            x = random.randint(arena.left + 60, arena.right - 60)
            y = random.randint(arena.top + 60, arena.bottom - 60)
            kind = random.choice(["spider", "skull"])
            img = self.img_spider if kind == "spider" else self.img_skull
            self.enemies.append(DummyEnemy(kind, (x, y), img, radius=18))

        # 보스 1마리씩(전시용)
        self.enemies.append(DummyEnemy("midboss", (arena.centerx + 260, arena.centery - 120), self.img_midboss, radius=36))
        self.enemies.append(DummyEnemy("finalboss", (arena.centerx + 260, arena.centery + 140), self.img_finalboss, radius=44))

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_overlay = PauseOverlay(self) if self.paused else None

    def handle_event(self, event):
        if self.paused and self.pause_overlay and self.pause_overlay.active:
            self.pause_overlay.handle_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self._toggle_pause()
            if event.key == pygame.K_ESCAPE:
                print("[UI Only] ESC (나가기 처리 대신 출력만)")

        if self.btn_pause.clicked(event):
            self._toggle_pause()
        if self.btn_to_start.clicked(event):
            print("[UI Only] 나가기 버튼 클릭")

    def update(self, dt):
        # UI 데모용으로 시간만 흐르게(원치 않으면 주석)
        if not self.paused:
            self.elapsed += dt
            if self.elapsed > self.total_time:
                self.elapsed = 0.0

    def _draw_hud(self, surf):
        bar_x, bar_y = 30, 18
        bar_w, bar_h = 520, 22

        pygame.draw.rect(surf, (45, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=10)
        ratio = 0.0 if self.exp_need <= 0 else (self.exp / self.exp_need)
        pygame.draw.rect(surf, (70, 160, 255), (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=10)
        pygame.draw.rect(surf, (170, 170, 185), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)

        surf.blit(self.font_small.render(f"EXP {self.exp}/{self.exp_need}", True, WHITE), (bar_x + 10, bar_y - 2))
        surf.blit(self.font.render(f"레벨 {self.level}", True, WHITE), (bar_x + bar_w + 18, 14))
        surf.blit(self.font.render(f"처치수 {self.kills}", True, WHITE), (bar_x + bar_w + 140, 14))

        remain = max(0.0, self.total_time - self.elapsed)
        surf.blit(self.font.render(f"{int(remain//60)}:{int(remain%60):02d}", True, WHITE), (WIDTH - 420, 14))

        if self.boss_deadline is not None:
            r = max(0.0, self.boss_deadline - self.elapsed)
            kind = "중간 보스" if self.active_boss_kind == "midboss" else "최종 보스"
            banner = pygame.Rect(380, 50, 520, 34)
            pygame.draw.rect(surf, (90, 40, 40), banner, border_radius=10)
            pygame.draw.rect(surf, (190, 90, 90), banner, 2, border_radius=10)
            surf.blit(self.font.render(f"{kind} 제한시간: {r:0.1f}s", True, WHITE), (banner.x + 12, banner.y + 6))

        mouse = pygame.mouse.get_pos()
        self.btn_to_start.draw(surf, mouse)
        self.btn_pause.draw(surf, mouse)

    def _draw_player(self, surf):
        rect = self.player_img.get_rect(center=(int(self.player.pos.x), int(self.player.pos.y)))
        surf.blit(self.player_img, rect)

        # 플레이어 히트박스(전시용)
        pygame.draw.circle(surf, (20, 20, 20), (int(self.player.pos.x), int(self.player.pos.y)), self.player.radius, 2)

        # HP bar
        w, h = 110, 20
        x = int(self.player.pos.x - w / 2)
        y = int(self.player.pos.y + 38)
        pygame.draw.rect(surf, (45, 45, 55), (x, y, w, h), border_radius=8)
        ratio = max(0, self.player.hp) / max(1, self.player.max_hp)
        pygame.draw.rect(surf, (235, 80, 80), (x, y, int(w * ratio), h), border_radius=8)
        pygame.draw.rect(surf, (180, 180, 195), (x, y, w, h), 2, border_radius=8)

    def _draw_enemies(self, surf):
        for e in self.enemies:
            rect = e.img.get_rect(center=(int(e.pos.x), int(e.pos.y)))
            surf.blit(e.img, rect)

    def draw(self, surf):
        # ✅ 배경
        surf.blit(self.bg, (0, 0))

        # ✅ 플레이 영역: “가드만” 치고 배경 보이게
        arena = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 90)
        pygame.draw.rect(surf, (70, 70, 85), arena, 2, border_radius=18)

        self._draw_hud(surf)
        self._draw_enemies(surf)
        self._draw_player(surf)

        if self.paused and self.pause_overlay and self.pause_overlay.active:
            self.pause_overlay.draw(surf)


# -----------------------------
# Main
# -----------------------------
def main():
    ui = InGameUIOnly()

    while True:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            ui.handle_event(event)

        ui.update(dt)
        ui.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()