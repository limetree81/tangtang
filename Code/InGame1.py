# magic_survivor_all_in_one.py
# Start -> Ingame -> End
# 요구사항 반영:
# 1) 레벨업 필요 EXP: 50, 100, 150, 200 ... (레벨업할 때마다 +50)
# 2) 전기 공격 색상(표시): 노란 계열 + 전기 이미지 투사체
# 3) 파이어볼: 직선 범위 공격 X -> 총알처럼 발사되는 투사체 O
# 4) 중간 보스 이동속도 2배
# 5) 불/전기 공격: 사각형 이펙트 X -> 몬스터처럼 이미지 투사체가 날아감
#
# 준비물(이 파이썬 파일과 같은 폴더에 두기):
# - Electric_Shock.jpg  (전기 투사체 이미지)
# - Fire_Ball.jpg       (불 투사체 이미지)
#
# 조작:
# - Start: 1/2/3 선택, Enter 시작, Esc 종료
# - Ingame: WASD/방향키 이동, P 또는 Pause 버튼 일시정지, Esc 시작화면
# - 레벨업 선택: 1/2/3 또는 클릭
# - End: Enter 재시작, Esc 시작화면

import os
import sys
import math
import random
import pygame

# -----------------------------
# Config
# -----------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

WHITE = (245, 245, 245)
BLACK = (12, 12, 15)
BLUE = (70, 160, 255)
GREEN = (60, 210, 120)
RED = (235, 80, 80)
YELLOW = (255, 220, 80)

MAX_SKILL_LEVEL = 5

# ✅ EXP: 50, 100, 150, 200 ...
EXP_BASE = 50
EXP_INC = 50
def exp_need_for_level(next_level: int) -> int:
    return EXP_BASE + EXP_INC * (next_level - 1)

# -----------------------------
# Helpers
# -----------------------------
def load_image(path: str, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        if size is None:
            size = (64, 64)
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((70, 70, 80, 255))
        pygame.draw.rect(surf, (160, 160, 170), surf.get_rect(), 3)
        try:
            f = pygame.font.SysFont("malgungothic", 14)
            t = f.render("NO IMG", True, (230, 230, 240))
            surf.blit(t, t.get_rect(center=surf.get_rect().center))
        except Exception:
            pass
        return surf

# -----------------------------
# UI
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

def draw_panel(surf, rect, title, title_font, body_bg=(35, 35, 42), border=(120, 120, 135)):
    pygame.draw.rect(surf, body_bg, rect, border_radius=18)
    pygame.draw.rect(surf, border, rect, 2, border_radius=18)
    if title:
        t = title_font.render(title, True, WHITE)
        surf.blit(t, (rect.x + 18, rect.y + 16))

# -----------------------------
# Screen Manager
# -----------------------------
class ScreenBase:
    def handle_event(self, event): ...
    def update(self, dt): ...
    def draw(self, surf): ...

class ScreenManager:
    def __init__(self):
        self.current = None

    def set(self, screen_obj):
        self.current = screen_obj

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, surf):
        if self.current:
            self.current.draw(surf)

# -----------------------------
# Entities
# -----------------------------
class Player:
    def __init__(self, config):
        self.config = config
        self.pos = pygame.Vector2(WIDTH * 0.5, HEIGHT * 0.55)
        self.radius = 18

        self.vel = float(config.get("VEL", 240))
        self.dmg = float(config.get("DMG", 1.0))

        # EXP/Level
        self.level = 0
        self.exp = 0
        self.exp_need = exp_need_for_level(1)

        # HP (이전 요청 유지: 레벨업 +10)
        base_hp = int(config.get("HP", 100))
        self.max_hp = base_hp
        self.hp = float(base_hp)

        self.kills = 0

    def move(self, dt, keys):
        mv = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]: mv.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: mv.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: mv.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: mv.x += 1
        if mv.length_squared() > 0:
            mv = mv.normalize()
        self.pos += mv * self.vel * dt

        self.pos.x = max(30, min(WIDTH - 30, self.pos.x))
        self.pos.y = max(70, min(HEIGHT - 30, self.pos.y))

    def add_exp(self, amount: int) -> bool:
        self.exp += int(amount)
        leveled_up = False
        while self.exp >= self.exp_need:
            self.exp -= self.exp_need
            self.level += 1
            leveled_up = True

            # 레벨업 HP +10
            self.max_hp += 10
            self.hp = min(self.max_hp, self.hp + 10)

            self.exp_need = exp_need_for_level(self.level + 1)
        return leveled_up

