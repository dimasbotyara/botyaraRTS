"""
botyaraRTS - tests/conftest.py
Общие фикстуры: headless pygame, маленькая карта, GameState.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import pytest

from core.tilemap import TileMap
from core.game import GameState


@pytest.fixture(scope='session', autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((320, 240))
    yield
    pygame.quit()


@pytest.fixture
def small_tilemap():
    """Маленькая карта 96x96 с 2 спавнами (быстрая генерация)."""
    return TileMap(96, 96, seed=777, spawn_count=2)


@pytest.fixture
def game_state(small_tilemap):
    gs = GameState(800, 600, seed=777, local_player_id=0,
                   tilemap=small_tilemap, player_count=2)
    # Стартовые базы обоим игрокам
    from core.game import spawn_starting_units
    spawn_starting_units(gs, 0)
    spawn_starting_units(gs, 1)
    yield gs
