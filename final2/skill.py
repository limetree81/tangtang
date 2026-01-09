import math
import pygame
import random

# =========================
# Projectile 클래스
# =========================
class Projectile:
    def __init__(self, pos, vel, damage, size=(10, 10), life=2.0, color=(255, 255, 255), is_fire=False):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.damage = damage
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.is_fire = is_fire
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        self.rect.topleft = (self.pos.x, self.pos.y)

    def draw(self, surf, cam):
        screen_pos = (self.pos.x - cam.x, self.pos.y - cam.y)
        alpha = int((self.life / self.max_life) * 255)
        
        if self.is_fire:
            # [일직선 화염 기둥 시각화]
            # 진행 방향에 맞춰 직사각형을 회전시킵니다.
            angle = math.degrees(math.atan2(-self.vel.y, self.vel.x))
            
            # size[1]은 길이(일자로 쭉 뻗는 정도), size[0]은 폭(두께)입니다.
            fire_surf = pygame.Surface((self.size[1], self.size[0]), pygame.SRCALPHA)
            
            # 화염 기둥 효과 (테두리는 붉은색, 안쪽은 밝은 주황색)
            pygame.draw.rect(fire_surf, (*self.color, alpha), (0, 0, self.size[1], self.size[0]), border_radius=5)
            pygame.draw.rect(fire_surf, (255, 200, 50, alpha), (5, 2, self.size[1]-10, self.size[0]-4), border_radius=3)
            
            rotated_fire = pygame.transform.rotate(fire_surf, angle)
            new_rect = rotated_fire.get_rect(center=(screen_pos[0], screen_pos[1]))
            surf.blit(rotated_fire, new_rect.topleft)
        else:
            s = pygame.Surface(self.size, pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surf.blit(s, screen_pos)

# =========================
# SkillBase (공통 부모 클래스)
# =========================
class SkillBase:
    def __init__(self, name, interval, damage):
        self.name = name
        self.level = 1
        self.interval = interval
        self.timer = 0.0
        self.base_damage = damage

    def update(self, dt, player, monsters, projectiles):
        self.timer += dt

    def apply_upgrade(self):
        self.level += 1

# =========================
# 1. BaseShotSkill (마법 총 / 마우스 조준 방식)
# =========================
class BaseShotSkill(SkillBase):
    def __init__(self):
        # 1단계: 기본 발사 - 기본 데미지 10, 초기 발사 간격 1.0초
        super().__init__("마법 총", 1.0, 10)

    def update(self, dt, player, monsters, projectiles):
        super().update(dt, player, monsters, projectiles)
        
        # 레벨업에 따른 발사 속도(interval) 강화 반영
        current_interval = self.interval
        if self.level == 3:
            current_interval *= 0.8  # 20% 속도 강화
        elif self.level == 4:
            current_interval *= 0.8  # 3단계 효과 유지
        elif self.level >= 5:
            current_interval = 0.15   # 5단계: 무한 연사 상태

        if self.timer >= current_interval:
            self.timer = 0
            self.fire_to_mouse(player, projectiles)

    def fire_to_mouse(self, player, projectiles):
        """[기능 추가] 마우스 커서 방향으로 조준하여 발사"""
        # 1. 마우스 현재 위치 가져오기
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        
        # 2. 플레이어의 화면상 위치 가져오기 (메인 엔진의 player.screen_pos 사용)
        # 만약 player 객체에 screen_pos가 없다면 SCREEN_W/2, SCREEN_H/2를 기본값으로 사용
        player_screen = getattr(player, 'screen_pos', pygame.Vector2(1100 // 2, 650 // 2))
        
        # 3. 방향 벡터 계산 (마우스 위치 - 플레이어 위치)
        direction = (mouse_pos - player_screen)
        
        if direction.length_squared() > 0:
            target_dir = direction.normalize()
            
            # 레벨별 투사체 개수 설정
            projectile_count = 1
            if self.level >= 2: projectile_count = 2
            if self.level >= 4: projectile_count = 3
            
            final_damage = self.base_damage
            if self.level >= 5:
                final_damage += 5

            # 4. 투사체 생성 및 발사
            for i in range(projectile_count):
                # 부채꼴 퍼짐 각도 계산
                angle_offset = (i - (projectile_count - 1) / 2) * 15
                vel = target_dir.rotate(angle_offset) * 650  # 빠른 투사체 속도
                
                # 투사체 객체 생성
                projectiles.append(Projectile(
                    player.pos, vel, final_damage, 
                    size=(12, 12), life=2.0, color=(200, 200, 255)
                ))

# =========================
# 2. FireConeSkill (로켓 방식 파이어볼)
# =========================
class FireConeSkill(SkillBase):
    def __init__(self):
        # 1단계: 기본 발사 - 무작위 적 타겟팅, 5초 주기, 데미지 10
        super().__init__("파이어 볼", 5.0, 10)
        self.explosion_radius = 60  # 초기 폭발 반지름

    def update(self, dt, player, monsters, projectiles):
        super().update(dt, player, monsters, projectiles)
        
        # 5단계: 연사력 강화 (발사 간격 30% 감소)
        current_interval = self.interval
        if self.level >= 5:
            current_interval *= 0.7

        if self.timer >= current_interval:
            self.timer = 0
            self.fire_rocket(player, monsters, projectiles)

    def fire_rocket(self, player, monsters, projectiles):
        """1. 타겟팅 로직: 무작위 조준 및 발사"""
        # 3단계: 공격 횟수 증가 (기본 1발, 3단계부터 2발)
        target_count = 1
        if self.level >= 3:
            target_count = 2

        # 4단계: 데미지 강화 (약 80% 상승)
        final_damage = self.base_damage
        if self.level >= 4:
            final_damage *= 1.8

        # 2단계 & 5단계: 폭발 범위 및 크기 설정
        current_radius = self.explosion_radius
        if self.level >= 2:
            current_radius *= 1.5  # 2단계: 범위 1.5배 확대
        if self.level >= 5:
            current_radius *= 1.3  # 5단계: 추가 확대

        # 투사체 크기 (5단계에서 대형화)
        proj_size = (30, 80)
        if self.level >= 5:
            proj_size = (60, 150)

        for _ in range(target_count):
            target_pos = None
            if monsters:
                # [타겟팅] 화면 내 무작위 적 선택
                target_enemy = random.choice(monsters)
                target_pos = target_enemy.pos
            else:
                # 적이 없으면 무작위 방향 설정
                random_angle = random.uniform(0, 360)
                target_pos = player.pos + pygame.Vector2(1, 0).rotate(random_angle) * 100

            # 직선 이동 벡터 계산 (쿠나이보다 느린 350 속도)
            direction = (target_pos - player.pos)
            if direction.length_squared() > 0:
                vel = direction.normalize() * 350
                
                # 로켓 투사체 생성 (is_fire=True, 폭발 전용 속성 추가)
                rocket = Projectile(
                    player.pos, vel, final_damage, 
                    size=proj_size, life=3.0, color=(255, 69, 0), is_fire=True
                )
                # 폭발 반지름 정보를 투사체 객체에 동적 저장 (충돌 시 사용)
                rocket.explosion_radius = current_radius
                projectiles.append(rocket)

    def handle_explosion(self, projectile, monsters):
        """2. 투사체 물리 및 폭발: 원형 범위 피해 판정"""
        # 충돌 지점(projectile.pos)을 중심으로 반지름 내 모든 적 검색
        explosion_pos = projectile.pos
        radius_sq = projectile.explosion_radius ** 2
        
        for m in monsters:
            if (m.pos - explosion_pos).length_squared() <= radius_sq:
                m.hp -= projectile.damage

# =========================
# ElectricShockSkill (일렉트릭 쇼크 - 즉시 타격형)
# =========================
class ElectricShockSkill(SkillBase):
    def __init__(self):
        # 기본 쿨타임 1.0초 (5단계에서 감소됨), 데미지 5
        super().__init__("일렉트릭 쇼크", 1.0, 5)
        self.strike_visuals = []  # 현재 화면에 그려질 번개 시각 효과 리스트

    def update(self, dt, player, monsters, projectiles):
        # 1. 공격 주기 및 상태 관리 (Update Logic)
        self.timer += dt
        
        # [조건 반영] 5단계: 발사 간격(쿨타임) 대폭 감소
        current_cooldown = self.interval
        if self.level >= 5:
            current_cooldown *= 0.4  # 60% 감소 (에너지 큐브 효과 모사)

        if self.timer >= current_cooldown:
            self.timer = 0
            self.strike_lightning(player, monsters)

        # 시각 효과 타이머 업데이트 (0.1초 동안만 유지)
        for visual in self.strike_visuals[:]:
            visual['life'] -= dt
            if visual['life'] <= 0:
                self.strike_visuals.remove(visual)

    def strike_lightning(self, player, monsters):
        """즉시 판정 및 다중 타격 로직"""
        if not monsters:
            return

        # [타겟팅 로직] 1~4단계: 레벨에 따라 번개 줄기 수 결정 (최대 4줄기 + 5단계 보너스)
        strike_count = self.level
        if self.level >= 5:
            strike_count += 2  # 5단계 추가 공격 횟수

        # [보스 우선순위] 보스가 있다면 리스트의 맨 앞으로 가져와 우선 타격 대상에 포함
        sorted_monsters = sorted(monsters, key=lambda m: getattr(m, 'kind', '') == 'finalboss', reverse=True)
        
        # 타겟팅 (다중 타격): 적이 부족하면 있는 만큼만 선택
        targets = random.sample(sorted_monsters, min(len(sorted_monsters), strike_count))

        for target in targets:
            # 1. 즉시 판정 (Hitbox Logic)
            # 타겟팅되는 순간 즉시 HP 감소
            damage = self.base_damage
            if self.level >= 3: # 3단계: 데미지 증가
                damage *= 1.5
            target.hp -= damage

            # 2. 시각 효과 생성 (지그재그 좌표 생성)
            self.create_zigzag_effect(player.pos, target.pos)

    def create_zigzag_effect(self, start_pos, end_pos):
        """시작점과 끝점 사이에 무작위 오프셋을 가진 지그재그 좌표 생성"""
        points = []
        steps = 5 # 지그재그 꺾임 횟수
        
        # 하늘에서 떨어지는 느낌을 위해 시작점을 적의 머리 위로 설정
        sky_start = pygame.Vector2(end_pos.x + random.randint(-20, 20), end_pos.y - 400)
        
        for i in range(steps + 1):
            t = i / steps
            # 선형 보간 점
            base_pos = sky_start.lerp(end_pos, t)
            if 0 < i < steps:
                # 무작위 오프셋(Offset) 추가
                offset = pygame.Vector2(random.randint(-15, 15), random.randint(-10, 10))
                base_pos += offset
            points.append(base_pos)
        
        self.strike_visuals.append({'points': points, 'life': 0.1})

    def draw(self, surf, cam):
        """지그재그 번개 렌더링"""
        for visual in self.strike_visuals:
            if len(visual['points']) < 2:
                continue
            
            # 카메라 좌표로 변환된 점들 생성
            screen_points = [(p.x - cam.x, p.y - cam.y) for p in visual['points']]
            
            # 번개 외곽선 (하늘색/흰색)
            pygame.draw.lines(surf, (200, 255, 255), False, screen_points, 3)
            # 번개 중심선 (흰색)
            pygame.draw.lines(surf, (255, 255, 255), False, screen_points, 1)

# =========================
# 4. ShieldSkill (프로텍트 쉴드 - 지속 범위 및 감속)
# =========================
class ShieldSkill(SkillBase):
    def __init__(self):
        # 1단계: 기본 활성화 - 반지름 50px, 기본 데미지 10, 10초 주기 발동
        super().__init__("프로텍트 쉴드", 10.0, 10)
        self.base_duration = 5.0
        self.radius = 50
        self.is_active = False
        self.active_timer = 0.0

    def update(self, dt, player, monsters, projectiles):
        # 1. 상태 관리 (활성화/비활성화 타이머)
        if not self.is_active:
            self.timer += dt
            if self.timer >= self.interval:
                self.is_active = True
                self.active_timer = 0
                self.timer = 0
        else:
            self.active_timer += dt
            # 레벨업에 따른 유지 기간 증가 (기본 5초 + 레벨당 5초)
            current_duration = self.base_duration + (self.level - 1) * 5.0
            
            # 2 & 5단계: 범위(반지름) 확대 로직
            # 1단계(50) -> 2단계(x1.3) -> 5단계(x1.2 추가)
            calc_radius = self.radius
            if self.level >= 2: calc_radius *= 1.3
            if self.level >= 5: calc_radius *= 1.2
            
            # 3 & 5단계: 데미지 강화 로직
            final_damage = self.base_damage
            if self.level >= 3: final_damage *= 1.5
            if self.level >= 5: final_damage *= 1.4

            if self.active_timer >= current_duration:
                # 보호막 해제 시 몬스터 속도 원복을 위해 추가 처리 필요 (아래 판정 로직 참고)
                self.is_active = False
            else:
                # 2. 판정 로직: 범위 내 적에게 틱 데미지 및 감속(Slow) 적용
                for m in monsters:
                    dist_sq = (m.pos - player.pos).length_squared()
                    if dist_sq <= calc_radius ** 2:
                        # [틱 데미지] dt에 비례하여 지속적으로 HP 차감
                        m.hp -= final_damage * dt
                        
                        # [4단계: 감속 장치] 범위 내 적 이동 속도 30% 감소 (0.7배)
                        if self.level >= 4:
                            # 몬스터의 원본 속도를 보존하면서 감속 적용
                            if not hasattr(m, 'original_speed'):
                                m.original_speed = m.speed
                            m.speed = m.original_speed * 0.7
                    else:
                        # 범위를 벗어난 적은 속도 원상복구
                        if hasattr(m, 'original_speed'):
                            m.speed = m.original_speed

    def draw(self, surf, player, cam):
        if self.is_active:
            # 현재 레벨에 따른 실시간 반지름 계산 (update 로직과 동일)
            draw_radius = self.radius
            if self.level >= 2: draw_radius *= 1.3
            if self.level >= 5: draw_radius *= 1.2
            
            screen_pos = (int(player.pos.x - cam.x), int(player.pos.y - cam.y))
            
            # 시각 효과: 반투명 원형 보호막
            shield_surf = pygame.Surface((draw_radius * 2, draw_radius * 2), pygame.SRCALPHA)
            # 4단계 이상이면 감속 역장을 표현하기 위해 색상을 진하게 변경
            shield_color = (100, 150, 255, 60) if self.level < 4 else (60, 100, 255, 90)
            
            pygame.draw.circle(shield_surf, shield_color, (int(draw_radius), int(draw_radius)), int(draw_radius))
            surf.blit(shield_surf, (screen_pos[0] - draw_radius, screen_pos[1] - draw_radius))
            
            # 테두리 선
            pygame.draw.circle(surf, (150, 200, 255), screen_pos, int(draw_radius), 2 if self.level < 5 else 4)

# =========================
# HealPotionSkill (회복 물약 - HP 회복형(3회 한정))
# =========================
class HealPotionSkill(SkillBase):
    def __init__(self):
        # interval, damage는 의미 없지만 SkillBase 구조 유지용
        super().__init__("회복 물약", interval=0, damage=0)
        self.max_uses = 3          # 최대 3회
        self.heal_amount = 50     # 회복량
        self.pending_heal = False

    def apply_upgrade(self):
        """
        레벨업 = 물약 선택
        선택 즉시 회복
        """
        if self.level < self.max_uses:
            self.level += 1
            self.pending_heal = True

    def update(self, dt, player, monsters, projectiles):
        if self.pending_heal:
            player.hp = min(player.max_hp, player.hp + self.heal_amount)
            self.pending_heal = False

    def is_max(self):
        """레벨업 목록에서 제거용"""
        return self.level >= self.max_uses