#!/usr/bin/env python3
"""Генератор скриншотов botyaraRTS для README и BUILDINGS_*.md.

Запуск из корня репозитория:
    SDL_VIDEODRIVER=dummy python3 tools/gen_screenshots.py
Создаёт screenshots/*.png и screenshots/buildings/*.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

pygame.init()
SCREEN = pygame.display.set_mode((1280, 800))

from core.game import Game, spawn_starting_units  # noqa: E402
from entities.building import (  # noqa: E402
    Headquarters, SupplyDepot, Refinery, PlasmaExtractor, TradingPost,
    Barracks, Factory, Starport, SpecOpsLab,
    Turret, SAMSite, Wall, ArtilleryBunker, ShieldGenerator,
    Armory, EngineeringBay,
)
from entities.vehicles import Tank  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'screenshots')
BLD_OUT = os.path.join(OUT, 'buildings')
os.makedirs(BLD_OUT, exist_ok=True)

CFG = dict(map_size='small', players=2, ai_difficulty='standard',
           ai_strategy='balanced', start_resources='rich',
           resource_density='normal', seed=1234)


def save(surface, name):
    path = os.path.join(OUT, name)
    pygame.image.save(surface, path)
    print('saved', path)


def disable_overlays(g):
    g.game_state.upgrade_system.is_choosing = False


# ---------- меню и экраны ----------
g = Game(SCREEN, 1280, 800)
g._render_menu()
save(SCREEN, 'menu.png')

g._open_create_match()
g._render_create_match()
save(SCREEN, 'match_setup.png')

# ---------- загрузка (середина генерации) ----------
g._start_singleplayer(CFG)
while g.state == 'loading' and g._load_progress < 0.45:
    g.menu_time += 0.03
    g._update_loading([])
    g._advance_loading(time_budget=0.02)
g._render_loading()
save(SCREEN, 'loading.png')
while g.state == 'loading':
    g.menu_time += 0.03
    g._update_loading([])
    g._advance_loading(time_budget=0.02)
g._render_loading()

gs = g.game_state
gs.debug_fog = False
gs.upgrade_system.is_choosing = False
g.match_start_countdown = 0          # без обратного отсчёта на кадрах
gs.camera.edge_scrolling = False     # без сползания камеры
dt = 1 / 30

# ---------- геймплей: база игрока ----------
sp = gs.tilemap.spawn_points[0]
wx, wy = gs.tilemap.tile_to_world(*sp)
gs.camera.target_zoom = gs.camera.zoom = 1.15
gs.camera.center_on(wx + 160, wy + 120, instant=True)
gs.render_manager.terrain.tile_cache.clear()
for f in range(60 * 30):
    g._update_game(dt, [])
    gs.upgrade_system.is_choosing = False   # предложение карт не даём открыть
g._render_game()
save(SCREEN, 'gameplay.png')

# ---------- бой: две танковые колонны ----------
cx, cy = wx + 1200, wy + 600
for i in range(4):
    gs.add_entity(Tank(cx - 260 + i * 60, cy - 90, 0))
    gs.add_entity(Tank(cx + 260 - i * 60, cy + 90, 1))
for t in list(gs.units):
    if isinstance(t, Tank) and t.hp < t.max_hp:
        pass
gs.camera.target_zoom = gs.camera.zoom = 1.45
gs.camera.center_on(cx, cy, instant=True)
gs.render_manager.terrain.tile_cache.clear()
for f in range(6 * 30):
    g._update_game(dt, [])
    gs.upgrade_system.is_choosing = False
g._render_game()
save(SCREEN, 'battle.png')

# ---------- панель сдачи ----------
gs.ai_surrender_request = 1
g._poll_surrender_request()
gs.camera.center_on(wx + 160, wy + 120, instant=True)
gs.render_manager.terrain.tile_cache.clear()
gs.upgrade_system.is_choosing = False
g._render_game()
save(SCREEN, 'surrender.png')
gs.ai_surrender_request = None
g._surrender_pending_pid = None

# ---------- лобби ----------
g2 = Game(SCREEN, 1280, 800)
g2._host_game()
for _ in range(8):
    g2._poll_network()
g2.server.add_ai_slot()
for _ in range(8):
    g2._poll_network()
g2._render_lobby()
save(SCREEN, 'lobby.png')
g2.server.stop()

# ---------- здания по отдельности ----------
BUILDINGS = [
    ('headquarters', Headquarters), ('supply_depot', SupplyDepot),
    ('refinery', Refinery), ('plasma_extractor', PlasmaExtractor),
    ('trading_post', TradingPost), ('barracks', Barracks),
    ('factory', Factory), ('starport', Starport),
    ('spec_ops_lab', SpecOpsLab), ('turret', Turret), ('sam_site', SAMSite),
    ('wall', Wall), ('artillery_bunker', ArtilleryBunker),
    ('shield_generator', ShieldGenerator), ('armory', Armory),
    ('engineering_bay', EngineeringBay),
]

# Чистая площадка: плоская зона возле спавна, очищаем от ресурсов
gs3 = Game(SCREEN, 1280, 800)
cfg3 = dict(CFG)
cfg3['seed'] = 777
gs3._start_singleplayer(cfg3)
while gs3.state == 'loading':
    gs3.menu_time += 0.03
    gs3._update_loading([])
    gs3._advance_loading(time_budget=0.02)
g3 = gs3
gs = g3.game_state
gs.debug_fog = False
gs.upgrade_system.is_choosing = False
g3.match_start_countdown = 0
gs.camera.edge_scrolling = False
from core.tilemap import TILE_GROUND, TILE_TITAN_ORE, TILE_PLASMA_GEYSER  # noqa: E402

bx, by = gs.tilemap.spawn_points[0]
grid_x, grid_y = bx + 20, by - 24  # старт сетки показа
for ty in range(grid_y - 4, grid_y + 36):
    for tx in range(grid_x - 4, grid_x + 44):
        if 0 <= tx < gs.tilemap.width and 0 <= ty < gs.tilemap.height:
            gs.tilemap.tiles[ty][tx] = TILE_GROUND
            gs.tilemap.heights[ty][tx] = 1
gs.tilemap.titan_deposits = [
    (tx, ty) for tx, ty in gs.tilemap.titan_deposits
    if not (grid_x - 6 <= tx <= grid_x + 44 and grid_y - 6 <= ty <= grid_y + 36)]
gs.tilemap.plasma_geysers = [
    (tx, ty) for tx, ty in gs.tilemap.plasma_geysers
    if not (grid_x - 6 <= tx <= grid_x + 44 and grid_y - 6 <= ty <= grid_y + 36)]
gs.minimap.pregen()

gs.camera.target_zoom = gs.camera.zoom = 2.2
gs.render_manager.terrain.tile_cache.clear()

CROP_W, CROP_H = 300, 240
slot = 0
for name, cls in BUILDINGS:
    col, row = slot % 6, slot // 6
    tx = grid_x + col * 7
    ty = grid_y + row * 7
    size = cls(0, 0).size_tiles
    wx2, wy2 = gs.tilemap.tile_to_world(tx + size // 2, ty + size // 2)
    b = cls(wx2, wy2, 0)
    b.is_completed = True
    b.construction_progress = b.build_time
    gs.add_entity(b)
    gs.camera.center_on(wx2, wy2, instant=True)
    gs.render_manager.terrain.tile_cache.clear()
    g3._render_game()
    cx2, cy2 = gs.camera.world_to_screen(wx2, wy2)
    rect = pygame.Rect(int(cx2 - CROP_W // 2), int(cy2 - CROP_H // 2),
                       CROP_W, CROP_H)
    rect.clamp_ip(SCREEN.get_rect())
    crop = SCREEN.subsurface(rect).copy()
    save(crop, f'buildings/{name}.png')
    gs.remove_entity(b)
    slot += 1

print('ALL SCREENSHOTS DONE')
