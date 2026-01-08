# magic_survivor_all_in_one.py
# Start -> Ingame -> End
# 요구사항 반영:
# 1) 레벨업 필요 EXP: 50, 100, 150, 200 ... (레벨업할 때마다 +50)
# 2) 전기 공격 색상(표시): 노란 계열 + 전기 이미지 투사체
# 3) 파이어볼: 직선 범위 공격 X -> 총알처럼 발사되는 투사체 O
# 4) 중간 보스 이동속도 2배
# 5) 불/전기 공격: 사각형 이펙트 X -> 몬스터처럼 이미지 투사체가 날아감
# 6) ✅ 스킬 선택창: 색상 '띠' 제거 -> 카드 네모 전체에 색상(반투명) 채움 + 라운드 깔끔 처리

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

WHITE  = (245, 245, 245)
BLACK  = (12, 12, 15)
BLUE   = (70, 160, 255)
GREEN  = (60, 210, 120)
RED    = (235, 80, 80)
YELLOW = (255, 220, 80)

MAX_SKILL_LEVEL = 5

# ✅ 배경/이미지 경로(본인 경로로 수정)
BACKGROUND_PATH = r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png"
PLAYER_IMG_PATHS = [
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_1.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_2.png",
    r"C:\Users\KDT43\Project1\tangtang\KHG\player_3.png",
]
MON_SPIDER_PATH   = r"C:\Users\KDT43\Project1\tangtang\KHG\monster_spider.png"
MON_SKULL_PATH    = r"C:\Users\KDT43\Project1\tangtang\KHG\monster_bone.png"
MIDBOSS_PATH      = r"C:\Users\KDT43\Project1\tangtang\KHG\middle_boss_dimenter.png"
FINALBOSS_PATH    = r"C:\Users\KDT43\Project1\tangtang\KHG\final_boss_pumpkin.png"
ELEC_SKILL_PATH   = r"C:\Users\KDT43\Project1\tangtang\KHG\Electric_Ball.png"
FIRE_SKILL_PATH   = r"C:\Users\KDT43\Project1\tangtang\KHG\FireBall.png"

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
        pygame.draw.rect(surf, (160, 160, 170), surf.get_rect(), 3)
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

def draw_panel(surf, rect, title, title_font, body_bg=(35, 35, 42), border=(120, 120, 135)):
    pygame.draw.rect(surf, body_bg, rect, border_radius=18)
    pygame.draw.rect(surf, border, rect, 2, border_radius=18)
    if title:
        t = title_font.render(title, True, WHITE)
        surf.blit(t, (rect.x + 18, rect.y + 16))

def draw_round_rect_alpha(dst_surf, rect, color_rgba, radius=18):
    """
    ✅ 알파(투명도) 포함 라운드 사각형을 '깔끔하게' 그리기 위한 헬퍼
    - dst_surf에 바로 알파 rect를 그리려면 Surface(SRCALPHA)로 한번 그려서 blit
    """
    x, y, w, h = rect
    temp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(temp, color_rgba, temp.get_rect(), border_radius=radius)
    dst_surf.blit(temp, (x, y))

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

        # HP (레벨업 +20)
        base_hp = int(config.get("HP", 100))
        self.max_hp = base_hp
        self.hp = float(base_hp)

        self.kills = 0

    def move(self, dt, keys):
        mv = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:    mv.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  mv.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  mv.x -= 1
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

            self.max_hp += 20
            self.hp = min(self.max_hp, self.hp + 20)

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
        super().__init__(unlocked=True)
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

