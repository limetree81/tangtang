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

# ✅ 난이도별 설정값
# spawn_prob_start: 시작 시점(0분)의 스폰 확률
# spawn_prob_end: 종료 시점(5분)의 스폰 확률 (계단식으로 증가)
# boss_count: 보스 소환 마리 수
# mob_hp: 일반 몬스터 기본 체력
# boss_hp: 보스 몬스터 기본 체력
# max_enemies: 화면 내 최대 적 수
# exp_drop: 몬스터 처치 시 획득하는 고정 경험치
# mob_damage: 일반 몬스터 충돌 데미지 (초당)
# boss_damage: 보스 몬스터 충돌 데미지 (초당)
DIFFICULTY_SETTINGS = {
    "easy": {
        "spawn_prob_start": 0.015, # 
        "spawn_prob_end": 0.045, 
        "boss_time_limit": 60.0,
        "max_enemies": 40,
        "boss_speed_mult": 1.0,
        "boss_count": 1,
        "mob_hp": 10,
        "boss_hp": 800,
        "exp_drop": 12,
        "mob_damage": 15,
        "boss_damage": 25
    },
    "normal": {
        "spawn_prob_start": 0.02,  # 시작: 보통
        "spawn_prob_end": 0.50,
        "boss_time_limit": 60.0,
        "max_enemies": 60,
        "boss_speed_mult": 1.0,
        "boss_count": 1,
        "mob_hp": 15,
        "boss_hp": 1200,
        "exp_drop": 15,
        "mob_damage": 20,
        "boss_damage": 40
    },
    "hard": {
        "spawn_prob_start": 0.025,
        "spawn_prob_end": 0.80,
        "boss_time_limit": 60.0,
        "max_enemies": 100,
        "boss_speed_mult": 1.2,
        "boss_count": 2,
        "mob_hp": 20,
        "boss_hp": 2000,
        "exp_drop": 75,
        "mob_damage": 25,
        "boss_damage": 60
    }
}

# ✅ 레벨별 필요 경험치 고정 테이블 (23개로 확장)
# 인덱스 0은 1레벨이 되기 위한 경험치, 인덱스 22는 23레벨이 되기 위한 경험치입니다.
EXP_TABLE = (
    50, 120, 220, 350, 520, 
    750, 1050, 1450, 1950, 2550, 
    3250, 4050, 4950, 5950, 7050, 
    8250, 9550, 11000, 12600, 14400,
    16400, 18600, 21000
)

def exp_need_for_level(next_level: int) -> int:
    """고정 튜플 테이블에서 다음 레벨에 필요한 경험치를 가져옵니다."""
    # 레벨은 1부터 시작하므로 인덱스는 next_level - 1
    # 1미만은 0번 인덱스, 23초과는 22번 인덱스를 참조하도록 제한
    idx = max(1, min(next_level, len(EXP_TABLE))) - 1
    return EXP_TABLE[idx]