class Enemy:
    def __init__(self, kind, pos, hp, exp_reward, img):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.exp_reward = int(exp_reward)
        self.radius = 18 if kind in ("spider", "skull") else 36
        self.img = img

        self.speed = 110 if kind in ("spider", "skull") else 220
        self.random_vel = pygame.Vector2(0, 0)
        self.random_change_t = 0.0

    def alive(self):
        return self.hp > 0

class Bullet:
    def __init__(self, pos, direction, damage):
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0:
            self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize()
        self.speed = 700
        self.damage = float(damage)
        self.radius = 5

    def update(self, dt):
        self.pos += self.dir * self.speed * dt

    def out_of_bounds(self):
        return (self.pos.x < -50 or self.pos.x > WIDTH + 50 or self.pos.y < -50 or self.pos.y > HEIGHT + 50)

# ✅ 불/전기 이미지 투사체
class SkillProjectile:
    def __init__(self, pos, direction, speed, damage, img, radius=12, life=2.0, pierce=1):
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0:
            self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize()

        self.speed = float(speed)
        self.damage = float(damage)
        self.img = img
        self.radius = int(radius)
        self.life = float(life)
        self.pierce = int(pierce)
        self.hit_count = 0

        ang = math.degrees(math.atan2(self.dir.y, self.dir.x))
        self.rot_img = pygame.transform.rotate(self.img, -ang)

    def update(self, dt):
        self.life -= dt
        self.pos += self.dir * self.speed * dt

    def dead(self):
        return (
            self.life <= 0
            or self.pos.x < -200 or self.pos.x > WIDTH + 200
            or self.pos.y < -200 or self.pos.y > HEIGHT + 200
        )

    def draw(self, surf):
        r = self.rot_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surf.blit(self.rot_img, r)

# -----------------------------
# Weapons
# -----------------------------
class WeaponBase:
    key = "base"
    name = "Base"
    color = (200, 200, 200)
    def __init__(self, unlocked=False):
        self.unlocked = unlocked
        self.level = 1 if unlocked else 0
    def is_max(self):
        return self.unlocked and self.level >= MAX_SKILL_LEVEL
    def can_offer(self):
        return not self.is_max()
    def acquire_or_level(self):
        if not self.unlocked:
            self.unlocked = True
            self.level = 1
            return
        if self.level < MAX_SKILL_LEVEL:
            self.level += 1
    def update(self, dt, gs): ...
    def draw(self, surf, gs): ...

class MagicGun(WeaponBase):
    key = "gun"
    name = "마법 총"
    color = BLUE
    def __init__(self):
        super().__init__(unlocked=True)  # 기본 무기
        self.cool = 1.0
        self.t = 0.0

    def update(self, dt, gs):
        self.t += dt
        if self.t < self.cool:
            return
        self.t -= self.cool

        mx, my = pygame.mouse.get_pos()
        dirv = pygame.Vector2(mx, my) - gs.player.pos
        base_angle = math.atan2(dirv.y, dirv.x)

        count = max(1, int(self.level))
        dmg = 10 * gs.player.dmg
        spread = 0.22
        angles = [base_angle] if count == 1 else [base_angle + spread * (i - (count - 1) / 2) for i in range(count)]
        for a in angles:
            dv = pygame.Vector2(math.cos(a), math.sin(a))
            gs.bullets.append(Bullet(gs.player.pos, dv, dmg))

# ✅ (3)(5) 파이어볼: 총알처럼 발사되는 이미지 투사체
class FireBall(WeaponBase):
    key = "fire"
    name = "파이어볼"
    color = (255, 140, 110)
    def __init__(self):
        super().__init__(unlocked=False)
        self.cool = 1.8
        self.t = 0.0

    def update(self, dt, gs):
        if not self.unlocked:
            return
        self.t += dt
        if self.t < self.cool:
            return
        self.t -= self.cool

        mx, my = pygame.mouse.get_pos()
        dirv = pygame.Vector2(mx, my) - gs.player.pos

        speed = 520 + 40 * (self.level - 1)
        dmg = (18 + 8 * (self.level - 1)) * gs.player.dmg
        pierce = 1 + (1 if self.level >= 4 else 0)

        gs.skill_projectiles.append(
            SkillProjectile(
                pos=gs.player.pos,
                direction=dirv,
                speed=speed,
                damage=dmg,
                img=gs.img_fire_skill,
                radius=14,
                life=2.2,
                pierce=pierce,
            )
        )

