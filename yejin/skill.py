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

# # =========================
# # 1. BaseShotSkill (마법 총)
# # =========================
# class BaseShotSkill(SkillBase):
#     def __init__(self):
#         super().__init__("마법 총", 1.0, 10)

#     def update(self, dt, player, monsters, projectiles):
#         super().update(dt, player, monsters, projectiles)
#         if self.timer >= self.interval:
#             self.timer = 0
#             mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
#             player_screen = getattr(player, 'screen_pos', pygame.Vector2(550, 325))
#             direction = (mouse_pos - player_screen)
#             if direction.length_squared() > 0:
#                 target_dir = direction.normalize()
#                 for i in range(self.level):
#                     angle = (i - (self.level-1)/2) * 10
#                     vel = target_dir.rotate(angle) * 500
#                     projectiles.append(Projectile(player.pos, vel, self.base_damage))

# =========================
# 1. BaseShotSkill (마법 총) - 개수 및 발사 횟수 동시 강화
# =========================
class BaseShotSkill(SkillBase):
    def __init__(self):
        # 기본 데미지 10, 초기 발사 간격 1.0초
        super().__init__("마법 총", 1.0, 10)

    def update(self, dt, player, monsters, projectiles):
        super().update(dt, player, monsters, projectiles)
        
        # [개선] 레벨업에 따른 발사 속도(간격) 감소 
        # 레벨 1: 1.0초, 레벨 2: 0.85초, 레벨 3: 0.7초 ... (최소 0.2초)
        current_interval = max(0.2, self.interval - (self.level - 1) * 0.15)
        
        if self.timer >= current_interval:
            self.timer = 0
            # 마우스 방향으로 조준
            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
            player_screen = getattr(player, 'screen_pos', pygame.Vector2(550, 325))
            direction = (mouse_pos - player_screen)
            
            if direction.length_squared() > 0:
                target_dir = direction.normalize()
                
                # [개선] 레벨업에 따른 총알 개수 증가 (1레벨당 1개씩 추가)
                # 총알 1개당 데미지는 10 고정
                for i in range(self.level):
                    # 총알들이 부채꼴 모양으로 퍼지도록 각도 계산
                    angle = (i - (self.level - 1) / 2) * 10
                    vel = target_dir.rotate(angle) * 500
                    projectiles.append(Projectile(player.pos, vel, self.base_damage))


# =========================
# 2. FireConeSkill (파이어 볼) - 일직선 타겟팅 발사
# =========================
class FireConeSkill(SkillBase):
    def __init__(self):
        super().__init__("파이어 볼", 5.0, 10)

    def update(self, dt, player, monsters, projectiles):
        super().update(dt, player, monsters, projectiles)
        if self.timer >= self.interval:
            self.timer = 0
            # 레벨업 시 화염 기둥의 두께(width) 증가
            width = 20 + (self.level - 1) * 20
            damage = 10 + (self.level - 1) * 10
            
            # 가장 가까운 적 방향으로 일직선 조준
            target_angle = random.uniform(0, 360)
            if monsters:
                closest = min(monsters, key=lambda m: (m.pos - player.pos).length_squared())
                dir_to_m = closest.pos - player.pos
                if dir_to_m.length_squared() > 0:
                    # 오차 범위를 최소화하여 일직선 정확도를 높임
                    target_angle = math.degrees(math.atan2(dir_to_m.y, dir_to_m.x))

            # vel 방향으로 '일자'로 길게 뻗어나가도록 설정
            vel = pygame.Vector2(1, 0).rotate(target_angle) * 450
            # size=(두께, 길이) -> 길이를 150으로 늘려 일직선 기둥 느낌 강조
            projectiles.append(Projectile(player.pos, vel, damage, size=(width, 150), color=(255, 60, 0), is_fire=True))

# =========================
# 3. ElectricShockSkill (일렉트릭 쇼크)
# =========================
class ElectricShockSkill(SkillBase):
    def __init__(self):
        super().__init__("일렉트릭 쇼크", 10.0, 10)
        self.duration = 5.0
        self.is_active = False
        self.active_timer = 0.0
        self.visual_timer = 0.0

    def update(self, dt, player, monsters, projectiles):
        if not self.is_active:
            self.timer += dt
            if self.timer >= self.interval:
                self.is_active = True
                self.active_timer = 0
                self.timer = 0
        else:
            self.active_timer += dt
            self.visual_timer += dt
            current_duration = self.duration + (self.level - 1) * 5.0
            radius = 50 + (self.level - 1) * 10

            if self.active_timer >= current_duration:
                self.is_active = False
            else:
                if self.visual_timer >= 0.05:
                    self.visual_timer = 0
                    angle = random.uniform(0, 360)
                    dist = random.uniform(0, radius)
                    offset = pygame.Vector2(dist, 0).rotate(angle)
                    v_pos = player.pos + offset
                    projectiles.append(Projectile(v_pos, pygame.Vector2(0, random.uniform(-30, 30)), 
                                                  0, size=(2, 10), life=0.15, color=(0, 255, 255)))
                for m in monsters:
                    if (m.pos - player.pos).length() <= radius:
                        m.hp -= self.base_damage * dt

    def draw(self, surf, player, cam):
        if self.is_active:
            radius = 50 + (self.level - 1) * 10
            screen_pos = (player.pos.x - cam.x, player.pos.y - cam.y)
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 255, 255, 40), (radius, radius), radius)
            surf.blit(s, (screen_pos[0] - radius, screen_pos[1] - radius))
            pygame.draw.circle(surf, (0, 255, 255, 150), screen_pos, radius, 1)

