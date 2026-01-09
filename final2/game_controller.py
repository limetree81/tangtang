import math
import pygame
import random
from config import (WIDTH, HEIGHT, SFX_MIDBOSS_SPAWN, BGM_FINAL_BOSS)
from entities import Enemy, Player

class WaveManager:
    """적 스폰과 관련된 시간 및 웨이브 상태를 관리하며, 사운드 트리거를 포함합니다."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.elapsed = 0.0
        self.total_time = 300.0
        self.prev_second = -1
        self.midboss_spawned = False
        self.finalboss_spawned = False
        self.boss_deadline = None
        self.active_boss_kind = None
        self.max_enemies_alive = 60

    def update(self, dt, gs, controller):
        self.elapsed += dt
        cur_sec = int(self.elapsed)
        
        if cur_sec != self.prev_second:
            self.prev_second = cur_sec
            self._spawn_routine(gs, controller)

        # 보스 스폰 체크
        if not self.midboss_spawned and self.elapsed >= 120:
            self._spawn_boss(gs, controller, "midboss")
        if not self.finalboss_spawned and self.elapsed >= 240:
            self._spawn_boss(gs, controller, "finalboss")

    def _spawn_routine(self, gs, controller):
        if len(controller.enemies) < self.max_enemies_alive:
            kind = "spider" if self.prev_second % 2 == 1 else "skull"
            side = random.choice(["top", "bottom", "left", "right"])
            margin = 30
            if side == "top": pos = (random.randint(margin, WIDTH - margin), -margin)
            elif side == "bottom": pos = (random.randint(margin, WIDTH - margin), HEIGHT + margin)
            elif side == "left": pos = (-margin, random.randint(80, HEIGHT - margin))
            else: pos = (WIDTH + margin, random.randint(80, HEIGHT - margin))
                
            img = gs.img_spider if kind == "spider" else gs.img_skull
            controller.enemies.append(Enemy(kind, pos, 10, 10, img))

    def _spawn_boss(self, gs, controller, kind):
        is_mid = (kind == "midboss")
        e = Enemy(kind, (WIDTH*0.7, HEIGHT*0.4), 
                  500 if is_mid else 1000, 
                  500 if is_mid else 0, 
                  gs.img_midboss if is_mid else gs.img_finalboss, 
                  36 if is_mid else 72)
        
        e.speed = 480 if is_mid else 260
        controller.enemies.append(e)
        
        self.active_boss_kind = kind
        self.boss_deadline = self.elapsed + 60.0
        
        # ✅ [수정] bgm -> audio로 변경 (GameScreen 속성 이름 일치)
        if is_mid:
            # 중간 보스: 효과음 1회 재생
            gs.audio.play_sfx(SFX_MIDBOSS_SPAWN)
            self.midboss_spawned = True
        else:
            # 최종 보스: 배경음악 교체
            gs.audio.play_bgm(BGM_FINAL_BOSS)
            self.finalboss_spawned = True

class GameController:
    def __init__(self, rm, player_config):
        self.rm = rm
        self.player_config = player_config
        self.wave_mgr = WaveManager()
        self.reset()

    def reset(self):
        self.player = Player(self.player_config)
        self.enemies = []
        self.skill_projectiles = [] 
        self.wave_mgr.reset()

    def tick_logic(self, dt, gs):
        self.wave_mgr.update(dt, gs, self)
        
        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        
        # 적 이동 로직
        for e in self.enemies:
            if not e.alive(): continue
            if e.kind in ("spider", "skull"):
                dv = self.player.pos - e.pos
                if dv.length_squared() > 0: e.pos += dv.normalize() * e.speed * dt
            else:
                e.random_change_t -= dt
                if e.random_change_t <= 0:
                    e.random_change_t = random.uniform(0.3, 0.7)
                    ang = random.uniform(0, math.tau)
                    e.random_vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * e.speed
                e.pos += e.random_vel * dt
                e.pos.x = max(60, min(WIDTH - 60, e.pos.x))
                e.pos.y = max(110, min(HEIGHT - 60, e.pos.y))

        # 스킬 업데이트
        for s in gs.skills:
            if s.level > 0: s.update(dt, self.player, self.enemies, self.skill_projectiles)
            
        # [충돌 로직 유지] 투사체 이동 및 적과의 충돌 처리
        for p in self.skill_projectiles[:]:
            p.update(dt)
            
            if p.life <= 0:
                if p in self.skill_projectiles: 
                    self.skill_projectiles.remove(p)
                continue

            hit_something = False
            
            for e in self.enemies:
                if not e.alive(): continue
                
                col_dist = e.radius + 10
                dist_sq = (e.pos - p.pos).length_squared()
                
                if dist_sq <= col_dist ** 2:
                    hit_something = True
                    
                    if getattr(p, 'is_fire', False):
                        ex_radius = getattr(p, 'explosion_radius', 60)
                        for target in self.enemies:
                            if target.alive() and (target.pos - p.pos).length_squared() <= ex_radius**2:
                                target.hp -= p.damage
                    else:
                        e.hp -= p.damage
                    
                    break
            
            if hit_something:
                if p in self.skill_projectiles:
                    self.skill_projectiles.remove(p)

        self._handle_collisions_and_rewards(dt, gs)
        self.enemies = [e for e in self.enemies if e.alive()]

    def _handle_collisions_and_rewards(self, dt, gs):
        p_pos = self.player.pos
        p_rad = self.player.radius
        leveled_up = False

        for e in self.enemies:
            if e.alive():
                dist_sq = (e.pos - p_pos).length_squared()
                min_dist = e.radius + p_rad
                if dist_sq <= min_dist**2:
                    dmg_mult = 1.5 if e.kind in ("midboss", "finalboss") else 1.0
                    self.player.hp -= 25 * dmg_mult * dt
                    if dist_sq > 0: e.pos = p_pos + (e.pos - p_pos).normalize() * (min_dist + 2)
            
            if not e.alive() and not getattr(e, '_rewarded', False):
                if e.kind in ("spider", "skull"):
                    self.player.kills += 1
                    if self.player.add_exp(e.exp_reward): leveled_up = True
                elif e.kind == "midboss":
                    if self.player.add_exp(800): leveled_up = True
                    self.wave_mgr.boss_deadline = None
                    self.wave_mgr.active_boss_kind = None
                elif e.kind == "finalboss":
                    gs.finish_game(True, "최종 보스 처치!")
                e._rewarded = True

        if leveled_up: gs.trigger_level_up()