import pygame
import sys
import random
# skill.py 파일에서 클래스들을 가져옵니다.
from skill import Projectile, BaseShotSkill, FireConeSkill, ElectricShockSkill, ShieldSkill

# =========================
# 테스트 환경 설정
# =========================
SCREEN_W, SCREEN_H = 1100, 650
MAP_W, MAP_H = 2000, 2000 
FPS = 60

# 색상 정의
BLACK = (15, 15, 20)
WHITE = (240, 240, 240)
RED = (255, 60, 60)
BLUE = (0, 191, 255)
GREEN = (50, 255, 100)

# =========================
# 테스트용 가상 클래스 (Mock Objects)
# =========================
class MockPlayer:
    def __init__(self):
        self.pos = pygame.Vector2(MAP_W // 2, MAP_H // 2)
        self.screen_pos = pygame.Vector2(SCREEN_W // 2, SCREEN_H // 2)
        self.speed = 300

class MockMonster:
    def __init__(self, pos, kind='normal'):
        self.pos = pygame.Vector2(pos)
        self.hp = 100
        self.max_hp = 100
        self.radius = 25 if kind == 'finalboss' else 20
        self.kind = kind # ElectricShockSkill의 보스 우선순위 로직 테스트용
        # [수정] ShieldSkill의 슬로우 효과를 위해 speed 속성 추가
        self.speed = 75 

    def update(self, player_pos, dt):
        direction = (player_pos - self.pos)
        if direction.length() > 50:
            # [수정] 고정값이 아닌 self.speed를 사용하여 감속 효과를 반영
            self.pos += direction.normalize() * self.speed * dt

    def draw(self, surf, cam):
        screen_pos = self.pos - cam
        color = (255, 200, 0) if self.kind == 'finalboss' else RED
        pygame.draw.circle(surf, color, (int(screen_pos.x), int(screen_pos.y)), self.radius)
        
        health_width = 40 * (max(0, self.hp) / self.max_hp)
        pygame.draw.rect(surf, (50, 0, 0), (screen_pos.x - 20, screen_pos.y - 35, 40, 5))
        pygame.draw.rect(surf, GREEN, (screen_pos.x - 20, screen_pos.y - 35, health_width, 5))

# =========================
# 메인 테스트 루프
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Magic Survivor - Final Skill System Test")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("malgungothic", 18)

    player = MockPlayer()
    cam = pygame.Vector2(player.pos.x - SCREEN_W // 2, player.pos.y - SCREEN_H // 2)
    
    # 스킬 인스턴스 생성
    skills = [BaseShotSkill(), FireConeSkill(), ElectricShockSkill(), ShieldSkill()]
    projectiles = []
    
    # 몬스터 생성 (일반 10마리 + 보스 1마리)
    monsters = [MockMonster(player.pos + pygame.Vector2(random.uniform(-500, 500), 
                                                        random.uniform(-500, 500))) for _ in range(10)]
    monsters.append(MockMonster(player.pos + pygame.Vector2(300, 300), kind='finalboss'))

    while True:
        dt = clock.tick(FPS) / 1000.0
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                # 1~4번 키로 레벨업 테스트
                if pygame.K_1 <= event.key <= pygame.K_4:
                    idx = event.key - pygame.K_1
                    skills[idx].apply_upgrade()

        # 플레이어 이동
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: move.y -= 1
        if keys[pygame.K_s]: move.y += 1
        if keys[pygame.K_a]: move.x -= 1
        if keys[pygame.K_d]: move.x += 1
        if move.length_squared() > 0:
            player.pos += move.normalize() * player.speed * dt
        
        # 카메라 업데이트
        cam.x = player.pos.x - SCREEN_W // 2
        cam.y = player.pos.y - SCREEN_H // 2

        # 3. 스킬 및 투사체 업데이트
        for s in skills:
            s.update(dt, player, monsters, projectiles)

        for p in projectiles[:]:
            p.update(dt)
            if p.life <= 0:
                projectiles.remove(p); continue
            
            # 투사체 충돌 판정 (파이어볼은 폭발 판정 등이 추가될 수 있음)
            if p.damage > 0:
                for m in monsters:
                    if (m.pos - p.pos).length() < m.radius + 5:
                        m.hp -= p.damage
                        if p in projectiles: projectiles.remove(p)
                        break

        # 4. 몬스터 업데이트 (사망 및 리스폰)
        for m in monsters[:]:
            m.update(player.pos, dt)
            if m.hp <= 0:
                monsters.remove(m)
                new_pos = player.pos + pygame.Vector2(random.uniform(-700, 700), random.uniform(-700, 700))
                monsters.append(MockMonster(new_pos))

        # 5. 그리기 (Render)
        # 배경 격자
        grid_size = 100
        for x in range(int(cam.x // grid_size) * grid_size, int((cam.x + SCREEN_W) // grid_size + 1) * grid_size, grid_size):
            pygame.draw.line(screen, (30, 30, 40), (x - cam.x, 0), (x - cam.x, SCREEN_H))
        for y in range(int(cam.y // grid_size) * grid_size, int((cam.y + SCREEN_H) // grid_size + 1) * grid_size, grid_size):
            pygame.draw.line(screen, (30, 30, 40), (0, y - cam.y), (SCREEN_W, y - cam.y))

        # 몬스터 & 투사체 그리기
        for m in monsters: m.draw(screen, cam)
        for p in projectiles: p.draw(screen, cam)

        # 스킬별 특수 시각 효과
        skills[2].draw(screen, cam)         # 일렉트릭 쇼크 (번개)
        skills[3].draw(screen, player, cam) # 프로텍트 쉴드

        # 플레이어 표시
        pygame.draw.circle(screen, WHITE, (int(player.pos.x - cam.x), int(player.pos.y - cam.y)), 20)

        # UI 정보 표시
        y_offset = 20
        for s in skills:
            status = "ACTIVE" if (hasattr(s, 'is_active') and s.is_active) else "CD"
            color = BLUE if status == "ACTIVE" else WHITE
            text = f"{s.name} LV.{s.level} [{status}]"
            img = font.render(text, True, color)
            screen.blit(img, (20, y_offset))
            y_offset += 30

        pygame.display.flip()

if __name__ == "__main__":
    main()