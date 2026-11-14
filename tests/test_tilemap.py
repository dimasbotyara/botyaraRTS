"""
botyaraRTS - tests/test_tilemap.py
Генерация карты: детерминизм, спавны, правила ресурсов, связность.
"""
from core.tilemap import (
    TileMap, TILE_GROUND, TILE_WALL, TILE_WATER, TILE_TITAN_ORE,
    TILE_PLASMA_GEYSER,
)


def test_generation_deterministic():
    a = TileMap(64, 64, seed=1234)
    b = TileMap(64, 64, seed=1234)
    assert a.tiles == b.tiles
    assert a.heights == b.heights
    assert a.titan_deposits == b.titan_deposits
    assert a.plasma_geysers == b.plasma_geysers


def test_generate_iter_progresses():
    tm = TileMap(64, 64, seed=99)
    steps = list(tm.generate_iter())
    # Прогресс монотонно растёт до 1.0
    progresses = [p for p, _ in steps]
    assert progresses[-1] == 1.0
    assert all(p2 >= p1 for p1, p2 in zip(progresses, progresses[1:]))


def test_spawn_counts():
    for count in (2, 3, 4):
        tm = TileMap(96, 96, seed=55, spawn_count=count)
        assert len(tm.spawn_points) == count
        for sx, sy in tm.spawn_points:
            assert tm.is_walkable(sx, sy)
            # Зона спавна очищена: земля под базой
            assert tm.get_tile(sx, sy) in (TILE_GROUND,)


def test_spawn_zones_clear():
    tm = TileMap(96, 96, seed=7, spawn_count=2)
    sx, sy = tm.spawn_points[0]
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            assert tm.get_tile(sx + dx, sy + dy) != TILE_WALL
            assert tm.get_tile(sx + dx, sy + dy) != TILE_WATER


def test_base_resources_near_spawn():
    tm = TileMap(96, 96, seed=31, spawn_count=2)
    for sx, sy in tm.spawn_points:
        near_ore = sum(1 for tx, ty in tm.titan_deposits
                       if (tx - sx) ** 2 + (ty - sy) ** 2 <= 15 ** 2)
        near_geyser = sum(1 for tx, ty in tm.plasma_geysers
                          if (tx - sx) ** 2 + (ty - sy) ** 2 <= 12 ** 2)
        assert near_ore >= 6, f"мало титана у спавна {sx},{sy}: {near_ore}"
        assert near_geyser >= 2, f"нет гейзеров у спавна {sx},{sy}"


def test_resource_patches_compact_and_symmetric():
    tm = TileMap(128, 128, seed=101, spawn_count=2)
    # Зеркальная симметрия кластеров: баланс половин карты
    w = tm.width
    ore = tm.titan_deposits
    left = sum(1 for tx, ty in ore if tx < w // 2)
    right = len(ore) - left
    assert abs(left - right) <= max(4, 0.35 * max(left, right)), \
        f"ресурсы несимметричны: left={left} right={right}"


def test_resources_not_inside_bases():
    tm = TileMap(96, 96, seed=64, spawn_count=2)
    # Тайл ресурса — либо часть базового кольца (~10 тайлов),
    # либо вне keepout нейтральных кластеров (19 тайлов с запасом)
    for sx, sy in tm.spawn_points:
        for tx, ty in tm.titan_deposits:
            d2 = (tx - sx) ** 2 + (ty - sy) ** 2
            assert d2 <= 12 ** 2 or d2 >= 17 ** 2, \
                f"кластер-одиночка внутри keepout: {(tx, ty)}"


def test_spawns_connected():
    from core.pathfinding import path_exists
    tm = TileMap(96, 96, seed=123, spawn_count=3)
    for i in range(len(tm.spawn_points)):
        for j in range(i + 1, len(tm.spawn_points)):
            a = tm.spawn_points[i]
            b = tm.spawn_points[j]
            assert path_exists(tm, a[0], a[1], b[0], b[1]), \
                f"спавны {a} и {b} не связаны"


def test_query_helpers():
    tm = TileMap(64, 64, seed=5)
    assert tm.get_tile(-1, 0) == TILE_WALL
    assert not tm.is_walkable(-5, -5)
    assert tm.tile_to_world(2, 3) == (2 * 32 + 16, 3 * 32 + 16)
    assert tm.world_to_tile(80, 112) == (2, 3)
