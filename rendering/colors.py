"""
botyaraRTS - rendering/colors.py
Палитры цветов, утилиты для работы с цветом.
Sci-fi неоновая палитра.
"""
import math
import random


def lerp_color(c1, c2, t):
    """Линейная интерполяция между двумя цветами."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def brighten(color, amount=30):
    """Осветлить цвет."""
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )


def darken(color, amount=30):
    """Затемнить цвет."""
    return (
        max(0, color[0] - amount),
        max(0, color[1] - amount),
        max(0, color[2] - amount),
    )


def alpha_color(color, alpha):
    """Добавить альфа-канал."""
    return (color[0], color[1], color[2], alpha)


def pulse_color(color, time_val, speed=2.0, intensity=30):
    """Пульсирующий цвет (для свечения)."""
    pulse = (math.sin(time_val * speed) + 1) / 2  # 0..1
    amount = int(pulse * intensity)
    return brighten(color, amount)


def shimmer_color(color, time_val, speed=3.0, intensity=20):
    """Мерцающий цвет (для ресурсов)."""
    shimmer = (math.sin(time_val * speed) + math.sin(time_val * speed * 1.7)) / 4 + 0.5
    amount = int(shimmer * intensity)
    return brighten(color, amount)


def team_color_light(team_color):
    """Светлый вариант командного цвета (для бликов)."""
    return brighten(team_color, 80)


def team_color_dark(team_color):
    """Тёмный вариант командного цвета (для теней)."""
    return darken(team_color, 60)


def team_color_glow(team_color):
    """Цвет свечения (полупрозрачный яркий)."""
    return (
        min(255, team_color[0] + 100),
        min(255, team_color[1] + 100),
        min(255, team_color[2] + 100),
        80,
    )


# === Sci-Fi палитра ===
class SciFiPalette:
    """Цвета в стиле sci-fi."""

    # Металлы
    STEEL = (140, 148, 155)
    STEEL_LIGHT = (175, 182, 190)
    STEEL_DARK = (90, 95, 102)
    TITANIUM = (180, 185, 195)
    GUNMETAL = (75, 80, 88)
    CHROME = (200, 205, 215)

    # Неон
    NEON_BLUE = (0, 180, 255)
    NEON_GREEN = (0, 255, 120)
    NEON_RED = (255, 50, 60)
    NEON_PURPLE = (180, 50, 255)
    NEON_ORANGE = (255, 150, 0)
    NEON_CYAN = (0, 255, 220)
    NEON_YELLOW = (255, 240, 0)

    # Энергия
    PLASMA_BLUE = (80, 150, 255)
    PLASMA_CORE = (200, 220, 255)
    ENERGY_GREEN = (50, 255, 100)
    ENERGY_YELLOW = (255, 230, 80)
    FIRE_ORANGE = (255, 120, 20)
    FIRE_RED = (255, 40, 10)
    FIRE_CORE = (255, 220, 150)

    # Террейн
    GROUND_DARK = (28, 38, 32)
    GROUND_MID = (42, 55, 45)
    GROUND_LIGHT = (58, 75, 62)
    ROCK_DARK = (50, 48, 45)
    ROCK_MID = (72, 68, 62)
    ROCK_LIGHT = (95, 90, 82)
    WATER_DEEP = (15, 35, 65)
    WATER_SHALLOW = (25, 55, 90)
    WATER_SURFACE = (40, 75, 120)

    # Ресурсы
    TITAN_ORE = (210, 195, 80)
    TITAN_GLOW = (255, 240, 120)
    PLASMA_SOURCE = (60, 140, 240)
    PLASMA_GLOW = (120, 180, 255)

    # UI
    SHIELD_BLUE = (60, 160, 255)
    HEAL_GREEN = (80, 255, 120)
    DAMAGE_RED = (255, 80, 60)

    # Тени
    SHADOW = (0, 0, 0, 60)
    SHADOW_DARK = (0, 0, 0, 100)
