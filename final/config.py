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
EXP_BASE = 50
EXP_INC = 50

def exp_need_for_level(next_level: int) -> int:
    """다음 레벨에 필요한 경험치 계산"""
    return EXP_BASE + EXP_INC * (next_level - 1)