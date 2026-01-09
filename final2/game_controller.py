import math
import pygame
import random
from config import (WIDTH, HEIGHT, SFX_MIDBOSS_SPAWN, BGM_FINAL_BOSS, DIFFICULTY_SETTINGS)
from entities import Enemy, Player

class WaveManager:
    """적 스폰과 관련된 시간 및 웨이브 상태를 관리하며, 사운드 트리거를 포함합니다."""
    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty
        self.reset()

    def reset(self):
        self.elapsed = 0.0
        self.total_time = 300.0 # 5분 제한
        self.prev_second = -1
        self.midboss_spawned = False
        self.finalboss_spawned = False
        self.boss_deadline = None
        self.active_boss_kind = None
        self.boss_time_over = False

        # 난이도 설정 적용
        self._apply_difficulty()

    def _apply_difficulty(self):
        """config.py에서 난이도 설정을 가져와 적용합니다."""
        # 설정이 없으면 normal을 기본값으로 사용
        settings = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["normal"])
        
        # ✅ 계단식 스폰 확률을 위한 시작/끝 값 로드
        self.spawn_prob_start = settings["spawn_prob_start"]
        self.spawn_prob_end = settings["spawn_prob_end"]
        self.spawn_prob = self.spawn_prob_start # 초기값 설정

        self.boss_time_limit = settings["boss_time_limit"]
        self.max_enemies_alive = settings["max_enemies"]
        self.boss_speed_mult = settings["boss_speed_mult"]
        self.boss_count = settings["boss_count"]     # 보스 소환 수
        self.mob_hp = settings["mob_hp"]             # 일반 몬스터 체력
        self.boss_hp = settings["boss_hp"]           # 보스 체력
        self.exp_drop = settings["exp_drop"]         # 경험치 고정값
        self.mob_damage = settings["mob_damage"]
        self.boss_damage = settings["boss_damage"]

    def update(self, dt, gs, controller):
        self.elapsed += dt
        
        # ✅ [추가] 계단식 스폰 확률 증가 로직 (1분마다 단계 상승)
        # 총 5분(300초) 게임이므로, 0~4단계 (총 5단계)
        # 0분대: 0단계, 1분대: 1단계 ... 4분대: 4단계
        current_phase = int(self.elapsed / 60.0)
        max_phases = 4 # 0, 1, 2, 3, 4 (총 5단계)
        
        # 범위를 0~4로 제한
        current_phase = min(current_phase, max_phases)
        
        # 선형 보간 (Lerp) 비율 계산 (0.0 ~ 1.0)
        ratio = current_phase / float(max_phases)
        
        # 현재 스폰 확률 갱신
        self.spawn_prob = self.spawn_prob_start + (self.spawn_prob_end - self.spawn_prob_start) * ratio

        # 매 프레임 확률 기반 스폰 로직
        if random.random() < self.spawn_prob:
            self._spawn_routine(gs, controller)

        # 보스 스폰 체크 (시간 기반)
        if not self.midboss_spawned and self.elapsed >= 120:
            self._spawn_boss(gs, controller, "midboss")
        if not self.finalboss_spawned and self.elapsed >= 240:
            self._spawn_boss(gs, controller, "finalboss")
            
        # 보스 제한 시간 체크
        if self.boss_deadline and self.elapsed >= self.boss_deadline:
            self.boss_time_over = True

    def _spawn_routine(self, gs, controller):
        if len(controller.enemies) < self.max_enemies_alive:
            # 종류 결정: 2초 단위로 종류가 바뀌는 기존 로직의 감성 유지
            current_sec = int(self.elapsed)
            kind = "spider" if current_sec % 2 == 1 else "skull"
            
            side = random.choice(["top", "bottom", "left", "right"])
            margin = 30
            if side == "top": pos = (random.randint(margin, WIDTH - margin), -margin)
            elif side == "bottom": pos = (random.randint(margin, WIDTH - margin), HEIGHT + margin)
            elif side == "left": pos = (-margin, random.randint(80, HEIGHT - margin))
            else: pos = (WIDTH + margin, random.randint(80, HEIGHT - margin))
                
            img = gs.img_spider if kind == "spider" else gs.img_skull
            
            # 경험치 계산: Config의 상수값 사용
            calculated_exp = self.exp_drop
            
            # config에서 가져온 체력 적용
            controller.enemies.append(Enemy(kind, pos, self.mob_hp, calculated_exp, img))

    def _spawn_boss(self, gs, controller, kind):
        is_mid = (kind == "midboss")
        
        # 중간 보스는 설정된 보스 체력의 50%
        base_hp = self.boss_hp * 0.5 if is_mid else self.boss_hp
        
        base_speed = 480 if is_mid else 260
        final_speed = base_speed * self.boss_speed_mult
        
        # 난이도 설정에 따른 마리 수만큼 소환
        for i in range(self.boss_count):
            # 여러 마리 소환 시 위치를 약간씩 다르게
            offset_x = (i - (self.boss_count - 1) / 2) * 150
            spawn_pos = (WIDTH * 0.7 + offset_x, HEIGHT * 0.4)
            
            e = Enemy(kind, spawn_pos, 
                      base_hp, 
                      500 if is_mid else 0, 
                      gs.img_midboss if is_mid else gs.img_finalboss, 
                      36 if is_mid else 72)
            e.speed = final_speed
            controller.enemies.append(e)
        
        self.active_boss_kind = kind
        self.boss_deadline = self.elapsed + self.boss_time_limit
        self.boss_time_over = False
        
        # 사운드 제어 (한 번만 재생)
        if is_mid:
            gs.audio.play_sfx(SFX_MIDBOSS_SPAWN)
            self.midboss_spawned = True
        else:
            gs.audio.play_bgm(BGM_FINAL_BOSS)
            self.finalboss_spawned = True