# ✅ 파이어볼: 총알처럼 발사되는 이미지 투사체
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
        base_dir = pygame.Vector2(mx, my) - gs.player.pos
        base_ang = math.atan2(base_dir.y, base_dir.x)

        count = min(4, self.level)
        spread = 0.18
        angles = [base_ang] if count == 1 else [base_ang + spread * (i - (count - 1) / 2) for i in range(count)]

        speed = 520 + 40 * (self.level - 1)
        dmg = (18 + 8 * (self.level - 1)) * gs.player.dmg
        pierce = 1 + (1 if self.level >= 4 else 0)

        for a in angles:
            dv = pygame.Vector2(math.cos(a), math.sin(a))
            gs.skill_projectiles.append(
                SkillProjectile(
                    pos=gs.player.pos,
                    direction=dv,
                    speed=speed,
                    damage=dmg,
                    img=gs.img_fire_skill,
                    radius=14,
                    life=2.2,
                    pierce=pierce
                )
            )

# ✅ 전기: 노란 느낌 + 이미지 투사체
class ElectricShock(WeaponBase):
    key = "elec"
    name = "전기"
    color = YELLOW

    def __init__(self):
        super().__init__(unlocked=False)
        self.cool = 2.5
        self.t = 0.0

    def update(self, dt, gs):
        if not self.unlocked:
            return
        self.t += dt
        if self.t < self.cool:
            return
        self.t -= self.cool

        count = min(4, self.level)
        base_dir = pygame.Vector2(pygame.mouse.get_pos()) - gs.player.pos
        base_ang = math.atan2(base_dir.y, base_dir.x)

        spread = 0.20
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

        self.font_h = pygame.font.SysFont("malgungothic", 44, bold=True)
        self.font   = pygame.font.SysFont("malgungothic", 22)
        self.font_name = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.font_hint = pygame.font.SysFont("malgungothic", 20)

        self.btn_rects = []
        w, h = 340, 170
        gap = 44
        total = w * 3 + gap * 2
        x0 = (WIDTH - total) // 2
        y0 = HEIGHT // 2 - 70
        for i in range(3):
            self.btn_rects.append(pygame.Rect(x0 + i * (w + gap), y0, w, h))

        self.hover_idx = -1

    def handle_event(self, event):
        if not self.active:
            return

        if event.type == pygame.MOUSEMOTION:
            self.hover_idx = -1
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(event.pos):
                    self.hover_idx = i
                    break

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

        # 전체 어둡게
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))

        title = self.font_h.render("레벨업!", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 170)))

        sub = self.font.render("스킬을 하나 선택하세요 (1/2/3 또는 클릭)", True, (230, 230, 240))
        surf.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 130)))

        # ✅ 카드 3개
        for i, r in enumerate(self.btn_rects):
            if i >= len(self.options):
                continue

            wpn = self.options[i]

            # ✅ (핵심) 카드 전체에 색상 채움(반투명) + 라운드 "확실히"
            #    - wpn.color는 RGB이므로 RGBA로 변환해서 사용
            fill_rgba = (wpn.color[0], wpn.color[1], wpn.color[2], 95)   # 카드 내부 색
            draw_round_rect_alpha(surf, r, fill_rgba, radius=20)

            # 카드 기본 바탕(짙은 반투명) 한 겹 더(가독성)
            draw_round_rect_alpha(surf, r, (25, 25, 32, 120), radius=20)

            # 테두리
            pygame.draw.rect(surf, (230, 230, 240), r, 2, border_radius=20)

            # hover 시 하이라이트(원하면 없애도 됨)
            if i == self.hover_idx:
                pygame.draw.rect(surf, (255, 255, 255), r, 3, border_radius=20)

            # 텍스트
            name = self.font_name.render(wpn.name, True, WHITE)
            lvl_line = f"현재 레벨: {wpn.level}/{MAX_SKILL_LEVEL}" if wpn.unlocked else "미해금: 선택 시 1레벨"
            lvl  = self.font.render(lvl_line, True, (240, 240, 245))
            hint = self.font_hint.render(f"[{i+1}] 선택", True, (240, 240, 245))

            surf.blit(name, (r.x + 22, r.y + 26))
            surf.blit(lvl,  (r.x + 22, r.y + 82))
            surf.blit(hint, (r.x + 22, r.y + 126))

        tip = self.font.render("※ 선택하면 게임이 계속 진행됩니다.", True, (220, 220, 230))
        surf.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 170)))

class PauseOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        self.font_h = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)

        self.btn_resume = Button(
            (WIDTH // 2 - 200, HEIGHT // 2 + 40, 400, 70),
            "계속하기 (P)", BLUE, (95, 185, 255),
            pygame.font.SysFont("malgungothic", 28, bold=True)
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
# -----------------------------
# Start Screen (UI from Game_start.py, integrated)
# -----------------------------
def draw_rounded_rect(surf, rect, color, radius=16, width=0):
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def fit_text_ellipsis(font, text, max_w):
    """텍스트가 max_w를 넘으면 ... 처리"""
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

class PlayerCard:
    def __init__(self, rect, player_data, image_surface, font_name, font_small):
        self.rect = pygame.Rect(rect)
        self.data = player_data
        self.image = image_surface
        self.font_name = font_name
        self.font_small = font_small
        self.selected = False

        self.img_rect = pygame.Rect(self.rect.x + 16, self.rect.y + 16, self.rect.w - 32, 210)
        self.text_x = self.rect.x + 18
        self.text_y = self.img_rect.bottom + 16

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

        base_col = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base_col, radius=18)

        # 선택 테두리: 더 굵고 잘 보이게(글로우 2겹)
        if self.selected:
            glow_rect = self.rect.inflate(8, 8)
            draw_rounded_rect(surf, glow_rect, (60, 160, 255), radius=22, width=7)
            draw_rounded_rect(surf, self.rect, BLUE, radius=18, width=6)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=2)

        # image frame
        draw_rounded_rect(surf, self.img_rect, (22, 22, 26), radius=14)
        draw_rounded_rect(surf, self.img_rect, (110, 110, 130), radius=14, width=2)

        img = self._get_scaled_image()
        if img:
            surf.blit(img, self.img_rect.topleft)
        else:
            ph = self.font_small.render("이미지 없음", True, (220, 220, 230))
            surf.blit(ph, ph.get_rect(center=self.img_rect.center))

        # Name
        name = self.font_name.render(self.data["name"], True, WHITE)
        surf.blit(name, (self.text_x, self.text_y))

        # Stats (간격 여유)
        max_w = self.rect.w - 36
        stats_y0 = self.text_y + 58
        stats_gap = 32

        hp_line = f"HP    {self.data['HP']}"
        vel_line = f"SPEED {self.data['VEL']}"
        dmg_line = f"DMG   x{self.data['DMG']}"

        surf.blit(self.font_small.render(fit_text_ellipsis(self.font_small, hp_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 0))
        surf.blit(self.font_small.render(fit_text_ellipsis(self.font_small, vel_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 1))
        surf.blit(self.font_small.render(fit_text_ellipsis(self.font_small, dmg_line, max_w), True, (210, 210, 220)),
                  (self.text_x, stats_y0 + stats_gap * 2))

    def hit_test(self, pos):
        return self.rect.collidepoint(pos)

class HelpPanel:
    def __init__(self, rect, help_lines, font_title, font_body):
        self.rect = pygame.Rect(rect)
        self.lines = help_lines
        self.font_title = font_title
        self.font_body = font_body

    def draw(self, surf):
        draw_rounded_rect(surf, self.rect, (42, 42, 50), radius=18)
        draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=3)

        title = self.font_title.render("도움말", True, WHITE)
        surf.blit(title, (self.rect.x + 16, self.rect.y + 16))

        y = self.rect.y + 62
        x = self.rect.x + 16
        max_w = self.rect.w - 32

        for ln in self.lines:
            txt = fit_text_ellipsis(self.font_body, ln, max_w)
            surf.blit(self.font_body.render(txt, True, (230, 230, 240)), (x, y))
            y += 24
            if y > self.rect.bottom - 20:
                break

class StartScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager):
        self.mgr = mgr

        # Fonts
        self.font_title = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font_h2 = pygame.font.SysFont("malgungothic", 26, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 20)
        self.font_small = pygame.font.SysFont("malgungothic", 16)

        self.PLAYERS = [
            {"id": "tank",   "name": "플레이어 1", "HP": 200, "VEL": 240, "DMG": 1.0},
            {"id": "speed",  "name": "플레이어 2", "HP": 100, "VEL": 400, "DMG": 1.0},
            {"id": "damage", "name": "플레이어 3", "HP": 100, "VEL": 240, "DMG": 1.5},
        ]

        # 이미지 경로 (원본 로직 유지)
        self.image_paths = [
            r"C:\Users\KDT43\Project1\tangtang\KHG\player_1.png",
            r"C:\Users\KDT43\Project1\tangtang\KHG\player_2.png",
            r"C:\Users\KDT43\Project1\tangtang\KHG\player_3.png",
        ]

        # Background
        try:
            self.bg = load_background_scaled(r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png")
        except Exception:
            self.bg = None

        # Layout
        self.selected = 0
        self.card_w, self.card_h = 250, 420
        self.gap = 30
        self.y_cards = 170

        total_w = self.card_w * 4 + self.gap * 3
        self.start_x = (WIDTH - total_w) // 2

        self.card_imgs = [load_image(p, size=(self.card_w - 32, 210)) for p in self.image_paths]

        self.cards = []
        for i in range(3):
            rect = (self.start_x + i * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
            self.cards.append(PlayerCard(rect, self.PLAYERS[i], self.card_imgs[i], self.font_h2, self.font_small))

        help_rect = (self.start_x + 3 * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
        help_lines = [
            "[플레이어 특징]",
            "P1: HP 높음",
            "P2: 이동속도(SPEED) 높음",
            "P3: 공격력(DMG) 높음",
            "",
            "[인게임 규칙]",
            "레벨업: EXP 50, 100, 150 ...",
            "레벨업 시 스킬 선택",
            "",
            "[조작 방법]",
            "이동: WASD / 방향키",
            "일시정지: P 또는 Pause",
            "스킬 선택: 1/2/3 또는 클릭",
        ]
        self.help_panel = HelpPanel(help_rect, help_lines, self.font_h2, self.font_small)

        self._sync_selected()

        # Bottom Buttons
        btn_w, btn_h = 500, 60
        btn_gap = 60
        btn_y = HEIGHT - 100
        total_btn = btn_w * 2 + btn_gap
        btn_x = (WIDTH - total_btn) // 2

        self.btn_quit = Button((btn_x, btn_y, btn_w, btn_h), "종료 (Esc)", RED, (180, 55, 55), self.font_h2, radius=18)
        self.btn_start = Button((btn_x + btn_w + btn_gap, btn_y, btn_w, btn_h), "시작하기 (Enter)", GREEN, (45, 185, 110), self.font_h2, radius=18)

    def _sync_selected(self):
        for i, c in enumerate(self.cards):
            c.selected = (i == self.selected)

    def _start_game(self):
        cfg = dict(self.PLAYERS[self.selected])
        cfg["IMG"] = self.image_paths[self.selected]
        self.mgr.set(GameScreen(self.mgr, cfg))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if event.key == pygame.K_RETURN:
                self._start_game()
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.selected = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]
                self._sync_selected()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, card in enumerate(self.cards):
                if card.hit_test(event.pos):
                    self.selected = i
                    self._sync_selected()
                    break

        if self.btn_quit.clicked(event):
            pygame.quit(); sys.exit()
        if self.btn_start.clicked(event):
            self._start_game()

    def update(self, dt): 
        pass

    def draw(self, surf):
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((18, 18, 24))

        mouse = pygame.mouse.get_pos()

        # Title (shadow + main)
        t_shadow = self.font_title.render("MAGIC SURVIVOR", True, (0, 0, 0))
        t_main = self.font_title.render("MAGIC SURVIVOR", True, WHITE)
        surf.blit(t_shadow, (82, 74))
        surf.blit(t_main, (80, 72))

        # Cards + Help
        for c in self.cards:
            c.draw(surf, mouse)
        self.help_panel.draw(surf)

        # Bottom panel (반투명, 배경이 보이게)
        bar_h = 130
        bar_rect = pygame.Rect(0, HEIGHT - bar_h, WIDTH, bar_h)
        panel = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 80))
        surf.blit(panel, bar_rect.topleft)
        pygame.draw.line(surf, (90, 90, 110), (0, HEIGHT - bar_h), (WIDTH, HEIGHT - bar_h), 2)

        self.btn_quit.draw(surf, mouse)
        self.btn_start.draw(surf, mouse)



class GameScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager, player_config: dict):
        self.mgr = mgr
        self.player_config = player_config

        self.font_h = pygame.font.SysFont("malgungothic", 36, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.font_small = pygame.font.SysFont("malgungothic", 18)

        self.player = Player(player_config)
        self.player_img = load_image(player_config.get("IMG", ""), size=(75, 75))

        self.img_spider   = load_image(MON_SPIDER_PATH, size=(30, 30))
        self.img_skull    = load_image(MON_SKULL_PATH, size=(30, 30))
        self.img_midboss  = load_image(MIDBOSS_PATH, size=(120, 120))
        self.img_finalboss= load_image(FINALBOSS_PATH, size=(150, 150))

        self.img_elec_skill = load_image(ELEC_SKILL_PATH, size=(80, 80))
        self.img_fire_skill = load_image(FIRE_SKILL_PATH, size=(60, 60))

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

        self.bg = load_background_scaled(BACKGROUND_PATH)

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
            return Enemy("spider", (x, y), hp=10, exp_reward=5, img=self.img_spider)
        return Enemy("skull", (x, y), hp=10, exp_reward=5, img=self.img_skull)

    def _spawn_midboss(self):
        e = Enemy("midboss", (WIDTH * 0.7, HEIGHT * 0.4), hp=500, exp_reward=2000, img=self.img_midboss)
        e.speed = 240 * 2  # ✅ 중간 보스 속도 2배
        self.enemies.append(e)
        self.active_boss_kind = "midboss"
        self.boss_deadline = self.elapsed + 60.0
        self.midboss_spawned = True

    def _spawn_finalboss(self):
        e = Enemy("finalboss", (WIDTH * 0.7, HEIGHT * 0.4), hp=1500, exp_reward=0, img=self.img_finalboss)
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
                for _ in range(4):
                    kind = random.choice(["spider", "skull"])
                    self.enemies.append(self._spawn_from_edges(kind))

        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)

        for w in self.weapons:
            w.update(dt, self)

        for b in self.bullets[:]:
            b.update(dt)
            if b.out_of_bounds():
                self.bullets.remove(b)

        for sp in self.skill_projectiles[:]:
            sp.update(dt)
            if sp.dead():
                self.skill_projectiles.remove(sp)

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

        for b in self.bullets[:]:
            for e in self.enemies:
                if not e.alive():
                    continue
                if (e.pos - b.pos).length() <= (e.radius + b.radius):
                    e.hp -= b.damage
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

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

        w, h = 100, 20
        x = int(self.player.pos.x - w / 2)
        y = int(self.player.pos.y + 34)
        pygame.draw.rect(surf, (45, 45, 55), (x, y, w, h), border_radius=8)
        ratio = max(0, self.player.hp) / max(1, self.player.max_hp)
        pygame.draw.rect(surf, (235, 80, 80), (x, y, int(w * ratio), h), border_radius=8)
        pygame.draw.rect(surf, (180, 180, 195), (x, y, w, h), 2, border_radius=8)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))

        arena = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 90)
        pygame.draw.rect(surf, (70, 70, 85), arena, 2, border_radius=18)

        self._draw_hud(surf)

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

        for b in self.bullets:
            pygame.draw.circle(surf, (255, 220, 80), (int(b.pos.x), int(b.pos.y)), b.radius)

        for sp in self.skill_projectiles:
            sp.draw(surf)

        for w in self.weapons:
            w.draw(surf, self)

        self._draw_player(surf)

        if self.overlay and self.overlay.active:
            self.overlay.draw(surf)

        if self.paused and self.pause_overlay and self.pause_overlay.active:
            self.pause_overlay.draw(surf)



