import pygame
import math
from config import WIDTH, HEIGHT, exp_need_for_level

# -----------------------------
# 1. Base Entities
# -----------------------------
class Player:
    def __init__(self, config):
        self.pos = pygame.Vector2(WIDTH * 0.5, HEIGHT * 0.55)
        # 스킬 시스템 조준을 위해 화면 위치 정보 추가
        self.screen_pos = pygame.Vector2(self.pos.x, self.pos.y)
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
        # 위치 이동 후 화면 좌표 동기화
        self.screen_pos = pygame.Vector2(self.pos.x, self.pos.y)

    def add_exp(self, amount: int) -> bool:
        # ✅ 최고 레벨 23으로 수정
        if self.level >= 23:
            return False
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
        self.max_hp = hp
        self.hp = hp
        self.exp_reward = exp_reward
        self.img = img
        self.radius = radius
        
        self.speed = 100
        self.random_vel = pygame.Vector2(0, 0)
        self.random_change_t = 0.0

    def alive(self):
        return self.hp > 0