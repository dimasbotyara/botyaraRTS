"""
botyaraRTS - ui/ping_system.py
Пинги на карте и миникарте.
"""
import pygame
import math
from settings import *


class PingSystem:
    """Система пингов."""

    def __init__(self):
        self.pings = []  # [{x, y, type, timer, max_timer}, ...]
        self.ping_types = {
            'attention': {'color': COLOR_UI_WARNING, 'text': '!'},
            'retreat': {'color': COLOR_UI_DANGER, 'text': '←'},
        }

    def add_ping(self, world_x, world_y, ping_type='attention'):
        """Добавить пинг."""
        info = self.ping_types.get(ping_type, self.ping_types['attention'])
        self.pings.append({
            'x': world_x,
            'y': world_y,
            'type': ping_type,
            'color': info['color'],
            'text': info['text'],
            'timer': 3.0,
            'max_timer': 3.0,
        })

    def update(self, dt):
        for ping in self.pings:
            ping['timer'] -= dt
        self.pings = [p for p in self.pings if p['timer'] > 0]

    def render(self, surface, camera):
        """Отрисовка пингов в мире."""
        for ping in self.pings:
            sx, sy = camera.world_to_screen(ping['x'], ping['y'])
            alpha = ping['timer'] / ping['max_timer']

            # Пульсирующий круг
            radius = int(20 + 15 * (1 - alpha))
            color = ping['color']

            if alpha > 0.3:
                pygame.draw.circle(surface, color, (int(sx), int(sy)), radius, 2)
                inner_r = max(3, int(radius * 0.3))
                pygame.draw.circle(surface, color, (int(sx), int(sy)), inner_r)

    def render_on_minimap(self, minimap):
        """Передать пинги на миникарту."""
        for ping in self.pings:
            minimap.add_ping(ping['x'], ping['y'], ping['color'])
