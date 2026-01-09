import pygame
import sys
from config import WIDTH, HEIGHT, FPS
from core import ResourceManager, ScreenManager, AudioManager
from screens import StartScreen

def main():
    # Pygame 초기화
    pygame.init()
    pygame.font.init()
    pygame.mixer.init() # 오디오 믹서 초기화
    
    # 화면 설정
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MAGIC SURVIVOR")
    clock = pygame.time.Clock()
    
    # 매니저 초기화
    rm = ResourceManager()
    mgr = ScreenManager()
    
    # AudioManager 인스턴스 생성
    # core.py에서 play(), pause() 등의 하위 호환 메서드를 추가했으므로 
    # 기존 screens.py 코드 변경 없이 작동합니다.
    audio = AudioManager() 
    
    # 시작 화면 설정 (오디오 매니저 전달)
    mgr.set(StartScreen(mgr, rm, audio))
    
    # 메인 게임 루프
    while True:
        dt = clock.tick(FPS) / 1000.0
        
        # 이벤트 처리
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            mgr.handle_event(event)
            
        # 업데이트 및 그리기
        mgr.update(dt)
        mgr.draw(screen)
        
        pygame.display.flip()

if __name__ == "__main__":
    main()