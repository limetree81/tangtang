import pygame
import sys
import random
from skill import BaseShotSkill, FireConeSkill, ElectricShockSkill, ShieldSkill

# 만약 스킬 클래스들이 별도의 skill.py에 있다면 아래 주석을 해제하고 import 하세요.
# from skill import * # =========================
# 테스트 환경 설정
# =========================
SCREEN_W, SCREEN_H = 1100, 650
MAP_W, MAP_H = 2000, 2000 # 넓은 맵
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
        # 스킬 클래스에서 사용하는 screen_pos (화면 중앙 고정 가정)
        self.screen_pos = pygame.Vector2(SCREEN_W // 2, SCREEN_H // 2)
        self.speed = 300

class MockMonster:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.hp = 100
        self.max_hp = 100
        self.radius = 20

    def update(self, player_pos, dt):
        # 플레이어를 천천히 추적 (조준 테스트용)
        direction = (player_pos - self.pos)
        if direction.length() > 0:
            self.pos += direction.normalize() * 80 * dt

    def draw(self, surf, cam):
        screen_pos = self.pos - cam
        # 몸체
        pygame.draw.circle(surf, RED, (int(screen_pos.x), int(screen_pos.y)), self.radius)
        # 체력바
        health_width = 40 * (self.hp / self.max_hp)
        pygame.draw.rect(surf, (50, 0, 0), (screen_pos.x - 20, screen_pos.y - 30, 40, 5))
        pygame.draw.rect(surf, GREEN, (screen_pos.x - 20, screen_pos.y - 30, health_width, 5))

# =========================
# 메인 테스트 루프
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Skill System Integration Test (Press 1-4 to Level Up)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("malgungothic", 18)

    # 객체 초기화
    player = MockPlayer()
    cam = pygame.Vector2(player.pos.x - SCREEN_W // 2, player.pos.y - SCREEN_H // 2)
    
    # 스킬 인스턴스 생성
    skills = [BaseShotSkill(), FireConeSkill(), ElectricShockSkill(), ShieldSkill()]
    projectiles = []
    
    # 몬스터 생성 (플레이어 주변)
    monsters = [MockMonster(player.pos + pygame.Vector2(random.uniform(-400, 400), 
                                                        random.uniform(-400, 400))) for _ in range(12)]

    while True:
        dt = clock.tick(FPS) / 1000.0
        screen.fill(BLACK)

        # 1. 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                # 숫자키 1~4로 스킬 레벨업 테스트
                if pygame.K_1 <= event.key <= pygame.K_4:
                    idx = event.key - pygame.K_1
                    skills[idx].apply_upgrade()
                    print(f"{skills[idx].name} 레벨업! 현재 레벨: {skills[idx].level}")

        # 2. 플레이어 이동 및 카메라 업데이트
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: move.y -= 1
        if keys[pygame.K_s]: move.y += 1
        if keys[pygame.K_a]: move.x -= 1
        if keys[pygame.K_d]: move.x += 1
        if move.length_squared() > 0:
            player.pos += move.normalize() * player.speed * dt
        
        # 카메라는 플레이어를 중앙에 유지
        cam.x = player.pos.x - SCREEN_W // 2
        cam.y = player.pos.y - SCREEN_H // 2

        # 3. 스킬 및 투사체 업데이트
        for s in skills:
            s.update(dt, player, monsters, projectiles)

        for p in projectiles[:]:
            p.update(dt)
            if p.life <= 0:
                projectiles.remove(p)
                continue
            
            # 투사체 vs 몬스터 충돌 (데미지가 있는 투사체만)
            if p.damage > 0:
                for m in monsters:
                    if (m.pos - p.pos).length() < m.radius + 5:
                        m.hp -= p.damage
                        if p in projectiles: projectiles.remove(p)
                        break

        # 4. 몬스터 업데이트 (사망 처리 포함)
        for m in monsters[:]:
            m.update(player.pos, dt)
            if m.hp <= 0:
                monsters.remove(m)
                # 새로운 몬스터 보충
                new_pos = player.pos + pygame.Vector2(random.uniform(-600, 600), random.uniform(-600, 600))
                monsters.append(MockMonster(new_pos))

        # 5. 그리기 (Render)
        # 배경 격자 (카메라 이동 확인용)
        grid_size = 100
        for x in range(0, MAP_W, grid_size):
            pygame.draw.line(screen, (30, 30, 40), (x - cam.x, 0), (x - cam.x, SCREEN_H))
        for y in range(0, MAP_H, grid_size):
            pygame.draw.line(screen, (30, 30, 40), (0, y - cam.y), (SCREEN_W, y - cam.y))

        # 몬스터 & 투사체
        for m in monsters: m.draw(screen, cam)
        for p in projectiles: p.draw(screen, cam)

        # 특수 시각 효과 (일렉트릭 쇼크, 보호막)
        skills[2].draw(screen, player, cam)
        skills[3].draw(screen, player, cam)

        # 플레이어 본체
        pygame.draw.circle(screen, WHITE, (SCREEN_W // 2, SCREEN_H // 2), 20)

        # UI 정보
        y_offset = 20
        controls = ["WASD: 이동", "Mouse: 조준", "1-4: 스킬 레벨업"]
        for ctrl in controls:
            img = font.render(ctrl, True, (150, 150, 150))
            screen.blit(img, (SCREEN_W - 150, y_offset))
            y_offset += 25

        y_offset = 20
        for s in skills:
            color = BLUE if (hasattr(s, 'is_active') and s.is_active) else WHITE
            text = f"{s.name} LV.{s.level} | Timer: {s.timer:.1f}s"
            img = font.render(text, True, color)
            screen.blit(img, (20, y_offset))
            y_offset += 30

        pygame.display.flip()

if __name__ == "__main__":
    main()