# -----------------------------
# End Screen (UI from Game_Finish.py, integrated)
# -----------------------------
def draw_glass_panel(surf, rect, radius=20, fill=(255, 255, 255, 235), outline=(120, 120, 130, 255), outline_w=2):
    """반투명 유리 느낌 패널(라운드)"""
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, outline, panel.get_rect(), width=outline_w, border_radius=radius)
    surf.blit(panel, (rect.x, rect.y))

class EndScreen(ScreenBase):
    def __init__(self, mgr: ScreenManager, success: bool, stats: dict):
        self.mgr = mgr
        self.success = success
        self.stats = stats

        self.font_title = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font_h2 = pygame.font.SysFont("malgungothic", 32, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 24)

        # Background
        try:
            self.bg = load_background_scaled(r"C:\Users\KDT43\Project1\tangtang\KHG\game_background.png")
        except Exception:
            self.bg = None

        # Buttons
        btn_w = 380
        btn_h = 64
        gap = 44
        bx = (WIDTH - (btn_w * 2 + gap)) // 2

        panel_w = 760
        panel_h = 360
        panel_x = (WIDTH - panel_w) // 2
        panel_y = 200

        btn_y = panel_y + panel_h + 26

        self.btn_restart = Button((bx, btn_y, btn_w, btn_h), "다시하기 (Enter)", BLUE, (95, 185, 255), self.font_h2, radius=18)
        self.btn_to_start = Button((bx + btn_w + gap, btn_y, btn_w, btn_h), "시작화면 (Esc)", GREEN, (45, 185, 110), self.font_h2, radius=18)

        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

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

    def update(self, dt): 
        pass

    def draw(self, surf):
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((12, 12, 18))
        mouse = pygame.mouse.get_pos()

        # Title
        main = "GAME SUCCESS!!" if self.success else "GAME OVER!"
        col = (60, 210, 120) if self.success else (235, 80, 80)
        title = self.font_title.render(main, True, col)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, 120)))

        # Glass result panel
        draw_glass_panel(surf, self.panel_rect, radius=26, fill=(245, 245, 245, 240), outline=(160, 160, 170, 255), outline_w=2)

        # Panel title
        hdr = self.font_h2.render("결과", True, (0, 0, 0))
        surf.blit(hdr, (self.panel_rect.x + 32, self.panel_rect.y + 26))

        t = max(0.0, float(self.stats.get("survival_time", 0.0)))
        mm = int(t // 60)
        ss = int(t % 60)
        kill = int(self.stats.get("kill_count", 0))
        reason = str(self.stats.get("reason", "")).strip()

        px = self.panel_rect.x + 32
        py = self.panel_rect.y + 92

        # Black text (요구사항)
        surf.blit(self.font.render(f"생존 시간: {mm}:{ss:02d}", True, (0, 0, 0)), (px, py))
        surf.blit(self.font.render(f"처치한 몬스터 수: {kill}", True, (0, 0, 0)), (px, py + 44))

        # 종료 사유(너무 아래로 내려가지 않게 패널 하단에서 여유)
        if reason:
            reason_y = self.panel_rect.y + self.panel_rect.h - 96
            surf.blit(self.font.render(f"종료 사유: {reason}", True, (0, 0, 0)), (px, reason_y))

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