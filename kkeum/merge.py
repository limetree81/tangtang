import pygame
import os
import json
import math
import random
from abc import ABC, abstractmethod

# =========================
# 1. Config & Constants (통합)
# =========================
SCREEN_W, SCREEN_H = 1280, 720 # 팀원 UI 규격에 맞춤
FPS = 60
MAP_W, MAP_H = 1500, 1500

# 색상 정의
WHITE = (245, 245, 245)
BLACK = (12, 12, 15)
GRAY = (90, 90, 100)
RED = (235, 80, 80)
GREEN = (60, 210, 120)
BLUE = (70, 160, 255)
YELLOW = (255, 220, 80)
GOLD = (255, 215, 0)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "assets")

# =========================
# 2. UI Helpers (팀원 코드 이식)
# =========================
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

# =========================
# 3. Resource Manager (통합 강화)
# =========================
class ResourceManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
        self.images = {}
        self.data = {}
        self.preload_data()

    def preload_data(self):
        self.data["player"] = self.load_json("player", {"hp":100, "speed":280, "dmg_mult":1.0})
        self.data["waves"] = self.load_json("waves", {"max_time":300})

    def load_json(self, name, default):
        path = os.path.join(DATA_DIR, f"{name}.json")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_img(self, name, size, color=None):
        key = f"{name}_{size}"
        if key in self.images: return self.images[key]
        
        path = os.path.join(ASSET_DIR, name if "." in name else f"{name}.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (size, size))
                self.images[key] = img
                return img
            except: pass
            
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        if color: pygame.draw.circle(surf, color, (size//2, size//2), size//2)
        else: surf.fill(GRAY)
        self.images[key] = surf
        return surf

# =========================
# 4. Core Logic: Base Classes
# =========================
class EntityBase(pygame.sprite.Sprite, ABC):
    def __init__(self, x, y, size, color, asset_name, rm):
        super().__init__()
        self.size = size
        self.world_pos = pygame.Vector2(x, y)
        self.image = rm.get_img(asset_name, size, color)
        self.rect = self.image.get_rect()

    def update_rect(self, camera):
        self.rect.center = camera.apply_pos(self.world_pos)

class PlayerBase(EntityBase):
    def __init__(self, x, y, data, rm):
        super().__init__(x, y, 45, GOLD, "harry", rm) # harry.png 시도
        self.base_data = data
        self.reset()

    def reset(self):
        self.hp = float(self.base_data.get("hp", 100))
        self.max_hp = self.hp
        self.speed = float(self.base_data.get("speed", 250))
        self.dmg_mult = float(self.base_data.get("dmg_mult", 1.0))
        self.level = 1
        self.exp = 0
        self.exp_next = 50
        self.world_pos = pygame.Vector2(MAP_W//2, MAP_H//2)
        self.kills = 0

    def move(self, dt):
        keys = pygame.key.get_pressed()
        mv = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: mv.y -= 1
        if keys[pygame.K_s]: mv.y += 1
        if keys[pygame.K_a]: mv.x -= 1
        if keys[pygame.K_d]: mv.x += 1
        if mv.length_squared() > 0:
            self.world_pos += mv.normalize() * self.speed * dt
        self.world_pos.x = max(30, min(MAP_W-30, self.world_pos.x))
        self.world_pos.y = max(30, min(MAP_H-30, self.world_pos.y))

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_next:
            self.exp -= self.exp_next
            self.level += 1
            self.exp_next += 50 # 팀원 요구사항: 레벨업 시마다 50씩 증가
            return True
        return False

class MonsterBase(EntityBase):
    def __init__(self, x, y, data, rm):
        kind = data.get("kind", "normal")
        color = RED if kind == "normal" else YELLOW if kind == "mid_boss" else (255, 0, 0)
        size = 35 if kind == "normal" else 80 if kind == "mid_boss" else 150
        super().__init__(x, y, size, color, data["id"], rm)
        self.kind = kind
        self.hp = data["hp"]
        self.max_hp = self.hp
        self.speed = data["speed"]
        self.damage = data["damage"]
        self.exp_reward = data["exp"]

    def follow_target(self, target_pos, dt):
        dir_vec = (target_pos - self.world_pos)
        if dir_vec.length_squared() > 0:
            self.world_pos += dir_vec.normalize() * self.speed * dt

# =========================
# 5. Magic Systems (팀원 로직 이식)
# =========================
class Projectile(EntityBase):
    def __init__(self, x, y, size, color, asset_name, rm, direction, speed, damage, life=2.0, pierce=1):
        super().__init__(x, y, size, color, asset_name, rm)
        self.dir = direction.normalize()
        self.speed = speed
        self.damage = damage
        self.life = life
        self.pierce = pierce
        self.hit_count = 0
        
        # 이미지 회전 (팀원 로직)
        ang = math.degrees(math.atan2(self.dir.y, self.dir.x))
        self.image = pygame.transform.rotate(self.image, -ang)

    def update(self, dt):
        self.life -= dt
        self.world_pos += self.dir * self.speed * dt
        return self.life <= 0

class MagicBase(ABC):
    def __init__(self, owner):
        self.owner = owner
        self.level = 0
        self.unlocked = False
        self.last_cast = 0
    
    @abstractmethod
    def update(self, dt, monsters, projectiles, current_time, rm): pass

class FireBallMagic(MagicBase):
    def update(self, dt, monsters, projectiles, current_time, rm):
        if not self.unlocked: return
        cooldown = 1500 # 1.5s
        if current_time - self.last_cast > cooldown:
            if monsters:
                target = min(monsters, key=lambda m: m.world_pos.distance_to(self.owner.world_pos))
                dirv = target.world_pos - self.owner.world_pos
                projectiles.add(Projectile(self.owner.world_pos.x, self.owner.world_pos.y, 40, RED, "Fire_Ball.jpg", rm, dirv, 500, 20 * self.owner.dmg_mult))
                self.last_cast = current_time

# =========================
# 6. Scene Management (통합)
# =========================
class Scene(ABC):
    def __init__(self, app): self.app = app
    @abstractmethod
    def handle_event(self, e): pass
    @abstractmethod
    def update(self, dt): pass
    @abstractmethod
    def draw(self, surf): pass

class StartScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        bx, by = SCREEN_W//2 - 110, SCREEN_H//2
        self.btn_start = Button((bx, by, 220, 60), "START GAME", GREEN, (40, 170, 90), app.font_p)

    def handle_event(self, e):
        if self.btn_start.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE):
            self.app.set_scene(PlayScene(self.app))

    def update(self, dt): pass
    
    def draw(self, surf):
        surf.fill(BLACK)
        title = self.app.font_h1.render("Wizard Survivor", True, GOLD)
        surf.blit(title, title.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 100)))
        self.btn_start.draw(surf, pygame.mouse.get_pos())

class PlayScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.player = PlayerBase(MAP_W//2, MAP_H//2, self.app.rm.data["player"], self.app.rm)
        self.camera = pygame.Vector2(0, 0) # Camera offset
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.magics = [FireBallMagic(self.player)]
        self.magics[0].unlocked = True # 기본 무기 해제
        
        self.timer = 0.0
        self.spawn_acc = 0.0
        self.is_paused = False
        self.boss_spawned = {"mid": False, "final": False}

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_p:
            self.is_paused = not self.is_paused

    def update(self, dt):
        if self.is_paused: return
        
        self.timer += dt
        self.spawn_acc += dt
        now = pygame.time.get_ticks()

        # 1. Spawn Logic
        if self.spawn_acc >= 1.2:
            self.spawn_acc = 0
            self.spawn_enemy()

        # 2. Player Move
        self.player.move(dt)
        
        # 3. Magic Cast
        for m in self.magics:
            m.update(dt, self.enemies.sprites(), self.projectiles, now, self.app.rm)
            
        # 4. Projectile Move
        for p in self.projectiles:
            if p.update(dt): p.kill()

        # 5. Enemy Move & Collision
        for e in self.enemies:
            e.follow_target(self.player.world_pos, dt)
            if self.player.world_pos.distance_to(e.world_pos) < 35:
                if self.player.take_damage(0.4): self.finish(False)
        
        # 6. Projectile Collision
        for p in self.projectiles:
            hits = pygame.sprite.spritecollide(p, self.enemies, False)
            if hits:
                for h in hits:
                    h.hp -= p.damage
                    if h.hp <= 0:
                        if self.player.gain_exp(h.exp_reward): pass # TODO: LevelUp Overlay
                        self.player.kills += 1
                        h.kill()
                p.kill()

        # 7. Camera Update
        self.camera.x = max(0, min(MAP_W - SCREEN_W, self.player.world_pos.x - SCREEN_W//2))
        self.camera.y = max(0, min(MAP_H - SCREEN_H, self.player.world_pos.y - SCREEN_H//2))

    def spawn_enemy(self):
        angle = random.uniform(0, 2*math.pi)
        pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * 800
        data = {"id": "ghost", "kind": "normal", "hp": 30, "speed": 110, "damage": 10, "exp": 15}
        self.enemies.add(MonsterBase(pos.x, pos.y, data, self.app.rm))

    def finish(self, success):
        res = {"success": success, "kills": self.player.kills, "time": int(self.timer)}
        self.app.set_scene(StartScene(self.app)) # 임시 리턴

    def draw(self, surf):
        surf.fill(BLACK)
        # Draw Map Tiles (사용자 로직)
        for x in range(0, MAP_W + 1, 100):
            pygame.draw.line(surf, (30,30,40), (x - self.camera.x, 0), (x - self.camera.x, SCREEN_H))
        for y in range(0, MAP_H + 1, 100):
            pygame.draw.line(surf, (30,30,40), (0, y - self.camera.y), (SCREEN_W, y - self.camera.y))

        # Draw Entities
        for e in self.enemies:
            e.rect.center = e.world_pos - self.camera
            surf.blit(e.image, e.rect)
        for p in self.projectiles:
            p.rect.center = p.world_pos - self.camera
            surf.blit(p.image, p.rect)
        
        self.player.rect.center = self.player.world_pos - self.camera
        surf.blit(self.player.image, self.player.rect)

        # UI HUD (팀원 스타일)
        self.draw_hud(surf)

    def draw_hud(self, surf):
        # HP Bar
        pygame.draw.rect(surf, (40,40,50), (30, 20, 300, 20), border_radius=10)
        pygame.draw.rect(surf, RED, (30, 20, 300 * (self.player.hp/self.player.max_hp), 20), border_radius=10)
        # EXP Bar
        pygame.draw.rect(surf, (40,40,50), (30, 50, 300, 10), border_radius=5)
        pygame.draw.rect(surf, BLUE, (30, 50, 300 * (self.player.exp/self.player.exp_next), 10), border_radius=5)
        
        txt = self.app.font_s.render(f"LV {self.player.level} | KILLS {self.player.kills} | TIME {int(self.timer)}s", True, WHITE)
        surf.blit(txt, (30, 70))

# =========================
# 7. Main Application
# =========================
class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Hogwarts Defense: Integrated Engine")
        self.clock = pygame.time.Clock()
        self.rm = ResourceManager()
        
        try:
            self.font_h1 = pygame.font.SysFont("malgungothic", 70, bold=True)
            self.font_p = pygame.font.SysFont("malgungothic", 30, bold=True)
            self.font_s = pygame.font.SysFont("malgungothic", 20)
        except:
            self.font_h1 = pygame.font.SysFont("arial", 70, bold=True)
            self.font_p = pygame.font.SysFont("arial", 30, bold=True)
            self.font_s = pygame.font.SysFont("arial", 20)

        self.scene = StartScene(self)

    def set_scene(self, scene): self.scene = scene

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                self.scene.handle_event(event)
            
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

if __name__ == "__main__":
    App().run()