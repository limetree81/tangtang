import pygame
import random
import math
from config import WIDTH, HEIGHT
from entities import Player, Enemy

# -----------------------------
# 1. Wave Manager (Spawning Logic)
# -----------------------------
class WaveManager:
    """적 스폰과 관련된 시간 및 웨이브 상태를 관리합니다."""
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
        """매 프레임 호출되어 스폰 타이머와 보스 이벤트를 체크합니다."""
        self.elapsed += dt
        cur_sec = int(self.elapsed)
        
        # 1초마다 일반 몹 스폰 체크
        if cur_sec != self.prev_second:
            self.prev_second = cur_sec
            self._spawn_routine(gs, controller)

        # 보스 스폰 및 제한시간 체크
        if not self.midboss_spawned and self.elapsed >= 120:
            self._spawn_boss(gs, controller, "midboss")
        if not self.finalboss_spawned and self.elapsed >= 240:
            self._spawn_boss(gs, controller, "finalboss")

    def _spawn_routine(self, gs, controller):
        """일반 몬스터를 화면 가장자리에서 생성합니다."""
        if len(controller.enemies) < self.max_enemies_alive:
            kind = "spider" if self.prev_second % 2 == 1 else "skull"
            side = random.choice(["top", "bottom", "left", "right"])
            margin = 30
            
            if side == "top":
                pos = (random.randint(margin, WIDTH - margin), -margin)
            elif side == "bottom":
                pos = (random.randint(margin, WIDTH - margin), HEIGHT + margin)
            elif side == "left":
                pos = (-margin, random.randint(80, HEIGHT - margin))
            else:
                pos = (WIDTH + margin, random.randint(80, HEIGHT - margin))
                
            img = gs.img_spider if kind == "spider" else gs.img_skull
            controller.enemies.append(Enemy(kind, pos, 20, 10, img))

    def _spawn_boss(self, gs, controller, kind):
        """중간 보스 및 최종 보스를 생성합니다."""
        is_mid = (kind == "midboss")
        e = Enemy(kind, (WIDTH*0.7, HEIGHT*0.4), 
                  500 if is_mid else 1000, 
                  500 if is_mid else 0, 
                  gs.img_midboss if is_mid else gs.img_finalboss, 
                  36 if is_mid else 72)
        
        # 중간 보스는 이동속도 2배 (기존 로직 계승)
        e.speed = 480 if is_mid else 260
        controller.enemies.append(e)
        
        self.active_boss_kind = kind
        self.boss_deadline = self.elapsed + 60.0
        
        if is_mid: self.midboss_spawned = True
        else: self.finalboss_spawned = True

# -----------------------------
# 2. Game Controller
# -----------------------------
class GameController:
    """게임의 핵심 물리 엔진, 충돌 판정, 보상 시스템을 관리합니다."""
    def __init__(self, rm, player_config):
        self.rm = rm
        self.player_config = player_config
        # 동일 파일 내의 WaveManager 인스턴스 생성
        self.wave_mgr = WaveManager()
        self.reset()

    def reset(self):
        """게임 데이터를 초기 상태로 리셋합니다."""
        self.player = Player(self.player_config)
        self.enemies = []
        self.skill_projectiles = [] 
        self.wave_mgr.reset()

    def tick_logic(self, dt, gs):
        """게임의 주 루프에서 실행되는 로직 업데이트입니다."""
        # 1. WaveManager에게 스폰 업무 위임
        self.wave_mgr.update(dt, gs, self)

        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        
        # 2. 적 이동 로직
        for e in self.enemies:
            if not e.alive(): continue
            if e.kind in ("spider", "skull"):
                dv = self.player.pos - e.pos
                if dv.length_squared() > 0:
                    e.pos += dv.normalize() * e.speed * dt
            else:
                # 보스 랜덤 이동 (방향 전환 및 화면 경계 제한)
                e.random_change_t -= dt
                if e.random_change_t <= 0:
                    e.random_change_t = random.uniform(0.2, 0.6)
                    ang = random.uniform(0, math.tau)
                    e.random_vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * e.speed
                e.pos += e.random_vel * dt
                e.pos.x = max(60, min(WIDTH - 60, e.pos.x))
                e.pos.y = max(110, min(HEIGHT - 60, e.pos.y))

        # 3. 스킬 업데이트 (장착된 스킬들)
        for s in gs.skills:
            if s.level > 0:
                s.update(dt, self.player, self.enemies, self.skill_projectiles)
            
        # 4. 투사체 이동 및 충돌
        for p in self.skill_projectiles[:]:
            p.update(dt)
            if p.life <= 0:
                if p in self.skill_projectiles: self.skill_projectiles.remove(p)
                continue
            
            if p.damage > 0:
                for e in self.enemies:
                    if not e.alive(): continue
                    # 투사체와 적의 반경 기반 충돌 판정
                    if (e.pos - p.pos).length_squared() <= (e.radius + 10)**2:
                        e.hp -= p.damage
                        # 파이어볼은 관통형이므로 제외, 일반 투사체는 소멸
                        if not getattr(p, 'is_fire', False):
                            if p in self.skill_projectiles: self.skill_projectiles.remove(p)
                        break

        # 5. 플레이어 피격 및 보상(경험치 등) 처리
        self._handle_collisions_and_rewards(dt, gs)

        # 6. 리스트 정리 (죽은 적들 완전히 제거)
        self.enemies = [e for e in self.enemies if e.alive()]

    def _handle_collisions_and_rewards(self, dt, gs):
        """플레이어와 적의 충돌 처리 및 사망 시 보상 지급을 담당합니다."""
        p_pos = self.player.pos
        p_rad = self.player.radius
        leveled_up = False

        for e in self.enemies:
            if e.alive():
                diff = e.pos - p_pos
                dist_sq = diff.length_squared()
                min_dist = e.radius + p_rad
                # 충돌 시 데미지 및 밀쳐내기
                if dist_sq <= min_dist**2:
                    self.player.hp -= (35 if e.kind == "finalboss" else 20) * dt
                    if dist_sq > 0:
                        e.pos = p_pos + diff.normalize() * (min_dist + 1)
                    else:
                        e.pos.x += random.choice([-1, 1])

            # 사망 판정 및 보상 처리 (중복 지급 방지 위해 _rewarded 플래그 사용)
            if not e.alive():
                if not getattr(e, '_rewarded', False):
                    if e.kind in ("spider", "skull"):
                        self.player.kills += 1
                        if self.player.add_exp(e.exp_reward): leveled_up = True
                    elif e.kind == "midboss":
                        if self.player.add_exp(500): leveled_up = True
                        self.wave_mgr.boss_deadline = None
                        self.wave_mgr.active_boss_kind = None
                    elif e.kind == "finalboss":
                        gs.finish_game(True, "최종 보스 처치!")
                    e._rewarded = True

        if leveled_up: 
            gs.trigger_level_up()
