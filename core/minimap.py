"""
botyaraRTS - core/minimap.py
Миникарта с интерактивностью и пингами.
"""
import pygame
from settings import *


class Minimap:
    def __init__(self, tilemap, screen_w, screen_h):
        self.tilemap = tilemap
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Размер и позиция (выровнены по высоте с центральной панелью HUD)
        self.size = 200
        self.padding = 10
        self.update_position()

        # Масштаб: мир → миникарта
        self.scale_x = self.size / MAP_WIDTH
        self.scale_y = self.size / MAP_HEIGHT

        # Кэш ландшафта (рисуется один раз)
        self.terrain_surface = pygame.Surface((self.size, self.size))
        self._render_terrain()

        # Пинги
        self.pings = []  # [(world_x, world_y, color, timer), ...]
        self.ping_duration = 3.0

        # Взаимодействие
        self.dragging = False

    def update_position(self):
        """Обновить позицию миникарты на экране."""
        self.size = 200
        self.x = self.padding
        self.y = self.screen_h - self.size - 10
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.scale_x = self.size / MAP_WIDTH
        self.scale_y = self.size / MAP_HEIGHT

    def _render_terrain(self):
        """Отрисовка ландшафта на кэшированную поверхность."""
        self.terrain_surface.fill(COLOR_MINIMAP_BG)

        for ty in range(self.tilemap.height):
            for tx in range(self.tilemap.width):
                color = self.tilemap.get_tile_color(tx, ty)
                mx = int(tx * self.scale_x * TILE_SIZE)
                my = int(ty * self.scale_y * TILE_SIZE)
                w = max(1, int(self.scale_x * TILE_SIZE))
                h = max(1, int(self.scale_y * TILE_SIZE))
                pygame.draw.rect(self.terrain_surface, color, (mx, my, w, h))

    def world_to_minimap(self, wx, wy):
        """Мировые координаты → координаты на миникарте."""
        mx = wx * self.scale_x + self.x
        my = wy * self.scale_y + self.y
        return mx, my

    def minimap_to_world(self, mx, my):
        """Координаты на миникарте → мировые координаты."""
        wx = (mx - self.x) / self.scale_x
        wy = (my - self.y) / self.scale_y
        return wx, wy

    def is_point_on_minimap(self, sx, sy):
        """Проверить, находится ли экранная точка на миникарте."""
        return self.rect.collidepoint(sx, sy)

    def handle_click(self, sx, sy, camera, button='left'):
        """Обработка клика по миникарте."""
        if not self.is_point_on_minimap(sx, sy):
            return False

        wx, wy = self.minimap_to_world(sx, sy)
        wx = max(0, min(wx, MAP_WIDTH))
        wy = max(0, min(wy, MAP_HEIGHT))

        if button == 'left':
            camera.center_on(wx, wy)
            self.dragging = True
        return True

    def handle_drag(self, sx, sy, camera):
        """Перетаскивание камеры по миникарте."""
        if not self.dragging:
            return
        wx, wy = self.minimap_to_world(sx, sy)
        wx = max(0, min(wx, MAP_WIDTH))
        wy = max(0, min(wy, MAP_HEIGHT))
        camera.center_on(wx, wy, instant=True)

    def handle_release(self):
        self.dragging = False

    def add_ping(self, world_x, world_y, color=COLOR_UI_WARNING):
        """Добавить пинг на миникарту."""
        self.pings.append({
            'x': world_x,
            'y': world_y,
            'color': color,
            'timer': self.ping_duration,
            'max_timer': self.ping_duration,
        })

    def update(self, dt):
        """Обновление пингов."""
        self.pings = [p for p in self.pings if p['timer'] > 0]
        for p in self.pings:
            p['timer'] -= dt

    def render(self, surface, camera, entities=None, fog_of_war=None):
        """Отрисовка миникарты."""
        # Фон ландшафта
        surface.blit(self.terrain_surface, (self.x, self.y))

        # Рамка
        pygame.draw.rect(surface, COLOR_MINIMAP_BORDER, self.rect, 2)

        # Юниты и здания
        if entities:
            for entity in entities:
                # Если есть туман войны — показываем только видимых
                if fog_of_war and not fog_of_war.is_visible_world(entity.x, entity.y):
                    if hasattr(entity, 'player_id') and entity.player_id != 0:
                        continue

                mx, my = self.world_to_minimap(entity.x, entity.y)
                if self.rect.collidepoint(mx, my):
                    color = COLOR_MINIMAP_FRIENDLY
                    if hasattr(entity, 'player_id'):
                        if entity.player_id != 0:  # Не наш
                            color = COLOR_MINIMAP_ENEMY

                    size = 2
                    if hasattr(entity, 'is_building') and entity.is_building:
                        size = 4

                    pygame.draw.rect(surface, color,
                                     (int(mx) - size // 2, int(my) - size // 2, size, size))

        # Ресурсы
        for tx, ty in self.tilemap.titan_deposits:
            wx, wy = self.tilemap.tile_to_world(tx, ty)
            mx, my = self.world_to_minimap(wx, wy)
            if self.rect.collidepoint(mx, my):
                pygame.draw.rect(surface, COLOR_MINIMAP_RESOURCE,
                                 (int(mx), int(my), 1, 1))

        # Viewport (белая рамка камеры)
        vis = camera.get_visible_rect()
        vx, vy = self.world_to_minimap(vis.x, vis.y)
        vw = vis.width * self.scale_x
        vh = vis.height * self.scale_y
        pygame.draw.rect(surface, COLOR_MINIMAP_VIEWPORT,
                         (int(vx), int(vy), int(vw), int(vh)), 1)

        # Пинги
        for ping in self.pings:
            mx, my = self.world_to_minimap(ping['x'], ping['y'])
            if self.rect.collidepoint(mx, my):
                alpha = ping['timer'] / ping['max_timer']
                radius = int(8 * (1 - alpha) + 3)
                ping_color = ping['color']
                pygame.draw.circle(surface, ping_color, (int(mx), int(my)), radius, 2)
                if alpha > 0.5:
                    pygame.draw.circle(surface, ping_color, (int(mx), int(my)), 2)

    def resize(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.update_position()