# # =========================
# # ElectricShockSkill (일렉트릭 쇼크 -> 천둥 배터리)
# # =========================
# class ElectricShockSkill(SkillBase):
#     def __init__(self):
#         # 기본 10초 주기, 데미지 10 고정
#         super().__init__("일렉트릭 쇼크", 10.0, 10)
#         self.duration = 5.0      # 발동 유지 시간
#         self.is_active = False
#         self.active_timer = 0.0
#         self.attack_timer = 0.0  # 번개가 떨어지는 개별 간격 타이머
#         self.chain_count = 0     # 전이(체인) 횟수 (진화 시 사용)

#     def update(self, dt, player, monsters, projectiles):
#         # 1. 발동 타이머 로직
#         if not self.is_active:
#             self.timer += dt
#             if self.timer >= self.interval:
#                 self.is_active = True
#                 self.active_timer = 0
#                 self.timer = 0
#         else:
#             self.active_timer += dt
#             # 레벨업에 따른 유지 시간 증가 (5초 + 레벨당 5초)
#             current_duration = self.duration + (self.level - 1) * 5.0
            
#             # 레벨업에 따른 번개 속도(간격) 조절 (레벨이 높을수록 더 자주 발사)
#             # 기본 0.5초당 1발 -> 레벨당 0.1초씩 감소 (최소 0.1초)
#             strike_interval = max(0.1, 0.5 - (self.level - 1) * 0.1)

#             if self.active_timer >= current_duration:
#                 self.is_active = False
#             else:
#                 self.attack_timer += dt
#                 if self.attack_timer >= strike_interval:
#                     self.attack_timer = 0
#                     self.strike_lightning(player, monsters, projectiles)

#     def strike_lightning(self, player, monsters, projectiles):
#         """가장 가까운 적을 자동 조준하여 번개 투사체 생성"""
#         if not monsters:
#             return

#         # 1. 자동 조준: 가장 가까운 적 포착 (필중)
#         target = min(monsters, key=lambda m: (m.pos - player.pos).length_squared())
        
#         # 2. 번개 투사체 생성 (하늘에서 떨어지는 연출을 위해 적 위치 위쪽에 생성)
#         strike_pos = pygame.Vector2(target.pos.x, target.pos.y - 100)
#         # 속도를 아래로 빠르게 주어 내리꽂는 느낌 부여
#         vel = pygame.Vector2(0, 1000)
        
#         # 번개 투사체 추가
#         projectiles.append(Projectile(
#             strike_pos, vel, self.base_damage, 
#             size=(4, 40), life=0.1, color=(0, 255, 255)
#         ))

#         # 3. 진화 형태 효과: 천둥 배터리 (주변 전이 피해)
#         # 만약 레벨이 5(최대)라면 주변 적에게 추가 전이 피해를 입힘
#         if self.level >= 5:
#             self.chain_reaction(target, monsters)

#     def chain_reaction(self, main_target, monsters):
#         """타격 시 주변 적에게 전이되는 광역 피해 (천둥 배터리 효과)"""
#         chain_range = 150  # 전이 범위
#         max_chains = 3     # 최대 전이 수
#         count = 0
        
#         for m in monsters:
#             if m == main_target: continue
#             if (m.pos - main_target.pos).length() <= chain_range:
#                 m.hp -= self.base_damage * 0.5 # 전이 데미지는 50%
#                 count += 1
#                 if count >= max_chains: break

#     def draw(self, surf, player, cam):
#         # 번개발사기는 투사체가 직접 조준하므로 별도의 범위 가이드는 그리지 않거나,
#         # 활성화 상태임을 알리는 작은 이펙트를 플레이어 주변에 표시할 수 있습니다.
#         if self.is_active:
#             # 플레이어 머리 위에 충전 상태 표시 (하늘색 원)
#             screen_pos = (player.pos.x - cam.x, player.pos.y - cam.y - 40)
#             pygame.draw.circle(surf, (0, 255, 255), screen_pos, 5)


# =========================
# 4. ShieldSkill (프로텍트 쉴드)
# =========================
class ShieldSkill(SkillBase):
    def __init__(self):
        super().__init__("프로텍트 쉴드", 10.0, 10)
        self.base_duration = 5.0
        self.is_active = False
        self.active_timer = 0.0

    def update(self, dt, player, monsters, projectiles):
        if not self.is_active:
            self.timer += dt
            if self.timer >= self.interval:
                self.is_active = True
                self.active_timer = 0
                self.timer = 0
        else:
            self.active_timer += dt
            current_duration = self.base_duration + (self.level - 1) * 5.0
            if self.active_timer >= current_duration:
                self.is_active = False
            else:
                radius = 50 + (self.level - 1) * 10
                for m in monsters:
                    if (m.pos - player.pos).length() <= radius:
                        m.hp -= self.base_damage * dt

    def draw(self, surf, player, cam):
        if self.is_active:
            radius = 50 + (self.level - 1) * 10
            screen_pos = (player.pos.x - cam.x, player.pos.y - cam.y)
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 150, 255, 80), (radius, radius), radius)
            surf.blit(s, (screen_pos[0] - radius, screen_pos[1] - radius))
            pygame.draw.circle(surf, (150, 200, 255), screen_pos, radius, 3)