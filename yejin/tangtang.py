import pygame
import math
import random
import sys

# 1. 초기화 및 화면 설정
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("원시인 서바이벌: 도형 버전 (보스 레이드)")
clock = pygame.time.Clock()

# 폰트 설정
try:
    font = pygame.font.SysFont("malgungothic", 30)
    small_font = pygame.font.SysFont("malgungothic", 20)
    damage_font = pygame.font.SysFont("malgungothic", 25, bold=True)
    title_font = pygame.font.SysFont("malgungothic", 60, bold=True)
except:
    font = pygame.font.SysFont("arial", 30)
    small_font = pygame.font.SysFont("arial", 20)
    damage_font = pygame.font.SysFont("arial", 25, bold=True)
    title_font = pygame.font.SysFont("arial", 60, bold=True)

# 2. 색상 정의
BLACK, WHITE, YELLOW = (0, 0, 0), (255, 255, 255), (255, 255, 0)
BLUE, RED, GRAY = (0, 150, 255), (255, 50, 50), (50, 50, 50)
BROWN, GOLD, GREEN = (139, 69, 19), (255, 215, 0), (0, 255, 0)
PURPLE = (160, 32, 240)
BG_COLOR = (34, 139, 34) # 숲 느낌의 초록색 배경

# 3. 클래스 정의
class Player:
    def __init__(self):
        self.pos = [WIDTH // 2, HEIGHT // 2]
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.speed = 4
        self.max_hp = 100
        self.hp = 100
        self.direction = "front"
        self.facing_right = True
        self.weapons = {"돌 도끼": 1, "회전 뼈다귀": 0}
        self.invinc_timer = 0

class Enemy:
    def __init__(self, x, y, speed, hp, size, color, is_boss=False):
        self.pos = [x, y]
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.size = size
        self.color = color
        self.is_boss = is_boss

class Axe:
    def __init__(self, pos, target_pos):
        self.pos = list(pos)
        dx, dy = target_pos[0]-pos[0], target_pos[1]-pos[1]
        dist = math.hypot(dx, dy)
        self.dir = [dx/dist, dy/dist] if dist != 0 else [0, 0]
        self.angle = 0
        self.gravity = -8
        self.damage = 15

    def update(self):
        self.pos[0] += self.dir[0] * 7
        self.pos[1] += self.dir[1] * 7 + self.gravity
        self.gravity += 0.4
        self.angle += 15

class DamageText:
    def __init__(self, x, y, damage):
        self.pos = [x, y]
        self.text = str(damage)
        self.timer = 500 

# 4. 게임 변수 초기화
player = Player()
enemies, axes, gems, damage_texts = [], [], [], []
bone_angle = 0
spawn_timer = axe_timer = 0
game_state = "PLAYING"
options = []
boss_spawned_levels = set()

def spawn_monster(diff):
    side = random.choice(['L', 'R', 'T', 'B'])
    if side == 'L': rx, ry = -50, random.randint(0, HEIGHT)
    elif side == 'R': rx, ry = WIDTH+50, random.randint(0, HEIGHT)
    elif side == 'T': rx, ry = random.randint(0, WIDTH), -50
    else: rx, ry = random.randint(0, WIDTH), HEIGHT+50
    enemies.append(Enemy(rx, ry, 2.0 + (diff*0.1), 20 + (diff*5), 18, RED))

def spawn_boss(level):
    rx, ry = random.randint(100, WIDTH-100), -100
    boss_hp = 500 + (level * 100)
    enemies.append(Enemy(rx, ry, 1.2, boss_hp, 60, PURPLE, is_boss=True))

# 5. 메인 루프
running = True
while running:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        
        if game_state == "LEVEL_UP" and event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_1, pygame.K_2]:
                choice = ["돌 도끼", "회전 뼈다귀"][event.key - pygame.K_1]
                player.weapons[choice] += 1
                game_state = "PLAYING"
        
        if game_state == "GAME_OVER" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                player = Player(); enemies, axes, gems, damage_texts = [], [], [], []; boss_spawned_levels = set(); game_state = "PLAYING"

    if game_state == "PLAYING":
        if player.invinc_timer > 0: player.invinc_timer -= dt
        
        # 보스 스폰 체크 (5레벨 마다)
        if player.level % 5 == 0 and player.level not in boss_spawned_levels:
            spawn_boss(player.level)
            boss_spawned_levels.add(player.level)

        # 플레이어 이동
        keys = pygame.key.get_pressed()
        moving_side = False
        if keys[pygame.K_a]: 
            player.pos[0] -= player.speed
            player.facing_right = False
            moving_side = True
        elif keys[pygame.K_d]: 
            player.pos[0] += player.speed
            player.facing_right = True
            moving_side = True
        if keys[pygame.K_w]: player.pos[1] -= player.speed
        elif keys[pygame.K_s]: player.pos[1] += player.speed

        # 스폰 타이머
        spawn_timer += dt
        if spawn_timer > 1000:
            spawn_monster(player.level // 2); spawn_timer = 0
            
        axe_timer += dt
        if axe_timer > max(200, 800 - (player.weapons["돌 도끼"] * 100)) and enemies:
            target = min(enemies, key=lambda e: math.hypot(e.pos[0]-player.pos[0], e.pos[1]-player.pos[1]))
            axes.append(Axe(player.pos, target.pos)); axe_timer = 0

        bone_angle += 0.05
        for a in axes[:]:
            a.update()
            if a.pos[1] > HEIGHT + 100: axes.remove(a)
            
        for d in damage_texts[:]:
            d.pos[1] -= 1; d.timer -= dt
            if d.timer <= 0: damage_texts.remove(d)

        for e in enemies[:]:
            dist = math.hypot(player.pos[0]-e.pos[0], player.pos[1]-e.pos[1])
            if dist != 0:
                e.pos[0] += (player.pos[0]-e.pos[0])/dist*e.speed
                e.pos[1] += (player.pos[1]-e.pos[1])/dist*e.speed
            
            # 피격 판정
            if dist < e.size + 15 and player.invinc_timer <= 0:
                player.hp -= 20 if e.is_boss else 10
                player.invinc_timer = 600
                if player.hp <= 0: game_state = "GAME_OVER"

            # 무기 충돌 (도끼)
            for a in axes[:]:
                if math.hypot(e.pos[0]-a.pos[0], e.pos[1]-a.pos[1]) < e.size + 15:
                    e.hp -= a.damage; damage_texts.append(DamageText(e.pos[0], e.pos[1], a.damage))
                    if a in axes: axes.remove(a)
            
            # 무기 충돌 (뼈다귀)
            if player.weapons["회전 뼈다귀"] > 0:
                for i in range(player.weapons["회전 뼈다귀"]):
                    ang = bone_angle + (i * (math.pi*2/player.weapons["회전 뼈다귀"]))
                    bx, by = player.pos[0]+math.cos(ang)*110, player.pos[1]+math.sin(ang)*110
                    if math.hypot(e.pos[0]-bx, e.pos[1]-by) < e.size + 20:
                        e.hp -= 1; damage_texts.append(DamageText(e.pos[0], e.pos[1], 1))

            if e.hp <= 0:
                count = 5 if e.is_boss else 1
                for _ in range(count): gems.append(pygame.Vector2(e.pos[0]+random.randint(-20,20), e.pos[1]+random.randint(-20,20)))
                enemies.remove(e)

        # 보석 및 레벨업
        for g in gems[:]:
            dist = math.hypot(player.pos[0]-g.x, player.pos[1]-g.y)
            if dist < 150:
                g.x += (player.pos[0]-g.x)/dist*8; g.y += (player.pos[1]-g.y)/dist*8
            if dist < 25:
                player.xp += 35; gems.remove(g)
        
        if player.xp >= player.xp_to_next:
            player.level += 1; player.xp = 0; player.xp_to_next += 50
            options = ["돌 도끼", "회전 뼈다귀"]; game_state = "LEVEL_UP"

    # --- 6. 그리기 ---
    screen.fill(BG_COLOR)
    
    # 보석 그리기
    for g in gems: pygame.draw.circle(screen, BLUE, (int(g.x), int(g.y)), 6)
    
    # 적 그리기
    for e in enemies:
        pygame.draw.circle(screen, e.color, (int(e.pos[0]), int(e.pos[1])), e.size)
        if e.is_boss:
            pygame.draw.rect(screen, BLACK, (WIDTH//2-150, 40, 300, 20))
            pygame.draw.rect(screen, PURPLE, (WIDTH//2-150, 40, (e.hp/e.max_hp)*300, 20))
            screen.blit(small_font.render("BOSS 등장!", True, WHITE), (WIDTH//2-40, 15))
        else:
            pygame.draw.rect(screen, BLACK, (e.pos[0]-15, e.pos[1]-e.size-10, 30, 5))
            pygame.draw.rect(screen, GREEN, (e.pos[0]-15, e.pos[1]-e.size-10, (e.hp/e.max_hp)*30, 5))

    # 도끼 그리기
    for a in axes:
        s = pygame.Surface((25, 8), pygame.SRCALPHA); s.fill(BROWN)
        screen.blit(pygame.transform.rotate(s, a.angle), (a.pos[0]-12, a.pos[1]-4))

    # 뼈다귀 그리기
    if player.weapons["회전 뼈다귀"] > 0:
        for i in range(player.weapons["회전 뼈다귀"]):
            ang = bone_angle + (i * (math.pi*2/player.weapons["회전 뼈다귀"]))
            pygame.draw.circle(screen, WHITE, (int(player.pos[0]+math.cos(ang)*110), int(player.pos[1]+math.sin(ang)*110)), 12)

    # --- 플레이어 그리기 (수정된 로직) ---
    show_player = True # 기본적으로는 보임
    
    if player.invinc_timer > 0:
        # 무적 시간 중일 때는 100ms 단위로 보였다 안보였다 함 (깜빡임)
        if (player.invinc_timer // 100) % 2 == 0:
            show_player = False
    
    if show_player:
        # 몸체 그리기 (도형 버전)
        pygame.draw.circle(screen, GREEN, (int(player.pos[0]), int(player.pos[1])), 20)
        # 눈 (방향 표시)
        eye_x = 8 if player.facing_right else -8
        pygame.draw.circle(screen, WHITE, (int(player.pos[0] + eye_x), int(player.pos[1] - 5)), 4)
    # 데미지 텍스트
    for d in damage_texts:
        screen.blit(damage_font.render(d.text, True, YELLOW), d.pos)

    # UI (XP, HP)
    pygame.draw.rect(screen, (30,30,30), (50, 10, 700, 15))
    pygame.draw.rect(screen, BLUE, (50, 10, (player.xp/player.xp_to_next)*700, 15))
    pygame.draw.rect(screen, RED, (WIDTH//2-100, HEIGHT-30, 200, 15))
    pygame.draw.rect(screen, GREEN, (WIDTH//2-100, HEIGHT-30, (player.hp/player.max_hp)*200, 15))
    screen.blit(small_font.render(f"LV.{player.level} HP:{player.hp}", True, WHITE), (60, 30))

    if game_state == "LEVEL_UP":
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((0,0,0,180)); screen.blit(s, (0,0))
        screen.blit(title_font.render("레벨업! 무기 강화", True, GOLD), (WIDTH//2-200, 150))
        for i, o in enumerate(options):
            pygame.draw.rect(screen, BROWN, (WIDTH//2-150, 280+i*100, 300, 60))
            screen.blit(font.render(f"{i+1}. {o}", True, WHITE), (WIDTH//2-100, 290+i*100))

    if game_state == "GAME_OVER":
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((100,0,0,150)); screen.blit(s, (0,0))
        screen.blit(title_font.render("부족의 전사여, 쓰러졌는가!", True, WHITE), (WIDTH//2-300, HEIGHT//2-50))
        screen.blit(font.render("R키를 눌러 다시 도전하라", True, WHITE), (WIDTH//2-160, HEIGHT//2+50))

    pygame.display.flip()

pygame.quit()