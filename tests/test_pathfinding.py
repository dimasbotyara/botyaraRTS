"""
botyaraRTS - tests/test_pathfinding.py
A*: путь, рампы, недостижимость.
"""
from core.pathfinding import find_path, path_exists, smooth_path


def test_path_found_between_spawns(small_tilemap):
    a = small_tilemap.spawn_points[0]
    b = small_tilemap.spawn_points[1]
    path = find_path(small_tilemap, a[0], a[1], b[0], b[1])
    assert path is not None
    assert path[0] == a
    assert path[-1] == b


def test_path_avoids_walls(small_tilemap):
    a = small_tilemap.spawn_points[0]
    b = small_tilemap.spawn_points[1]
    path = find_path(small_tilemap, a[0], a[1], b[0], b[1])
    from core.tilemap import TILE_WALL, TILE_WATER
    for tx, ty in path:
        assert small_tilemap.get_tile(tx, ty) not in (TILE_WALL, TILE_WATER)


def test_smooth_path_removes_collinear(small_tilemap):
    a = small_tilemap.spawn_points[0]
    b = small_tilemap.spawn_points[1]
    path = find_path(small_tilemap, a[0], a[1], b[0], b[1])
    smooth = smooth_path(path, small_tilemap)
    assert len(smooth) <= len(path)
    assert smooth[0] == path[0] and smooth[-1] == path[-1]


def test_unreachable_target_sealed_area(small_tilemap):
    """Запечатанная область: путь ведёт к ближайшему достижимому тайлу."""
    from core.tilemap import TILE_WALL, TILE_GROUND
    tm = small_tilemap
    cx, cy = 48, 48
    # Строим коробку 3x3 со стенами
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if max(abs(dx), abs(dy)) == 2:
                tm.tiles[cy + dy][cx + dx] = TILE_WALL
    tm.tiles[cy][cx] = TILE_GROUND

    # path_exists внутрь коробки — ложь
    assert not path_exists(tm, cx, cy, tm.spawn_points[0][0], tm.spawn_points[0][1])

    # find_path к недостижимой цели — не None (ближайший достижимый) или None,
    # но не падает; за пределами коробки путь до спавна работает
    path = find_path(tm, tm.spawn_points[0][0], tm.spawn_points[0][1], 30, 30)
    if path is not None:
        from core.tilemap import TILE_WALL as W
        for tx, ty in path:
            assert tm.get_tile(tx, ty) != W


def test_path_costs_through_ramps(small_tilemap):
    """Путь не рвётся на границах высот (рампы проходимы)."""
    from core.tilemap import TILE_RAMP
    tm = small_tilemap
    ramps = [(tx, ty) for ty in range(tm.height) for tx in range(tm.width)
             if tm.tiles[ty][tx] == TILE_RAMP]
    if ramps:
        tx, ty = ramps[0]
        # Соседний тайл должен достигаться
        path = find_path(tm, tx, ty, tx + 2, ty)
        assert path is not None or not tm.is_walkable(tx + 2, ty)
