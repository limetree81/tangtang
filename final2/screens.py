import pygame
import random
import math
import sys
import os
from config import (WIDTH, HEIGHT, BLACK, WHITE, BLUE, RED, GREEN, 
                    MAX_SKILL_LEVEL, BGM_START, BGM_GAME, BGM_CLEAR)
from entities import Player, Enemy
# skill.py의 스킬 시스템 임포트
from skill import BaseShotSkill, FireConeSkill, ElectricShockSkill, ShieldSkill

# 외부 파일에서 로직 컨트롤러와 웨이브 매니저를 가져옵니다.
from game_controller import WaveManager, GameController

# -----------------------------
# 1. UI Helpers & Constants
# -----------------------------
GRAY = (90, 90, 100)
FONT_H1_SIZE = 64
FONT_H2_SIZE = 26
FONT_NORMAL_SIZE = 22
FONT_SMALL_SIZE = 16

def draw_rounded_rect(surf, rect, color, radius=16, width=0):
    """둥근 모서리 사각형 그리기"""
    if isinstance(rect, tuple): rect = pygame.Rect(rect)
    pygame.draw.rect(surf, color, rect, border_radius=radius, width=width)

def draw_checkbox(surf, rect, checked=False):
    """체크박스 그리기"""
    pygame.draw.rect(surf, (28, 28, 34), rect, border_radius=5)
    pygame.draw.rect(surf, (170, 170, 185), rect, 2, border_radius=5)
    if checked:
        p1 = (rect.x + 3, rect.y + rect.h // 2)
        p2 = (rect.x + rect.w // 2 - 1, rect.y + rect.h - 4)
        p3 = (rect.x + rect.w - 3, rect.y + 4)
        pygame.draw.lines(surf, (120, 240, 160), False, [p1, p2, p3], 3)

def draw_glass_panel(surf, rect, radius=22, fill_rgba=(30, 30, 36, 145), border_rgba=(230, 230, 235, 255), border_w=2):
    """반투명 글래스 패널 효과"""
    if isinstance(rect, tuple): rect = pygame.Rect(rect)
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, fill_rgba, panel.get_rect(), border_radius=radius)
    surf.blit(panel, (rect.x, rect.y))
    pygame.draw.rect(surf, border_rgba, rect, border_w, border_radius=radius)

def draw_divider(surf, x1, y, x2, alpha=120, thickness=2):
    """구분선 그리기"""
    w = abs(x2 - x1)
    if w <= 0: return
    line = pygame.Surface((w, thickness), pygame.SRCALPHA)
    pygame.draw.rect(line, (230, 230, 235, alpha), (0, 0, w, thickness), border_radius=thickness // 2)
    surf.blit(line, (min(x1, x2), y))

# ✅ [추가] 체력 회복 스킬 클래스
class HealSkill:
    def __init__(self):
        self.name = "체력 회복 (50%)"
        self.level = 0
        self.max_level = MAX_SKILL_LEVEL # 최대 사용 횟수 제한 (예: 5회)
        self.player = None  # GameScreen에서 설정됨

    def apply_upgrade(self):
        self.level += 1
        if self.player:
            # 최대 체력의 50% 회복
            heal_amount = self.player.max_hp * 0.5
            self.player.hp = min(self.player.max_hp, self.player.hp + heal_amount)

    def update(self, dt, player, enemies, projectiles):
        pass  # 즉시 발동형이라 업데이트 로직 없음

class Button:
    def __init__(self, rect, text, color=GRAY, hover_color=BLUE, text_color=WHITE, radius=16, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.radius = radius
        self.font = font if font else pygame.font.SysFont("malgungothic", 26, bold=True)

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        c = self.hover_color if hover else self.color
        draw_rounded_rect(surf, self.rect, c, radius=self.radius)
        draw_rounded_rect(surf, self.rect, (255, 255, 255), radius=self.radius, width=2)
        label = self.font.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class PlayerCard:
    def __init__(self, rect, player_data, image_surface):
        self.rect = pygame.Rect(rect)
        self.data = player_data
        self.image = image_surface
        self.selected = False
        self.img_rect = pygame.Rect(self.rect.x + 16, self.rect.y + 16, self.rect.w - 32, 210)
        self.font_h2 = pygame.font.SysFont("malgungothic", 26, bold=True)
        self.font_small = pygame.font.SysFont("malgungothic", 16)

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        base_col = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base_col, radius=18)

        if self.selected:
            glow_rect = self.rect.inflate(8, 8)
            draw_rounded_rect(surf, glow_rect, (60, 160, 255), radius=22, width=7)
            draw_rounded_rect(surf, self.rect, BLUE, radius=18, width=6)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=18, width=2)

        draw_rounded_rect(surf, self.img_rect, (22, 22, 26), radius=14)
        if self.image:
            # 이미지 비율 유지하면서 중앙 정렬
            img_rect = self.image.get_rect(center=self.img_rect.center)
            surf.blit(self.image, img_rect)

        text_x = self.rect.x + 18
        text_y = self.img_rect.bottom + 16
        name = self.font_h2.render(self.data["name"], True, WHITE)
        surf.blit(name, (text_x, text_y))

        stats_y = text_y + 58
        stats_gap = 24
        # 데이터 표시 (HP, Speed, Dmg)
        stats = [
            f"HP: {self.data['HP']}", 
            f"SPEED: {self.data['VEL']}", 
            f"DMG: x{self.data['DMG']}"
        ]
        for i, txt in enumerate(stats):
            surf.blit(self.font_small.render(txt, True, (210, 210, 220)), (text_x, stats_y + i * stats_gap))

class StageCard:
    def __init__(self, rect, key, title, subtitle):
        self.rect = pygame.Rect(rect)
        self.key = key
        self.title = title
        self.subtitle = subtitle
        self.selected = False
        self.font = pygame.font.SysFont("malgungothic", 20)
        self.font_small = pygame.font.SysFont("malgungothic", 16)

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        base = (42, 42, 50) if not hover else (55, 55, 66)
        draw_rounded_rect(surf, self.rect, base, radius=16)

        if self.selected:
            glow = self.rect.inflate(6, 6)
            draw_rounded_rect(surf, glow, (60, 160, 255), radius=20, width=5)
            draw_rounded_rect(surf, self.rect, (70, 160, 255), radius=16, width=4)
        else:
            draw_rounded_rect(surf, self.rect, (130, 130, 150), radius=16, width=2)

        cb_rect = pygame.Rect(self.rect.right - 32, self.rect.y + 16, 18, 18)
        draw_checkbox(surf, cb_rect, checked=self.selected)

        surf.blit(self.font.render(self.title, True, WHITE), (self.rect.x + 18, self.rect.y + 14))
        surf.blit(self.font_small.render(self.subtitle, True, (225, 225, 235)), (self.rect.x + 18, self.rect.y + 46))

# -----------------------------
# 2. Overlay Screens
# -----------------------------
class PauseOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        self.font_h = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.btn_resume = Button(
            (WIDTH // 2 - 200, HEIGHT // 2 + 40, 400, 70),
            "계속하기 (P)", BLUE, (95, 185, 255),
            font=pygame.font.SysFont("malgungothic", 28)
        )

    def handle_event(self, event):
        if not self.active: return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
            self._resume()
        if self.btn_resume.clicked(event):
            self._resume()

    def _resume(self):
        self.active = False
        self.gs.paused = False
        self.gs.audio.unpause()

    def draw(self, surf):
        if not self.active: return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        title = self.font_h.render("PAUSED", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))

        tip = self.font.render("게임이 일시정지되었습니다. P 또는 버튼으로 재개할 수 있습니다.", True, (220, 220, 230))
        surf.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))

        self.btn_resume.draw(surf, pygame.mouse.get_pos())

class SkillChoiceOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        # 레벨이 마스터(5) 미만인 스킬들만 후보로 선정
        self.options = [s for s in gs.skills if s.level < MAX_SKILL_LEVEL]
        random.shuffle(self.options)
        self.options = self.options[:3]
        
        self.font_h = pygame.font.SysFont("malgungothic", 44, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.name_font = pygame.font.SysFont("malgungothic", 28)
        
        w, h, gap = 320, 160, 40
        x0 = (WIDTH - (w*3 + gap*2)) // 2
        y0 = HEIGHT // 2 - 70
        self.btn_rects = [pygame.Rect(x0 + i*(w+gap), y0, w, h) for i in range(3)]

    def handle_event(self, event):
        if not self.active: return
        idx = -1
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(event.pos): idx = i
        
        if 0 <= idx < len(self.options):
            self.options[idx].apply_upgrade()
            self.active = False
            self.gs.audio.unpause()

    def draw(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 160)); surf.blit(ov, (0, 0))
        surf.blit(self.font_h.render("레벨업! 스킬을 선택하세요", True, WHITE), (WIDTH // 2 - 250, HEIGHT // 2 - 160))
        for i, r in enumerate(self.btn_rects):
            if i >= len(self.options): continue
            sk = self.options[i]
            # UI 스타일 통일: 둥근 모서리
            draw_rounded_rect(surf, r, (45, 45, 55), radius=18)
            draw_rounded_rect(surf, r, (180, 180, 195), radius=18, width=2)
            
            surf.blit(self.name_font.render(sk.name, True, WHITE), (r.x + 22, r.y + 24))
            
            # ✅ 스킬 타입에 따라 설명 텍스트 분기 처리
            if isinstance(sk, HealSkill):
                # 힐 스킬인 경우 남은 사용 횟수 표시
                # MAX_SKILL_LEVEL을 최대 횟수로 간주
                remain = MAX_SKILL_LEVEL - sk.level
                lvl_txt = f"남은 사용 횟수: {remain}/{MAX_SKILL_LEVEL}"
            else:
                # 일반 스킬인 경우 현재 레벨 표시
                lvl_txt = f"현재 레벨: {sk.level}" if sk.level > 0 else "신규 해금!"
                
            surf.blit(self.font.render(lvl_txt, True, (210, 210, 220)), (r.x + 22, r.y + 76))
            surf.blit(self.font.render(f"[{i+1}] 선택", True, (210, 210, 220)), (r.x + 22, r.y + 116))

# -----------------------------
# 3. Main Screens
# -----------------------------
class StartScreen:
    def __init__(self, mgr, rm, audio):
        self.mgr = mgr; self.rm = rm; self.audio = audio
        self.audio.play(BGM_START)
        
        # 배경 이미지 로드
        self.bg = self.rm.get_image("game_background.png", (WIDTH, HEIGHT))
        
        # 폰트
        self.font_h1 = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font_h2 = pygame.font.SysFont("malgungothic", 26, bold=True)

        # 플레이어 설정 데이터
        self.PLAYERS = [
            {"id": "tank", "name": "플레이어 1", "HP": 150, "VEL": 240, "DMG": 1.0, "img_file": "player_1.png"},
            {"id": "speed", "name": "플레이어 2", "HP": 100, "VEL": 360, "DMG": 1.0, "img_file": "player_2.png"},
            {"id": "damage", "name": "플레이어 3", "HP": 100, "VEL": 240, "DMG": 1.5, "img_file": "player_3.png"}
        ]
        
        # 카드 레이아웃
        self.card_w, self.card_h = 250, 410
        self.gap = 30
        self.y_cards = 170
        total_w = self.card_w * 4 + self.gap * 3
        self.start_x = (WIDTH - total_w) // 2
        
        # PlayerCard 객체 생성
        self.cards = []
        for i, p_data in enumerate(self.PLAYERS):
            rect = pygame.Rect(self.start_x + i * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
            img = self.rm.get_image(p_data["img_file"], (150, 150)) # 카드 내부용 이미지 사이즈
            self.cards.append(PlayerCard(rect, p_data, img))
        self.selected_idx = 0

        # 난이도(스테이지) 패널
        self.stage_panel_rect = pygame.Rect(self.start_x + 3 * (self.card_w + self.gap), self.y_cards, self.card_w, self.card_h)
        stage_defs = [("easy", "쉬움", "보스 HP/속도 낮음"), ("normal", "보통", "기본 난이도"), ("hard", "어려움", "보스 강화")]
        self.stage_cards = []
        for i, (key, title, sub) in enumerate(stage_defs):
            r = pygame.Rect(self.stage_panel_rect.x + 16, self.stage_panel_rect.y + 78 + i * 112, self.card_w - 32, 96)
            self.stage_cards.append(StageCard(r, key, title, sub))
        self.stage_idx = 1 # Default Normal

        # 버튼
        btn_y = HEIGHT - 100
        btn_w, btn_h = 510, 60
        btn_gap = 60
        btn_x_start = (WIDTH - (btn_w * 2 + btn_gap)) // 2
        self.btn_exit = Button((btn_x_start, btn_y, btn_w, btn_h), "종료 (Esc)", RED)
        self.btn_start = Button((btn_x_start + btn_w + btn_gap, btn_y, btn_w, btn_h), "시작하기 (Enter)", GREEN)
        
        self._sync()

    def _sync(self):
        for i, c in enumerate(self.cards): c.selected = (i == self.selected_idx)
        for i, s in enumerate(self.stage_cards): s.selected = (i == self.stage_idx)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if event.key == pygame.K_RETURN: self._start_game()
            
            # 숫자키로 선택
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.selected_idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[event.key]
            if event.key in (pygame.K_4, pygame.K_5, pygame.K_6):
                self.stage_idx = {pygame.K_4: 0, pygame.K_5: 1, pygame.K_6: 2}[event.key]
            self._sync()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, card in enumerate(self.cards):
                if card.rect.collidepoint(event.pos): self.selected_idx = i
            for i, sc in enumerate(self.stage_cards):
                if sc.rect.collidepoint(event.pos): self.stage_idx = i
            self._sync()
            
        if self.btn_exit.clicked(event): pygame.quit(); sys.exit()
        if self.btn_start.clicked(event): self._start_game()

    def _start_game(self):
        # 선택된 플레이어 및 난이도 설정
        cfg = dict(self.PLAYERS[self.selected_idx])
        cfg["IMG"] = self.PLAYERS[self.selected_idx]["img_file"]
        cfg["DIFFICULTY"] = self.stage_cards[self.stage_idx].key
        self.mgr.set(GameScreen(self.mgr, cfg, self.rm, self.audio))

    def update(self, dt): pass

    def draw(self, surf):
        # 배경
        if self.bg: surf.blit(self.bg, (0, 0))
        else: surf.fill((18, 18, 24))

        mouse = pygame.mouse.get_pos()
        
        # 타이틀
        t_shadow = self.font_h1.render("MAGIC SURVIVOR", True, (0, 0, 0))
        t_main = self.font_h1.render("MAGIC SURVIVOR", True, WHITE)
        surf.blit(t_shadow, (82, 74)); surf.blit(t_main, (80, 72))

        # 캐릭터 카드
        for c in self.cards: c.draw(surf, mouse)
        
        # 스테이지 패널
        draw_rounded_rect(surf, self.stage_panel_rect, (35, 35, 42), radius=18)
        draw_rounded_rect(surf, self.stage_panel_rect, (120, 120, 135), radius=18, width=2)
        surf.blit(self.font_h2.render("스테이지", True, WHITE), (self.stage_panel_rect.x + 18, self.stage_panel_rect.y + 16))
        for sc in self.stage_cards: sc.draw(surf, mouse)
            
        # 버튼
        self.btn_exit.draw(surf, mouse)
        self.btn_start.draw(surf, mouse)

class GameScreen:
    def __init__(self, mgr, player_config, rm, audio):
        self.mgr = mgr; self.rm = rm; self.audio = audio
        self.controller = GameController(rm, player_config)
        self.audio.play(BGM_GAME)
        self._load_resources(player_config)
        
        # ✅ 스킬 초기화 (HealSkill 포함)
        self.skills = [BaseShotSkill(), FireConeSkill(), ElectricShockSkill(), ShieldSkill(), HealSkill()]
        
        # 1레벨부터 시작하는 기본 스킬(BaseShotSkill) 제외하고 나머지는 0레벨
        for i in range(1, len(self.skills)):
            self.skills[i].level = 0

        # ✅ 모든 스킬에 플레이어 참조 주입 (HealSkill 회복 효과를 위해 필수)
        for s in self.skills:
            s.player = self.controller.player
        
        self.overlay = None; self.paused = False; self.pause_overlay = None
        
        # UI Font
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.font_small = pygame.font.SysFont("malgungothic", 18)
        
        # UI Buttons (상단)
        self.btn_to_start = Button((WIDTH - 290, 14, 130, 40), "나가기", RED, (180, 55, 55), font=pygame.font.SysFont("malgungothic", 22), radius=14)
        self.btn_pause = Button((WIDTH - 150, 14, 130, 40), "Pause (P)", (90, 90, 110), (120, 120, 140), font=pygame.font.SysFont("malgungothic", 22), radius=14)
        
        self.cam = pygame.Vector2(0, 0) 

    def _load_resources(self, cfg):
        self.bg = self.rm.get_image("game_background.png", (WIDTH, HEIGHT))
        self.player_img = self.rm.get_image(cfg.get("IMG", ""), (80, 80))
        self.img_spider = self.rm.get_image("monster_spider.png", (30, 30))
        self.img_skull = self.rm.get_image("monster_bone.png", (30, 30))
        self.img_midboss = self.rm.get_image("middle_boss_dimenter.png", (120, 120))
        self.img_finalboss = self.rm.get_image("final_boss_pumpkin.png", (150, 150))

    def trigger_level_up(self):
        if any(s.level < MAX_SKILL_LEVEL for s in self.skills):
            self.overlay = SkillChoiceOverlay(self); self.audio.pause()

    def finish_game(self, success, reason):
        # 보스 브금 등을 끄고 결과 화면으로 전환
        self.audio.stop()
        stats = {
            "survival_time": self.controller.wave_mgr.elapsed, 
            "kill_count": self.controller.player.kills, 
            "player_config": self.controller.player_config, 
            "reason": reason
        }
        self.mgr.set(EndScreen(self.mgr, success, stats, self.rm, self.audio))

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.audio.pause()
            self.pause_overlay = PauseOverlay(self)
        else:
            self.audio.unpause()
            self.pause_overlay = None

    def handle_event(self, event):
        if self.overlay and self.overlay.active:
            self.overlay.handle_event(event)
            if not self.overlay.active: self.overlay = None
            return
        if self.paused and self.pause_overlay:
            self.pause_overlay.handle_event(event)
            if not self.pause_overlay.active:
                self.paused = False
                self.pause_overlay = None
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p: self._toggle_pause()
            if event.key == pygame.K_ESCAPE: self.audio.stop(); self.mgr.set(StartScreen(self.mgr, self.rm, self.audio))
        if self.btn_to_start.clicked(event): self.audio.stop(); self.mgr.set(StartScreen(self.mgr, self.rm, self.audio))
        if self.btn_pause.clicked(event): self._toggle_pause()

    def update(self, dt):
        if not self.paused and self.overlay is None:
            self.controller.tick_logic(dt, self)
            if self.controller.player.hp <= 0: self.finish_game(False, "플레이어 HP 소진")
            if self.controller.wave_mgr.elapsed >= self.controller.wave_mgr.total_time: self.finish_game(False, "시간 종료")

    def draw(self, surf):
        # 1. 배경
        if self.bg: surf.blit(self.bg, (0, 0))
        else: surf.fill(BLACK)
        
        # 2. 플레이 영역 (아레나) 경계선
        arena = pygame.Rect(20, 70, WIDTH-40, HEIGHT-90)
        # 안쪽은 비우고 테두리만 그리기 (배경이 보이도록)
        pygame.draw.rect(surf, (70,70,85), arena, 2, border_radius=18)
        
        c = self.controller; w = c.wave_mgr
        
        # 3. 적 그리기
        for e in c.enemies:
            if not e.alive(): continue
            surf.blit(e.img, e.img.get_rect(center=e.pos))
            # 보스 체력바
            if e.kind in ("midboss", "finalboss"):
                bx, by, bw, bh = int(e.pos.x - 100), int(e.pos.y - 70), 200, 12
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=8)
                pygame.draw.rect(surf, WHITE, (bx, by, int(bw * (e.hp / e.max_hp)), bh), border_radius=8)
            # 일반 몬스터 체력바 (작게)
            else:
                bw, bh = 40, 6
                bx, by = int(e.pos.x - bw // 2), int(e.pos.y + 22)
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=3)
                pygame.draw.rect(surf, RED, (bx, by, int(bw * (e.hp / e.max_hp)), bh), border_radius=3)
        
        # 4. 스킬 및 투사체
        for p in c.skill_projectiles: p.draw(surf, self.cam)
        if self.skills[2].level > 0: self.skills[2].draw(surf, self.cam) # Electric
        if self.skills[3].level > 0: self.skills[3].draw(surf, c.player, self.cam) # Shield
        
        # 5. 플레이어
        surf.blit(self.player_img, self.player_img.get_rect(center=c.player.pos))
        
        # 6. HUD
        self._draw_hud(surf)
        
        # 오버레이
        if self.overlay: self.overlay.draw(surf)
        elif self.paused and self.pause_overlay:
            self.pause_overlay.draw(surf)

    def _draw_hud(self, surf):
        c = self.controller; w = c.wave_mgr
        
        # 상단 바 배경
        bar_x, bar_y = 30, 18
        bar_w, bar_h = 520, 22
        pygame.draw.rect(surf, (45, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=10)
        
        # 경험치 바
        ratio = 0.0 if c.player.exp_need <= 0 else (c.player.exp / c.player.exp_need)
        pygame.draw.rect(surf, BLUE, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=10)
        pygame.draw.rect(surf, (170, 170, 185), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)
        
        # 텍스트 정보
        surf.blit(self.font_small.render(f"EXP {c.player.exp}/{c.player.exp_need}", True, WHITE), (bar_x + 10, bar_y - 2))
        surf.blit(self.font.render(f"레벨 {c.player.level}", True, WHITE), (bar_x + bar_w + 18, 14))
        surf.blit(self.font.render(f"처치수 {c.player.kills}", True, WHITE), (bar_x + bar_w + 140, 14))
        
        # 시간 표시
        rem = max(0.0, w.total_time - w.elapsed)
        surf.blit(self.font.render(f"{int(rem//60)}:{int(rem%60):02d}", True, WHITE), (WIDTH - 420, 14))
        
        # 플레이어 HP 바
        px, py, pw, ph = int(c.player.pos.x - 80), int(c.player.pos.y + 34), 160, 14
        pygame.draw.rect(surf, (45, 45, 55), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, RED, (px, py, int(pw * (c.player.hp / c.player.max_hp)), ph), border_radius=8)
        pygame.draw.rect(surf, (180, 180, 195), (px, py, pw, ph), 2, border_radius=8)
        
        # 보스 타이머 배너
        if w.boss_deadline:
            r = max(0.0, w.boss_deadline - w.elapsed)
            kind = "중간 보스" if w.active_boss_kind=='midboss' else "최종 보스"
            banner = pygame.Rect(380, 50, 520, 34)
            pygame.draw.rect(surf, (90, 40, 40), banner, border_radius=10)
            pygame.draw.rect(surf, (190, 90, 90), banner, 2, border_radius=10)
            surf.blit(self.font.render(f"{kind} 제한시간: {r:0.1f}s", True, WHITE), (banner.x + 12, banner.y + 6))

        # 상단 버튼
        mouse = pygame.mouse.get_pos()
        self.btn_to_start.draw(surf, mouse)
        self.btn_pause.draw(surf, mouse)

class EndScreen:
    def __init__(self, mgr, success, stats, rm, audio):
        self.mgr = mgr; self.success = success; self.stats = stats; self.rm = rm; self.audio = audio
        
        if self.success:
            self.audio.play_sfx(BGM_CLEAR)
        
        # 배경 로드
        self.bg = self.rm.get_image("game_background.png", (WIDTH, HEIGHT))
            
        self.font_h1 = pygame.font.SysFont("malgungothic", 86)
        self.font_h2 = pygame.font.SysFont("malgungothic", 36)
        self.font = pygame.font.SysFont("malgungothic", 26)
        self.font_small = pygame.font.SysFont("malgungothic", 22)
        
        # 레이아웃 상수
        self.PANEL_W, self.PANEL_H = 940, 310
        btn_w, btn_h = 435, 90
        btn_gap = 70
        bottom_margin = 60
        
        btn_y = HEIGHT - bottom_margin - btn_h
        btn_x = (WIDTH - (btn_w * 2 + btn_gap)) // 2
        
        self.btn_restart = Button((btn_x, btn_y, btn_w, btn_h), "다시하기 (Enter)", BLUE, (95, 185, 255), radius=22, font=pygame.font.SysFont("malgungothic", 34))
        self.btn_to_start = Button((btn_x + btn_w + btn_gap, btn_y, btn_w, btn_h), "시작화면 (Esc)", GREEN, (45, 185, 110), radius=22, font=pygame.font.SysFont("malgungothic", 34))
        
        self.panel_rect = pygame.Rect((WIDTH - self.PANEL_W)//2, btn_y - 28 - self.PANEL_H, self.PANEL_W, self.PANEL_H)

    def _stop_clear_sound(self):
        """화면 전환 시 클리어 브금(SFX)이 재생 중이라면 중단합니다."""
        if self.success and BGM_CLEAR in self.audio.sfx_cache:
            self.audio.sfx_cache[BGM_CLEAR].stop()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: 
                self._stop_clear_sound()
                self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm, self.audio))
            if event.key == pygame.K_ESCAPE: 
                self._stop_clear_sound()
                self.mgr.set(StartScreen(self.mgr, self.rm, self.audio))
        if self.btn_restart.clicked(event): 
            self._stop_clear_sound()
            self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm, self.audio))
        if self.btn_to_start.clicked(event): 
            self._stop_clear_sound()
            self.mgr.set(StartScreen(self.mgr, self.rm, self.audio))

    def update(self, dt): pass
    
    def draw(self, surf):
        if self.bg: surf.blit(self.bg, (0, 0))
        else: surf.fill((12, 12, 18))
        
        main_text = "GAME SUCCESS!" if self.success else "GAME OVER!"
        col = GREEN if self.success else RED
        
        # Title
        title = self.font_h1.render(main_text, True, col)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, 155)))
        
        # Glass Panel
        draw_glass_panel(surf, self.panel_rect)
        
        px = self.panel_rect.x + 44
        py = self.panel_rect.y + 34
        
        surf.blit(self.font_h2.render("결과", True, BLACK), (px, py))
        py += 70
        
        t = self.stats.get("survival_time", 0)
        kill = self.stats.get("kill_count", 0)
        reason = self.stats.get("reason", "")
        
        lines = [
            f"- 생존 시간 : {int(t//60)}:{int(t%60):02d}",
            f"- 처치한 몬스터 수 : {kill}"
        ]
        
        surf.blit(self.font.render(lines[0], True, BLACK), (px, py))
        py += 50
        surf.blit(self.font.render(lines[1], True, BLACK), (px, py))
        py += 66
        
        draw_divider(surf, self.panel_rect.x + 85, py, self.panel_rect.right - 85)
        py += 20
        
        surf.blit(self.font_small.render(f"종료 사유: {reason}", True, BLACK), (px, py))
        
        mouse = pygame.mouse.get_pos()
        self.btn_restart.draw(surf, mouse)
        self.btn_to_start.draw(surf, mouse)