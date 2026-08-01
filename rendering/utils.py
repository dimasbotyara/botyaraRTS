"""
botyaraRTS - rendering/utils.py
Утилиты рисования: примитивы с антиалиасингом, тени, свечение.
"""
import pygame
import math
from rendering.colors import *


def draw_shadow(surface, x, y, width, height, offset_x=2, offset_y=3):
    """Нарисовать тень под объектом."""
    shadow = pygame.Surface((width + 4, height + 4), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 40),
                        (2, 2, width, int(height * 0.4)))
    surface.blit(shadow, (x - 2 + offset_x, y + height - int(height * 0.2) + offset_y))


def draw_glow(surface, x, y, radius, color, alpha=40):
    """Нарисовать свечение (несколько полупрозрачных кругов)."""
    glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = radius * 2
    for i in range(3):
        r = radius + i * (radius // 2)
        a = max(5, alpha - i * 15)
        c = (color[0], color[1], color[2], a)
        pygame.draw.circle(glow, c, (center, center), r)
    surface.blit(glow, (x - radius * 2, y - radius * 2))


def draw_neon_line(surface, color, start, end, width=2, glow_width=6):
    """Неоновая линия со свечением."""
    # Свечение
    glow_color = (color[0], color[1], color[2], 40)
    glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.line(glow_surf, glow_color, start, end, glow_width)
    surface.blit(glow_surf, (0, 0))
    # Основная линия
    pygame.draw.line(surface, color, start, end, width)
    # Блик (яркий центр)
    bright = brighten(color, 80)
    pygame.draw.line(surface, bright, start, end, max(1, width - 1))


def draw_neon_circle(surface, color, center, radius, width=2):
    """Неоновый круг со свечением."""
    glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
    gc = (radius * 3 // 2, radius * 3 // 2)
    glow_color = (color[0], color[1], color[2], 30)
    pygame.draw.circle(glow, glow_color, gc, radius + 4)
    surface.blit(glow, (center[0] - radius * 3 // 2, center[1] - radius * 3 // 2))
    pygame.draw.circle(surface, color, center, radius, width)
    bright = brighten(color, 60)
    pygame.draw.circle(surface, bright, center, max(1, radius - 1), max(1, width - 1))


def draw_neon_rect(surface, color, rect, width=2):
    """Неоновый прямоугольник."""
    glow_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
    glow_color = (color[0], color[1], color[2], 25)
    pygame.draw.rect(glow_surf, glow_color, (0, 0, rect.width + 8, rect.height + 8),
                     border_radius=4)
    surface.blit(glow_surf, (rect.x - 4, rect.y - 4))
    pygame.draw.rect(surface, color, rect, width, border_radius=2)


def draw_thick_polygon(surface, color, points, width=2):
    """Полигон с обводкой."""
    if len(points) < 3:
        return
    pygame.draw.polygon(surface, darken(color, 20), points)
    pygame.draw.polygon(surface, color, points, width)


def draw_chevron(surface, color, cx, cy, size, angle=0):
    """Шеврон (стрелка-указатель направления)."""
    rad = math.radians(angle)
    points = []
    # Три точки шеврона
    offsets = [
        (0, -size),      # кончик
        (-size * 0.6, size * 0.4),  # лево
        (0, size * 0.1),            # центр зад
        (size * 0.6, size * 0.4),   # право
    ]
    for ox, oy in offsets:
        rx = ox * math.cos(rad) - oy * math.sin(rad)
        ry = ox * math.sin(rad) + oy * math.cos(rad)
        points.append((cx + rx, cy + ry))

    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, brighten(color, 40), points, 1)


def draw_exhaust(surface, x, y, angle, length=8, spread=4, time_val=0):
    """Выхлоп двигателя (частицы)."""
    rad = math.radians(angle + 180)  # Противоположное направление
    for i in range(3):
        offset = (i + 1) * (length / 3)
        spread_x = math.sin(time_val * 10 + i * 2) * spread * (i + 1) / 3
        px = x + math.cos(rad) * offset + spread_x
        py = y + math.sin(rad) * offset
        alpha = max(30, 150 - i * 50)
        r = max(1, 4 - i)
        color = lerp_color(SciFiPalette.FIRE_CORE, SciFiPalette.FIRE_ORANGE, i / 3)
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, alpha), (r * 2, r * 2), r)
        surface.blit(glow, (int(px - r * 2), int(py - r * 2)))


def draw_health_ring(surface, cx, cy, radius, hp_ratio, color_full, color_low):
    """Кольцо здоровья вокруг юнита."""
    if hp_ratio >= 1.0:
        return
    ring_color = lerp_color(color_low, color_full, hp_ratio)
    angle_end = hp_ratio * 360
    # Рисуем дугу через точки
    points = []
    segments = max(4, int(angle_end / 10))
    for i in range(segments + 1):
        a = math.radians(-90 + (angle_end * i / segments))
        px = cx + math.cos(a) * radius
        py = cy + math.sin(a) * radius
        points.append((px, py))

    if len(points) >= 2:
        pygame.draw.lines(surface, ring_color, False, points, 2)


def draw_stripe_pattern(surface, rect, color1, color2, stripe_width=4, angle=45):
    """Паттерн полос (для строящихся зданий)."""
    clip = surface.get_clip()
    surface.set_clip(rect)
    rad = math.radians(angle)
    step = stripe_width * 2
    for i in range(-rect.height, rect.width + rect.height, step):
        x1 = rect.x + i
        y1 = rect.y
        x2 = x1 - int(rect.height * math.tan(rad))
        y2 = rect.bottom
        pygame.draw.line(surface, color2, (x1, y1), (x2, y2), stripe_width // 2)
    surface.set_clip(clip)


def rotate_point(cx, cy, x, y, angle_deg):
    """Повернуть точку вокруг центра."""
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    dx = x - cx
    dy = y - cy
    rx = dx * cos_a - dy * sin_a + cx
    ry = dx * sin_a + dy * cos_a + cy
    return rx, ry


def rotate_points(cx, cy, points, angle_deg):
    """Повернуть список точек."""
    return [rotate_point(cx, cy, px, py, angle_deg) for px, py in points]
