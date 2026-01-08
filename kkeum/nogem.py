import pygame
import random
import math
from abc import ABC, abstractmethod

# ----------------------------------------------------------------
# 1. 전역 설정 (마법 테마 색상)
# ----------------------------------------------------------------
class Config:
    WIDTH, HEIGHT = 800, 600
    FPS = 60
    TILE_SIZE = 64
    COLORS = {
        "BG": (15, 15, 25),      # 어두운 밤
        "TILE": (25, 25, 40),    # 마법 학교 바닥
        "PLAYER": (255, 215, 0), # 황금빛 (해리)
        "DEMENTOR": (50, 50, 70), # 회색 (디멘터)
        "DEATH_EATER": (0, 0, 0), # 검정 (죽음을 먹는 자)
        "FIRE": (255, 69, 0),     # 주황색
        "ELECTRIC": (0, 191, 255), # 하늘색
        "SHIELD": (255, 255, 255, 100), # 반투명 흰색
        "UI_EXP": (138, 43, 226), # 보라색 (마력)
        "UI_HP": (178, 34, 34)    # 진빨강 (체력)
    }

# ----------------------------------------------------------------
# 2. 카메라 시스템
# ----------------------------------------------------------------
class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, player_pos):
        self.offset = player_pos - pygame.Vector2(Config.WIDTH//2, Config.HEIGHT//2)

    def apply(self, world_pos):
        return world_pos - self.offset

    def draw_bg(self, surface):
        start_x = int(self.offset.x // Config.TILE_SIZE) * Config.TILE_SIZE
        start_y = int(self.offset.y // Config.TILE_SIZE) * Config.TILE_SIZE
        for x in range(start_x - Config.TILE_SIZE, start_x + Config.WIDTH + Config.TILE_SIZE, Config.TILE_SIZE):
            for y in range(start_y - Config.TILE_SIZE, start_y + Config.HEIGHT + Config.TILE_SIZE, Config.TILE_SIZE):
                rel_pos = pygame.Vector2(x, y) - self.offset
                pygame.draw.rect(surface, Config.COLORS["TILE"], (rel_pos.x, rel_pos.y, Config.TILE_SIZE-1, Config.TILE_SIZE-1))

# ----------------------------------------------------------------
# 3. 캐릭터 및 적 클래스
# ----------------------------------------------------------------
class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, size, color):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size//2, size//2), size//2)
        self.rect = self.image.get_rect()
        self.world_pos = pygame.Vector2(x, y)
        self.hp = 100
        self.max_hp = 100

    def draw(self, surface, camera):
        self.rect.center = camera.apply(self.world_pos)
        surface.blit(self.image, self.rect)

class Player(Entity):
    def __init__(self):
        super().__init__(0, 0, 30, Config.COLORS["PLAYER"])
        self.speed = 4.5
        self.level = 1
        self.exp = 0
        self.exp_next = 50
        self.magics = []

    def update(self):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: move.y -= 1
        if keys[pygame.K_s]: move.y += 1
        if keys[pygame.K_a]: move.x -= 1
        if keys[pygame.K_d]: move.x += 1
        if move.length() > 0:
            self.world_pos += move.normalize() * self.speed

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_next:
            self.level += 1
            self.exp -= self.exp_next
            self.exp_next = int(self.exp_next * 1.4)
            return True
        return False

class Enemy(Entity):
    def __init__(self, x, y, e_type):
        size = 30 if e_type == "dementor" else 20
        color = Config.COLORS["DEMENTOR"] if e_type == "dementor" else Config.COLORS["DEATH_EATER"]
        super().__init__(x, y, size, color)
        self.speed = 1.0 if e_type == "dementor" else 2.8
        self.hp = 30 if e_type == "dementor" else 12
        self.exp_val = 20

    def update(self, p_pos):
        dir_vec = (p_pos - self.world_pos)
        if dir_vec.length() > 0:
            self.world_pos += dir_vec.normalize() * self.speed

# ----------------------------------------------------------------
# 4. 마법 시스템 (Fire, Electric, Shield)
# ----------------------------------------------------------------
class Magic(ABC):
    def __init__(self, owner):
        self.owner = owner
        self.level = 1
        self.last_cast = 0

    @abstractmethod
    def cast(self, enemies, projectiles, current_time): pass

class FireMagic(Magic):
    DATA = {1: [15, 700], 2: [25, 600], 3: [40, 450]} # 데미지, 쿨타임
    def cast(self, enemies, projectiles, current_time):
        stats = self.DATA.get(self.level, self.DATA[3])
        if enemies and current_time - self.last_cast > stats[1]:
            target = min(enemies, key=lambda e: e.world_pos.distance_to(self.owner.world_pos))
            projectiles.add(SpellProjectile(self.owner.world_pos, target.world_pos, stats[0], Config.COLORS["FIRE"]))
            self.last_cast = current_time

class ElectricMagic(Magic):
    DATA = {1: [10, 1000, 3], 2: [15, 900, 5], 3: [20, 800, 8]} # 데미지, 쿨타임, 타겟 수
    def cast(self, enemies, projectiles, current_time):
        stats = self.DATA.get(self.level, self.DATA[3])
        if enemies and current_time - self.last_cast > stats[1]:
            # 여러 적에게 전기 충격 (단순 구현을 위해 가장 가까운 N명 타격)
            sorted_enemies = sorted(enemies, key=lambda e: e.world_pos.distance_to(self.owner.world_pos))
            for i in range(min(len(sorted_enemies), stats[2])):
                sorted_enemies[i].hp -= stats[0]
            self.last_cast = current_time

class ShieldMagic(Magic):
    DATA = {1: [2, 80], 2: [4, 110], 3: [6, 150]} # 틱데미지, 범위
    def cast(self, enemies, projectiles, current_time):
        stats = self.DATA.get(self.level, self.DATA[3])
        # 보호막은 상시 유지 효과 (충돌 로직에서 처리됨)
        pass

class SpellProjectile(Entity):
    def __init__(self, pos, target, dmg, color):
        super().__init__(pos.x, pos.y, 12, color)
        self.dir = (target - pos).normalize()
        self.damage = dmg
        self.spawn_t = pygame.time.get_ticks()

    def update(self):
        self.world_pos += self.dir * 9
        if pygame.time.get_ticks() - self.spawn_t > 1500: self.kill()

# ----------------------------------------------------------------
# 5. 게임 컨트롤러
# ----------------------------------------------------------------
class GameController:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))
        self.clock = pygame.time.Clock()
        self.camera = Camera()
        self.player = Player()
        
        # 초기 마법: 불 마법
        self.player.magics.append(FireMagic(self.player))
        self.player.magics.append(ShieldMagic(self.player)) # 테스트용 보호막 추가
        
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.is_paused = False
        self.font = pygame.font.SysFont("malgungothic", 22, bold=True)

    def spawn(self):
        if len(self.enemies) < 25:
            angle = random.uniform(0, math.pi*2)
            pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * 550
            self.enemies.add(Enemy(pos.x, pos.y, random.choice(["dementor", "death_eater"])))

    def collisions(self):
        # 마법 투사체 충돌
        for p in self.projectiles:
            hit = pygame.sprite.spritecollide(p, self.enemies, False)
            if hit:
                hit[0].hp -= p.damage
                if hit[0].hp <= 0:
                    if self.player.gain_exp(hit[0].exp_val): self.is_paused = True
                    hit[0].kill()
                p.kill()

        # 보호막 및 접촉 충돌
        shield = next((m for m in self.player.magics if isinstance(m, ShieldMagic)), None)
        for e in self.enemies:
            dist = e.world_pos.distance_to(self.player.world_pos)
            # 1. 보호막 판정
            if shield and dist < shield.DATA[shield.level][1]:
                e.hp -= shield.DATA[shield.level][0]
                # 밀쳐내기 효과
                e.world_pos += (e.world_pos - self.player.world_pos).normalize() * 2
            
            # 2. 플레이어 본체 충돌
            if dist < 25:
                self.player.hp -= 0.5
                if self.player.hp <= 0: exit()
            
            # 적 사망 체크 (보호막/전기 데미지)
            if e.hp <= 0:
                if self.player.gain_exp(e.exp_val): self.is_paused = True
                e.kill()

    def draw_ui(self):
        # 상단 마력(EXP) 및 체력(HP) 게이지
        exp_w = (self.player.exp / self.player.exp_next) * Config.WIDTH
        pygame.draw.rect(self.screen, (20,20,30), (0,0,Config.WIDTH, 12))
        pygame.draw.rect(self.screen, Config.COLORS["UI_EXP"], (0,0,exp_w, 12))
        hp_w = (max(0, self.player.hp)/100) * Config.WIDTH
        pygame.draw.rect(self.screen, (20,20,30), (0,12,Config.WIDTH, 12))
        pygame.draw.rect(self.screen, Config.COLORS["UI_HP"], (0,12,hp_w, 12))
        
        txt = self.font.render(f"WIZARD LEVEL: {self.player.level}", True, (255,255,255))
        self.screen.blit(txt, (10, 35))

    def run(self):
        while True:
            dt = self.clock.tick(Config.FPS)
            now = pygame.time.get_ticks()
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return
                if self.is_paused and e.type == pygame.KEYDOWN:
                    # 선택 시스템 (단순화: 1-Fire, 2-Electric, 3-Shield 업그레이드)
                    if e.key == pygame.K_1: 
                        m = next((m for m in self.player.magics if isinstance(m, FireMagic)), None)
                        if m: m.level += 1
                        self.is_paused = False
                    elif e.key == pygame.K_2:
                        if not any(isinstance(m, ElectricMagic) for m in self.player.magics):
                            self.player.magics.append(ElectricMagic(self.player))
                        else:
                            next(m for m in self.player.magics if isinstance(m, ElectricMagic)).level += 1
                        self.is_paused = False
                    elif e.key == pygame.K_3:
                        m = next((m for m in self.player.magics if isinstance(m, ShieldMagic)), None)
                        if m: m.level += 1
                        self.is_paused = False

            if not self.is_paused:
                self.player.update()
                self.spawn()
                self.enemies.update(self.player.world_pos)
                self.projectiles.update()
                for m in self.player.magics: m.cast(self.enemies.sprites(), self.projectiles, now)
                self.collisions()
                self.camera.update(self.player.world_pos)

            self.screen.fill(Config.COLORS["BG"])
            self.camera.draw_bg(self.screen)
            
            # 보호막 시각 효과
            shield = next((m for m in self.player.magics if isinstance(m, ShieldMagic)), None)
            if shield:
                s_pos = self.camera.apply(self.player.world_pos)
                s_radius = shield.DATA[shield.level][1]
                s_surface = pygame.Surface((s_radius*2, s_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(s_surface, (200, 230, 255, 60), (s_radius, s_radius), s_radius)
                self.screen.blit(s_surface, (s_pos.x - s_radius, s_pos.y - s_radius))

            for s in list(self.enemies) + list(self.projectiles) + [self.player]:
                s.draw(self.screen, self.camera)
            
            self.draw_ui()
            if self.is_paused:
                overlay = pygame.Surface((Config.WIDTH, Config.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,180))
                self.screen.blit(overlay, (0,0))
                msg = self.font.render("스펠북이 열렸습니다! [1:불, 2:전기, 3:보호막] 강화", True, (255, 215, 0))
                self.screen.blit(msg, (Config.WIDTH//2 - 250, Config.HEIGHT//2))
            
            pygame.display.flip()

if __name__ == "__main__":
    GameController().run()