class GameController:
    def __init__(self, rm, player_config):
        self.rm = rm
        self.player_config = player_config
        # 플레이어 설정에서 난이도 가져오기 (기본값 normal)
        difficulty = player_config.get("DIFFICULTY", "normal")
        self.wave_mgr = WaveManager(difficulty)
        self.reset()

    def reset(self):
        self.player = Player(self.player_config)
        self.enemies = []
        self.skill_projectiles = [] 
        self.wave_mgr.reset()

    def tick_logic(self, dt, gs):
        self.wave_mgr.update(dt, gs, self)
        
        # 보스 시간 초과 시 게임 종료
        if self.wave_mgr.boss_time_over:
            gs.finish_game(False, "보스 처치 시간 초과!")
            return

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
            
        # 투사체 이동 및 충돌 처리
        for p in self.skill_projectiles[:]:
            p.update(dt)
            
            if p.life <= 0:
                if p in self.skill_projectiles: 
                    self.skill_projectiles.remove(p)
                continue

            hit_something = False
            
            # 플레이어의 데미지 배율 적용
            actual_damage = p.damage * self.player.dmg

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
                                target.hp -= actual_damage
                    else:
                        e.hp -= actual_damage
                    
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
        
        # 현재 살아있는 보스 카운트 (보스 2마리 모두 처치해야 완료되도록)
        bosses_alive = sum(1 for e in self.enemies if e.kind in ("midboss", "finalboss"))

        for e in self.enemies:
            if e.alive():
                dist_sq = (e.pos - p_pos).length_squared()
                min_dist = e.radius + p_rad
                
                # 플레이어 vs 적 충돌 처리
                if dist_sq <= min_dist**2:
                    if e.kind in ("midboss", "finalboss"):
                        damage_amount = self.wave_mgr.boss_damage
                    else:
                        damage_amount = self.wave_mgr.mob_damage
                        
                    self.player.hp -= damage_amount * dt
                    
                    # 충돌 시 적을 살짝 밀어냄
                    if dist_sq > 0: e.pos = p_pos + (e.pos - p_pos).normalize() * (min_dist + 2)
            
            if not e.alive() and not getattr(e, '_rewarded', False):
                if e.kind in ("spider", "skull"):
                    self.player.kills += 1
                    if self.player.add_exp(e.exp_reward): leveled_up = True
                elif e.kind == "midboss":
                    if self.player.add_exp(800): leveled_up = True
                    # 모든 보스가 죽었는지 체크
                    if bosses_alive <= 1: # 지금 죽은 녀석 포함이므로 1 이하
                        self.wave_mgr.boss_deadline = None
                        self.wave_mgr.active_boss_kind = None
                        self.wave_mgr.boss_time_over = False
                elif e.kind == "finalboss":
                    if bosses_alive <= 1:
                        gs.finish_game(True, "최종 보스 처치!")
                e._rewarded = True

        if leveled_up: gs.trigger_level_up()