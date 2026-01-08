import pygame
import random
import math
import os
import json
from abc import ABC, abstractmethod

# =========================
# 1. Config & Constants
# =========================
WIDTH, HEIGHT = 1100, 650
FPS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "assets/")

# 색상 정의
COLORS = {
    "BG": (20, 20, 25),
    "TILE": (40, 40, 50),
    "PLAYER": (255, 215, 0),
    "ENEMY": (235, 80, 80),
    "MID_BOSS": (255, 100, 100),
    "FINAL_BOSS": (255, 0, 0),
    "EXP": (60, 140, 255),
    "UI_BAR_BG": (40, 40, 45),
    "WHITE": (245, 245, 245),
    "GOLD": (255, 215, 0),
    "CLEAR": (100, 255, 100)
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
        self.preload_data()

    def preload_data(self):
        self.game_data["player"] = self.load_json("player.json", {"id": "harry", "hp": 100, "speed": 280})
        self.game_data["waves"] = self.load_json("waves.json", {"max_time": 300, "difficulty_scale": 1.1})

    def load_json(self, filename, default_data):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)
            return default_data
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_image(self, name, size, color):
        cache_key = f"{name}_{size}"
        if cache_key in self.images:
            return self.images[cache_key]
        
        path = os.path.join(ASSET_DIR, f"{name}.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (size, size))
                self.images[cache_key] = img
                return img
            except:
                pass
        
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2)
        self.images[cache_key] = surface
        return surface

    def play_bgm(self, filename):
        path = os.path.join(ASSET_DIR, filename)
        print(f"bgm path : {path}")
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
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
        
        for x in range(start_x - self.tile_size, start_x + WIDTH + self.tile_size, self.tile_size):
            for y in range(start_y - self.tile_size, start_y + HEIGHT + self.tile_size, self.tile_size):
                rect = pygame.Rect(x - camera_offset.x, y - camera_offset.y, self.tile_size, self.tile_size)
                pygame.draw.rect(surface, COLORS["TILE"], rect, 1)

class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_pos):
        self.offset.x = target_pos.x - WIDTH // 2
        self.offset.y = target_pos.y - HEIGHT // 2

# =========================
# 4. Base Entities
# =========================
class EntityBase(pygame.sprite.Sprite, ABC):
    def __init__(self, x, y, size, color, asset_name=None, rm=None):
        super().__init__()
        self.size = size
        self.world_pos = pygame.Vector2(x, y)
        self.image = rm.get_image(asset_name, size, color)
        self.rect = self.image.get_rect()

    def update_rect(self, camera_offset):
        self.rect.center = self.world_pos - camera_offset

class PlayerBase(EntityBase):
    def __init__(self, x, y, data, rm):
        super().__init__(x, y, 40, COLORS["PLAYER"], "player", rm)
        self.data = data
        self.reset()

    def reset(self):
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

class MonsterBase(EntityBase):
    def __init__(self, x, y, data, rm):
        kind = data.get("kind", "normal")
        if kind == "final_boss":
            color = COLORS["FINAL_BOSS"]
            size = 120
        elif kind == "mid_boss":
            color = COLORS["MID_BOSS"]
            size = 70
        else:
            color = COLORS["ENEMY"]
            size = 30
            
        super().__init__(x, y, size, color, data["id"], rm)
        self.kind = kind
        self.speed = data["speed"]
        self.hp = data["hp"]
        self.max_hp = self.hp
        self.damage = data["damage"]
        self.exp_reward = data["exp"]

    def follow(self, target_pos, dt):
        dir_vec = (target_pos - self.world_pos)
        if dir_vec.length_squared() > 0:
            self.world_pos += dir_vec.normalize() * self.speed * dt

# =========================
# 5. Wave Manager (확장됨)
# =========================
class WaveManager:
    def __init__(self, wave_data):
        self.data = wave_data
        self.reset()

    def reset(self):
        self.timer = 0.0
        self.spawn_accumulator = 0.0
        self.mid_boss_spawned = False
        self.final_boss_spawned = False

    def get_phase(self):
        """시간대별 페이즈 반환"""
        if self.timer >= 240: # 4분~5분
            return "FINAL_WAVE"
        if self.timer >= 120: # 2분~3분
            return "MID_WAVE"
        return "NORMAL_WAVE"

    def update(self, dt):
        self.timer += dt
        self.spawn_accumulator += dt
        
        # 기본 스폰율 (시간이 갈수록 빨라짐)
        spawn_rate = 1.5 - min(1.2, self.timer / 300)
        
        if self.spawn_accumulator >= spawn_rate:
            self.spawn_accumulator = 0
            return True
        return False