# ✅ (2)(5) 전기: 노란 느낌 + 이미지 투사체
class ElectricShock(WeaponBase):
    key = "elec"
    name = "전기"
    color = YELLOW
    def __init__(self):
        super().__init__(unlocked=False)
        self.cool = 2.3
        self.t = 0.0

    def update(self, dt, gs):
        if not self.unlocked:
            return
        self.t += dt
        if self.t < self.cool:
            return
        self.t -= self.cool

        count = min(4, self.level)  # 레벨 따라 발사 수 증가
        base_dir = pygame.Vector2(pygame.mouse.get_pos()) - gs.player.pos
        base_ang = math.atan2(base_dir.y, base_dir.x)

        spread = 0.18
        angles = [base_ang] if count == 1 else [base_ang + spread * (i - (count - 1) / 2) for i in range(count)]

        for a in angles:
            dv = pygame.Vector2(math.cos(a), math.sin(a))
            speed = 650 + 30 * (self.level - 1)
            dmg = (14 + 6 * (self.level - 1)) * gs.player.dmg
            pierce = 1 + (1 if self.level >= 5 else 0)

            gs.skill_projectiles.append(
                SkillProjectile(
                    pos=gs.player.pos,
                    direction=dv,
                    speed=speed,
                    damage=dmg,
                    img=gs.img_elec_skill,
                    radius=12,
                    life=1.8,
                    pierce=pierce,
                )
            )

class ProtectShield(WeaponBase):
    key = "shield"
    name = "보호막"
    color = (140, 255, 180)
    def __init__(self):
        super().__init__(unlocked=False)
        self.tick = 0.0
        self.tick_interval = 0.5

    def update(self, dt, gs):
        if not self.unlocked:
            return
        self.tick += dt
        if self.tick < self.tick_interval:
            return
        self.tick -= self.tick_interval

        radius = 50 + 50 * (self.level - 1)
        dmg = 10 * gs.player.dmg

        for e in gs.enemies:
            if not e.alive():
                continue
            dist2 = (e.pos.x - gs.player.pos.x) ** 2 + (e.pos.y - gs.player.pos.y) ** 2
            if dist2 <= (radius + e.radius) ** 2:
                e.hp -= dmg

    def draw(self, surf, gs):
        if not self.unlocked:
            return
        radius = 50 + 50 * (self.level - 1)
        pygame.draw.circle(surf, (120, 255, 180), (int(gs.player.pos.x), int(gs.player.pos.y)), radius, 3)

# -----------------------------
# Overlays
# -----------------------------
class SkillChoiceOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        candidates = [w for w in gs.weapons if w.can_offer()]
        random.shuffle(candidates)
        self.options = candidates[:3]

        self.font_h = pygame.font.SysFont("malgungothic", 44)
        self.font = pygame.font.SysFont("malgungothic", 22)

        self.btn_rects = []
        w, h = 320, 160
        gap = 40
        total = w * 3 + gap * 2
        x0 = (WIDTH - total) // 2
        y0 = HEIGHT // 2 - 70
        for i in range(3):
            self.btn_rects.append(pygame.Rect(x0 + i * (w + gap), y0, w, h))

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]
            if idx < len(self.options):
                self.options[idx].acquire_or_level()
                self.active = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(event.pos) and i < len(self.options):
                    self.options[i].acquire_or_level()
                    self.active = False

    def draw(self, surf):
        if not self.active:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        title = self.font_h.render("레벨업! 스킬을 선택하세요", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 160)))

        for i, r in enumerate(self.btn_rects):
            pygame.draw.rect(surf, (45, 45, 55), r, border_radius=18)
            pygame.draw.rect(surf, (180, 180, 195), r, 2, border_radius=18)

            if i >= len(self.options):
                continue

            wpn = self.options[i]
            name = pygame.font.SysFont("malgungothic", 28).render(wpn.name, True, WHITE)
            lvl_line = f"현재 레벨: {wpn.level}/{MAX_SKILL_LEVEL}" if wpn.unlocked else "미해금: 선택 시 1레벨"
            lvl = self.font.render(lvl_line, True, (210, 210, 220))
            hint = self.font.render(f"[{i+1}] 선택", True, (210, 210, 220))

            strip = pygame.Rect(r.x, r.y, 12, r.h)
            pygame.draw.rect(surf, wpn.color, strip, border_radius=18)

            surf.blit(name, (r.x + 22, r.y + 24))
            surf.blit(lvl, (r.x + 22, r.y + 76))
            surf.blit(hint, (r.x + 22, r.y + 116))

class PauseOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        self.font_h = pygame.font.SysFont("malgungothic", 64)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.btn_resume = Button(
            (WIDTH // 2 - 200, HEIGHT // 2 + 40, 400, 70),
            "계속하기 (P)", BLUE, (95, 185, 255),
            pygame.font.SysFont("malgungothic", 28)
        )

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            self.active = False
            self.gs.paused = False
        if self.btn_resume.clicked(event):
            self.active = False
            self.gs.paused = False

    def draw(self, surf):
        if not self.active:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        title = self.font_h.render("PAUSED", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        tip = self.font.render("게임이 일시정지되었습니다. P 또는 버튼으로 재개할 수 있습니다.", True, (220, 220, 230))
        surf.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))

        self.btn_resume.draw(surf, pygame.mouse.get_pos())

# -----------------------------
# Screens
# -----------------------------
class StartScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager):
        self.mgr = mgr
        self.font_h1 = pygame.font.SysFont("malgungothic", 52)
        self.font_h2 = pygame.font.SysFont("malgungothic", 20)
        self.font = pygame.font.SysFont("malgungothic", 20)
        self.font_small = pygame.font.SysFont("malgungothic", 16)

        self.PLAYERS = [
            {"id": "tank",   "name": "플레이어 1", "HP": 130, "VEL": 240, "DMG": 1.0},
            {"id": "speed",  "name": "플레이어 2", "HP": 100, "VEL": 290, "DMG": 1.0},
            {"id": "damage", "name": "플레이어 3", "HP": 100, "VEL": 240, "DMG": 1.3}
        ]

        # 여기 경로는 본인 환경에 맞게 바꿔도 됨
        self.image_paths = [
            r"C:\Users\KDT43\Project1\tangtang\KHG\player1.jpg",
            r"C:\Users\KDT43\Project1\tangtang\KHG\player2.jpg",
            r"C:\Users\KDT43\Project1\tangtang\KHG\player3.jpg",
        ]

        self.card_w = 280
        self.card_h = 390
        self.card_gap = 26
        total_w = self.card_w * 4 + self.card_gap * 3
        self.start_x = (WIDTH - total_w) // 2
        self.cards_y = 170

        self.card_rects = [
            pygame.Rect(self.start_x + i * (self.card.card_w + self.card_gap) if False else 0, 0, 0, 0)
        ]  # dummy to avoid linter

        self.card_rects = [
            pygame.Rect(self.start_x + i * (self.card_w + self.card_gap), self.cards_y, self.card_w, self.card_h)
            for i in range(3)
        ]

        self.help_rect = pygame.Rect(
            self.start_x + 3 * (self.card_w + self.card_gap), self.cards_y, self.card_w, self.card_h
        )

        self.selected = 0
        self.card_imgs = [load_image(p, size=(self.card_w - 40, 190)) for p in self.image_paths]

        btn_y = self.cards_y + self.card_h + 40
        btn_w = 420
        btn_h = 70
        gap = 60
        bx = (WIDTH - (btn_w * 2 + gap)) // 2

        self.btn_quit = Button((bx, btn_y, btn_w, btn_h), "종료 (Esc)", RED, (180, 55, 55), self.font_h2)
        self.btn_start = Button((bx + btn_w + gap, btn_y, btn_w, btn_h), "시작하기 (Enter)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if event.key == pygame.K_RETURN:
                cfg = dict(self.PLAYERS[self.selected])
                cfg["IMG"] = self.image_paths[self.selected]
                self.mgr.set(GameScreen(self.mgr, cfg))
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.selected = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(event.pos):
                    self.selected = i

        if self.btn_quit.clicked(event):
            pygame.quit(); sys.exit()
        if self.btn_start.clicked(event):
            cfg = dict(self.PLAYERS[self.selected])
            cfg["IMG"] = self.image_paths[self.selected]
            self.mgr.set(GameScreen(self.mgr, cfg))

    def update(self, dt): pass

    def draw(self, surf):
        surf.fill(BLACK)
        mouse = pygame.mouse.get_pos()

        title = self.font_h1.render("MAGIC SURVIVOR - START", True, WHITE)
        surf.blit(title, (80, 70))
        sub = self.font.render("플레이어 선택 (카드/1~3) | 시작 Enter | 종료 Esc", True, (190, 190, 200))
        surf.blit(sub, (80, 132))

        for i, r in enumerate(self.card_rects):
            sel = (i == self.selected)
            border = BLUE if sel else (120, 120, 135)
            pygame.draw.rect(surf, (35, 35, 42), r, border_radius=18)
            pygame.draw.rect(surf, border, r, 3 if sel else 2, border_radius=18)

            img_area = pygame.Rect(r.x + 20, r.y + 20, r.w - 40, 190)
            pygame.draw.rect(surf, (60, 60, 70), img_area, border_radius=12)
            surf.blit(self.card_imgs[i], self.card_imgs[i].get_rect(center=img_area.center))

            name = self.font_h2.render(self.PLAYERS[i]["name"], True, WHITE)
            surf.blit(name, (r.x + 22, r.y + 230))

            hp = self.font_small.render(f"HP  {self.PLAYERS[i]['HP']}", True, (210, 210, 220))
            vel = self.font_small.render(f"VEL {self.PLAYERS[i]['VEL']}", True, (210, 210, 220))
            dmg = self.font_small.render(f"DMG x{self.PLAYERS[i]['DMG']}", True, (210, 210, 220))
            surf.blit(hp, (r.x + 22, r.y + 275))
            surf.blit(vel, (r.x + 22, r.y + 300))
            surf.blit(dmg, (r.x + 22, r.y + 325))

        draw_panel(surf, self.help_rect, "도움말", self.font_h2)
        x = self.help_rect.x + 18
        y = self.help_rect.y + 70
        lines = [
            "[플레이어]",
            "P1: HP 높음",
            "P2: 이동속도(VEL) 높음",
            "P3: 공격력(DMG) 높음",
            "",
            "[인게임]",
            "레벨업: EXP 100마다",
            "레벨업 시 스킬 선택",
            "",
            "[조작]",
            "이동: WASD / 방향키",
            "스킬 선택: 1/2/3",
        ]
        yy = y
        for ln in lines:
            txt = self.font.render(ln, True, (215, 215, 225))
            surf.blit(txt, (x, yy))
            yy += 28
            if yy > self.help_rect.bottom - 30:
                break

        self.btn_quit.draw(surf, mouse)
        self.btn_start.draw(surf, mouse)

class GameScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager, player_config: dict):
        self.mgr = mgr
        self.player_config = player_config

        self.font_h = pygame.font.SysFont("malgungothic", 36)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.font_small = pygame.font.SysFont("malgungothic", 18)

        self.player = Player(player_config)
        self.player_img = load_image(player_config.get("IMG", ""), size=(80, 80))

        # 몬스터 이미지 경로는 필요에 맞게 변경 가능
        self.img_spider = load_image(r"C:\Users\KDT43\Project1\tangtang\KHG\monster_spider.png", size=(30, 30))
        self.img_skull = load_image(r"C:\Users\KDT43\Project1\tangtang\KHG\monster_bone.png", size=(30, 30))
        self.img_midboss = load_image(r"C:\Users\KDT43\Project1\tangtang\KHG\middle_boss_dimenter.png", size=(120, 120))
        self.img_finalboss = load_image(r"C:\Users\KDT43\Project1\tangtang\KHG\final_boss_pumpkin.png", size=(150, 150))

        # 스킬 이미지(현재 파일과 같은 폴더)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.img_elec_skill = load_image(os.path.join(base_dir, r"C:\Users\KDT43\Project1\tangtang\KHG\Electric_Shock.jpg"), size=(48, 48))
        self.img_fire_skill = load_image(os.path.join(base_dir, r"C:\Users\KDT43\Project1\tangtang\KHG\Fire_Ball.jpg"), size=(60, 60))

        self.total_time = 300.0
        self.elapsed = 0.0

        self.midboss_spawn_t = 120.0
        self.finalboss_spawn_t = 240.0

        self.boss_deadline = None
        self.active_boss_kind = None
        self.midboss_spawned = False
        self.finalboss_spawned = False

        self.enemies = []
        self.bullets = []
        self.skill_projectiles = []

        self.prev_second = -1
        self.max_enemies_alive = 60

        self.weapons = [MagicGun(), FireBall(), ElectricShock(), ProtectShield()]
        self.overlay = None

        self.paused = False
        self.pause_overlay = None

        self.btn_to_start = Button((WIDTH - 290, 14, 130, 40), "나가기", RED, (180, 55, 55), pygame.font.SysFont("malgungothic", 22))
        self.btn_pause = Button((WIDTH - 150, 14, 130, 40), "Pause (P)", (90, 90, 110), (120, 120, 140), pygame.font.SysFont("malgungothic", 22))

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_overlay = PauseOverlay(self) if self.paused else None

    def handle_event(self, event):
        if self.overlay and self.overlay.active:
            self.overlay.handle_event(event)
            return

        if self.paused and self.pause_overlay and self.pause_overlay.active:
            self.pause_overlay.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.mgr.set(StartScreen(self.mgr))
            if self.btn_to_start.clicked(event):
                self.mgr.set(StartScreen(self.mgr))
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.mgr.set(StartScreen(self.mgr))
            if event.key == pygame.K_p:
                self._toggle_pause()

        if self.btn_to_start.clicked(event):
            self.mgr.set(StartScreen(self.mgr))
        if self.btn_pause.clicked(event):
            self._toggle_pause()

    def _spawn_from_edges(self, kind):
        side = random.choice(["top", "bottom", "left", "right"])
        margin = 30
        if side == "top":
            x, y = random.randint(margin, WIDTH - margin), -margin
        elif side == "bottom":
            x, y = random.randint(margin, WIDTH - margin), HEIGHT + margin
        elif side == "left":
            x, y = -margin, random.randint(80, HEIGHT - margin)
        else:
            x, y = WIDTH + margin, random.randint(80, HEIGHT - margin)

        if kind == "spider":
            return Enemy("spider", (x, y), hp=10, exp_reward=10, img=self.img_spider)
        return Enemy("skull", (x, y), hp=10, exp_reward=10, img=self.img_skull)

    def _spawn_midboss(self):
        e = Enemy("midboss", (WIDTH * 0.7, HEIGHT * 0.4), hp=500, exp_reward=500, img=self.img_midboss)
        # ✅ (4) 속도 2배
        e.speed = 240 * 2
        self.enemies.append(e)
        self.active_boss_kind = "midboss"
        self.boss_deadline = self.elapsed + 60.0
        self.midboss_spawned = True

    def _spawn_finalboss(self):
        e = Enemy("finalboss", (WIDTH * 0.7, HEIGHT * 0.4), hp=1000, exp_reward=0, img=self.img_finalboss)
        e.speed = 260
        self.enemies.append(e)
        self.active_boss_kind = "finalboss"
        self.boss_deadline = self.elapsed + 60.0
        self.finalboss_spawned = True

    def _end_game(self, success, reason=""):
        stats = {
            "success": success,
            "reason": reason,
            "survival_time": self.elapsed,
            "kill_count": self.player.kills,
            "player_config": self.player_config,
        }
        self.mgr.set(EndScreen(self.mgr, success, stats))

    def update(self, dt):
        if self.overlay and self.overlay.active:
            return
        if self.paused:
            return

        self.elapsed += dt
        if self.elapsed >= self.total_time:
            self._end_game(False, "시간 종료")
            return

        if (not self.midboss_spawned) and self.elapsed >= self.midboss_spawn_t:
            self._spawn_midboss()
        if (not self.finalboss_spawned) and self.elapsed >= self.finalboss_spawn_t:
            self._spawn_finalboss()

        if self.boss_deadline is not None and self.elapsed > self.boss_deadline:
            self._end_game(False, "보스를 제한시간 안에 처치하지 못했습니다.")
            return

        cur_sec = int(self.elapsed)
        if cur_sec != self.prev_second:
            self.prev_second = cur_sec
            if len(self.enemies) < self.max_enemies_alive:
                if cur_sec % 2 == 1:
                    self.enemies.append(self._spawn_from_edges("spider"))
                    self.enemies.append(self._spawn_from_edges("spider"))
                else:
                    self.enemies.append(self._spawn_from_edges("skull"))
                    self.enemies.append(self._spawn_from_edges("skull"))

        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)

        for w in self.weapons:
            w.update(dt, self)

        # update bullets
        for b in self.bullets[:]:
            b.update(dt)
            if b.out_of_bounds():
                self.bullets.remove(b)

        # update skill projectiles
        for sp in self.skill_projectiles[:]:
            sp.update(dt)
            if sp.dead():
                self.skill_projectiles.remove(sp)

        # enemies move
        for e in self.enemies:
            if not e.alive():
                continue

            if e.kind in ("spider", "skull"):
                dirv = self.player.pos - e.pos
                if dirv.length_squared() > 0:
                    dirv = dirv.normalize()
                e.pos += dirv * e.speed * dt

                if (e.pos - self.player.pos).length() <= (e.radius + self.player.radius):
                    self.player.hp -= 20 * dt
            else:
                e.random_change_t -= dt
                if e.random_change_t <= 0:
                    e.random_change_t = random.uniform(0.2, 0.6)
                    ang = random.uniform(0, math.tau)
                    e.random_vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * e.speed

                e.pos += e.random_vel * dt
                e.pos.x = max(60, min(WIDTH - 60, e.pos.x))
                e.pos.y = max(110, min(HEIGHT - 60, e.pos.y))

                if (e.pos - self.player.pos).length() <= (e.radius + self.player.radius):
                    self.player.hp -= 35 * dt

        # bullet collision
        for b in self.bullets[:]:
            for e in self.enemies:
                if not e.alive():
                    continue
                if (e.pos - b.pos).length() <= (e.radius + b.radius):
                    e.hp -= b.damage
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

        # skill projectile collision
        for sp in self.skill_projectiles[:]:
            for e in self.enemies:
                if not e.alive():
                    continue
                if (e.pos - sp.pos).length() <= (e.radius + sp.radius):
                    e.hp -= sp.damage
                    sp.hit_count += 1
                    if sp.hit_count >= sp.pierce:
                        if sp in self.skill_projectiles:
                            self.skill_projectiles.remove(sp)
                    break

        # death handling
        leveled = False
        alive_list = []
        for e in self.enemies:
            if e.alive():
                alive_list.append(e)
                continue

            if e.kind in ("spider", "skull"):
                self.player.kills += 1
                if self.player.add_exp(e.exp_reward):
                    leveled = True
            elif e.kind == "midboss":
                if self.player.add_exp(500):
                    leveled = True
                self.boss_deadline = None
                self.active_boss_kind = None
            elif e.kind == "finalboss":
                self._end_game(True, "최종 보스 처치!")
                return

        self.enemies = alive_list

        if self.player.hp <= 0:
            self._end_game(False, "플레이어 HP가 0이 되었습니다.")
            return

        if leveled and any(w.can_offer() for w in self.weapons):
            self.overlay = SkillChoiceOverlay(self)

    def _draw_hud(self, surf):
        bar_x, bar_y = 30, 18
        bar_w, bar_h = 520, 22

        pygame.draw.rect(surf, (45, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=10)
        ratio = 0.0 if self.player.exp_need <= 0 else (self.player.exp / self.player.exp_need)
        pygame.draw.rect(surf, (70, 160, 255), (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=10)
        pygame.draw.rect(surf, (170, 170, 185), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)

        surf.blit(self.font_small.render(f"EXP {self.player.exp}/{self.player.exp_need}", True, WHITE), (bar_x + 10, bar_y - 2))
        surf.blit(self.font.render(f"레벨 {self.player.level}", True, WHITE), (bar_x + bar_w + 18, 14))
        surf.blit(self.font.render(f"처치수 {self.player.kills}", True, WHITE), (bar_x + bar_w + 140, 14))

        remain = max(0.0, self.total_time - self.elapsed)
        surf.blit(self.font.render(f"{int(remain//60)}:{int(remain%60):02d}", True, WHITE), (WIDTH - 420, 14))

        if self.boss_deadline is not None:
            r = max(0.0, self.boss_deadline - self.elapsed)
            kind = "중간 보스" if self.active_boss_kind == "midboss" else "최종 보스"
            banner = pygame.Rect(380, 50, 520, 34)
            pygame.draw.rect(surf, (90, 40, 40), banner, border_radius=10)
            pygame.draw.rect(surf, (190, 90, 90), banner, 2, border_radius=10)
            surf.blit(self.font.render(f"{kind} 제한시간: {r:0.1f}s", True, WHITE), (banner.x + 12, banner.y + 6))

        self.btn_to_start.draw(surf, pygame.mouse.get_pos())
        self.btn_pause.draw(surf, pygame.mouse.get_pos())

    def _draw_player(self, surf):
        rect = self.player_img.get_rect(center=(int(self.player.pos.x), int(self.player.pos.y)))
        surf.blit(self.player_img, rect)
        pygame.draw.circle(surf, (20, 20, 20), (int(self.player.pos.x), int(self.player.pos.y)), self.player.radius, 2)

        # HP bar
        w, h = 160, 14
        x = int(self.player.pos.x - w / 2)
        y = int(self.player.pos.y + 34)
        pygame.draw.rect(surf, (45, 45, 55), (x, y, w, h), border_radius=8)
        ratio = max(0, self.player.hp) / max(1, self.player.max_hp)
        pygame.draw.rect(surf, (235, 80, 80), (x, y, int(w * ratio), h), border_radius=8)
        pygame.draw.rect(surf, (180, 180, 195), (x, y, w, h), 2, border_radius=8)

    def draw(self, surf):
        surf.fill(BLACK)

        arena = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 90)
        pygame.draw.rect(surf, (20, 20, 26), arena, border_radius=18)
        pygame.draw.rect(surf, (70, 70, 85), arena, 2, border_radius=18)

        self._draw_hud(surf)

        # enemies
        for e in self.enemies:
            if not e.alive():
                continue
            rect = e.img.get_rect(center=(int(e.pos.x), int(e.pos.y)))
            surf.blit(e.img, rect)

            if e.kind in ("midboss", "finalboss"):
                bw, bh = 200, 12
                bx = int(e.pos.x - bw / 2)
                by = int(e.pos.y - 70)
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=8)
                ratio = max(0, e.hp) / max(1, e.max_hp)
                pygame.draw.rect(surf, WHITE, (bx, by, int(bw * ratio), bh), border_radius=8)

        # bullets
        for b in self.bullets:
            pygame.draw.circle(surf, (255, 220, 80), (int(b.pos.x), int(b.pos.y)), b.radius)

        # skill projectiles (불/전기 이미지)
        for sp in self.skill_projectiles:
            sp.draw(surf)

        # shield drawing (if unlocked)
        for w in self.weapons:
            w.draw(surf, self)

        self._draw_player(surf)

        if self.overlay and self.overlay.active:
            self.overlay.draw(surf)

        if self.paused and self.pause_overlay and self.pause_overlay.active:
            self.pause_overlay.draw(surf)

class EndScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager, success: bool, stats: dict):
        self.mgr = mgr
        self.success = success
        self.stats = stats

        self.font_h1 = pygame.font.SysFont("malgungothic", 64)
        self.font_h2 = pygame.font.SysFont("malgungothic", 32)
        self.font = pygame.font.SysFont("malgungothic", 24)

        btn_w = 420
        btn_h = 70
        gap = 60
        bx = (WIDTH - (btn_w * 2 + gap)) // 2
        by = HEIGHT - 160

        self.btn_restart = Button((bx, by, btn_w, btn_h), "다시하기 (Enter)", BLUE, (95, 185, 255), self.font_h2)
        self.btn_to_start = Button((bx + btn_w + gap, by, btn_w, btn_h), "시작화면 (Esc)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.mgr.set(GameScreen(self.mgr, self.stats["player_config"]))
            if event.key == pygame.K_ESCAPE:
                self.mgr.set(StartScreen(self.mgr))

        if self.btn_restart.clicked(event):
            self.mgr.set(GameScreen(self.mgr, self.stats["player_config"]))
        if self.btn_to_start.clicked(event):
            self.mgr.set(StartScreen(self.mgr))

    def update(self, dt): pass

    def draw(self, surf):
        surf.fill(BLACK)
        mouse = pygame.mouse.get_pos()

        main = "GAME SUCCESS!!" if self.success else "GAME OVER!"
        col = GREEN if self.success else RED
        title = self.font_h1.render(main, True, col)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, 140)))

        panel = pygame.Rect(WIDTH // 2 - 380, 220, 760, 320)
        draw_panel(surf, panel, "결과", self.font_h2)

        t = max(0.0, float(self.stats.get("survival_time", 0.0)))
        mm = int(t // 60)
        ss = int(t % 60)
        kill = int(self.stats.get("kill_count", 0))
        reason = self.stats.get("reason", "")

        lines = [
            f"- 생존 시간: {mm}:{ss:02d}",
            f"- 처치한 몬스터 수: {kill}",
            f"- 최종 레벨: {self.stats.get('player_config', {}).get('name','')} / Lv ??? (표시 없음)",
        ]

        y = panel.y + 90
        for ln in lines[:2]:
            surf.blit(self.font.render(ln, True, (230, 230, 240)), (panel.x + 30, y))
            y += 44

        if reason:
            surf.blit(self.font.render(f"종료 사유: {reason}", True, (200, 200, 215)), (panel.x + 30, panel.y + 230))

        self.btn_restart.draw(surf, mouse)
        self.btn_to_start.draw(surf, mouse)

# -----------------------------
# Main
# -----------------------------
def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MAGIC SURVIVOR")
    clock = pygame.time.Clock()

    mgr = ScreenManager()
    mgr.set(StartScreen(mgr))

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            mgr.handle_event(event)

        mgr.update(dt)
        mgr.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()