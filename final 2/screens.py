import pygame
import random
import math
import sys
from config import WIDTH, HEIGHT, BLACK, WHITE, BLUE, RED, GREEN, MAX_SKILL_LEVEL
from core import Button, draw_panel
from entities import Player, Enemy
# skill.py의 스킬 시스템 임포트
from skill import BaseShotSkill, FireConeSkill, ElectricShockSkill, ShieldSkill

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
            # ✅ 일반 적 체력을 10에서 30으로 상향하여 여러 번 맞아야 죽도록 설정
            controller.enemies.append(Enemy(kind, pos, 30, 10, img))

    def _spawn_boss(self, gs, controller, kind):
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
    def __init__(self, rm, player_config):
        self.rm = rm
        self.player_config = player_config
        # WaveManager 인스턴스 생성
        self.wave_mgr = WaveManager()
        self.reset()

    def reset(self):
        self.player = Player(self.player_config)
        self.enemies = []
        self.skill_projectiles = [] 
        self.wave_mgr.reset()

    def tick_logic(self, dt, gs):
        # ✅ WaveManager에게 스폰 업무 위임
        self.wave_mgr.update(dt, gs, self)

        keys = pygame.key.get_pressed()
        self.player.move(dt, keys)
        
        # 적 이동
        for e in self.enemies:
            if not e.alive(): continue
            if e.kind in ("spider", "skull"):
                dv = self.player.pos - e.pos
                if dv.length_squared() > 0:
                    e.pos += dv.normalize() * e.speed * dt
            else:
                # 보스 랜덤 이동
                e.random_change_t -= dt
                if e.random_change_t <= 0:
                    e.random_change_t = random.uniform(0.2, 0.6)
                    ang = random.uniform(0, math.tau)
                    e.random_vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * e.speed
                e.pos += e.random_vel * dt
                e.pos.x = max(60, min(WIDTH - 60, e.pos.x))
                pos_y_min = 110 # HUD 영역 고려
                e.pos.y = max(pos_y_min, min(HEIGHT - 60, e.pos.y))

        # 스킬 업데이트
        for s in gs.skills:
            if s.level > 0:
                s.update(dt, self.player, self.enemies, self.skill_projectiles)
            
        # 투사체 이동 및 충돌
        for p in self.skill_projectiles[:]:
            p.update(dt)
            if p.life <= 0:
                if p in self.skill_projectiles: self.skill_projectiles.remove(p)
                continue
            
            # ✅ 중복 히트 방지를 위한 히트 타겟 관리
            if not hasattr(p, 'hit_targets'):
                p.hit_targets = set()
            
            if p.damage > 0:
                for e in self.enemies:
                    if not e.alive() or e in p.hit_targets: continue
                    
                    # 충돌 판정 (투사체 크기와 적 반지름 고려)
                    hit_dist = e.radius + (max(p.size) // 2)
                    if (e.pos - p.pos).length_squared() <= hit_dist**2:
                        # ✅ 플레이어 공격력 배율 적용하여 데미지 계산
                        final_dmg = p.damage * self.player.dmg
                        e.hp -= final_dmg
                        p.hit_targets.add(e)
                        
                        # ✅ 화염 투사체(파이어볼) 특수 처리: 폭발 효과
                        if getattr(p, 'is_fire', False):
                            ex_rad_sq = getattr(p, 'explosion_radius', 60)**2
                            for other in self.enemies:
                                if other is not e and other.alive():
                                    if (other.pos - p.pos).length_squared() <= ex_rad_sq:
                                        other.hp -= final_dmg * 0.5 # 스플래시 데미지
                            # 화염 투사체는 폭발 후 소멸
                            if p in self.skill_projectiles: self.skill_projectiles.remove(p)
                        else:
                            # 일반 투사체는 명중 시 소멸
                            if p in self.skill_projectiles: self.skill_projectiles.remove(p)
                        break

        # 플레이어 충돌 및 사망 보상 처리
        self._handle_collisions_and_rewards(dt, gs)

        # 리스트 정리
        self.enemies = [e for e in self.enemies if e.alive()]

    def _handle_collisions_and_rewards(self, dt, gs):
        p_pos = self.player.pos
        p_rad = self.player.radius
        leveled_up = False

        for e in self.enemies:
            if e.alive():
                diff = e.pos - p_pos
                dist_sq = diff.length_squared()
                min_dist = e.radius + p_rad
                if dist_sq <= min_dist**2:
                    self.player.hp -= (35 if e.kind == "finalboss" else 20) * dt
                    if dist_sq > 0:
                        e.pos = p_pos + diff.normalize() * (min_dist + 1)
                    else:
                        e.pos.x += random.choice([-1, 1])

            # 사망 판정 및 보상
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

        if leveled_up: gs.trigger_level_up()

# -----------------------------
# 3. Overlay Screens
# -----------------------------
class PauseOverlay:
    def __init__(self, gs):
        self.gs = gs
        self.active = True
        self.font_h = pygame.font.SysFont("malgungothic", 64, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.btn_resume = Button((WIDTH // 2 - 200, HEIGHT // 2 + 40, 400, 70), "계속하기 (P)", BLUE, (95, 185, 255), pygame.font.SysFont("malgungothic", 28))

    def handle_event(self, event):
        if not self.active: return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_p: self._resume()
        if self.btn_resume.clicked(event): self._resume()

    def _resume(self):
        self.active = False; self.gs.paused = False; self.gs.bgm.unpause()

    def draw(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 170)); surf.blit(overlay, (0, 0))
        title = self.font_h.render("PAUSED", True, WHITE)
        surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
        tip = self.font.render("게임이 일시정지되었습니다. P 또는 버튼으로 재개할 수 있습니다.", True, (220, 220, 230))
        surf.blit(tip, tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))
        self.btn_resume.draw(surf, pygame.mouse.get_pos())

class SkillChoiceOverlay:
    def __init__(self, gs):
        self.gs = gs; self.active = True
        self.options = [s for s in gs.skills if s.level < MAX_SKILL_LEVEL]
        random.shuffle(self.options)
        self.options = self.options[:3]
        self.font_h = pygame.font.SysFont("malgungothic", 44, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.name_font = pygame.font.SysFont("malgungothic", 28)
        w, h, gap = 320, 160, 40; x0 = (WIDTH - (w*3 + gap*2)) // 2; y0 = HEIGHT // 2 - 70
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
            self.active = False; self.gs.bgm.unpause()

    def draw(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 160)); surf.blit(ov, (0, 0))
        surf.blit(self.font_h.render("레벨업! 스킬을 선택하세요", True, WHITE), (WIDTH // 2 - 250, HEIGHT // 2 - 160))
        for i, r in enumerate(self.btn_rects):
            if i >= len(self.options): continue
            sk = self.options[i]; pygame.draw.rect(surf, (45, 45, 55), r, border_radius=18); pygame.draw.rect(surf, (180, 180, 195), r, 2, border_radius=18)
            surf.blit(self.name_font.render(sk.name, True, WHITE), (r.x + 22, r.y + 24))
            lvl_txt = f"현재 레벨: {sk.level}" if sk.level > 0 else "신규 해금!"
            surf.blit(self.font.render(lvl_txt, True, (210, 210, 220)), (r.x + 22, r.y + 76))
            surf.blit(self.font.render(f"[{i+1}] 선택", True, (210, 210, 220)), (r.x + 22, r.y + 116))

# -----------------------------
# 4. Main Screens
# -----------------------------
class StartScreen:
    def __init__(self, mgr, rm, bgm):
        self.mgr = mgr; self.rm = rm; self.bgm = bgm
        self.bgm.play("start_bgm.mp3")
        self.font_h1 = pygame.font.SysFont("malgungothic", 52, bold=True)
        self.font_h2 = pygame.font.SysFont("malgungothic", 20, bold=True)
        self.font = pygame.font.SysFont("malgungothic", 20)
        self.font_small = pygame.font.SysFont("malgungothic", 16)
        self.PLAYERS = [{"id": "tank", "name": "플레이어 1", "HP": 130, "VEL": 240, "DMG": 1.0}, {"id": "speed", "name": "플레이어 2", "HP": 100, "VEL": 290, "DMG": 1.0}, {"id": "damage", "name": "플레이어 3", "HP": 100, "VEL": 240, "DMG": 1.3}]
        self.image_paths = ["player1.jpg", "player2.jpg", "player3.jpg"]
        self.card_w, self.card_h, self.card_gap = 280, 390, 26; x0 = (WIDTH - (self.card_w*4 + self.card_gap*3)) // 2
        self.card_rects = [pygame.Rect(x0 + i*(self.card_w + self.card_gap), 170, self.card_w, self.card_h) for i in range(3)]
        self.help_rect = pygame.Rect(x0 + 3*(self.card_w + self.card_gap), 170, self.card_w, self.card_h)
        self.selected = 0; self.card_imgs = [self.rm.get_image(p, (self.card_w-40, 190)) for p in self.image_paths]
        bx = (WIDTH - (420*2 + 60)) // 2; btn_y = 170 + self.card_h + 40
        self.btn_quit = Button((bx, btn_y, 420, 70), "종료 (Esc)", RED, (180, 55, 55), self.font_h2)
        self.btn_start = Button((bx + 480, btn_y, 420, 70), "시작하기 (Enter)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
            if event.key == pygame.K_RETURN: self._start_game()
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3): self.selected = event.key - pygame.K_1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(event.pos): self.selected = i
        if self.btn_quit.clicked(event): pygame.quit(); sys.exit()
        if self.btn_start.clicked(event): self._start_game()

    def _start_game(self):
        cfg = dict(self.PLAYERS[self.selected]); cfg["IMG"] = self.image_paths[self.selected]
        self.mgr.set(GameScreen(self.mgr, cfg, self.rm, self.bgm))

    def update(self, dt): pass
    def draw(self, surf):
        surf.fill(BLACK); m = pygame.mouse.get_pos()
        surf.blit(self.font_h1.render("MAGIC SURVIVOR - START", True, WHITE), (80, 70))
        surf.blit(self.font.render("플레이어 선택 (카드/1~3) | 시작 Enter | 종료 Esc", True, (190, 190, 200)), (80, 132))
        for i, r in enumerate(self.card_rects):
            sel = (i == self.selected); border = BLUE if sel else (120, 120, 135)
            pygame.draw.rect(surf, (35, 35, 42), r, border_radius=18); pygame.draw.rect(surf, border, r, 3 if sel else 2, border_radius=18)
            img_a = pygame.Rect(r.x+20, r.y+20, r.w-40, 190); pygame.draw.rect(surf, (60, 60, 70), img_a, border_radius=12)
            surf.blit(self.card_imgs[i], self.card_imgs[i].get_rect(center=img_a.center))
            surf.blit(self.font_h2.render(self.PLAYERS[i]["name"], True, WHITE), (r.x + 22, r.y + 230))
            for j, k in enumerate(["HP", "VEL", "DMG"]):
                val = self.PLAYERS[i][k]; val_str = f"x{val}" if k == "DMG" else str(val)
                surf.blit(self.font_small.render(f"{k}  {val_str}", True, (210, 210, 220)), (r.x + 22, r.y + 275 + j * 25))
        draw_panel(surf, self.help_rect, "도움말", self.font_h2)
        yy = self.help_rect.y + 70
        for ln in ["[플레이어]", "P1: HP 높음", "P2: 이동속도 높음", "P3: 공격력 높음", "", "[인게임]", "레벨업: EXP 획득 시", "레벨업 시 스킬 선택", "", "[조작]", "이동: WASD / 방향키"]:
            surf.blit(self.font.render(ln, True, (215, 215, 225)), (self.help_rect.x + 18, yy)); yy += 28
        self.btn_quit.draw(surf, m); self.btn_start.draw(surf, m)

class GameScreen:
    def __init__(self, mgr, player_config, rm, bgm):
        self.mgr = mgr; self.rm = rm; self.bgm = bgm
        self.controller = GameController(rm, player_config)
        self.bgm.play("game_bgm.mp3")
        self._load_resources(player_config)
        
        self.skills = [BaseShotSkill(), FireConeSkill(), ElectricShockSkill(), ShieldSkill()]
        for i in range(1, len(self.skills)):
            self.skills[i].level = 0
        
        self.overlay = None; self.paused = False; self.pause_overlay = None
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.info_font = pygame.font.SysFont("malgungothic", 20)
        self.btn_to_start = Button((WIDTH - 290, 14, 130, 40), "나가기", RED, (180, 55, 55), self.font)
        self.btn_pause = Button((WIDTH - 150, 14, 130, 40), "Pause (P)", (90, 90, 110), (120, 120, 140), self.font)
        self.cam = pygame.Vector2(0, 0) 

    def _load_resources(self, cfg):
        self.player_img = self.rm.get_image(cfg.get("IMG", ""), (80, 80))
        self.img_spider = self.rm.get_image("monster_spider.png", (30, 30))
        self.img_skull = self.rm.get_image("monster_bone.png", (30, 30))
        self.img_midboss = self.rm.get_image("middle_boss_dimenter.png", (120, 120))
        self.img_finalboss = self.rm.get_image("final_boss_pumpkin.png", (150, 150))

    def trigger_level_up(self):
        if any(s.level < MAX_SKILL_LEVEL for s in self.skills):
            self.overlay = SkillChoiceOverlay(self); self.bgm.pause()

    def finish_game(self, success, reason):
        self.bgm.stop()
        stats = {"survival_time": self.controller.wave_mgr.elapsed, "kill_count": self.controller.player.kills, "player_config": self.controller.player_config, "reason": reason}
        self.mgr.set(EndScreen(self.mgr, success, stats, self.rm, self.bgm))

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused: self.bgm.pause(); self.pause_overlay = PauseOverlay(self)
        else: self.bgm.unpause(); self.pause_overlay = None

    def handle_event(self, event):
        if self.overlay and self.overlay.active:
            self.overlay.handle_event(event)
            if not self.overlay.active: self.overlay = None
            return
        if self.paused and self.pause_overlay:
            self.pause_overlay.handle_event(event)
            if not self.pause_overlay.active: self.paused = False; self.pause_overlay = None
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p: self._toggle_pause()
            if event.key == pygame.K_ESCAPE: self.bgm.stop(); self.mgr.set(StartScreen(self.mgr, self.rm, self.bgm))
        if self.btn_to_start.clicked(event): self.bgm.stop(); self.mgr.set(StartScreen(self.mgr, self.rm, self.bgm))
        if self.btn_pause.clicked(event): self._toggle_pause()

    def update(self, dt):
        if not self.paused and self.overlay is None:
            self.controller.tick_logic(dt, self)
            if self.controller.player.hp <= 0: self.finish_game(False, "플레이어 HP 소진")
            if self.controller.wave_mgr.elapsed >= self.controller.wave_mgr.total_time: self.finish_game(False, "시간 종료")

    def draw(self, surf):
        surf.fill(BLACK); arena = pygame.Rect(20, 70, WIDTH-40, HEIGHT-90); pygame.draw.rect(surf, (20,20,26), arena, border_radius=18); pygame.draw.rect(surf, (70,70,85), arena, 2, border_radius=18)
        c = self.controller; w = c.wave_mgr
        
        for e in c.enemies:
            if not e.alive(): continue
            surf.blit(e.img, e.img.get_rect(center=e.pos))
            if e.kind in ("midboss", "finalboss"):
                # 보스 체력바 (위쪽)
                bx, by, bw, bh = int(e.pos.x - 100), int(e.pos.y - 70), 200, 12
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=8); pygame.draw.rect(surf, WHITE, (bx, by, int(bw * (e.hp / e.max_hp)), bh), border_radius=8)
            else:
                # 일반몹 체력바 (자기 바로 밑에)
                bw, bh = 40, 6
                bx, by = int(e.pos.x - bw // 2), int(e.pos.y + 22)
                pygame.draw.rect(surf, (45, 45, 55), (bx, by, bw, bh), border_radius=3)
                pygame.draw.rect(surf, RED, (bx, by, int(bw * (e.hp / e.max_hp)), bh), border_radius=3)
        
        for p in c.skill_projectiles: p.draw(surf, self.cam)
        if self.skills[2].level > 0: self.skills[2].draw(surf, self.cam)
        if self.skills[3].level > 0: self.skills[3].draw(surf, c.player, self.cam)
        
        surf.blit(self.player_img, self.player_img.get_rect(center=c.player.pos))
        self._draw_hud(surf)
        
        if w.boss_deadline:
            r = max(0.0, w.boss_deadline - w.elapsed); banner = pygame.Rect(380, 50, 520, 34); pygame.draw.rect(surf, (90, 40, 40), banner, border_radius=10); pygame.draw.rect(surf, (190, 90, 90), banner, 2, border_radius=10)
            surf.blit(self.font.render(f"{'중간 보스' if w.active_boss_kind=='midboss' else '최종 보스'} 제한시간: {r:0.1f}s", True, WHITE), (banner.x + 12, banner.y + 6))

        if self.overlay: self.overlay.draw(surf)
        elif self.paused and self.pause_overlay: self.pause_overlay.draw(surf)

    def _draw_hud(self, surf):
        c = self.controller; w = c.wave_mgr; bx, by, bw, bh = 30, 18, 520, 22
        pygame.draw.rect(surf, (45,45,55), (bx, by, bw, bh), border_radius=10); pygame.draw.rect(surf, BLUE, (bx, by, int(bw * (c.player.exp/c.player.exp_need)), bh), border_radius=10)
        surf.blit(self.info_font.render(f"Lv {c.player.level} | Kills {c.player.kills}", True, WHITE), (570, 14))
        rem = max(0.0, w.total_time - w.elapsed); surf.blit(self.info_font.render(f"{int(rem//60)}:{int(rem%60):02d}", True, WHITE), (WIDTH - 420, 14))
        px, py, pw, ph = int(c.player.pos.x - 80), int(c.player.pos.y + 34), 160, 14
        pygame.draw.rect(surf, (45, 45, 55), (px, py, pw, ph), border_radius=8); pygame.draw.rect(surf, RED, (px, py, int(pw * (c.player.hp / c.player.max_hp)), ph), border_radius=8); pygame.draw.rect(surf, (180, 180, 195), (px, py, pw, ph), 2, border_radius=8)
        self.btn_to_start.draw(surf, pygame.mouse.get_pos()); self.btn_pause.draw(surf, pygame.mouse.get_pos())

class EndScreen:
    def __init__(self, mgr, success, stats, rm, bgm):
        self.mgr = mgr; self.success = success; self.stats = stats; self.rm = rm; self.bgm = bgm
        self.font_h1 = pygame.font.SysFont("malgungothic", 64); self.font_h2 = pygame.font.SysFont("malgungothic", 32); self.font = pygame.font.SysFont("malgungothic", 24)
        bx = (WIDTH - 900) // 2; by = HEIGHT - 160
        self.btn_restart = Button((bx, by, 420, 70), "다시하기 (Enter)", BLUE, (95, 185, 255), self.font_h2)
        self.btn_to_start = Button((bx + 480, by, 420, 70), "시작화면 (Esc)", GREEN, (45, 185, 110), self.font_h2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm, self.bgm))
            if event.key == pygame.K_ESCAPE: self.mgr.set(StartScreen(self.mgr, self.rm, self.bgm))
        if self.btn_restart.clicked(event): self.mgr.set(GameScreen(self.mgr, self.stats["player_config"], self.rm, self.bgm))
        if self.btn_to_start.clicked(event): self.mgr.set(StartScreen(self.mgr, self.rm, self.bgm))

    def update(self, dt): pass
    def draw(self, surf):
        surf.fill(BLACK); m = pygame.mouse.get_pos(); title = "GAME SUCCESS!!" if self.success else "GAME OVER!"
        surf.blit(self.font_h1.render(title, True, GREEN if self.success else RED), (WIDTH//2-200, 100))
        panel = pygame.Rect(WIDTH // 2 - 380, 220, 760, 320); draw_panel(surf, panel, "결과", self.font_h2)
        t = self.stats.get("survival_time", 0); kill = self.stats.get("kill_count", 0); reason = self.stats.get("reason", "")
        for i, ln in enumerate([f"- 생존 시간: {int(t//60)}:{int(t%60):02d}", f"- 처치한 몬스터 수: {kill}"]):
            surf.blit(self.font.render(ln, True, (230, 230, 240)), (panel.x + 30, panel.y + 90 + i*44))
        if reason: surf.blit(self.font.render(f"종료 사유: {reason}", True, (200, 200, 215)), (panel.x + 30, panel.y + 230))
        self.btn_restart.draw(surf, m); self.btn_to_start.draw(surf, m)