# =========================
# 6. Game Controller
# =========================
class GameController:
    def __init__(self, resource_manager):
        self.rm = resource_manager
        self.screen = pygame.display.get_surface()
        self.clock = pygame.time.Clock()
        self.camera = Camera()
        self.world = World(2500, 2500)
        
        try:
            self.font_h1 = pygame.font.SysFont("malgungothic", 60, bold=True)
            self.font_h2 = pygame.font.SysFont("malgungothic", 30, bold=True)
            self.font_p = pygame.font.SysFont("malgungothic", 20)
        except:
            self.font_h1 = pygame.font.SysFont("arial", 60, bold=True)
            self.font_h2 = pygame.font.SysFont("arial", 30, bold=True)
            self.font_p = pygame.font.SysFont("arial", 20)

        self.player = PlayerBase(1250, 1250, self.rm.game_data["player"], self.rm)
        self.wave_mgr = WaveManager(self.rm.game_data["waves"])
        
        self.enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group()
        
        self.state = "START" # START, PLAYING, GAMEOVER, CLEAR
        self.kill_count = 0
        self.survive_time_str = "00:00"

    def reset_game(self):
        self.player.reset()
        self.wave_mgr.reset()
        self.enemies.empty()
        self.all_sprites.empty()
        self.all_sprites.add(self.player)
        self.kill_count = 0
        self.state = "PLAYING"

    def spawn_enemy(self):
        phase = self.wave_mgr.get_phase()
        angle = random.uniform(0, math.pi * 2)
        spawn_pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * 750
        
        m_data = {"id": "dementor", "kind": "normal", "speed": 130, "hp": 30, "damage": 10, "exp": 20}
        
        # 페이즈별 특수 스폰 로직
        if phase == "MID_WAVE":
            if not self.wave_mgr.mid_boss_spawned:
                # 중간 보스 (한 번만 스폰 혹은 특정 주기)
                m_data = {"id": "mid_boss", "kind": "mid_boss", "speed": 100, "hp": 500, "damage": 20, "exp": 100}
                self.wave_mgr.mid_boss_spawned = True
            elif random.random() < 0.2: # 20% 확률로 강화 몹
                m_data["hp"] = 60
                m_data["speed"] = 150
                
        elif phase == "FINAL_WAVE":
            if not self.wave_mgr.final_boss_spawned:
                # 최종 보스 스폰
                m_data = {"id": "final_boss", "kind": "final_boss", "speed": 80, "hp": 2000, "damage": 40, "exp": 0}
                self.wave_mgr.final_boss_spawned = True
            else:
                # 최종 보스전 잡몹들
                m_data["hp"] = 100
                m_data["speed"] = 160

        enemy = MonsterBase(spawn_pos.x, spawn_pos.y, m_data, self.rm)
        self.enemies.add(enemy)
        self.all_sprites.add(enemy)

    def handle_collisions(self):
        # 플레이어 피격
        hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
        for enemy in hits:
            if self.player.world_pos.distance_to(enemy.world_pos) < enemy.size * 0.7:
                self.player.hp -= 0.5
                if self.player.hp <= 0:
                    self.finish_round(success=False)

        # 몬스터 처치 판정 (팀원들이 구현할 투사체 로직에서 호출되겠지만, 여기서는 체력 체크)
        for enemy in self.enemies:
            if enemy.hp <= 0:
                self.kill_count += 1
                if enemy.kind == "final_boss":
                    self.finish_round(success=True)
                enemy.kill()

    def finish_round(self, success=False):
        m = int(self.wave_mgr.timer // 60)
        s = int(self.wave_mgr.timer % 60)
        self.survive_time_str = f"{m:02}:{s:02}"
        self.state = "CLEAR" if success else "GAMEOVER"
        
        # 5분이 지나면 자동 종료 (최종 보스 안 죽였을 경우 등)
        if self.wave_mgr.timer >= 300 and self.state == "PLAYING":
             self.state = "GAMEOVER"

    def draw_ui(self):
        if self.state == "PLAYING":
            # 체력 바
            pygame.draw.rect(self.screen, COLORS["UI_BAR_BG"], (20, 20, 250, 20), border_radius=5)
            pygame.draw.rect(self.screen, (220, 40, 40), (20, 20, 250 * (self.player.hp / self.player.max_hp), 20), border_radius=5)
            
            # 타이머 및 처치 수
            m = int(self.wave_mgr.timer // 60)
            s = int(self.wave_mgr.timer % 60)
            self.screen.blit(self.font_p.render(f"Time: {m:02}:{s:02} / 05:00", True, COLORS["WHITE"]), (20, 50))
            self.screen.blit(self.font_p.render(f"Kills: {self.kill_count}", True, COLORS["WHITE"]), (20, 75))
            
            # 페이즈 표시
            phase = self.wave_mgr.get_phase()
            phase_txt = "DANGER: Mid Boss Arrived!" if phase == "MID_WAVE" else "CRITICAL: Voldemort Appears!" if phase == "FINAL_WAVE" else "Survive the Horde"
            color = COLORS["GOLD"] if phase != "NORMAL_WAVE" else COLORS["WHITE"]
            self.screen.blit(self.font_p.render(phase_txt, True, color), (20, 105))

    def draw_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 210))
        self.screen.blit(overlay, (0, 0))
        
        if self.state == "START":
            title, subtitle, color = "Hogwarts Defense", "Survive for 5 Minutes", COLORS["GOLD"]
        elif self.state == "GAMEOVER":
            title, subtitle, color = "Mission Failed", "Harry is defeated...", COLORS["ENEMY"]
        elif self.state == "CLEAR":
            title, subtitle, color = "VICTORY!", "The Dark Lord has been vanquished!", COLORS["CLEAR"]
            
        t_surf = self.font_h1.render(title, True, color)
        s_surf = self.font_h2.render(subtitle, True, COLORS["WHITE"])
        instr_surf = self.font_p.render("Press 'SPACE' to Play Again", True, (180, 180, 180))
        
        self.screen.blit(t_surf, t_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
        self.screen.blit(s_surf, s_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))
        
        if self.state != "START":
            stat_txt = self.font_p.render(f"Kills: {self.kill_count} | Time: {self.survive_time_str}", True, COLORS["EXP"])
            self.screen.blit(stat_txt, stat_txt.get_rect(center=(WIDTH//2, HEIGHT//2 + 80)))
            
        self.screen.blit(instr_surf, instr_surf.get_rect(center=(WIDTH//2, HEIGHT//2 + 160)))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and self.state != "PLAYING":
                        self.reset_game()

            if self.state == "PLAYING":
                self.player.move(dt, (self.world.width, self.world.height))
                if self.wave_mgr.update(dt): self.spawn_enemy()
                for enemy in self.enemies: enemy.follow(self.player.world_pos, dt)
                self.handle_collisions()
                self.camera.update(self.player.world_pos)
                
                # 5분 시간 제한 체크
                if self.wave_mgr.timer >= 300:
                    self.finish_round(success=False)

            self.screen.fill(COLORS["BG"])
            self.world.draw_background(self.screen, self.camera.offset)
            
            if self.state != "START":
                # 보스 체력 바 표시 로직 추가 (필요 시)
                for sprite in self.all_sprites:
                    sprite.update_rect(self.camera.offset)
                    self.screen.blit(sprite.image, sprite.rect)
                    # 보스 전용 체력바 (간단히 표현)
                    if isinstance(sprite, MonsterBase) and (sprite.kind == "mid_boss" or sprite.kind == "final_boss"):
                        bar_rect = pygame.Rect(sprite.rect.left, sprite.rect.top - 10, sprite.rect.width, 5)
                        pygame.draw.rect(self.screen, (50, 0, 0), bar_rect)
                        pygame.draw.rect(self.screen, (255, 0, 0), (bar_rect.x, bar_rect.y, bar_rect.width * (sprite.hp/sprite.max_hp), 5))
            
            self.draw_ui()
            if self.state != "PLAYING":
                self.draw_overlay()
            
            pygame.display.flip()

# =========================
# 7. Main Entry Point
# =========================
def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    
    rm = ResourceManager()
    rm.play_bgm("bgm.mp3")
    
    game = GameController(rm)
    game.run()
    
    pygame.quit()

if __name__ == "__main__":
    main()