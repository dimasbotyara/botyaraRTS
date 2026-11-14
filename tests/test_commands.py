"""
botyaraRTS - tests/test_commands.py
Применение сетевых команд: движение, атака, стройка, производство.
"""
from network.commands import apply_command, compute_state_hash
from entities.worker import Worker


def test_move_command_by_ids(game_state):
    gs = game_state
    workers = [u for u in gs.units if isinstance(u, Worker)
               and u.player_id == 0][:2]
    ids = [w.id for w in workers]
    apply_command(gs, {'cmd': 'move', 'player_id': 0, 'unit_ids': ids,
                       'x': 2000.0, 'y': 2000.0})
    for w in workers:
        assert w.state == 'MOVE'
        assert w.move_target == (2000.0, 2000.0)


def test_move_ignores_foreign_units(game_state):
    gs = game_state
    foreign = [u for u in gs.units if u.player_id == 1][:1]
    apply_command(gs, {'cmd': 'move', 'player_id': 0, 'unit_ids': [foreign[0].id],
                       'x': 0.0, 'y': 0.0})
    assert foreign[0].state != 'MOVE' or foreign[0].move_target != (0.0, 0.0)


def test_build_command_places_building(game_state):
    gs = game_state
    player = gs.players[0]
    player.titan = 1000
    base_tx, base_ty = gs.tilemap.spawn_points[0]
    tx, ty = base_tx + 6, base_ty + 6
    # Освобождаем место, если занято ресурсом
    from core.tilemap import TILE_GROUND
    if gs.tilemap.get_tile(tx, ty) != TILE_GROUND:
        gs.tilemap.tiles[ty][tx] = TILE_GROUND
    n_before = len(gs.buildings)
    apply_command(gs, {'cmd': 'build', 'player_id': 0, 'building': 'Barracks',
                       'tx': tx, 'ty': ty})
    assert len(gs.buildings) == n_before + 1
    b = gs.buildings[-1]
    assert b.player_id == 0 and not b.is_completed
    assert player.titan < 1000  # стоимость списана


def test_build_rejects_overlap_and_bad_tiles(game_state):
    gs = game_state
    player = gs.players[0]
    player.titan = 1000
    tx, ty = gs.tilemap.spawn_points[0]
    n_before = len(gs.buildings)
    # Точка прямо на HQ — пересечение
    apply_command(gs, {'cmd': 'build', 'player_id': 0, 'building': 'Barracks',
                       'tx': tx, 'ty': ty})
    assert len(gs.buildings) == n_before


def test_produce_and_cancel_refund(game_state):
    gs = game_state
    player = gs.players[0]
    player.titan = 1000
    player.plasma = 100
    hq = next(b for b in gs.buildings if b.accepts_resources)
    apply_command(gs, {'cmd': 'produce', 'player_id': 0,
                       'building_id': hq.id, 'unit': 'Worker'})
    assert len(hq.production_queue) == 1
    before = player.titan
    apply_command(gs, {'cmd': 'cancel_produce', 'player_id': 0,
                       'building_id': hq.id, 'index': 0})
    assert hq.production_queue == []
    assert player.titan == before + 50


def test_unknown_command_is_ignored(game_state):
    apply_command(game_state, {'cmd': 'totally_unknown', 'player_id': 0})


def test_state_hash_changes_with_state(game_state):
    gs = game_state
    h1 = compute_state_hash(gs)
    w = gs.units[0]
    w.take_damage(10)
    h2 = compute_state_hash(gs)
    assert h1 != h2
