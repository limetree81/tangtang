import os
import sys
import math
import random
import pygame
import json
from abc import ABC, abstractmethod

# -----------------------------
# 1. Config & Constants
# -----------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "assets/")

WHITE = (245, 245, 245)
BLACK = (12, 12, 15)
BLUE = (70, 160, 255)
GREEN = (60, 210, 120)
RED = (235, 80, 80)
YELLOW = (255, 220, 80)

MAX_SKILL_LEVEL = 5
EXP_BASE = 50
EXP_INC = 50

def exp_need_for_level(next_level: int) -> int:
    return EXP_BASE + EXP_INC * (next_level - 1)

# -----------------------------
# 2. ResourceManager (Image Loader & Cacher)
# -----------------------------
class ResourceManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
        self.images = {}

    def get_image(self, name, size, color=(70, 70, 80)):
        # name이 전체 경로인 경우 파일명만 추출하거나 그대로 사용
        file_name = os.path.basename(name)
        cache_key = f"{file_name}_{size}"
        if cache_key in self.images:
            return self.images[cache_key]
        
        # 에셋 폴더 또는 직접 경로 확인
        search_paths = [os.path.join(ASSET_DIR, file_name), name]
        for path in search_paths:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    if size:
                        img = pygame.transform.smoothscale(img, size)
                    self.images[cache_key] = img
                    return img
                except:
                    pass
        
        # 이미지 로드 실패 시 대체 도형 생성 (InGame1 스타일의 NO IMG 박스)
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
# 3. Game Controller (Logic Handler)
# -----------------------------
class GameController:
    """게임의 엔티티들과 진행 상태를 중앙 관리"""
    def __init__(self, rm, player_config):
        self.rm = rm
        self.player_config = player_config
        self.reset()

    def reset(self):
        self.player = Player(self.player_config)
        self.enemies = []
        self.bullets = []
        self.skill_projectiles = []
        self.elapsed = 0.0
        self.total_time = 300.0
        self.state = "PLAYING"
        
        self.midboss_spawned = False
        self.finalboss_spawned = False
        self.boss_deadline = None
        self.active_boss_kind = None

# -----------------------------
# 4. Entities & Weapons
# -----------------------------
class Player:
    def __init__(self, config):
        self.pos = pygame.Vector2(WIDTH * 0.5, HEIGHT * 0.55)
        self.radius = 18
        self.vel = float(config.get("VEL", 240))
        self.dmg = float(config.get("DMG", 1.0))
        self.level = 0
        self.exp = 0
        self.exp_need = exp_need_for_level(1)
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
        if mv.length_squared() > 0: mv = mv.normalize()
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
            self.max_hp += 10
            self.hp = min(self.max_hp, self.hp + 10)
            self.exp_need = exp_need_for_level(self.level + 1)
        return leveled_up

class Enemy:
    def __init__(self, kind, pos, hp, exp_reward, img, radius=18):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.hp = float(hp); self.max_hp = float(hp)
        self.exp_reward = int(exp_reward); self.radius = radius; self.img = img
        self.speed = 110 if kind in ("spider", "skull") else 220
        self.random_vel = pygame.Vector2(0, 0); self.random_change_t = 0.0
    def alive(self): return self.hp > 0

class Bullet:
    def __init__(self, pos, direction, damage):
        self.pos = pygame.Vector2(pos); self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0: self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize(); self.speed = 700; self.damage = float(damage); self.radius = 5
    def update(self, dt): self.pos += self.dir * self.speed * dt
    def out_of_bounds(self): return self.pos.x < -50 or self.pos.x > WIDTH + 50 or self.pos.y < -50 or self.pos.y > HEIGHT + 50

class SkillProjectile:
    def __init__(self, pos, direction, speed, damage, img, radius=12, life=2.0, pierce=1):
        self.pos = pygame.Vector2(pos); self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0: self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize(); self.speed = float(speed); self.damage = float(damage); self.img = img
        self.radius = int(radius); self.life = float(life); self.pierce = int(pierce); self.hit_count = 0
        ang = math.degrees(math.atan2(self.dir.y, self.dir.x))
        self.rot_img = pygame.transform.rotate(self.img, -ang)
    def update(self, dt): self.life -= dt; self.pos += self.dir * self.speed * dt
    def dead(self): return self.life <= 0 or self.pos.x < -200 or self.pos.x > WIDTH + 200 or self.pos.y < -200 or self.pos.y > HEIGHT + 200
    def draw(self, surf):
        r = self.rot_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surf.blit(self.rot_img, r)

