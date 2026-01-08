import pygame
import random
import math
import os
import json
from abc import ABC, abstractmethod

# =========================
# 1. Config & Constants
# =========================
SCREEN_W, SCREEN_H = 1100, 650
FPS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "assets")

# 색상 정의
COLORS = {
    "BG": (20, 20, 25),
    "TILE": (40, 40, 50),
    "PLAYER": (255, 215, 0),
    "ENEMY": (235, 80, 80),
    "EXP": (60, 140, 255),
    "UI_BAR_BG": (40, 40, 45),
    "WHITE": (245, 245, 245),
    "BLACK": (10, 10, 15),
    "GOLD": (255, 215, 0)
}

# =========================
# 2. Resource & Data Manager
# =========================
class ResourceManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if not os.path.exists(ASSET_DIR): os.makedirs(ASSET_DIR)
        self.images = {}
        self.game_data = {}

    def load_json(self, filename, default_data):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_image(self, name, size, color):
        print(f"image: name:{name}")
        """이미지 로드 시도, 없으면 기본 도형 반환"""
        if name in self.images:
            return self.images[name]
        
        path = os.path.join(ASSET_DIR, f"{name}.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (size, size))
                self.images[name] = img
                return img
            except:
                pass
        
        # Fallback: 원형 도형 생성
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2)
        self.images[name] = surface
        return surface

    def play_bgm(self, filename):
        print("""BGM 재생 (파일이 없을 경우 대비 예외처리)""")
        path = os.path.join(ASSET_DIR, filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1) # 무한 반복
            except:
                print(f"BGM 로드 실패: {filename}")

