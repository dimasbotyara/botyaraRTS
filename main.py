"""
botyaraRTS - main.py
Точка входа. Инициализация pygame, запуск игры.
"""
import pygame
import sys
import os

# Добавляем корневую папку в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import *
from core.game import Game


def get_display_info():
    """Получить разрешение монитора."""
    pygame.init()
    info = pygame.display.Info()
    return info.current_w, info.current_h


def set_window_icon():
    """Иконка окна из assets/branding/icon.png."""
    try:
        icon_path = os.path.join(ASSETS_DIR, 'branding', 'icon_512.png')
        if os.path.exists(icon_path):
            icon = pygame.image.load(icon_path)
            pygame.display.set_icon(
                pygame.transform.smoothscale(icon, (32, 32)))
    except Exception:
        pass  # Иконка — не критична


def main():
    pygame.init()
    pygame.mixer.init()

    # Получаем разрешение монитора
    monitor_w, monitor_h = get_display_info()

    # Применяем настройки
    settings = game_settings
    if settings.get('fullscreen'):
        screen_w, screen_h = monitor_w, monitor_h
        screen = pygame.display.set_mode((screen_w, screen_h), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    else:
        screen_w = min(settings.get('screen_width'), monitor_w)
        screen_h = min(settings.get('screen_height'), monitor_h)
        screen = pygame.display.set_mode((screen_w, screen_h), pygame.RESIZABLE)

    pygame.display.set_caption(GAME_TITLE)
    set_window_icon()

    # Создаём и запускаем игру
    game = Game(screen, screen_w, screen_h)
    game.run()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