class WeaponBase:
    def __init__(self, unlocked=False): self.unlocked = unlocked; self.level = 1 if unlocked else 0
    def is_max(self): return self.unlocked and self.level >= MAX_SKILL_LEVEL
    def can_offer(self): return not self.is_max()
    def acquire_or_level(self):
        if not self.unlocked: self.unlocked = True; self.level = 1; return
        if self.level < MAX_SKILL_LEVEL: self.level += 1
    def update(self, dt, gs): pass
    def draw(self, surf, gs): pass

class MagicGun(WeaponBase):
    key = "gun"; name = "마법 총"; color = BLUE
    def __init__(self): super().__init__(unlocked=True); self.cool = 1.0; self.t = 0.0
    def update(self, dt, gs):
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos(); dirv = pygame.Vector2(mx, my) - gs.controller.player.pos
        base_ang = math.atan2(dirv.y, dirv.x); count = max(1, int(self.level)); dmg = 10 * gs.controller.player.dmg
        spread = 0.22; angles = [base_ang] if count == 1 else [base_ang + spread*(i-(count-1)/2) for i in range(count)]
        for a in angles: gs.controller.bullets.append(Bullet(gs.controller.player.pos, pygame.Vector2(math.cos(a), math.sin(a)), dmg))

class FireBall(WeaponBase):
    key = "fire"; name = "파이어볼"; color = (255, 140, 110)
    def __init__(self): super().__init__(unlocked=False); self.cool = 1.8; self.t = 0.0
    def update(self, dt, gs):
        if not self.unlocked: return
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos(); dirv = pygame.Vector2(mx, my) - gs.controller.player.pos
        speed = 520+40*(self.level-1); dmg = (18+8*(self.level-1))*gs.controller.player.dmg
        gs.controller.skill_projectiles.append(SkillProjectile(gs.controller.player.pos, dirv, speed, dmg, gs.img_fire_skill, 14, 2.2, 1+(1 if self.level>=4 else 0)))

class ElectricShock(WeaponBase):
    key = "elec"; name = "전기"; color = YELLOW
    def __init__(self): super().__init__(unlocked=False); self.cool = 2.3; self.t = 0.0
    def update(self, dt, gs):
        if not self.unlocked: return
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos(); base_dir = pygame.Vector2(mx, my) - gs.controller.player.pos
        base_ang = math.atan2(base_dir.y, base_dir.x); count = min(4, self.level); spread = 0.18
        angles = [base_ang] if count == 1 else [base_ang + spread*(i-(count-1)/2) for i in range(count)]
        for a in angles: gs.controller.skill_projectiles.append(SkillProjectile(gs.controller.player.pos, pygame.Vector2(math.cos(a), math.sin(a)), 650+30*(self.level-1), (14+6*(self.level-1))*gs.controller.player.dmg, gs.img_elec_skill, 12, 1.8, 1+(1 if self.level>=5 else 0)))

class ProtectShield(WeaponBase):
    key = "shield"; name = "보호막"; color = (140, 255, 180)
    def __init__(self): super().__init__(unlocked=False); self.tick = 0.0; self.tick_interval = 0.5
    def update(self, dt, gs):
        if not self.unlocked: return
        self.tick += dt
        if self.tick < self.tick_interval: return
        self.tick -= self.tick_interval
        rad = 50+50*(self.level-1); dmg = 10*gs.controller.player.dmg
        for e in gs.controller.enemies:
            if e.alive() and (e.pos - gs.controller.player.pos).length_squared() <= (rad + e.radius)**2: e.hp -= dmg
    def draw(self, surf, gs):
        if self.unlocked: pygame.draw.circle(surf, (120, 255, 180), (int(gs.controller.player.pos.x), int(gs.controller.player.pos.y)), 50+50*(self.level-1), 3)

