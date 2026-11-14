"""
botyaraRTS - core/tilemap.py
Тайловая карта с процедурной генерацией (Perlin Noise),
высотами, стенами, рампами и ресурсами.

Генерация инкрементальная: generate_iter() отдаёт (прогресс, label)
после каждой полосы тайлов, чтобы экран загрузки оставался живым.
"""
import pygame
import random
import math
from settings import *


# === Простой Perlin-подобный шум без внешних зависимостей ===
class SimplexNoise:
    """Упрощённый value noise с интерполяцией для генерации карт."""

    def __init__(self, seed=None):
        # Локальный RNG: не трогаем глобальное состояние random
        rng = random.Random(seed if seed else 0)
        self.perm = list(range(256))
        rng.shuffle(self.perm)
        self.perm *= 2

    def _noise2d(self, x, y):
        """Хеш-функция для получения псевдослучайного значения в точке."""
        n = int(x) + int(y) * 57
        n = (n << 13) ^ n
        idx = abs(n) % 256
        return self.perm[idx] / 255.0

    def _smoothed(self, x, y):
        corners = (self._noise2d(x-1, y-1) + self._noise2d(x+1, y-1) +
                   self._noise2d(x-1, y+1) + self._noise2d(x+1, y+1)) / 16.0
        sides = (self._noise2d(x-1, y) + self._noise2d(x+1, y) +
                 self._noise2d(x, y-1) + self._noise2d(x, y+1)) / 8.0
        center = self._noise2d(x, y) / 4.0
        return corners + sides + center

    def _interpolated(self, x, y):
        ix, iy = int(x), int(y)
        fx, fy = x - ix, y - iy

        # Cosine interpolation
        fx = (1 - math.cos(fx * math.pi)) * 0.5
        fy = (1 - math.cos(fy * math.pi)) * 0.5

        v1 = self._smoothed(ix, iy)
        v2 = self._smoothed(ix + 1, iy)
        v3 = self._smoothed(ix, iy + 1)
        v4 = self._smoothed(ix + 1, iy + 1)

        i1 = v1 * (1 - fx) + v2 * fx
        i2 = v3 * (1 - fx) + v4 * fx

        return i1 * (1 - fy) + i2 * fy

    def octave_noise(self, x, y, octaves=4, persistence=0.5, scale=0.02):
        """Многооктавный шум."""
        total = 0
        frequency = scale
        amplitude = 1
        max_value = 0

        for _ in range(octaves):
            total += self._interpolated(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2

        return total / max_value


# === Типы тайлов ===
TILE_GROUND = 0
TILE_WALL = 1
TILE_WATER = 2
TILE_RAMP = 3
TILE_TITAN_ORE = 4
TILE_PLASMA_GEYSER = 5


class TileMap:
    """Тайловая карта мира."""

    def __init__(self, width=MAP_WIDTH_TILES, height=MAP_HEIGHT_TILES,
                 seed=None, spawn_count=2, resource_density=1.0):
        self.width = width
        self.height = height
        self.seed = seed if seed else random.randint(0, 999999)
        self.spawn_count = max(2, min(4, int(spawn_count)))
        self.resource_density = float(resource_density)

        # Данные карты
        self.tiles = [[TILE_GROUND] * width for _ in range(height)]
        self.heights = [[HEIGHT_LOW] * width for _ in range(height)]
        self.ramps = [[False] * width for _ in range(height)]

        # Позиции ресурсов
        self.titan_deposits = []   # [(tx, ty), ...]
        self.plasma_geysers = []   # [(tx, ty), ...]

        # Позиции спавна (базы игроков)
        self.spawn_points = []  # [(tx, ty), ...]

        # Кэш отрисовки
        self._surface_cache = {}
        self._dirty = True

        # Генерация
        self.generate()

    # ========================================
    # ГЕНЕРАЦИЯ (инкрементальная)
    # ========================================

    def generate(self):
        """Синхронная генерация (для тестов и прямого использования)."""
        for _ in self.generate_iter():
            pass

    def generate_iter(self):
        """Инкрементальная генерация карты.

        Генератор: yield (progress 0..1, localization_key_or_None).
        Между yield'ами выполняется ограниченный объём работы,
        чтобы экран загрузки мог перерисовываться между шагами.
        """
        rng = random.Random(self.seed)
        noise = SimplexNoise(self.seed)
        noise2 = SimplexNoise(self.seed + 42)

        # --- Шаг 1: высоты и препятствия (полосами по 16 рядов) ---
        band = 16
        y = 0
        while y < self.height:
            y_end = min(y + band, self.height)
            for ty in range(y, y_end):
                for tx in range(self.width):
                    h = noise.octave_noise(tx, ty, octaves=5, persistence=0.5, scale=0.015)
                    w = noise2.octave_noise(tx, ty, octaves=3, persistence=0.6, scale=0.03)

                    if h < 0.35:
                        self.heights[ty][tx] = HEIGHT_LOW
                    elif h < 0.6:
                        self.heights[ty][tx] = HEIGHT_MID
                    else:
                        self.heights[ty][tx] = HEIGHT_HIGH

                    if w > 0.72 and h > 0.3:
                        self.tiles[ty][tx] = TILE_WALL

                    if h < 0.2 and w < 0.5:
                        self.tiles[ty][tx] = TILE_WATER
            y = y_end
            yield 0.45 * (y / self.height), 'loading.terrain'

        # --- Шаг 2: рампы (полосами) ---
        y = 1
        while y < self.height - 1:
            y_end = min(y + band, self.height - 1)
            for ty in range(y, y_end):
                for tx in range(1, self.width - 1):
                    if self.tiles[ty][tx] != TILE_GROUND:
                        continue
                    h = self.heights[ty][tx]
                    has_lower = False
                    has_higher = False
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nh = self.heights[ty + dy][tx + dx]
                        if nh < h and self.tiles[ty + dy][tx + dx] == TILE_GROUND:
                            has_lower = True
                        if nh > h and self.tiles[ty + dy][tx + dx] == TILE_GROUND:
                            has_higher = True
                    if (has_lower or has_higher) and rng.random() < 0.3:
                        self.ramps[ty][tx] = True
                        self.tiles[ty][tx] = TILE_RAMP
            y = y_end
            yield 0.45 + 0.10 * (y / self.height), 'loading.ramps'

        # --- Шаг 3: спавн-зоны ---
        self._place_spawn_points(rng)
        for sx, sy in self.spawn_points:
            self._clear_spawn_zone(sx, sy, radius=15)
        yield 0.58, 'loading.spawn_zones'

        # --- Шаг 4: ресурсы (аккуратные симметричные патчи) ---
        for progress, _ in self._generate_resources_iter(rng):
            yield 0.58 + 0.32 * progress, 'loading.resources'

        # --- Шаг 5: связность спавнов ---
        self._ensure_connectivity()
        yield 1.0, 'loading.connectivity'

        self._dirty = True

    def _place_spawn_points(self, rng):
        """Расставить спавны: 2 — по диагонали, 3 — треугольник, 4 — по углам."""
        margin = 25
        w, h = self.width, self.height

        if self.spawn_count == 2:
            candidates = [(margin, margin), (w - margin, h - margin)]
        elif self.spawn_count == 3:
            cx, cy = w // 2, h // 2
            r = int(min(w, h) * 0.33)
            candidates = []
            for i in range(3):
                a = -math.pi / 2 + i * 2 * math.pi / 3
                candidates.append((int(cx + math.cos(a) * r),
                                   int(cy + math.sin(a) * r)))
        else:
            candidates = [(margin, margin), (w - margin, margin),
                          (w - margin, h - margin), (margin, h - margin)]

        self.spawn_points = []
        for px, py in candidates:
            px = max(margin, min(w - margin - 1, px))
            py = max(margin, min(h - margin - 1, py))
            self.spawn_points.append(self._nearest_open_tile(px, py))

    def _nearest_open_tile(self, tx, ty, max_radius=30):
        """Спиральный поиск ближайшего проходимого тайла."""
        if self.is_walkable(tx, ty):
            return (tx, ty)
        for r in range(1, max_radius):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height \
                            and self.is_walkable(nx, ny):
                        return (nx, ny)
        return (tx, ty)

    def _clear_spawn_zone(self, cx, cy, radius=15):
        """Очистить зону вокруг спавна — плоская земля."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < self.width and 0 <= y < self.height:
                    if dx * dx + dy * dy <= radius * radius:
                        self.tiles[y][x] = TILE_GROUND
                        self.heights[y][x] = HEIGHT_MID
                        self.ramps[y][x] = False

    # ========================================
    # РЕСУРСЫ: аккуратные патчи с симметрией
    # ========================================

    def _generate_resources_iter(self, rng):
        """Размещение ресурсов.

        Правила:
        - компактные круглые патчи титана (центр + кольца), а не аморфные блобы;
        - зеркальная симметрия кластеров относительно центра карты (честность);
        - минимальная дистанция между кластерами и от баз;
        - гейзеры плазмы парами возле кластеров;
        - гарантированная база у каждого спавна (кольцо титана + 2 гейзера).
        """
        self.titan_deposits = []
        self.plasma_geysers = []

        w, h = self.width, self.height
        margin = 14
        base_keepout = 19          # дистанция нейтральных кластеров от баз
        cluster_min_dist = 16      # минимальная дистанция между кластерами

        ring1 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        ring2 = [(2, 0), (-2, 0), (0, 2), (0, -2), (2, 1), (-2, -1),
                 (1, 2), (-1, -2), (2, -1), (-2, 1), (1, -2), (-1, 2)]

        def patch_tiles(cx, cy, size):
            """Компактный патч: центр + заполненные кольца."""
            tiles = [(cx, cy)]
            for ring in (ring1, ring2):
                offsets = ring[:]
                rng.shuffle(offsets)
                for dx, dy in offsets:
                    if len(tiles) >= size:
                        break
                    tiles.append((cx + dx, cy + dy))
            return tiles

        def near_spawn(cx, cy, keepout):
            for sx, sy in self.spawn_points:
                if (cx - sx) ** 2 + (cy - sy) ** 2 < keepout * keepout:
                    return True
            return False

        def placeable(cx, cy):
            if not (margin <= cx < w - margin and margin <= cy < h - margin):
                return False
            if self.tiles[cy][cx] != TILE_GROUND:
                return False
            return not near_spawn(cx, cy, base_keepout)

        def place_titan_patch(cx, cy, size):
            count = 0
            for tx, ty in patch_tiles(cx, cy, size):
                if 0 <= tx < w and 0 <= ty < h and self.tiles[ty][tx] == TILE_GROUND:
                    self.tiles[ty][tx] = TILE_TITAN_ORE
                    self.titan_deposits.append((tx, ty))
                    count += 1
            return count

        def place_geyser_pair(cx, cy, dx, dy):
            """Пара гейзеров рядом друг с другом."""
            count = 0
            for ox, oy in ((dx, dy), (dx + 1, dy)):
                tx, ty = cx + ox, cy + oy
                if 0 <= tx < w and 0 <= ty < h and self.tiles[ty][tx] == TILE_GROUND:
                    self.tiles[ty][tx] = TILE_PLASMA_GEYSER
                    self.plasma_geysers.append((tx, ty))
                    count += 1
            return count

        # --- 1) Гарантированная база у каждого спавна ---
        for sx, sy in self.spawn_points:
            # Ровное кольцо из 8 тайлов титана
            base_rot = rng.uniform(0, math.pi / 4)
            for i in range(8):
                angle = base_rot + (i / 8) * math.pi * 2
                tx = int(round(sx + math.cos(angle) * 10))
                ty = int(round(sy + math.sin(angle) * 10))
                if 0 <= tx < w and 0 <= ty < h and self.tiles[ty][tx] == TILE_GROUND:
                    self.tiles[ty][tx] = TILE_TITAN_ORE
                    self.titan_deposits.append((tx, ty))

            # Два гейзера на безопасной дистанции
            for angle in (base_rot + 0.7, base_rot + 0.7 + math.pi):
                tx = int(round(sx + math.cos(angle) * 7))
                ty = int(round(sy + math.sin(angle) * 7))
                if 0 <= tx < w and 0 <= ty < h and self.tiles[ty][tx] == TILE_GROUND:
                    self.tiles[ty][tx] = TILE_PLASMA_GEYSER
                    self.plasma_geysers.append((tx, ty))
        yield 0.25, None

        # --- 2) Нейтральные кластеры с зеркальной симметрией ---
        area = w * h
        base_clusters = max(4, int(area / 6400))
        num_clusters = max(2, int(base_clusters * self.resource_density))

        placed_centers = []
        attempts = 0
        max_attempts = num_clusters * 80

        while len(placed_centers) < num_clusters and attempts < max_attempts:
            attempts += 1
            cx = rng.randint(margin, w - margin - 1)
            cy = rng.randint(margin, h - margin - 1)

            if not placeable(cx, cy):
                continue
            if any((cx - ox) ** 2 + (cy - oy) ** 2 < cluster_min_dist ** 2
                   for ox, oy in placed_centers):
                continue

            # Зеркальная пара относительно центра карты
            mx, my = w - 1 - cx, h - 1 - cy
            mirror_ok = (mx, my) != (cx, cy) and placeable(mx, my) and \
                all((mx - ox) ** 2 + (my - oy) ** 2 >= cluster_min_dist ** 2
                    for ox, oy in placed_centers)

            size = rng.randint(6, 9)
            place_titan_patch(cx, cy, size)
            if mirror_ok:
                place_titan_patch(mx, my, size)

            # Гейзеры возле кластера
            gdx = rng.randint(-4, 3)
            gdy = rng.randint(-4, 3)
            place_geyser_pair(cx, cy, gdx, gdy)
            if mirror_ok:
                place_geyser_pair(mx, my, -gdx - 1, gdy)

            placed_centers.append((cx, cy))
            if mirror_ok:
                placed_centers.append((mx, my))

            progress = len(placed_centers) / max(1, num_clusters)
            yield 0.25 + 0.75 * min(1.0, progress), None

        yield 1.0, None

    def _ensure_connectivity(self):
        """Проверить что все спавны связаны путями. Если нет — прорубаем коридор."""
        if len(self.spawn_points) < 2:
            return

        from core.pathfinding import path_exists
        sx1, sy1 = self.spawn_points[0]
        for sx2, sy2 in self.spawn_points[1:]:
            if not path_exists(self, sx1, sy1, sx2, sy2):
                self._carve_corridor(sx1, sy1, sx2, sy2)

    def _carve_corridor(self, x1, y1, x2, y2, width=3):
        """Прорубить проходимый коридор между двумя точками."""
        steps = max(abs(x2 - x1), abs(y2 - y1))
        if steps == 0:
            return

        for i in range(steps + 1):
            t = i / steps
            cx = int(x1 + (x2 - x1) * t)
            cy = int(y1 + (y2 - y1) * t)

            for dx in range(-width, width + 1):
                for dy in range(-width, width + 1):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        if self.tiles[y][x] in (TILE_WALL, TILE_WATER):
                            self.tiles[y][x] = TILE_GROUND
                            self.heights[y][x] = HEIGHT_MID

    # === Запросы к карте ===

    def is_walkable(self, tx, ty):
        """Можно ли ходить по этому тайлу?"""
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return False
        return self.tiles[ty][tx] not in (TILE_WALL, TILE_WATER)

    def is_buildable(self, tx, ty, size=1):
        """Можно ли построить здание на этом тайле (или группе тайлов)?"""
        for dy in range(size):
            for dx in range(size):
                x, y = tx + dx, ty + dy
                if x >= self.width or y >= self.height:
                    return False
                if self.tiles[y][x] != TILE_GROUND:
                    return False
        return True

    def is_ramp(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return False
        return self.ramps[ty][tx]

    def get_height(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return 0
        return self.heights[ty][tx]

    def get_tile(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return TILE_WALL
        return self.tiles[ty][tx]

    def world_to_tile(self, wx, wy):
        """Мировые координаты → тайловые."""
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def tile_to_world(self, tx, ty):
        """Тайловые координаты → мировые (центр тайла)."""
        return tx * TILE_SIZE + TILE_SIZE // 2, ty * TILE_SIZE + TILE_SIZE // 2

    # === Рендер ===

    def get_tile_color(self, tx, ty):
        """Получить цвет тайла для отрисовки."""
        tile = self.get_tile(tx, ty)
        height = self.get_height(tx, ty)

        if tile == TILE_WALL:
            return COLOR_WALL
        elif tile == TILE_WATER:
            return COLOR_WATER
        elif tile == TILE_RAMP:
            return COLOR_RAMP
        elif tile == TILE_TITAN_ORE:
            return COLOR_TITAN_ORE
        elif tile == TILE_PLASMA_GEYSER:
            return COLOR_PLASMA_GEYSER
        else:
            # Земля — яркость зависит от высоты
            if height == HEIGHT_LOW:
                return COLOR_LOW_GROUND
            elif height == HEIGHT_MID:
                return COLOR_MID_GROUND
            else:
                return COLOR_HIGH_GROUND

    def render(self, surface, camera):
        """Отрисовка видимых тайлов."""
        start_x, start_y, end_x, end_y = camera.get_visible_tiles()

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                color = self.get_tile_color(tx, ty)

                # Мировые координаты тайла
                wx = tx * TILE_SIZE
                wy = ty * TILE_SIZE

                # Экранные координаты
                sx, sy = camera.world_to_screen(wx, wy)
                size = int(TILE_SIZE * camera.zoom)

                if size < 1:
                    size = 1

                pygame.draw.rect(surface, color, (int(sx), int(sy), size, size))

                # Рисуем границу для рамп (чтобы были видны подъёмы)
                if self.is_ramp(tx, ty):
                    pygame.draw.rect(surface, (100, 120, 100),
                                     (int(sx), int(sy), size, size), 1)

    def render_grid(self, surface, camera, color=(40, 50, 45)):
        """Отрисовка сетки поверх карты."""
        start_x, start_y, end_x, end_y = camera.get_visible_tiles()

        for ty in range(start_y, end_y + 1):
            wy = ty * TILE_SIZE
            sx1, sy1 = camera.world_to_screen(start_x * TILE_SIZE, wy)
            sx2, sy2 = camera.world_to_screen(end_x * TILE_SIZE, wy)
            pygame.draw.line(surface, color, (int(sx1), int(sy1)), (int(sx2), int(sy2)))

        for tx in range(start_x, end_x + 1):
            wx = tx * TILE_SIZE
            sx1, sy1 = camera.world_to_screen(wx, start_y * TILE_SIZE)
            sx2, sy2 = camera.world_to_screen(wx, end_y * TILE_SIZE)
            pygame.draw.line(surface, color, (int(sx1), int(sy1)), (int(sx2), int(sy2)))