# =========================
# 3. World & Camera
# =========================
class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tile_size = 100

    def draw_background(self, surface, camera_offset):
        start_x = int(camera_offset.x // self.tile_size) * self.tile_size
        start_y = int(camera_offset.y // self.tile_size) * self.tile_size
        
        for x in range(start_x - self.tile_size, start_x + SCREEN_W + self.tile_size, self.tile_size):
            for y in range(start_y - self.tile_size, start_y + SCREEN_H + self.tile_size, self.tile_size):
                # 격자 그리기
                rect = pygame.Rect(x - camera_offset.x, y - camera_offset.y, self.tile_size, self.tile_size)
                pygame.draw.rect(surface, COLORS["TILE"], rect, 1)

class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_pos):
        self.offset.x = target_pos.x - SCREEN_W // 2
        self.offset.y = target_pos.y - SCREEN_H // 2

# =========================
# 4. Base Entities (Core Logic)
# =========================
class EntityBase(pygame.sprite.Sprite, ABC):
    def __init__(self, x, y, size, color, asset_name=None, rm=None):
        super().__init__()
        self.size = size
        self.world_pos = pygame.Vector2(x, y)
        self.image = rm.get_image(asset_name, size, color) if rm else None
        if not self.image:
            self.image = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect = self.image.get_rect()

    def update_rect(self, camera_offset):
        self.rect.center = self.world_pos - camera_offset

class PlayerBase(EntityBase):
    def __init__(self, x, y, data, rm):
        super().__init__(x, y, 40, COLORS["PLAYER"], "player", rm)
        self.data = data # 초기 스탯 보관
        self.reset()

    def reset(self):
        """다시 시작할 때 스탯 초기화"""
        self.speed = self.data.get("speed", 250)
        self.hp = self.data.get("hp", 100)
        self.max_hp = self.hp
        self.world_pos = pygame.Vector2(1000, 1000)
        self.level = 1
        self.exp = 0
        self.exp_next = 100

    def move(self, dt, world_size):
        keys = pygame.key.get_pressed()
        input_vec = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: input_vec.y -= 1
        if keys[pygame.K_s]: input_vec.y += 1
        if keys[pygame.K_a]: input_vec.x -= 1
        if keys[pygame.K_d]: input_vec.x += 1
        
        if input_vec.length_squared() > 0:
            self.world_pos += input_vec.normalize() * self.speed * dt
        
        self.world_pos.x = max(0, min(world_size[0], self.world_pos.x))
        self.world_pos.y = max(0, min(world_size[1], self.world_pos.y))

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_next:
            self.level += 1
            self.exp -= self.exp_next
            self.exp_next = int(self.exp_next * 1.5)
            return True
        return False

class MonsterBase(EntityBase):
    def __init__(self, x, y, data, rm):
        size = 30 if data["kind"] == "normal" else 60
        color = COLORS["ENEMY"]
        super().__init__(x, y, size, color, data["id"], rm)
        self.speed = data["speed"]
        self.hp = data["hp"]
        self.damage = data["damage"]
        self.exp_reward = data["exp"]

    def follow(self, target_pos, dt):
        dir_vec = (target_pos - self.world_pos)
        if dir_vec.length_squared() > 0:
            self.world_pos += dir_vec.normalize() * self.speed * dt

# =========================
# 5. Wave & Game Engine
# =========================
class WaveManager:
    def __init__(self, wave_data):
        self.data = wave_data
        self.reset()

    def reset(self):
        self.timer = 0.0
        self.spawn_accumulator = 0.0

    def update(self, dt):
        self.timer += dt
        self.spawn_accumulator += dt
        spawn_rate = 1.5 - min(1.0, self.timer / 300)
        if self.spawn_accumulator >= spawn_rate:
            self.spawn_accumulator = 0
            return True
        return False

class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Wizard Survivor: Core Engine")
        self.clock = pygame.time.Clock()
        self.rm = ResourceManager()
        self.camera = Camera()
        self.world = World(2000, 2000)
        
        # 폰트 로드
        try:
            self.font_h1 = pygame.font.SysFont("malgungothic", 60, bold=True)
            self.font_h2 = pygame.font.SysFont("malgungothic", 30, bold=True)
            self.font_p = pygame.font.SysFont("malgungothic", 20)
        except:
            self.font_h1 = pygame.font.SysFont("arial", 60, bold=True)
            self.font_h2 = pygame.font.SysFont("arial", 30, bold=True)
            self.font_p = pygame.font.SysFont("arial", 20)

        # 데이터 로드
        self.player_data = self.rm.load_json("player.json", {"id": "harry", "hp": 100, "speed": 280})
        self.wave_data = self.rm.load_json("waves.json", {"difficulty_scale": 1.1})
        
        self.player = PlayerBase(1000, 1000, self.player_data, self.rm)
        self.wave_mgr = WaveManager(self.wave_data)
        
        self.enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group()
        
        # 상태 관리: START, PLAYING, GAMEOVER
        self.state = "START"
        self.kill_count = 0
        self.survive_time_str = "00:00"
        
        # BGM 시작 (파일이 있다면 bgm.mp3 또는 bgm.wav)
        self.rm.play_bgm("bgm.mp3")

    def reset_game(self):
        """게임을 처음 상태로 리셋"""
        self.player.reset()
        self.wave_mgr.reset()
        self.enemies.empty()
        self.all_sprites.empty()
        self.all_sprites.add(self.player)
        self.kill_count = 0
        self.state = "PLAYING"

    def spawn_enemy(self):
        angle = random.uniform(0, math.pi * 2)
        spawn_dist = 700
        spawn_pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * spawn_dist
        
        m_data = {"id": "dementor", "kind": "normal", "speed": 120, "hp": 30, "damage": 10, "exp": 20}
        enemy = MonsterBase(spawn_pos.x, spawn_pos.y, m_data, self.rm)
        self.enemies.add(enemy)
        self.all_sprites.add(enemy)

    def handle_collisions(self):
        # 적 vs 플레이어 충돌
        hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
        for enemy in hits:
            dist = self.player.world_pos.distance_to(enemy.world_pos)
            if dist < 30:
                self.player.hp -= 0.5
                if self.player.hp <= 0:
                    self.finish_round()

        # (임시) 적 체력 고갈 시 킬 카운트 증가 테스트용 
        # 실제 투사체 로직은 팀원 구현 영역이지만, 킬 카운팅 인터페이스 확인을 위해 로직 포함
        for enemy in self.enemies:
            if enemy.hp <= 0:
                self.kill_count += 1
                enemy.kill()

    def finish_round(self):
        """라운드 종료 시 데이터 정리"""
        m = int(self.wave_mgr.timer // 60)
        s = int(self.wave_mgr.timer % 60)
        self.survive_time_str = f"{m:02}:{s:02}"
        self.state = "GAMEOVER"

    def draw_ui(self):
        # 인게임 HUD
        if self.state == "PLAYING":
            # 상단 바
            pygame.draw.rect(self.screen, COLORS["UI_BAR_BG"], (20, 20, 250, 20), border_radius=5)
            pygame.draw.rect(self.screen, (220, 40, 40), (20, 20, 250 * (self.player.hp / self.player.max_hp), 20), border_radius=5)
            
            # 정보 텍스트
            m = int(self.wave_mgr.timer // 60)
            s = int(self.wave_mgr.timer % 60)
            txt_time = self.font_p.render(f"Survival: {m:02}:{s:02}", True, COLORS["WHITE"])
            txt_kills = self.font_p.render(f"Kills: {self.kill_count}", True, COLORS["WHITE"])
            self.screen.blit(txt_time, (20, 50))
            self.screen.blit(txt_kills, (20, 75))

    def draw_overlay(self, title, subtitle):
        """메뉴 및 결과 오버레이"""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 200))
        self.screen.blit(overlay, (0, 0))
        
        t_surf = self.font_h1.render(title, True, COLORS["GOLD"])
        s_surf = self.font_h2.render(subtitle, True, COLORS["WHITE"])
        instr_surf = self.font_p.render("Press 'SPACE' to Start/Restart", True, (180, 180, 180))
        
        self.screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 50)))
        self.screen.blit(s_surf, s_surf.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 30)))
        self.screen.blit(instr_surf, instr_surf.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 150)))

        if self.state == "GAMEOVER":
            stat_txt = self.font_p.render(f"Total Kills: {self.kill_count} | Survival Time: {self.survive_time_str}", True, COLORS["EXP"])
            self.screen.blit(stat_txt, stat_txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 80)))

    def run(self):
        while True:
            dt_raw = self.clock.tick(FPS)
            dt = dt_raw / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.state != "PLAYING":
                            self.reset_game()

            if self.state == "PLAYING":
                # Logic
                self.player.move(dt, (self.world.width, self.world.height))
                if self.wave_mgr.update(dt):
                    self.spawn_enemy()
                
                for enemy in self.enemies:
                    enemy.follow(self.player.world_pos, dt)
                
                self.handle_collisions()
                self.camera.update(self.player.world_pos)

            # Rendering
            self.screen.fill(COLORS["BG"])
            self.world.draw_background(self.screen, self.camera.offset)
            
            if self.state == "PLAYING" or self.state == "GAMEOVER":
                for sprite in self.all_sprites:
                    sprite.update_rect(self.camera.offset)
                    self.screen.blit(sprite.image, sprite.rect)
            
            self.draw_ui()

            if self.state == "START":
                self.draw_overlay("Hogwarts Defense", "Are you ready, Wizard?")
            elif self.state == "GAMEOVER":
                self.draw_overlay("Mission Failed", "Harry is exhausted...")

            pygame.display.flip()

if __name__ == "__main__":
    GameController().run()