# -----------------------------
# 5. UI Helpers
# -----------------------------
class Button:
    def __init__(self, rect, text, color, hover, font, text_color=WHITE, radius=14):
        self.rect = pygame.Rect(rect); self.text = text; self.color = color; self.hover = hover; self.font = font; self.text_color = text_color; self.radius = radius
    def draw(self, surf, mouse_pos):
        c = self.hover if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=self.radius)
        pygame.draw.rect(surf, (220, 220, 230), self.rect, 2, border_radius=self.radius)
        l = self.font.render(self.text, True, self.text_color); surf.blit(l, l.get_rect(center=self.rect.center))
    def clicked(self, event): return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

def draw_panel(surf, rect, title, title_font, body_bg=(35, 35, 42), border=(120, 120, 135)):
    pygame.draw.rect(surf, body_bg, rect, border_radius=18)
    pygame.draw.rect(surf, border, rect, 2, border_radius=18)
    if title: surf.blit(title_font.render(title, True, WHITE), (rect.x + 18, rect.y + 16))

# -----------------------------
# 6. Screens
# -----------------------------
class StartScreen:
    def __init__(self, mgr, rm):
        self.mgr = mgr; self.rm = rm
        self.font_h1 = pygame.font.SysFont("malgungothic", 52); self.font_h2 = pygame.font.SysFont("malgungothic", 20); self.font = pygame.font.SysFont("malgungothic", 20); self.font_small = pygame.font.SysFont("malgungothic", 16)
        self.PLAYERS = [{"id": "tank", "name": "플레이어 1", "HP": 130, "VEL": 240, "DMG": 1.0}, {"id": "speed", "name": "플레이어 2", "HP": 100, "VEL": 290, "DMG": 1.0}, {"id": "damage", "name": "플레이어 3", "HP": 100, "VEL": 240, "DMG": 1.3}]
        self.image_paths = [r"assets\player1.jpg", r"assets\player2.jpg", r"assets\player3.jpg"]
        self.card_w, self.card_h, self.card_gap = 280, 390, 26
        total_w = self.card_w * 4 + self.card_gap * 3; self.start_x = (WIDTH - total_w) // 2; self.cards_y = 170
        self.card_rects = [pygame.Rect(self.start_x + i * (self.card_w + self.card_gap), self.cards_y, self.card_w, self.card_h) for i in range(3)]
        self.help_rect = pygame.Rect(self.start_x + 3 * (self.card_w + self.card_gap), self.cards_y, self.card_w, self.card_h)
        self.selected = 0
        # ✅ ResourceManager 사용
        self.card_imgs = [self.rm.get_image(p, (self.card_w - 40, 190)) for p in self.image_paths]
        bx = (WIDTH - (420 * 2 + 60)) // 2; btn_y = self.cards_y + self.card_h + 40
        self.btn_quit = Button((bx, btn_y, 420, 70), "종료 (Esc)", RED, (180, 55, 55), self.font_h2)
        self.btn_start = Button((bx + 420 + 60, btn_y, 420, 70), "시작하기 (Enter)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if event.key == pygame.K_RETURN: self._start_game()
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3): self.selected = event.key - pygame.K_1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(event.pos): self.selected = i
        if self.btn_quit.clicked(event): pygame.quit(); sys.exit()
        if self.btn_start.clicked(event): self._start_game()

    def _start_game(self):
        cfg = dict(self.PLAYERS[self.selected]); cfg["IMG"] = self.image_paths[self.selected]
        self.mgr.set(GameScreen(self.mgr, cfg, self.rm))

    def update(self, dt): pass
    def draw(self, surf):
        surf.fill(BLACK); mouse = pygame.mouse.get_pos()
        surf.blit(self.font_h1.render("MAGIC SURVIVOR - START", True, WHITE), (80, 70))
        surf.blit(self.font.render("플레이어 선택 (카드/1~3) | 시작 Enter | 종료 Esc", True, (190, 190, 200)), (80, 132))
        for i, r in enumerate(self.card_rects):
            sel = (i == self.selected); border = BLUE if sel else (120, 120, 135)
            pygame.draw.rect(surf, (35, 35, 42), r, border_radius=18)
            pygame.draw.rect(surf, border, r, 3 if sel else 2, border_radius=18)
            img_area = pygame.Rect(r.x + 20, r.y + 20, r.w - 40, 190); pygame.draw.rect(surf, (60, 60, 70), img_area, border_radius=12)
            surf.blit(self.card_imgs[i], self.card_imgs[i].get_rect(center=img_area.center))
            surf.blit(self.font_h2.render(self.PLAYERS[i]["name"], True, WHITE), (r.x + 22, r.y + 230))
            for j, k in enumerate(["HP", "VEL", "DMG"]):
                val = self.PLAYERS[i][k]; val_str = f"x{val}" if k=="DMG" else str(val)
                surf.blit(self.font_small.render(f"{k}  {val_str}", True, (210, 210, 220)), (r.x + 22, r.y + 275 + j*25))
        draw_panel(surf, self.help_rect, "도움말", self.font_h2)
        yy = self.help_rect.y + 70
        for ln in ["[플레이어]", "P1: HP 높음", "P2: 이동속도 높음", "P3: 공격력 높음", "", "[인게임]", "레벨업: EXP 획득 시", "레벨업 시 스킬 선택", "", "[조작]", "이동: WASD / 방향키"]:
            surf.blit(self.font.render(ln, True, (215, 215, 225)), (self.help_rect.x + 18, yy)); yy += 28
        self.btn_quit.draw(surf, mouse); self.btn_start.draw(surf, mouse)

