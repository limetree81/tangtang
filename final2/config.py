import os
import pygame

# -----------------------------
# 1. Config & Constants
# -----------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 60

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSET_DIR = os.path.join(BASE_DIR, "assets")

# 색상 정의
WHITE = (245, 245, 245)
BLACK = (12, 12, 15)
BLUE = (70, 160, 255)
GREEN = (60, 210, 120)
RED = (235, 80, 80)
YELLOW = (255, 220, 80)

MAX_SKILL_LEVEL = 5
# ✅ 오디오 자원 설정
BGM_START = "start_bgm.mp3"
BGM_GAME = "game_bgm.mp3"
BGM_FINAL_BOSS = "final_boss_bgm.mp3"  # 최종 보스전 브금
BGM_CLEAR = "clear_bgm.mp3"           # 게임 클리어 브금
SFX_MIDBOSS_SPAWN = "midboss_sfx.mp3" # 중간 보스 등장 효과음

# ✅ 레벨별 필요 경험치 고정 테이블 (20개)
# 인덱스 0은 1레벨이 되기 위한 경험치, 인덱스 19는 20레벨이 되기 위한 경험치입니다.
EXP_TABLE = (
    50, 120, 220, 350, 520, 
    750, 1050, 1450, 1950, 2550, 
    3250, 4050, 4950, 5950, 7050, 
    8250, 9550, 11000, 12600, 14400
)

def exp_need_for_level(next_level: int) -> int:
    """고정 튜플 테이블에서 다음 레벨에 필요한 경험치를 가져옵니다."""
    # 레벨은 1부터 시작하므로 인덱스는 next_level - 1
    # 1미만은 0번 인덱스, 20초과는 19번 인덱스를 참조하도록 제한
    idx = max(1, min(next_level, len(EXP_TABLE))) - 1
    return EXP_TABLE[idx]