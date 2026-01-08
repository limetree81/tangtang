import math
import random
import pygame

# =========================
# 1. Projectile (투사체) 클래스
# =========================
class Projectile:
    def __init__(self, pos, vel, damage, life, width, height, color, is_rect=False):
        self.pos = pygame.Vector2(pos)   # 투사체 현재 위치
        self.vel = pygame.Vector2(vel)   # 투사체 이동 속도 및 방향
        self.damage = damage             # 적중 시 입히는 데미지
        self.life = life                 # 투사체 생존 시간 (초 단위)
        self.width = width               # 투사체 가로 크기 (또는 원의 지름)
        self.height = height             # 투사체 세로 크기
        self.color = color               # 투사체 색상
        self.is_rect = is_rect           # 직사각형 판정 여부 (파이어볼 등)

    def update(self, dt):
        # 매 프레임 위치 업데이트 및 생존 시간 감소
        self.pos += self.vel * dt
        self.life -= dt

    def is_alive(self):
        # 생존 시간이 남았는지 확인
        return self.life > 0

    def draw(self, surf, cam):
        # 카메라 좌표를 고려하여 화면(Screen) 상의 위치 계산
        screen_pos = (int(self.pos.x - cam.x), int(self.pos.y - cam.y))
        
        if self.is_rect:
            # 2번 무기(파이어볼) 등 직사각형 모양 그리기 (중앙 기준)
            rect = pygame.Rect(screen_pos[0] - self.width//2, 
                               screen_pos[1] - self.height//2, 
                               self.width, self.height)
            pygame.draw.rect(surf, self.color, rect)
        else:
            # 기본 원형 투사체 그리기
            pygame.draw.circle(surf, self.color, screen_pos, self.width // 2)

# =========================
# 2. Skill Base (부모 클래스)
# =========================
class SkillBase:
    def __init__(self, owner):
        self.owner = owner          # 스킬을 보유한 플레이어 객체
        self.level = 1              # 현재 스킬 레벨
        self.max_level = 5          # 스킬 만렙 제한
        self.cooldown_acc = 0.0     # 쿨타임 계산을 위한 누적 시간

    def level_up(self):
        # 레벨업 로직 (최대 레벨을 넘지 않음)
        if self.level < self.max_level:
            self.level += 1
            return True
        return False

# =========================
# 3. 개별 스킬 구현 (팀원 B의 핵심 파트)
# =========================

class MagicGun(SkillBase):
    """1. 마법 총: 초당 1회 마우스 방향으로 발사"""
    def update(self, dt, monsters, projectiles, mouse_pos):
        self.cooldown_acc += dt
        if self.cooldown_acc >= 1.0:  # 스펙: 초당 1회 발사
            self.cooldown_acc = 0
            self.activate(projectiles, mouse_pos)

    def activate(self, projectiles, mouse_pos):
        # 플레이어 위치에서 마우스 방향으로의 벡터 계산
        direction = (pygame.Vector2(mouse_pos) - self.owner.pos)
        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = pygame.Vector2(1, 0) # 마우스가 플레이어와 겹칠 때 기본 방향

        # 스펙: 레벨 업에 따라 총알 개수 증가 (LV 1=1개, LV 2=2개...)
        count = self.level 
        for i in range(count):
            # 여러 발일 경우 부채꼴 모양으로 각도 분산 (10도씩)
            angle_offset = (i - (count-1)/2) * 10 
            vel = direction.rotate(angle_offset) * 600
            # 데미지 고정 10, 크기 10px
            projectiles.append(Projectile(self.owner.pos, vel, 10, 1.5, 10, 10, (100, 200, 255)))

class FireBall(SkillBase):
    """2. 파이어 볼: 5초당 1회, 레벨에 따라 가로 폭과 데미지 증가"""
    def update(self, dt, monsters, projectiles, mouse_pos):
        self.cooldown_acc += dt
        if self.cooldown_acc >= 5.0: # 스펙: 5초당 1회
            self.cooldown_acc = 0
            self.activate(projectiles, mouse_pos)

    def activate(self, projectiles, mouse_pos):
        direction = (pygame.Vector2(mouse_pos) - self.owner.pos)
        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = pygame.Vector2(1, 0)

        # 스펙: 기본 20px, 레벨당 20px씩 증가
        width = 20 + (self.level - 1) * 20
        # 스펙: 기본 데미지 10, 레벨당 10씩 증가
        damage = 10 + (self.level - 1) * 10
        
        # 가로 width, 세로 100px 직사각형 불기둥 생성
        projectiles.append(Projectile(self.owner.pos, direction * 300, damage, 2.0, width, 100, (255, 80, 0), True))

class ElectricShock(SkillBase):
    """3. 일렉트릭 쇼크: 10초 주기 발동, 5초(기본) 유지, 십자 방향 공격"""
    def __init__(self, owner):
        super().__init__(owner)
        self.active_timer = 0.0     # 전기가 켜져 있는 시간 체크
        self.is_active = False      # 현재 활성화 상태 여부

    def update(self, dt, monsters):
        self.cooldown_acc += dt
        
        # 스펙: 10초 주기로 발동
        if not self.is_active and self.cooldown_acc >= 10.0:
            self.is_active = True
            self.cooldown_acc = 0
            # 스펙: 유지 시간 기본 5초, 레벨업 시 5초씩 증가
            self.active_timer = 5.0 + (self.level - 1) * 5.0

        if self.is_active:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self.is_active = False # 시간이 다 되면 꺼짐
            
            # 스펙: 전기 발사 크기 기본 50px, 레벨당 10px씩 증가
            size = 50 + (self.level - 1) * 10
            
            # 4방향 (Y, -Y, X, -X) 좌표 계산
            directions = [pygame.Vector2(0, size), pygame.Vector2(0, -size), 
                          pygame.Vector2(size, 0), pygame.Vector2(-size, 0)]
            
            for d in directions:
                # 플레이어 기준 해당 방향에 50x50 크기의 판정 박스 생성
                hit_box = pygame.Rect(self.owner.pos.x + d.x - 25, 
                                      self.owner.pos.y + d.y - 25, 50, 50)
                for m in monsters:
                    if m.alive() and hit_box.collidepoint(m.pos):
                        m.hp -= 10 * dt # 스펙: 데미지 10 고정 (지속 데미지)

    def draw(self, surf, cam):
        # 전기 활성화 중에만 시각화
        if self.is_active:
            size = 50 + (self.level - 1) * 10
            screen_pos = self.owner.pos - cam
            for d in [pygame.Vector2(0, size), pygame.Vector2(0, -size), 
                      pygame.Vector2(size, 0), pygame.Vector2(-size, 0)]:
                p = screen_pos + d
                # 십자 위치에 노란색 사각형 그리기
                pygame.draw.rect(surf, (255, 255, 100), (p.x-25, p.y-25, 50, 50), 2)

class ProtectShield(SkillBase):
    """4. 프로텍트 쉴드: 5초 유지(기본), 레벨당 유지시간/크기 증가"""
    def __init__(self, owner):
        super().__init__(owner)
        self.active_timer = 0.0
        self.is_active = False

    def update(self, dt, monsters):
        self.cooldown_acc += dt
        # 10초 간격으로 스킬 재발동 체크
        if not self.is_active and self.cooldown_acc >= 10.0:
            self.is_active = True
            self.cooldown_acc = 0
            # 스펙: 유지 시간 기본 5초, 레벨업 시 5초씩 증가
            self.active_timer = 5.0 + (self.level - 1) * 5.0

        if self.is_active:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self.is_active = False

            # 스펙: 크기 기본 50px, 레벨업 시 10px씩 증가
            radius = 50 + (self.level - 1) * 10
            for m in monsters:
                # 플레이어와 몬스터 사이의 거리가 보호막 반경보다 작으면 데미지
                if m.alive() and (m.pos - self.owner.pos).length() <= radius:
                    m.hp -= 10 * dt # 스펙: 닿을 시 데미지 10

    def draw(self, surf, cam):
        if self.is_active:
            radius = 50 + (self.level - 1) * 10
            screen_pos = (int(self.owner.pos.x - cam.x), int(self.owner.pos.y - cam.y))
            # 반투명 초록색 쉴드 이펙트
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 255, 0, 80), (radius, radius), radius)
            surf.blit(s, (screen_pos[0]-radius, screen_pos[1]-radius))