class GameScreen:
    def __init__(self, mgr, player_config, rm):
        self.mgr = mgr; self.rm = rm
        # ✅ GameController가 게임 데이터 로딩/관리 담당
        self.controller = GameController(rm, player_config)
        self.font_h = pygame.font.SysFont("malgungothic", 36); self.font = pygame.font.SysFont("malgungothic", 22); self.font_small = pygame.font.SysFont("malgungothic", 18)
        # ✅ ResourceManager 사용
        self.player_img = self.rm.get_image(player_config.get("IMG", ""), (80, 80))
        self.img_spider = self.rm.get_image(r"assets\monster_spider.png", (30, 30))
        self.img_skull = self.rm.get_image(r"assets\monster_bone.png", (30, 30))
        self.img_midboss = self.rm.get_image(r"assets\middle_boss_dimenter.png", (120, 120))
        self.img_finalboss = self.rm.get_image(r"assets\final_boss_pumpkin.png", (150, 150))
        self.img_elec_skill = self.rm.get_image("Electric_Shock.jpg", (48, 48))
        self.img_fire_skill = self.rm.get_image("Fire_Ball.jpg", (60, 60))
        self.weapons = [MagicGun(), FireBall(), ElectricShock(), ProtectShield()]
        self.overlay, self.paused, self.prev_second = None, False, -1
        self.btn_to_start = Button((WIDTH - 290, 14, 130, 40), "나가기", RED, (180, 55, 55), self.font)
        self.btn_pause = Button((WIDTH - 150, 14, 130, 40), "Pause (P)", (90, 90, 110), (120, 120, 140), self.font)

    def handle_event(self, event):
        if self.overlay and self.overlay.active: self.overlay.handle_event(event); return
        if self.paused:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p: self.paused = False
            if self.btn_to_start.clicked(event): self.mgr.set(StartScreen(self.mgr, self.rm))
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.mgr.set(StartScreen(self.mgr, self.rm))
            if event.key == pygame.K_p: self.paused = True
        if self.btn_to_start.clicked(event): self.mgr.set(StartScreen(self.mgr, self.rm))
        if self.btn_pause.clicked(event): self.paused = True

    def update(self, dt):
        if self.paused or (self.overlay and self.overlay.active): return
        c = self.controller; c.elapsed += dt
        if c.elapsed >= c.total_time: self._end_game(False, "시간 종료"); return
        if not c.midboss_spawned and c.elapsed >= 120: self._spawn_boss("midboss")
        if not c.finalboss_spawned and c.elapsed >= 240: self._spawn_boss("finalboss")
        if c.boss_deadline and c.elapsed > c.boss_deadline: self._end_game(False, "보스 처치 시간 초과")
        cur_sec = int(c.elapsed)
        if cur_sec != self.prev_second:
            self.prev_second = cur_sec
            if len(c.enemies) < 60:
                side = random.choice(["top", "bottom", "left", "right"])
                x = random.randint(30, WIDTH-30) if side in ("top", "bottom") else (-30 if side=="left" else WIDTH+30)
                y = (-30 if side=="top" else HEIGHT+30) if side in ("top", "bottom") else random.randint(80, HEIGHT-30)
                kind = "spider" if cur_sec % 2 == 1 else "skull"
                c.enemies.append(Enemy(kind, (x, y), 10, 10, self.img_spider if kind=="spider" else self.img_skull))
        keys = pygame.key.get_pressed(); c.player.move(dt, keys)
        for w in self.weapons: w.update(dt, self)
        for b in c.bullets[:]:
            b.update(dt)
            if b.out_of_bounds(): c.bullets.remove(b)
        for sp in c.skill_projectiles[:]:
            sp.update(dt)
            if sp.dead(): c.skill_projectiles.remove(sp)
        for e in c.enemies[:]:
            if not e.alive(): continue
            if e.kind in ("spider", "skull"):
                dv = c.player.pos - e.pos
                if dv.length_squared() > 0: e.pos += dv.normalize() * e.speed * dt
                if (e.pos - c.player.pos).length() <= (e.radius + c.player.radius): c.player.hp -= 20 * dt
            else:
                e.random_change_t -= dt
                if e.random_change_t <= 0: e.random_change_t = random.uniform(0.2, 0.6); ang = random.uniform(0, math.tau); e.random_vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * e.speed
                e.pos += e.random_vel * dt; e.pos.x = max(60, min(WIDTH-60, e.pos.x)); e.pos.y = max(110, min(HEIGHT-60, e.pos.y))
                if (e.pos - c.player.pos).length() <= (e.radius + c.player.radius): c.player.hp -= 35 * dt
            for b in c.bullets[:]:
                if (e.pos - b.pos).length() <= (e.radius + b.radius):
                    e.hp -= b.damage
                    if b in c.bullets: c.bullets.remove(b)
            for sp in c.skill_projectiles[:]:
                if (e.pos - sp.pos).length() <= (e.radius + sp.radius):
                    e.hp -= sp.damage; sp.hit_count += 1
                    if sp.hit_count >= sp.pierce and sp in c.skill_projectiles: c.skill_projectiles.remove(sp)
            if not e.alive():
                if e.kind in ("spider", "skull"):
                    c.player.kills += 1
                    if c.player.add_exp(e.exp_reward): self.overlay = SkillChoiceOverlay(self)
                elif e.kind == "midboss": c.player.add_exp(500); c.boss_deadline = None; c.active_boss_kind = None
                elif e.kind == "finalboss": self._end_game(True, "최종 보스 처치!")
                c.enemies.remove(e)
        if c.player.hp <= 0: self._end_game(False, "플레이어 HP 소진")

    def _spawn_boss(self, kind):
        c = self.controller; is_mid = (kind == "midboss")
        e = Enemy(kind, (WIDTH*0.7, HEIGHT*0.4), 500 if is_mid else 1000, 500 if is_mid else 0, self.img_midboss if is_mid else self.img_finalboss, 36 if is_mid else 72)
        e.speed = 480 if is_mid else 260; c.enemies.append(e); c.active_boss_kind = kind; c.boss_deadline = c.elapsed + 60.0
        if is_mid: c.midboss_spawned = True
        else: c.finalboss_spawned = True

    def _end_game(self, success, reason):
        self.mgr.set(EndScreen(self.mgr, success, {"survival_time": self.controller.elapsed, "kill_count": self.controller.player.kills, "player_config": self.controller.player_config, "reason": reason}, self.rm))

    def draw(self, surf):
        surf.fill(BLACK); arena = pygame.Rect(20, 70, WIDTH - 40, HEIGHT - 90); pygame.draw.rect(surf, (20, 20, 26), arena, border_radius=18); pygame.draw.rect(surf, (70, 70, 85), arena, 2, border_radius=18)
        c = self.controller; bar_x, bar_y, bar_w, bar_h = 30, 18, 520, 22
        pygame.draw.rect(surf, (45, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=10); pygame.draw.rect(surf, BLUE, (bar_x, bar_y, int(bar_w * (c.player.exp/c.player.exp_need)), bar_h), border_radius=10); pygame.draw.rect(surf, (170, 170, 185), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)
        surf.blit(self.font_small.render(f"EXP {c.player.exp}/{c.player.exp_need}", True, WHITE), (bar_x+10, bar_y-2)); surf.blit(self.font.render(f"레벨 {c.player.level}", True, WHITE), (bar_x+bar_w+18, 14)); surf.blit(self.font.render(f"처치수 {c.player.kills}", True, WHITE), (bar_x+bar_w+140, 14))
        rem = max(0.0, c.total_time - c.elapsed); surf.blit(self.font.render(f"{int(rem//60)}:{int(rem%60):02d}", True, WHITE), (WIDTH - 420, 14))
        if c.boss_deadline:
            r = max(0.0, c.boss_deadline - c.elapsed); banner = pygame.Rect(380, 50, 520, 34); pygame.draw.rect(surf, (90, 40, 40), banner, border_radius=10); pygame.draw.rect(surf, (190, 90, 90), banner, 2, border_radius=10)
            surf.blit(self.font.render(f"{'중간 보스' if c.active_boss_kind=='midboss' else '최종 보스'} 제한시간: {r:0.1f}s", True, WHITE), (banner.x + 12, banner.y + 6))
        self.btn_to_start.draw(surf, pygame.mouse.get_pos()); self.btn_pause.draw(surf, pygame.mouse.get_pos())
        for e in c.enemies:
            surf.blit(e.img, e.img.get_rect(center=e.pos))
            if e.kind in ("midboss", "finalboss"):
                bx, by, bw, bh = int(e.pos.x - 100), int(e.pos.y - 70), 200, 12
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=8); pygame.draw.rect(surf, WHITE, (bx, by, int(bw * (e.hp/e.max_hp)), bh), border_radius=8)
        for b in c.bullets: pygame.draw.circle(surf, YELLOW, (int(b.pos.x), int(b.pos.y)), b.radius)
        for sp in c.skill_projectiles: sp.draw(surf)
        for w in self.weapons: w.draw(surf, self)
        p_rect = self.player_img.get_rect(center=c.player.pos); surf.blit(self.player_img, p_rect); pygame.draw.circle(surf, (20,20,20), (int(c.player.pos.x), int(c.player.pos.y)), c.player.radius, 2)
        px, py, pw, ph = int(c.player.pos.x - 80), int(c.player.pos.y + 34), 160, 14
        pygame.draw.rect(surf, (45, 45, 55), (px, py, pw, ph), border_radius=8); pygame.draw.rect(surf, RED, (px, py, int(pw * (c.player.hp/c.player.max_hp)), ph), border_radius=8); pygame.draw.rect(surf, (180, 180, 195), (px, py, pw, ph), 2, border_radius=8)
        if self.overlay and self.overlay.active: self.overlay.draw(surf)
        if self.paused:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0,0,0,170)); surf.blit(ov, (0,0))
            surf.blit(pygame.font.SysFont("malgungothic", 64).render("PAUSED", True, WHITE), (WIDTH//2 - 120, HEIGHT//2 - 60))

class EndScreen:
    def __init__(self, mgr, success, stats, rm):
        self.mgr = mgr; self.success = success; self.stats = stats; self.rm = rm
        self.font_h1 = pygame.font.SysFont("malgungothic", 64); self.font_h2 = pygame.font.SysFont("malgungothic", 32); self.font = pygame.font.SysFont("malgungothic", 24)
        bx = (WIDTH - (420 * 2 + 60)) // 2; by = HEIGHT - 160
        self.btn_restart = Button((bx, by, 420, 70), "다시하기 (Enter)", BLUE, (95, 185, 255), self.font_h2)
        self.btn_to_start = Button((bx + 420 + 60, by, 420, 70), "시작화면 (Esc)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm))
            if event.key == pygame.K_ESCAPE: self.mgr.set(StartScreen(self.mgr, self.rm))
        if self.btn_restart.clicked(event): self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm))
        if self.btn_to_start.clicked(event): self.mgr.set(StartScreen(self.mgr, self.rm))

    def update(self, dt): pass
    def draw(self, surf):
        surf.fill(BLACK); mouse = pygame.mouse.get_pos()
        title = "GAME SUCCESS!!" if self.success else "GAME OVER!"
        surf.blit(self.font_h1.render(title, True, GREEN if self.success else RED), (WIDTH // 2 - 200, 100))
        panel = pygame.Rect(WIDTH // 2 - 380, 220, 760, 320); draw_panel(surf, panel, "결과", self.font_h2)
        t = self.stats.get("survival_time", 0); kill = self.stats.get("kill_count", 0); reason = self.stats.get("reason", "")
        for i, ln in enumerate([f"- 생존 시간: {int(t//60)}:{int(t%60):02d}", f"- 처치한 몬스터 수: {kill}"]):
            surf.blit(self.font.render(ln, True, (230, 230, 240)), (panel.x + 30, panel.y + 90 + i*44))
        if reason: surf.blit(self.font.render(f"종료 사유: {reason}", True, (200, 200, 215)), (panel.x + 30, panel.y + 230))
        self.btn_restart.draw(surf, mouse); self.btn_to_start.draw(surf, mouse)

class SkillChoiceOverlay:
    def __init__(self, gs):
        self.gs = gs; self.active = True; self.options = [w for w in gs.weapons if w.can_offer()][:3]
        self.font_h = pygame.font.SysFont("malgungothic", 44); self.font = pygame.font.SysFont("malgungothic", 22)
        w, h, gap = 320, 160, 40; x0 = (WIDTH - (w*3 + gap*2)) // 2; y0 = HEIGHT // 2 - 70
        self.btn_rects = [pygame.Rect(x0 + i*(w+gap), y0, w, h) for i in range(3)]

    def handle_event(self, event):
        if not self.active: return
        idx = -1
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3): idx = event.key - pygame.K_1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(event.pos): idx = i
        if 0 <= idx < len(self.options): self.options[idx].acquire_or_level(); self.active = False

    def draw(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 160)); surf.blit(ov, (0, 0))
        surf.blit(self.font_h.render("레벨업! 스킬을 선택하세요", True, WHITE), (WIDTH // 2 - 250, HEIGHT // 2 - 160))
        for i, r in enumerate(self.btn_rects):
            if i >= len(self.options): continue
            wpn = self.options[i]; pygame.draw.rect(surf, (45, 45, 55), r, border_radius=18); pygame.draw.rect(surf, (180, 180, 195), r, 2, border_radius=18)
            pygame.draw.rect(surf, wpn.color, (r.x, r.y, 12, r.h), border_radius=18)
            surf.blit(pygame.font.SysFont("malgungothic", 28).render(wpn.name, True, WHITE), (r.x + 22, r.y + 24))
            lvl_txt = f"현재 레벨: {wpn.level}/{MAX_SKILL_LEVEL}" if wpn.unlocked else "미해금: 선택 시 1레벨"
            surf.blit(self.font.render(lvl_txt, True, (210, 210, 220)), (r.x + 22, r.y + 76)); surf.blit(self.font.render(f"[{i+1}] 선택", True, (210, 210, 220)), (r.x + 22, r.y + 116))

class ScreenManager:
    def __init__(self): self.current = None
    def set(self, s): self.current = s
    def handle_event(self, e): self.current.handle_event(e)
    def update(self, dt): self.current.update(dt)
    def draw(self, surf): self.current.draw(surf)

def main():
    pygame.init(); pygame.font.init(); screen = pygame.display.set_mode((WIDTH, HEIGHT)); clock = pygame.time.Clock()
    rm = ResourceManager(); mgr = ScreenManager(); mgr.set(StartScreen(mgr, rm))
    while True:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            mgr.handle_event(e)
        mgr.update(dt); mgr.draw(screen); pygame.display.flip()

if __name__ == "__main__": main()