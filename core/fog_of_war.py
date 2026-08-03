"""
botyaraRTS - core/fog_of_war.py
Туман войны с тремя состояниями: неисследовано, исследовано, видимо.
"""
import pygame
from settings import *


# Состояния тумана
FOG_STATE_UNEXPLORED = 0
FOG_STATE_EXPLORED = 1
FOG_STATE_VISIBLE = 2


class FogOfWar:
    def __init__(self, map_width_tiles, map_height_tiles):
        self.width = map_width_tiles
        self.height = map_height_tiles

        # Массив текущей видимости (обновляется каждый тик)
        self.visibility = [[FOG_STATE_UNEXPLORED] * self.width for _ in range(self.height)]

        # Массив "когда-либо исследовано"
        self.explored = [[False] * self.width for _ in range(self.height)]

        # Поверхность для рендера тумана
        self.fog_surface = None
        self._fog_tile_size = 4  # Рисуем туман крупнее для производительности
        self._needs_update = True

        # Таймер обновления
        self.update_timer = 0

        # Кэш радиусов обзора
        self._vision_circles = {}

    def _get_vision_circle(self, radius):
        """Кэшированный список тайлов в радиусе обзора."""
        if radius in self._vision_circles:
            return self._vision_circles[radius]

        tiles = []
        r_sq = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r_sq:
                    tiles.append((dx, dy))

        self._vision_circles[radius] = tiles
        return tiles

    def update(self, dt, vision_sources):
        """
        Обновить видимость.
        vision_sources: список (tile_x, tile_y, vision_radius)
        """
        self.update_timer += dt
        if self.update_timer < VISION_UPDATE_INTERVAL:
            return
        self.update_timer = 0

        # Сбрасываем видимость (но не explored)
        for y in range(self.height):
            for x in range(self.width):
                if self.visibility[y][x] == FOG_STATE_VISIBLE:
                    self.visibility[y][x] = FOG_STATE_EXPLORED if self.explored[y][x] else FOG_STATE_UNEXPLORED

        # Применяем видимость от юнитов и зданий
        for vx, vy, radius in vision_sources:
            circle = self._get_vision_circle(radius)
            for dx, dy in circle:
                tx, ty = vx + dx, vy + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    self.visibility[ty][tx] = FOG_STATE_VISIBLE
                    self.explored[ty][tx] = True

        self._needs_update = True

    def is_visible(self, tx, ty):
        """Видим ли тайл прямо сейчас?"""
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return False
        return self.visibility[ty][tx] == FOG_STATE_VISIBLE

    def is_explored(self, tx, ty):
        """Был ли тайл когда-либо исследован?"""
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return False
        return self.explored[ty][tx]

    def is_visible_world(self, wx, wy):
        """Видимость по мировым координатам."""
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)
        return self.is_visible(tx, ty)

    def _get_explored_surf(self, size):
        """Получить кэшированный полупрозрачный тайл для исследованных областей."""
        if not hasattr(self, '_explored_surfaces'):
            self._explored_surfaces = {}
        if size not in self._explored_surfaces:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 160))
            self._explored_surfaces[size] = surf
        return self._explored_surfaces[size]

    def render(self, surface, camera):
        """Отрисовка тумана войны поверх карты."""
        start_x, start_y, end_x, end_y = camera.get_visible_tiles()
        zoom = camera.zoom
        size = int(TILE_SIZE * zoom)

        if size < 1:
            return

        explored_surf = self._get_explored_surf(size)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                if 0 <= ty < self.height and 0 <= tx < self.width:
                    state = self.visibility[ty][tx]
                else:
                    state = FOG_STATE_UNEXPLORED

                if state == FOG_STATE_VISIBLE:
                    continue  # Прозрачный

                sx, sy = camera.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                isx, isy = int(sx), int(sy)

                if state == FOG_STATE_UNEXPLORED:
                    pygame.draw.rect(surface, (0, 0, 0), (isx, isy, size, size))
                elif state == FOG_STATE_EXPLORED:
                    surface.blit(explored_surf, (isx, isy))

    def reveal_all(self):
        """Открыть всю карту (для дебага)."""
        for y in range(self.height):
            for x in range(self.width):
                self.visibility[y][x] = FOG_STATE_VISIBLE
                self.explored[y][x] = True
