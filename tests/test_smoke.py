"""
botyaraRTS - tests/test_smoke.py
Интеграционные дымовые тесты: загрузка матча, симуляция, ИИ в деле.
"""
import time

import pygame
import pytest

from core.game import Game, GameState
from core.tilemap import TileMap
from settings import MATCH_SIZES


def _load_game(pygame_headless, cfg, size=800):
    screen = pygame.display.get_surface()
    g = Game(screen, size, size)
    g._start_singleplayer(cfg)
    deadline = time.time() + 60
    while g.state == 'loading' and time.time() < deadline:
        g.menu_time += 0.03
        g._update_loading([])
        g._advance_loading(time_budget=0.02)
    return g


def test_full_match_load_and_sim(pygame_headless):
    cfg = dict(map_size='small', players=2, ai_difficulty='standard',
               ai_strategy='rush', start_resources='normal',
               resource_density='normal', seed=4242)
    g = _load_game(pygame_headless, cfg)
    assert g.state == 'playing'
    gs = g.game_state
    assert len(gs.players) == 2
    assert len(gs.units) == 12          # 6 рабочих x2
    assert len(gs.buildings) == 4       # HQ+склад x2
    assert gs.ai_brains and 1 in gs.ai_brains

    # 30 секунд симуляции на фиксированном тике
    from settings import SIM_DT
    for f in range(int(30 / SIM_DT)):
        g._update_game(SIM_DT, [])
        if g.state != 'playing':
            break
    # ИИ должен был начать стройку
    ai_buildings = [b for b in gs.buildings if b.player_id == 1]
    assert len(ai_buildings) >= 3


def test_map_sizes_registered():
    assert MATCH_SIZES['small'] < MATCH_SIZES['medium'] < MATCH_SIZES['large']


def test_gamestate_sync_pregen(pygame_headless):
    """Отложенная предгенерация догоняется finish_pregen."""
    tm = TileMap(64, 64, seed=8)
    gs = GameState(400, 300, seed=8, tilemap=tm, player_count=2,
                   defer_pregen=True)
    assert gs._pregen_done is False
    gs.finish_pregen()
    assert gs._pregen_done is True
    assert len(gs.minimap.terrain_surface.get_at((0, 0))) >= 3


def test_multiplayer_spawn_assignment(pygame_headless):
    """Локальный игрок 1 получает свой спавн (не спавн хоста)."""
    tm = TileMap(64, 64, seed=17, spawn_count=2)
    gs1 = GameState(400, 300, seed=17, local_player_id=0, tilemap=tm,
                    player_count=2)
    gs2 = GameState(400, 300, seed=17, local_player_id=1, tilemap=tm,
                    player_count=2)
    assert gs1.tilemap is tm and gs2.tilemap is tm
    sp0 = tm.tile_to_world(*tm.spawn_points[0])
    sp1 = tm.tile_to_world(*tm.spawn_points[1])
    assert abs(gs1.camera.x - sp0[0]) < abs(gs1.camera.x - sp1[0])
    assert abs(gs2.camera.x - sp1[0]) < abs(gs2.camera.x - sp0[0])
