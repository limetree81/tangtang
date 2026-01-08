import pygame
import math
import random
from abc import ABC, abstractmethod

# integrated_v2.py에서 정의한 엔진 컴포넌트들을 사용한다고 가정합니다.
# (실제 실행 시에는 같은 폴더에 두고 import 하거나 하나로 합쳐서 사용합니다.)
from integrated_v2 import (
    Scene, PlayerBase, MonsterBase, SpellProjectile, 
    Button, SCREEN_W, SCREEN_H, MAP_W, MAP_H, 
    WHITE, BLACK, GRAY, RED, GREEN, BLUE, GOLD, YELLOW
)

# -----------------------------
# 1. UI 전용 컴포넌트 (팀원 코드 유지)
# -----------------------------
class Overlay:
    """일시정지 및 선택 화면을 위한 반투명 오버레이 베이스"""
    def __init__(self, app, title):
        self.app = app
        self.title = title
        self.font_h = app.font_p
        self.font_s = app.font_s
        self.surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    def draw_base(self, surf):
        self.surf.fill((0, 0, 0, 180)) # 어두운 배경
        surf.blit(self.surf, (0, 0))
        
        # 타이틀 렌더링
        title_img = self.font_h.render(self.title, True, GOLD)
        surf.blit(title_img, title_img.get_rect(center=(SCREEN_W//2, 150)))

class SkillChoiceOverlay(Overlay):
    """레벨업 시 마법 선택창"""
    def __init__(self, app):
        super().__init__(app, "새로운 마법 습득")
        self.choices = [
            {"id": "fire", "name": "Incendio", "desc": "가까운 적에게 화염구 발사"},
            {"id": "electric", "name": "Stupefy", "desc": "다수의 적에게 전격 피해"},
            {"id": "shield", "name": "Protego", "desc": "주변 적 접근 방해"}
        ]
        self.btns = []
        for i in range(3):
            self.btns.append(Button((SCREEN_W//2-200, 250 + i*100, 400, 80), 
                             self.choices[i]["name"], (45, 45, 55), (70, 70, 90), app.font_p))

    def draw(self, surf, mouse_pos):
        self.draw_base(surf)
        for i, btn in enumerate(self.btns):
            btn.draw(surf, mouse_pos)
            # 설명 텍스트
            desc = self.app.font_s.render(self.choices[i]["desc"], True, (200, 200, 210))
            surf.blit(desc, (SCREEN_W//2 + 220, 275 + i*100))

# -----------------------------
# 2. Main Game Screen (사용자 로직 제어부)
# -----------------------------
class PlayScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        # 1) 엔진 로직 초기화 (사용자 설계 기반)
        self.player = PlayerBase(MAP_W//2, MAP_H//2, self.app.rm.data["player"], self.app.rm)
        self.camera = pygame.Vector2(0, 0)
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        
        # 2) 게임 상태 변수
        self.timer = 0.0
        self.spawn_acc = 0.0
        self.magic_acc = 0.0
        self.is_paused = False
        self.show_level_up = False
        
        # 3) UI 전용 객체
        self.level_up_ui = SkillChoiceOverlay(app)
        self.pause_btn = Button((SCREEN_W - 120, 20, 100, 40), "PAUSE", (60, 60, 70), (90, 90, 110), app.font_s)

    def handle_event(self, e):
        # 일시정지 버튼 클릭 처리
        if self.pause_btn.is_clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_p):
            self.is_paused = not self.is_paused

        # 레벨업 시 선택 처리
        if self.show_level_up:
            for i, btn in enumerate(self.level_up_ui.btns):
                if btn.is_clicked(e):
                    # 여기에 스킬 강화 로직 연결
                    self.show_level_up = False
                    self.is_paused = False

    def update(self, dt):
        if self.is_paused or self.show_level_up:
            return

        self.timer += dt
        now = pygame.time.get_ticks()

        # 1) 플레이어 이동 로직 (integrated_v2 로직)
        self.player.move(dt)

        # 2) 적 스폰 로직 (integrated_v2 로직)
        self.spawn_acc += dt
        if self.spawn_acc >= 1.5:
            self.spawn_acc = 0
            self.spawn_monster()

        # 3) 마법 자동 시전 로직 (InGame1 UI 로직 접목)
        self.magic_acc += dt * 1000
        if self.magic_acc >= 1200: # 1.2초마다 발사
            self.magic_acc = 0
            self.cast_magic(now)

        # 4) 엔티티 업데이트 (이동 및 물리)
        for enemy in self.enemies:
            enemy.follow(self.player.world_pos, dt)
        
        for proj in self.projectiles:
            if proj.update(dt):
                proj.kill()

        # 5) 충돌 판정 (사용자 엔진 로직)
        self.check_collisions()

        # 6) 카메라 트래킹 (integrated_v2 로직)
        self.camera.x = max(0, min(MAP_W - SCREEN_W, self.player.world_pos.x - SCREEN_W//2))
        self.camera.y = max(0, min(MAP_H - SCREEN_H, self.player.world_pos.y - SCREEN_H//2))

    def spawn_monster(self):
        angle = random.uniform(0, 2*math.pi)
        pos = self.player.world_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * 800
        # 사용자님의 MonsterBase 클래스 생성
        m_data = {"id": "ghost", "kind": "normal", "hp": 40, "speed": 115, "damage": 10, "exp": 25}
        self.enemies.add(MonsterBase(pos.x, pos.y, m_data, self.app.rm))

    def cast_magic(self, now):
        if self.enemies:
            # 가장 가까운 적 타겟팅 (사용자 로직)
            target = min(self.enemies, key=lambda e: e.world_pos.distance_to(self.player.world_pos))
            direction = target.world_pos - self.player.world_pos
            # 팀원의 화려한 이미지 투사체 생성 (ResourceManager 경유)
            self.projectiles.add(SpellProjectile(self.player.world_pos.x, self.player.world_pos.y, 
                                               45, "Fire_Ball.jpg", self.app.rm, direction, 600, 25))

    def check_collisions(self):
        # 투사체 vs 적
        for p in self.projectiles:
            hits = pygame.sprite.spritecollide(p, self.enemies, False)
            if hits:
                for h in hits:
                    h.hp -= p.damage
                    if h.hp <= 0:
                        # 레벨업 발생 체크 (사용자 로직)
                        if self.player.gain_exp(h.exp_reward):
                            self.show_level_up = True
                            self.is_paused = True
                        self.player.kill_count += 1
                        h.kill()
                p.kill()

        # 플레이어 vs 적 접촉 피해
        hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
        if hits:
            if self.player.take_damage(0.4): # 사망 시
                self.app.set_scene(ResultScene(self.app, {"success": False, "kills": self.player.kill_count, "time": int(self.timer)}))

    def draw(self, surf):
        surf.fill(BLACK)
        
        # 1) 배경 맵 렌더링
        for x in range(0, MAP_W + 1, 100):
            pygame.draw.line(surf, (35, 35, 45), (x - self.camera.x, 0), (x - self.camera.x, SCREEN_H))
        for y in range(0, MAP_H + 1, 100):
            pygame.draw.line(surf, (35, 35, 45), (0, y - self.camera.y), (SCREEN_W, y - self.camera.y))

        # 2) 월드 객체 렌더링 (카메라 오프셋 적용)
        for enemy in self.enemies:
            enemy.update_rect(self.camera)
            surf.blit(enemy.image, enemy.rect)
        
        for proj in self.projectiles:
            proj.update_rect(self.camera)
            surf.blit(proj.image, proj.rect)
            
        self.player.update_rect(self.camera)
        surf.blit(self.player.image, self.player.rect)

        # 3) HUD 렌더링 (팀원 UI 디자인)
        self.draw_hud(surf)
        
        # 4) 오버레이 (일시정지/레벨업)
        if self.show_level_up:
            self.level_up_ui.draw(surf, pygame.mouse.get_pos())
        elif self.is_paused:
            self.draw_pause_screen(surf)

    def draw_hud(self, surf):
        # 상단 HUD 패널 디자인
        pygame.draw.rect(surf, (20, 20, 25), (20, 20, 350, 100), border_radius=15)
        # HP 바
        pygame.draw.rect(surf, (45, 45, 50), (40, 40, 300, 20), border_radius=10)
        pygame.draw.rect(surf, RED, (40, 40, 300 * (self.player.hp/self.player.max_hp), 20), border_radius=10)
        # EXP 바
        pygame.draw.rect(surf, (45, 45, 50), (40, 75, 300, 10), border_radius=5)
        pygame.draw.rect(surf, BLUE, (40, 75, 300 * (self.player.exp/self.player.exp_next), 10), border_radius=5)
        
        info = self.app.font_s.render(f"LV {self.player.level} | KILLS {self.player.kill_count} | TIME {int(self.timer)}s", True, WHITE)
        surf.blit(info, (40, 95))
        
        self.pause_btn.draw(surf, pygame.mouse.get_pos())

    def draw_pause_screen(self, surf):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))
        txt = self.app.font_p.render("GAME PAUSED", True, WHITE)
        surf.blit(txt, txt.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))

class ResultScene(Scene):
    """게임 종료 후 결과창"""
    def __init__(self, app, stats):
        super().__init__(app)
        self.stats = stats
        self.btn_main = Button((SCREEN_W//2-100, 450, 200, 60), "메인으로", (50, 50, 60), (80, 80, 100), app.font_s)

    def handle_event(self, e):
        if self.btn_main.is_clicked(e):
            # integrated_v2.py의 App.set_scene을 통해 시작화면으로 복귀
            from integrated_v2 import StartScene
            self.app.set_scene(StartScene(self.app))

    def update(self, dt): pass

    def draw(self, surf):
        surf.fill((10, 10, 15))
        title = "MISSION COMPLETE" if self.stats["success"] else "MISSION FAILED"
        color = GREEN if self.stats["success"] else RED
        
        title_surf = self.app.font_h1.render(title, True, color)
        surf.blit(title_surf, title_surf.get_rect(center=(SCREEN_W//2, 200)))
        
        res_txt = self.app.font_p.render(f"Kills: {self.stats['kills']} | Time: {self.stats['time']}s", True, WHITE)
        surf.blit(res_txt, res_txt.get_rect(center=(SCREEN_W//2, 320)))
        
        self.btn_main.draw(surf, pygame.mouse.get_pos())