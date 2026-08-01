"""
botyaraRTS - rendering/terrain_renderer.py
Рендер тайлов ландшафта: земля, стены, вода, ресурсы, рампы.
Каждый тайл — мини-пиксельарт из геометрии.
"""
import pygame
import math
import random
from settings import *
from rendering.colors import SciFiPalette, lerp_color, brighten, darken, shimmer_color
from core.tilemap import (TILE_GROUND, TILE_WALL, TILE_WATER,
                           TILE_RAMP, TILE_TITAN_ORE, TILE_PLASMA_GEYSER)


class TerrainRenderer:
    """Рендер ландшафта с кэшированием."""

    def __init__(self, tilemap):
        self.tilemap = tilemap

        # Кэш тайлов — рисуем каждый тайл один раз в Surface
        self.tile_cache = {}  # (tx, ty) -> Surface
        self.cache_zoom = 1.0

        # Сид для псевдослучайных деталей каждого тайла
        self.detail_rng = random.Random(tilemap.seed)
        self.tile_details = {}  # (tx, ty) -> {список деталей}
        self._generate_tile_details()

        # Анимация (вода, ресурсы)
        self.anim_time = 0

    def _generate_tile_details(self):
        """Предгенерация деталей для каждого тайла (камешки, трещины, травинки)."""
        rng = self.detail_rng
        for ty in range(self.tilemap.height):
            for tx in range(self.tilemap.width):
                tile = self.tilemap.get_tile(tx, ty)
                height = self.tilemap.get_height(tx, ty)

                details = []

                if tile == TILE_GROUND:
                    # Травинки / мелкие камешки
                    num = rng.randint(0, 4)
                    for _ in range(num):
                        details.append({
                            'type': rng.choice(['pebble', 'grass', 'crack']),
                            'x': rng.randint(2, TILE_SIZE - 3),
                            'y': rng.randint(2, TILE_SIZE - 3),
                            'size': rng.randint(1, 3),
                            'shade': rng.randint(-15, 15),
                        })

                elif tile == TILE_WALL:
                    # Трещины, кристаллы в стенах
                    num = rng.randint(1, 3)
                    for _ in range(num):
                        details.append({
                            'type': rng.choice(['crack', 'crystal', 'ridge']),
                            'x': rng.randint(3, TILE_SIZE - 4),
                            'y': rng.randint(3, TILE_SIZE - 4),
                            'size': rng.randint(2, 5),
                            'shade': rng.randint(-10, 10),
                            'angle': rng.randint(0, 360),
                        })

                elif tile == TILE_TITAN_ORE:
                    # Кристаллы титана
                    num = rng.randint(2, 5)
                    for _ in range(num):
                        details.append({
                            'type': 'crystal',
                            'x': rng.randint(4, TILE_SIZE - 5),
                            'y': rng.randint(4, TILE_SIZE - 5),
                            'size': rng.randint(3, 7),
                            'angle': rng.randint(0, 360),
                            'height': rng.randint(4, 10),
                        })

                elif tile == TILE_PLASMA_GEYSER:
                    # Точки плазмы
                    num = rng.randint(2, 4)
                    for _ in range(num):
                        details.append({
                            'type': 'vent',
                            'x': rng.randint(6, TILE_SIZE - 7),
                            'y': rng.randint(6, TILE_SIZE - 7),
                            'size': rng.randint(2, 5),
                        })

                self.tile_details[(tx, ty)] = details

    def update(self, dt):
        """Обновление анимации."""
        self.anim_time += dt

    def render(self, surface, camera):
        """Отрисовка видимых тайлов."""
        start_x, start_y, end_x, end_y = camera.get_visible_tiles()
        zoom = camera.zoom

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                wx = tx * TILE_SIZE
                wy = ty * TILE_SIZE
                sx, sy = camera.world_to_screen(wx, wy)
                size = int(TILE_SIZE * zoom)

                if size < 1:
                    continue

                # Отрисовка тайла
                self._render_tile(surface, tx, ty, int(sx), int(sy), size, zoom)

    def _render_tile(self, surface, tx, ty, sx, sy, size, zoom):
        """Отрисовка одного тайла."""
        tile = self.tilemap.get_tile(tx, ty)
        height = self.tilemap.get_height(tx, ty)

        if tile == TILE_GROUND:
            self._render_ground(surface, tx, ty, sx, sy, size, height, zoom)
        elif tile == TILE_WALL:
            self._render_wall(surface, tx, ty, sx, sy, size, height, zoom)
        elif tile == TILE_WATER:
            self._render_water(surface, tx, ty, sx, sy, size, zoom)
        elif tile == TILE_RAMP:
            self._render_ramp(surface, tx, ty, sx, sy, size, height, zoom)
        elif tile == TILE_TITAN_ORE:
            self._render_titan_ore(surface, tx, ty, sx, sy, size, zoom)
        elif tile == TILE_PLASMA_GEYSER:
            self._render_plasma_geyser(surface, tx, ty, sx, sy, size, zoom)

    def _render_ground(self, surface, tx, ty, sx, sy, size, height, zoom):
        """Земля с деталями."""
        # Базовый цвет по высоте
        if height == 0:
            base = SciFiPalette.GROUND_DARK
        elif height == 1:
            base = SciFiPalette.GROUND_MID
        else:
            base = SciFiPalette.GROUND_LIGHT

        # Рисуем основу
        pygame.draw.rect(surface, base, (sx, sy, size, size))

        # Лёгкая текстура — перепад яркости для «зернистости»
        if size >= 8:
            half = size // 2
            shade = darken(base, 5)
            # Четвертинки разного оттенка
            if (tx + ty) % 2 == 0:
                pygame.draw.rect(surface, shade, (sx, sy, half, half))
                pygame.draw.rect(surface, shade, (sx + half, sy + half, half, half))

        # Граница высоты — тёмная линия для объёма
        if height > 0:
            # Проверяем соседей — если сосед ниже, рисуем край обрыва
            for dx, dy, edge in [(0, 1, 'bottom'), (1, 0, 'right'),
                                   (0, -1, 'top'), (-1, 0, 'left')]:
                ntx, nty = tx + dx, ty + dy
                if 0 <= ntx < self.tilemap.width and 0 <= nty < self.tilemap.height:
                    nh = self.tilemap.get_height(ntx, nty)
                    if nh < height and not self.tilemap.is_ramp(ntx, nty):
                        edge_color = darken(base, 35)
                        if edge == 'bottom':
                            pygame.draw.line(surface, edge_color,
                                             (sx, sy + size - 1), (sx + size, sy + size - 1), 2)
                        elif edge == 'top':
                            pygame.draw.line(surface, edge_color,
                                             (sx, sy), (sx + size, sy), 2)
                        elif edge == 'right':
                            pygame.draw.line(surface, edge_color,
                                             (sx + size - 1, sy), (sx + size - 1, sy + size), 2)
                        elif edge == 'left':
                            pygame.draw.line(surface, edge_color,
                                             (sx, sy), (sx, sy + size), 2)

        # Детали
        if size >= 12:
            details = self.tile_details.get((tx, ty), [])
            scale = size / TILE_SIZE
            for d in details:
                dx = int(d['x'] * scale) + sx
                dy = int(d['y'] * scale) + sy
                ds = max(1, int(d['size'] * scale))

                if d['type'] == 'pebble':
                    c = brighten(base, d['shade'])
                    pygame.draw.circle(surface, c, (dx, dy), ds)
                elif d['type'] == 'grass':
                    c = brighten(base, d['shade'] + 15)
                    pygame.draw.line(surface, c, (dx, dy), (dx, dy - ds * 2), 1)
                elif d['type'] == 'crack':
                    c = darken(base, 20)
                    pygame.draw.line(surface, c, (dx, dy), (dx + ds, dy + ds), 1)

    def _render_wall(self, surface, tx, ty, sx, sy, size, height, zoom):
        """Стена/скала с 3D-эффектом."""
        # Основа
        base = SciFiPalette.ROCK_MID
        pygame.draw.rect(surface, base, (sx, sy, size, size))

        # Верхняя грань (светлая)
        top_h = max(2, size // 5)
        top_color = SciFiPalette.ROCK_LIGHT
        pygame.draw.rect(surface, top_color, (sx, sy, size, top_h))

        # Боковая грань (тёмная) — правая и нижняя
        side_w = max(2, size // 6)
        side_color = SciFiPalette.ROCK_DARK
        pygame.draw.rect(surface, side_color,
                         (sx + size - side_w, sy + top_h, side_w, size - top_h))
        pygame.draw.rect(surface, side_color,
                         (sx, sy + size - side_w, size - side_w, side_w))

        # Детали
        if size >= 12:
            details = self.tile_details.get((tx, ty), [])
            scale = size / TILE_SIZE
            for d in details:
                dx = int(d['x'] * scale) + sx
                dy = int(d['y'] * scale) + sy
                ds = max(1, int(d['size'] * scale))

                if d['type'] == 'crack':
                    c = darken(base, 25)
                    angle = d.get('angle', 0)
                    ex = dx + int(math.cos(math.radians(angle)) * ds * 2)
                    ey = dy + int(math.sin(math.radians(angle)) * ds * 2)
                    pygame.draw.line(surface, c, (dx, dy), (ex, ey), 1)
                elif d['type'] == 'crystal':
                    c = brighten(base, 30)
                    pygame.draw.polygon(surface, c, [
                        (dx, dy - ds), (dx - ds // 2, dy + ds // 2),
                        (dx + ds // 2, dy + ds // 2)
                    ])
                elif d['type'] == 'ridge':
                    c = brighten(base, 15)
                    pygame.draw.line(surface, c, (dx, dy), (dx + ds, dy), 2)

        # Обводка
        pygame.draw.rect(surface, darken(base, 30), (sx, sy, size, size), 1)

    def _render_water(self, surface, tx, ty, sx, sy, size, zoom):
        """Вода с анимацией волн."""
        # Базовый цвет
        t = self.anim_time
        wave = math.sin(t * 1.5 + tx * 0.5 + ty * 0.3) * 0.5 + 0.5

        base = lerp_color(SciFiPalette.WATER_DEEP, SciFiPalette.WATER_SHALLOW, wave * 0.3)
        pygame.draw.rect(surface, base, (sx, sy, size, size))

        # Волны (горизонтальные линии)
        if size >= 8:
            wave_color = lerp_color(SciFiPalette.WATER_SHALLOW, SciFiPalette.WATER_SURFACE,
                                    wave)
            num_waves = max(1, size // 8)
            for i in range(num_waves):
                wy = sy + int((i + 0.5) * size / num_waves)
                offset = int(math.sin(t * 2 + i + tx * 0.8) * size * 0.1)
                pygame.draw.line(surface, wave_color,
                                 (sx + offset, wy), (sx + size + offset, wy), 1)

        # Блик
        if size >= 12:
            bx = sx + int((math.sin(t * 0.7 + tx) + 1) * size * 0.3)
            by = sy + int((math.cos(t * 0.5 + ty) + 1) * size * 0.2)
            bsize = max(2, size // 8)
            highlight = brighten(SciFiPalette.WATER_SURFACE, 40)
            pygame.draw.circle(surface, highlight, (bx, by), bsize)

    def _render_ramp(self, surface, tx, ty, sx, sy, size, height, zoom):
        """Рампа (переход между высотами) со стрелкой направления."""
        # Градиент от тёмного к светлому
        base_low = SciFiPalette.GROUND_DARK
        base_high = SciFiPalette.GROUND_LIGHT
        base_mid = lerp_color(base_low, base_high, 0.5)

        pygame.draw.rect(surface, base_mid, (sx, sy, size, size))

        # Определяем направление рампы
        direction = None
        for dx, dy, dir_name in [(0, -1, 'up'), (0, 1, 'down'),
                                    (-1, 0, 'left'), (1, 0, 'right')]:
            ntx, nty = tx + dx, ty + dy
            if 0 <= ntx < self.tilemap.width and 0 <= nty < self.tilemap.height:
                nh = self.tilemap.get_height(ntx, nty)
                if nh > height:
                    direction = dir_name
                    break

        # Градиентные полосы по направлению
        if size >= 8:
            num_stripes = max(2, size // 6)
            for i in range(num_stripes):
                t = i / num_stripes
                c = lerp_color(base_low, base_high, t)

                if direction == 'up':
                    y_pos = sy + size - int(t * size)
                    pygame.draw.line(surface, c, (sx, y_pos), (sx + size, y_pos), 2)
                elif direction == 'down':
                    y_pos = sy + int(t * size)
                    pygame.draw.line(surface, c, (sx, y_pos), (sx + size, y_pos), 2)
                elif direction == 'left':
                    x_pos = sx + size - int(t * size)
                    pygame.draw.line(surface, c, (x_pos, sy), (x_pos, sy + size), 2)
                elif direction == 'right':
                    x_pos = sx + int(t * size)
                    pygame.draw.line(surface, c, (x_pos, sy), (x_pos, sy + size), 2)

        # Стрелка направления
        if size >= 16:
            cx, cy = sx + size // 2, sy + size // 2
            arrow_size = size // 4
            arrow_color = brighten(base_mid, 50)

            if direction == 'up':
                pts = [(cx, cy - arrow_size), (cx - arrow_size, cy + arrow_size // 2),
                       (cx + arrow_size, cy + arrow_size // 2)]
            elif direction == 'down':
                pts = [(cx, cy + arrow_size), (cx - arrow_size, cy - arrow_size // 2),
                       (cx + arrow_size, cy - arrow_size // 2)]
            elif direction == 'left':
                pts = [(cx - arrow_size, cy), (cx + arrow_size // 2, cy - arrow_size),
                       (cx + arrow_size // 2, cy + arrow_size)]
            elif direction == 'right':
                pts = [(cx + arrow_size, cy), (cx - arrow_size // 2, cy - arrow_size),
                       (cx - arrow_size // 2, cy + arrow_size)]
            else:
                pts = None

            if pts:
                pygame.draw.polygon(surface, arrow_color, pts)

        # Обводка
        ramp_border = brighten(base_mid, 20)
        pygame.draw.rect(surface, ramp_border, (sx, sy, size, size), 1)

    def _render_titan_ore(self, surface, tx, ty, sx, sy, size, zoom):
        """Титановая руда — светящиеся кристаллы."""
        # Земля под рудой
        base = SciFiPalette.GROUND_MID
        pygame.draw.rect(surface, base, (sx, sy, size, size))

        # Свечение
        t = self.anim_time
        glow_color = shimmer_color(SciFiPalette.TITAN_ORE, t + tx * 0.5, speed=2, intensity=25)

        # Легкое свечение на фоне
        if size >= 8:
            glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*glow_color, 20), (0, 0, size, size))
            surface.blit(glow_surf, (sx, sy))

        # Кристаллы
        details = self.tile_details.get((tx, ty), [])
        scale = size / TILE_SIZE
        for d in details:
            if d['type'] != 'crystal':
                continue
            dx = int(d['x'] * scale) + sx
            dy = int(d['y'] * scale) + sy
            ds = max(2, int(d['size'] * scale))
            dh = max(3, int(d.get('height', 6) * scale))

            # Кристалл — вытянутый ромб
            crystal_color = shimmer_color(SciFiPalette.TITAN_ORE, t + d['x'] * 0.1)
            pts = [
                (dx, dy - dh),           # верх
                (dx - ds // 2, dy),      # лево
                (dx, dy + ds // 3),      # низ
                (dx + ds // 2, dy),      # право
            ]
            pygame.draw.polygon(surface, crystal_color, pts)
            # Блик
            bright = brighten(crystal_color, 60)
            pygame.draw.line(surface, bright, pts[0],
                             ((pts[0][0] + pts[3][0]) // 2, (pts[0][1] + pts[3][1]) // 2), 1)

        # Рамка ресурса
        if size >= 12:
            pygame.draw.rect(surface, darken(SciFiPalette.TITAN_ORE, 30),
                             (sx, sy, size, size), 1)

    def _render_plasma_geyser(self, surface, tx, ty, sx, sy, size, zoom):
        """Плазменный гейзер — пульсирующая энергия."""
        # Земля
        base = darken(SciFiPalette.GROUND_MID, 10)
        pygame.draw.rect(surface, base, (sx, sy, size, size))

        t = self.anim_time
        cx, cy = sx + size // 2, sy + size // 2

        # Центральная воронка
        vent_r = max(3, size // 4)
        vent_color = lerp_color(SciFiPalette.PLASMA_SOURCE, SciFiPalette.PLASMA_GLOW,
                                (math.sin(t * 3) + 1) / 2)

        # Внешнее свечение (пульсирующее)
        pulse = (math.sin(t * 2.5) + 1) / 2
        glow_r = int(vent_r * (1.5 + pulse * 0.5))
        glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        glow_alpha = int(20 + pulse * 25)
        pygame.draw.circle(glow_surf, (*SciFiPalette.PLASMA_GLOW, glow_alpha),
                           (size // 2, size // 2), glow_r)
        surface.blit(glow_surf, (sx, sy))

        # Кольца
        ring_r = int(vent_r * (1.2 + pulse * 0.3))
        pygame.draw.circle(surface, darken(vent_color, 20), (cx, cy), ring_r, 1)

        # Центр
        pygame.draw.circle(surface, vent_color, (cx, cy), vent_r)
        core_color = brighten(vent_color, 50)
        pygame.draw.circle(surface, core_color, (cx, cy), max(1, vent_r // 2))

        # Пузырьки / вентиляционные отверстия
        details = self.tile_details.get((tx, ty), [])
        scale = size / TILE_SIZE
        for d in details:
            if d['type'] != 'vent':
                continue
            dx = int(d['x'] * scale) + sx
            dy = int(d['y'] * scale) + sy
            ds = max(1, int(d['size'] * scale))
            bubble_phase = (t * 2 + d['x'] * 0.5) % 3
            if bubble_phase < 1:
                bc = brighten(SciFiPalette.PLASMA_GLOW, 30)
                pygame.draw.circle(surface, bc, (dx, dy), ds)

        # Рамка ресурса
        if size >= 12:
            pygame.draw.rect(surface, darken(SciFiPalette.PLASMA_SOURCE, 20),
                             (sx, sy, size, size), 1)

    def render_grid(self, surface, camera, color=None):
        """Отрисовка сетки поверх карты."""
        if color is None:
            color = (40, 50, 45, 80)

        start_x, start_y, end_x, end_y = camera.get_visible_tiles()
        zoom = camera.zoom
        tile_size = int(TILE_SIZE * zoom)

        if tile_size < 4:
            return  # Слишком мелко

        grid_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        for ty in range(start_y, end_y + 1):
            wy = ty * TILE_SIZE
            sx1, sy1 = camera.world_to_screen(start_x * TILE_SIZE, wy)
            sx2, sy2 = camera.world_to_screen(end_x * TILE_SIZE, wy)
            pygame.draw.line(grid_surf, color, (int(sx1), int(sy1)), (int(sx2), int(sy2)))

        for tx in range(start_x, end_x + 1):
            wx = tx * TILE_SIZE
            sx1, sy1 = camera.world_to_screen(wx, start_y * TILE_SIZE)
            sx2, sy2 = camera.world_to_screen(wx, end_y * TILE_SIZE)
            pygame.draw.line(grid_surf, color, (int(sx1), int(sy1)), (int(sx2), int(sy2)))

        surface.blit(grid_surf, (0, 0))
