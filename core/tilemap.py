"""
botyaraRTS - core/tilemap.py
Тайловая карта с процедурной генерацией (Perlin Noise),
высотами, стенами, рампами и ресурсами.
"""
import pygame
import random
import math
from settings import *


# === Простой Perlin-подобный шум без внешних зависимостей ===
class SimplexNoise:
    """Упрощённый value noise с интерполяцией для генерации карт."""

    def __init__(self, seed=None):
        self.seed = seed if seed else random.randint(0, 999999)
        random.seed(self.seed)
        self.perm = list(range(256))
        random.shuffle(self.perm)
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

    def __init__(self, width=MAP_WIDTH_TILES, height=MAP_HEIGHT_TILES, seed=None):
        self.width = width
        self.height = height
        self.seed = seed if seed else random.randint(0, 999999)

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

    def generate(self):
        """Процедурная генерация карты."""
        random.seed(self.seed)
        noise = SimplexNoise(self.seed)
        noise2 = SimplexNoise(self.seed + 42)

        # Шаг 1: Генерация высот через шум
        for y in range(self.height):
            for x in range(self.width):
                # Основной шум для высот
                h = noise.octave_noise(x, y, octaves=5, persistence=0.5, scale=0.015)

                # Дополнительный шум для стен/препятствий
                w = noise2.octave_noise(x, y, octaves=3, persistence=0.6, scale=0.03)

                # Определяем высоту
                if h < 0.35:
                    self.heights[y][x] = HEIGHT_LOW
                elif h < 0.6:
                    self.heights[y][x] = HEIGHT_MID
                else:
                    self.heights[y][x] = HEIGHT_HIGH

                # Стены (скалы)
                if w > 0.72 and h > 0.3:
                    self.tiles[y][x] = TILE_WALL

                # Вода в низинах
                if h < 0.2 and w < 0.5:
                    self.tiles[y][x] = TILE_WATER

        # Шаг 2: Генерация рамп (переходы между высотами)
        self._generate_ramps()

        # Шаг 3: Спавн-зоны (противоположные углы карты)
        margin = 25
        self.spawn_points = [
            (margin, margin),
            (self.width - margin, self.height - margin),
        ]
        # Очищаем зоны вокруг спавнов
        for sx, sy in self.spawn_points:
            self._clear_spawn_zone(sx, sy, radius=15)

        # Шаг 4: Ресурсы
        self._generate_resources()

        # Шаг 5: Проверка проходимости между спавнами
        self._ensure_connectivity()

        self._dirty = True

    def _generate_ramps(self):
        """Создание рамп на границах разных высот."""
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y][x] != TILE_GROUND:
                    continue

                h = self.heights[y][x]
                # Проверяем соседей — если рядом есть тайл другой высоты
                has_lower = False
                has_higher = False
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        nh = self.heights[ny][nx]
                        if nh < h and self.tiles[ny][nx] == TILE_GROUND:
                            has_lower = True
                        if nh > h and self.tiles[ny][nx] == TILE_GROUND:
                            has_higher = True

                # Рампа на границе высот (с шансом, чтобы не было слишком много)
                if (has_lower or has_higher) and random.random() < 0.3:
                    self.ramps[y][x] = True
                    self.tiles[y][x] = TILE_RAMP

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

    def _generate_resources(self):
        """Размещение ресурсов (титан и плазма)."""
        self.titan_deposits = []
        self.plasma_geysers = []

        # Генерируем кластеры ресурсов
        num_clusters = 16
        random.seed(self.seed + 100)

        for _ in range(num_clusters):
            cx = random.randint(20, self.width - 20)
            cy = random.randint(20, self.height - 20)

            # Не ставим ресурсы на стены или воду
            if self.tiles[cy][cx] != TILE_GROUND:
                continue

            # Кластер титана (5-8 тайлов)
            for i in range(random.randint(5, 8)):
                dx = random.randint(-3, 3)
                dy = random.randint(-3, 3)
                tx, ty = cx + dx, cy + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if self.tiles[ty][tx] == TILE_GROUND:
                        self.tiles[ty][tx] = TILE_TITAN_ORE
                        self.titan_deposits.append((tx, ty))

            # 1-2 гейзера плазмы рядом
            for _ in range(random.randint(1, 2)):
                dx = random.randint(-5, 5)
                dy = random.randint(-5, 5)
                tx, ty = cx + dx, cy + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if self.tiles[ty][tx] == TILE_GROUND:
                        self.tiles[ty][tx] = TILE_PLASMA_GEYSER
                        self.plasma_geysers.append((tx, ty))

        # Гарантированные ресурсы рядом со спавнами
        for sx, sy in self.spawn_points:
            for i in range(8):
                angle = (i / 8) * math.pi * 2
                r = random.randint(8, 12)
                tx = int(sx + math.cos(angle) * r)
                ty = int(sy + math.sin(angle) * r)
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if self.tiles[ty][tx] == TILE_GROUND:
                        self.tiles[ty][tx] = TILE_TITAN_ORE
                        self.titan_deposits.append((tx, ty))

            # Плазма рядом со спавном
            for i in range(2):
                angle = (i / 2) * math.pi * 2 + 0.5
                r = random.randint(6, 10)
                tx = int(sx + math.cos(angle) * r)
                ty = int(sy + math.sin(angle) * r)
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if self.tiles[ty][tx] == TILE_GROUND:
                        self.tiles[ty][tx] = TILE_PLASMA_GEYSER
                        self.plasma_geysers.append((tx, ty))

    def _ensure_connectivity(self):
        """Проверить что все спавны связаны путями. Если нет — прорубаем коридор."""
        if len(self.spawn_points) < 2:
            return

        from core.pathfinding import path_exists
        sx1, sy1 = self.spawn_points[0]
        sx2, sy2 = self.spawn_points[1]

        if not path_exists(self, sx1, sy1, sx2, sy2):
            # Прорубаем прямой коридор
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
