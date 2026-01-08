import pygame
import os
import json
import math
import random
from abc import ABC, abstractmethod

# =========================
# 1. Config & Constants
# =========================
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
MAP_W, MAP_H = 2000, 2000

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
# 2. Resource Manager (이미지 로딩 전담)
# =========================
class ResourceManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
        self.images = {}
        self.data = {}
        self.preload_data()

    def preload_data(self):
        self.data["player"] = self.load_json("player", {"hp": 100, "speed": 280, "name": "Harry Potter"})
        self.data["waves"] = self.load_json("waves", {"max_time": 300})

    def load_json(self, name, default):
        path = os.path.join(DATA_DIR, f"{name}.json")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_img(self, name, size=None, color=None):
        """이미지 로딩 및 캐싱. 파일이 없으면 도형으로 대체."""
        key = f"{name}_{size}"
        if key in self.images: return self.images[key]
        
        path = os.path.join(ASSET_DIR, name if "." in name else f"{name}.png")
        img = None
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if size:
                    img = pygame.transform.smoothscale(img, (size, size))
            except: pass
            
        if img is None:
            # Fallback: 이미지가 없을 경우 원형 도형 생성
            s = size if size else 40
            img = pygame.Surface((s, s), pygame.SRCALPHA)
            c = color if color else GRAY
            pygame.draw.circle(img, c, (s//2, s//2), s//2)
        
        self.images[key] = img
        return img

    def play_bgm(self, name):
        path = os.path.join(ASSET_DIR, name)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
            except: pass

# =========================
# 3. UI Components (팀원 코드)
# =========================
class Button:
    def __init__(self, rect, text, color, hover_color, font, text_color=WHITE, radius=12):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = font
        self.text_color = text_color
        self.radius = radius

    def draw(self, surf, mouse_pos):
        c = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=self.radius)
        pygame.draw.rect(surf, (150, 150, 170), self.rect, 2, border_radius=self.radius)
        txt_surf = self.font.render(self.text, True, self.text_color)
        surf.blit(txt_surf, txt_surf.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

# =========================
# 4. Core Logic: Base Entities
# =========================
class EntityBase(pygame.sprite.Sprite, ABC):
    def __init__(self, x, y, size, color, asset_name, rm):
        super().__init__()
        self.size = size
        self.world_pos = pygame.Vector2(x, y)
        self.image = rm.get_img(asset_name, size, color)
        self.rect = self.image.get_rect()

    def update_rect(self, camera_offset):
        self.rect.center = self.world_pos - camera_offset

class PlayerBase(EntityBase):
    def __init__(self, x, y, data, rm):
        super().__init__(x, y, 50, GOLD, "harry.png", rm)
        self.data = data
        self.reset()

    def reset(self):
        self.hp = float(self.data.get("hp", 100))
        self.max_hp = self.hp
        self.speed = float(self.data.get("speed", 250))
        self.level = 1
        self.exp = 0
        self.exp_next = 50
        self.world_pos = pygame.Vector2(MAP_W//2, MAP_H//2)
        self.kill_count = 0

    def move(self, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]: move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move.x += 1
        
        if move.length_squared() > 0:
            self.world_pos += move.normalize() * self.speed * dt
        
        # 맵 경계 제한
        self.world_pos.x = max(25, min(MAP_W-25, self.world_pos.x))
        self.world_pos.y = max(25, min(MAP_H-25, self.world_pos.y))

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_next:
            self.exp -= self.exp_next
            self.level += 1
            self.exp_next += 50 # 레벨업마다 +50 요구량 증가
            return True
        return False

class MonsterBase(EntityBase):
    def __init__(self, x, y, data, rm):
        kind = data.get("kind", "normal")
        color = RED if kind == "normal" else YELLOW if kind == "mid_boss" else (200, 0, 0)
        size = 35 if kind == "normal" else 75 if kind == "mid_boss" else 130
        super().__init__(x, y, size, color, f"{kind}.png", rm)
        self.kind = kind
        self.hp = data["hp"]
        self.speed = data["speed"]
        self.damage = data["damage"]
        self.exp_reward = data["exp"]

    def follow(self, target_pos, dt):
        dir_v = (target_pos - self.world_pos)
        if dir_v.length_squared() > 0:
            self.world_pos += dir_v.normalize() * self.speed * dt

# =========================
# 5. Magic Systems (팀원 마법 로직)
# =========================
class SpellProjectile(EntityBase):
    def __init__(self, x, y, size, asset, rm, direction, speed, damage, life=1.5):
        super().__init__(x, y, size, WHITE, asset, rm)
        self.dir = direction.normalize()
        self.speed = speed
        self.damage = damage
        self.life = life
        # 회전 연산
        angle = math.degrees(math.atan2(-self.dir.y, self.dir.x))
        self.image = pygame.transform.rotate(self.image, angle)

    def update(self, dt):
        self.world_pos += self.dir * self.speed * dt
        self.life -= dt
        return self.life <= 0

# =========================
# 6. Scene Framework (App 기반)
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
        self.btn_start = Button((SCREEN_W//2-120, SCREEN_H//2+50, 240, 60), "마법 시전 시작", (40, 45, 60), (70, 80, 110), app.font_p)

    def handle_event(self, e):
        if self.btn_start.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN):
            self.app.set_scene(PlayScene(self.app))

    def update(self, dt): pass

    def draw(self, surf):
        surf.fill(BLACK)
        title = self.app.font_h1.render("Wizard Survivor", True, GOLD)
        surf.blit(title, title.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 80)))
        self.btn_start.draw(surf, pygame.mouse.get_pos())

class PlayScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.player = PlayerBase(MAP_W//2, MAP_H//2, self.app.rm.data["player"], self.app.rm)
        self.camera = pygame.Vector2(0, 0)
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        
        self.timer = 0.0
        self.spawn_acc = 0.0
        self.is_paused = False
        self.magic_timer = 0
        
        # 초기 마법: 불덩어리
        self.unlocked_magics = ["fire"]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_p or e.key == pygame.K_ESCAPE:
                self.is_paused = not self.is_paused

    def spawn_logic(self, dt):
        self.spawn_acc += dt
        if self.spawn_acc >= 1.5:
            self.spawn_acc = 0
            angle = random.uniform(0, 2*math.pi)
            pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * 800
            data = {"id": "ghost", "kind": "normal", "hp": 35, "speed": 120, "damage": 10, "exp": 20}
            self.enemies.add(MonsterBase(pos.x, pos.y, data, self.app.rm))

    def magic_logic(self, dt):
        self.magic_timer += dt * 1000
        if self.magic_timer >= 1200: # 1.2초마다 발사
            self.magic_timer = 0
            if self.enemies:
                target = min(self.enemies, key=lambda e: e.world_pos.distance_to(self.player.world_pos))
                direction = target.world_pos - self.player.world_pos
                # 불덩어리 투사체 (리소스 매니저 사용)
                self.projectiles.add(SpellProjectile(self.player.world_pos.x, self.player.world_pos.y, 40, "Fire_Ball.jpg", self.app.rm, direction, 550, 20))

    def update(self, dt):
        if self.is_paused: return

        self.timer += dt
        self.player.move(dt)
        self.spawn_logic(dt)
        self.magic_logic(dt)

        # 적 이동 및 충돌
        for e in self.enemies:
            e.follow(self.player.world_pos, dt)
            if self.player.world_pos.distance_to(e.world_pos) < 35:
                if self.player.take_damage(0.5): self.finish(False)

        # 투사체 업데이트 및 충돌
        for p in self.projectiles:
            if p.update(dt): p.kill()
            hits = pygame.sprite.spritecollide(p, self.enemies, False)
            if hits:
                for h in hits:
                    h.hp -= p.damage
                    if h.hp <= 0:
                        if self.player.gain_exp(h.exp_reward): pass # TODO: LevelUp UI
                        self.player.kill_count += 1
                        h.kill()
                p.kill()

        # 카메라 업데이트
        self.camera.x = max(0, min(MAP_W - SCREEN_W, self.player.world_pos.x - SCREEN_W//2))
        self.camera.y = max(0, min(MAP_H - SCREEN_H, self.player.world_pos.y - SCREEN_H//2))

    def finish(self, success):
        stats = {"success": success, "kills": self.player.kill_count, "time": int(self.timer)}
        self.app.set_scene(ResultScene(self.app, stats))

    def draw(self, surf):
        surf.fill(BLACK)
        # 맵 타일
        for x in range(0, MAP_W + 1, 100):
            pygame.draw.line(surf, (30,30,40), (x - self.camera.x, 0), (x - self.camera.x, SCREEN_H))
        for y in range(0, MAP_H + 1, 100):
            pygame.draw.line(surf, (30,30,40), (0, y - self.camera.y), (SCREEN_W, y - self.camera.y))

        # 적 & 투사체
        for e in self.enemies:
            e.update_rect(self.camera)
            surf.blit(e.image, e.rect)
        for p in self.projectiles:
            p.update_rect(self.camera)
            surf.blit(p.image, p.rect)
        
        # 플레이어
        self.player.update_rect(self.camera)
        surf.blit(self.player.image, self.player.rect)

        # HUD
        self.draw_hud(surf)

    def draw_hud(self, surf):
        # 체력 바
        pygame.draw.rect(surf, (40, 40, 50), (30, 20, 300, 20), border_radius=10)
        pygame.draw.rect(surf, RED, (30, 20, 300 * (self.player.hp/self.player.max_hp), 20), border_radius=10)
        # 경험치 바
        pygame.draw.rect(surf, (40, 40, 50), (30, 50, 300, 10), border_radius=5)
        pygame.draw.rect(surf, BLUE, (30, 50, 300 * (self.player.exp/self.player.exp_next), 10), border_radius=5)
        
        info = self.app.font_s.render(f"LV {self.player.level} | KILLS {self.player.kill_count} | TIME {int(self.timer)}s", True, WHITE)
        surf.blit(info, (30, 70))

class ResultScene(Scene):
    def __init__(self, app, stats):
        super().__init__(app)
        self.stats = stats
        self.btn_retry = Button((SCREEN_W//2-100, SCREEN_H//2+80, 200, 50), "다시 시도", (50, 60, 50), (80, 100, 80), app.font_s)

    def handle_event(self, e):
        if self.btn_retry.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN):
            self.app.set_scene(StartScene(self.app))

    def update(self, dt): pass

    def draw(self, surf):
        surf.fill((15, 15, 20))
        title_str = "승리!" if self.stats["success"] else "패배..."
        col = GREEN if self.stats["success"] else RED
        title = self.app.font_h1.render(title_str, True, col)
        surf.blit(title, title.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 100)))
        
        res_txt = self.app.font_p.render(f"처치: {self.stats['kills']} | 생존 시간: {self.stats['time']}초", True, WHITE)
        surf.blit(res_txt, res_txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))
        self.btn_retry.draw(surf, pygame.mouse.get_pos())

# =========================
# 7. Main Application
# =========================
class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Hogwarts Defense: 통합 엔진 v2")
        self.clock = pygame.time.Clock()
        self.rm = ResourceManager()
        
        # 폰트 통합 로딩
        try:
            self.font_h1 = pygame.font.SysFont("malgungothic", 80, bold=True)
            self.font_p = pygame.font.SysFont("malgungothic", 35, bold=True)
            self.font_s = pygame.font.SysFont("malgungothic", 22)
        except:
            self.font_h1 = pygame.font.SysFont("arial", 80, bold=True)
            self.font_p = pygame.font.SysFont("arial", 35, bold=True)
            self.font_s = pygame.font.SysFont("arial", 22)

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