import pygame
import math
from config import WIDTH, HEIGHT, BLUE, YELLOW, MAX_SKILL_LEVEL, exp_need_for_level

# -----------------------------
# 1. Base Entities
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
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.exp_reward = int(exp_reward)
        self.radius = radius
        self.img = img
        self.speed = 110 if kind in ("spider", "skull") else 220
        self.random_vel = pygame.Vector2(0, 0)
        self.random_change_t = 0.0

    def alive(self): return self.hp > 0

class Bullet:
    def __init__(self, pos, direction, damage):
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0: self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize()
        self.speed = 700
        self.damage = float(damage)
        self.radius = 5

    def update(self, dt):
        self.pos += self.dir * self.speed * dt

    def out_of_bounds(self):
        return self.pos.x < -50 or self.pos.x > WIDTH + 50 or self.pos.y < -50 or self.pos.y > HEIGHT + 50

class SkillProjectile:
    def __init__(self, pos, direction, speed, damage, img, radius=12, life=2.0, pierce=1):
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction)
        if self.dir.length_squared() == 0: self.dir = pygame.Vector2(1, 0)
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
        return self.life <= 0 or self.pos.x < -200 or self.pos.x > WIDTH + 200 or self.pos.y < -200 or self.pos.y > HEIGHT + 200

    def draw(self, surf):
        r = self.rot_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surf.blit(self.rot_img, r)

# -----------------------------
# 2. Weapons
# -----------------------------
class WeaponBase:
    def __init__(self, unlocked=False):
        self.unlocked = unlocked
        self.level = 1 if unlocked else 0
    def is_max(self): return self.unlocked and self.level >= MAX_SKILL_LEVEL
    def can_offer(self): return not self.is_max()
    def acquire_or_level(self):
        if not self.unlocked:
            self.unlocked = True
            self.level = 1
            return
        if self.level < MAX_SKILL_LEVEL: self.level += 1
    def update(self, dt, gs): pass
    def draw(self, surf, gs): pass

class MagicGun(WeaponBase):
    key = "gun"; name = "마법 총"; color = BLUE
    def __init__(self):
        super().__init__(unlocked=True)
        self.cool = 1.0; self.t = 0.0
    def update(self, dt, gs):
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos()
        dirv = pygame.Vector2(mx, my) - gs.controller.player.pos
        base_ang = math.atan2(dirv.y, dirv.x)
        count = max(1, int(self.level)); dmg = 10 * gs.controller.player.dmg
        spread = 0.22
        angles = [base_ang] if count == 1 else [base_ang + spread*(i-(count-1)/2) for i in range(count)]
        for a in angles:
            gs.controller.bullets.append(Bullet(gs.controller.player.pos, pygame.Vector2(math.cos(a), math.sin(a)), dmg))

class FireBall(WeaponBase):
    key = "fire"; name = "파이어볼"; color = (255, 140, 110)
    def __init__(self):
        super().__init__(unlocked=False)
        self.cool = 1.8; self.t = 0.0
    def update(self, dt, gs):
        if not self.unlocked: return
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos()
        dirv = pygame.Vector2(mx, my) - gs.controller.player.pos
        speed = 520+40*(self.level-1); dmg = (18+8*(self.level-1))*gs.controller.player.dmg
        gs.controller.skill_projectiles.append(SkillProjectile(gs.controller.player.pos, dirv, speed, dmg, gs.img_fire_skill, 14, 2.2, 1+(1 if self.level>=4 else 0)))

class ElectricShock(WeaponBase):
    key = "elec"; name = "전기"; color = YELLOW
    def __init__(self):
        super().__init__(unlocked=False)
        self.cool = 2.3; self.t = 0.0
    def update(self, dt, gs):
        if not self.unlocked: return
        self.t += dt
        if self.t < self.cool: return
        self.t -= self.cool
        mx, my = pygame.mouse.get_pos()
        base_dir = pygame.Vector2(mx, my) - gs.controller.player.pos
        base_ang = math.atan2(base_dir.y, base_dir.x); count = min(4, self.level); spread = 0.18
        angles = [base_ang] if count == 1 else [base_ang + spread*(i-(count-1)/2) for i in range(count)]
        for a in angles:
            gs.controller.skill_projectiles.append(SkillProjectile(gs.controller.player.pos, pygame.Vector2(math.cos(a), math.sin(a)), 650+30*(self.level-1), (14+6*(self.level-1))*gs.controller.player.dmg, gs.img_elec_skill, 12, 1.8, 1+(1 if self.level>=5 else 0)))

class ProtectShield(WeaponBase):
    key = "shield"; name = "보호막"; color = (140, 255, 180)
    def __init__(self):
        super().__init__(unlocked=False)
        self.tick = 0.0; self.tick_interval = 0.5
    def update(self, dt, gs):
        if not self.unlocked: return
        self.tick += dt
        if self.tick < self.tick_interval: return
        self.tick -= self.tick_interval
        rad = 50+50*(self.level-1); dmg = 10*gs.controller.player.dmg
        for e in gs.controller.enemies:
            if e.alive() and (e.pos - gs.controller.player.pos).length_squared() <= (rad + e.radius)**2: e.hp -= dmg
    def draw(self, surf, gs):
        if self.unlocked:
            pygame.draw.circle(surf, (120, 255, 180), (int(gs.controller.player.pos.x), int(gs.controller.player.pos.y)), 50+50*(self.level-1), 3)