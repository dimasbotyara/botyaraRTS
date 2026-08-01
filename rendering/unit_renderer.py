"""
botyaraRTS - rendering/unit_renderer.py
Базовый рендер юнитов: тени, выделение, HP, стойка, общие эффекты.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *


class UnitRenderer:
    """Базовые методы отрисовки для всех юнитов."""

    @staticmethod
    def get_team_color(player_id):
        return PLAYER_COLORS[player_id % len(PLAYER_COLORS)]

    @staticmethod
    def render_shadow(surface, cx, cy, width, height, zoom):
        """Тень под юнитом."""
        shadow_w = int(width * 0.9)
        shadow_h = int(height * 0.3)
        shadow_surf = pygame.Surface((shadow_w + 4, shadow_h + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 35),
                            (2, 2, shadow_w, shadow_h))
        surface.blit(shadow_surf,
                     (cx - shadow_w // 2 - 2, cy + int(height * 0.35)))

    @staticmethod
    def render_selection_indicator(surface, cx, cy, radius, zoom, team_color):
        """Кольцо выделения под юнитом."""
        sel_w = int(radius * 2.2)
        sel_h = int(radius * 0.8)
        sel_surf = pygame.Surface((sel_w + 8, sel_h + 8), pygame.SRCALPHA)

        # Внешний эллипс (свечение)
        glow_color = (*team_color, 30)
        pygame.draw.ellipse(sel_surf, glow_color, (0, 0, sel_w + 8, sel_h + 8))

        # Основной эллипс
        pygame.draw.ellipse(sel_surf, (*COLOR_SELECTION_BOX, 180),
                            (4, 4, sel_w, sel_h), 2)

        surface.blit(sel_surf,
                     (cx - sel_w // 2 - 4, cy + int(radius * 0.3) - 4))

    @staticmethod
    def render_stance_icon(surface, cx, cy, radius, stance, zoom):
        """Маленькая иконка стойки."""
        icon_size = max(4, int(6 * zoom))
        ix = cx + int(radius * 0.8)
        iy = cy - int(radius * 0.8)

        if stance == 'AGGRESSIVE':
            # Красный мечик
            pygame.draw.line(surface, SciFiPalette.NEON_RED,
                             (ix - icon_size, iy + icon_size),
                             (ix + icon_size, iy - icon_size), 2)
            pygame.draw.line(surface, SciFiPalette.NEON_RED,
                             (ix - icon_size // 2, iy - icon_size // 2),
                             (ix + icon_size // 2, iy + icon_size // 2), 1)
        elif stance == 'DEFENSIVE':
            # Синий щит
            pygame.draw.circle(surface, SciFiPalette.NEON_BLUE,
                               (ix, iy), icon_size, 2)
        elif stance == 'HOLD_POSITION':
            # Жёлтый якорь
            pygame.draw.circle(surface, SciFiPalette.NEON_YELLOW,
                               (ix, iy), icon_size // 2)
            pygame.draw.line(surface, SciFiPalette.NEON_YELLOW,
                             (ix, iy), (ix, iy + icon_size), 2)

    @staticmethod
    def render_state_indicator(surface, cx, cy, radius, state, zoom, anim_time):
        """Индикатор текущего состояния (MOVE/ATTACK/etc)."""
        if state == 'MOVE':
            # Маленькие следы
            pass  # Рисуются трассой в отдельном методе
        elif state == 'ATTACK':
            # Красная вспышка
            pulse = (math.sin(anim_time * 8) + 1) / 2
            if pulse > 0.6:
                flash = pygame.Surface((int(radius * 3), int(radius * 3)), pygame.SRCALPHA)
                pygame.draw.circle(flash, (255, 50, 50, int(30 * pulse)),
                                   (int(radius * 1.5), int(radius * 1.5)),
                                   int(radius * 1.2))
                surface.blit(flash, (cx - int(radius * 1.5), cy - int(radius * 1.5)))

    @staticmethod
    def render_hp_bar(surface, cx, cy, radius, hp, max_hp, zoom,
                      shield=0, max_shield=0):
        """Полоска HP над юнитом."""
        if hp >= max_hp and shield >= max_shield:
            return

        bar_w = int(radius * 2.4)
        bar_h = max(3, int(4 * zoom))
        bx = cx - bar_w // 2
        by = cy - int(radius * 1.3)

        # Фон
        pygame.draw.rect(surface, (20, 0, 0), (bx - 1, by - 1, bar_w + 2, bar_h + 2))

        # HP
        ratio = hp / max_hp if max_hp > 0 else 0
        if ratio > 0.6:
            hp_color = SciFiPalette.HEAL_GREEN
        elif ratio > 0.3:
            hp_color = SciFiPalette.ENERGY_YELLOW
        else:
            hp_color = SciFiPalette.DAMAGE_RED

        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, hp_color, (bx, by, fill_w, bar_h))

        # Щит
        if max_shield > 0:
            shield_h = max(2, bar_h - 1)
            shield_y = by - shield_h - 2
            pygame.draw.rect(surface, (10, 20, 40),
                             (bx - 1, shield_y - 1, bar_w + 2, shield_h + 2))
            s_ratio = shield / max_shield if max_shield > 0 else 0
            s_fill = int(bar_w * s_ratio)
            if s_fill > 0:
                pygame.draw.rect(surface, SciFiPalette.SHIELD_BLUE,
                                 (bx, shield_y, s_fill, shield_h))

    @staticmethod
    def render_carry_indicator(surface, cx, cy, radius, resource_type, zoom):
        """Индикатор несомого ресурса (для рабочего)."""
        dot_r = max(2, int(3 * zoom))
        dy = cy - int(radius * 1.5)
        if resource_type == 'titan':
            color = SciFiPalette.TITAN_ORE
        else:
            color = SciFiPalette.PLASMA_GLOW
        pygame.draw.circle(surface, color, (cx, dy), dot_r)
        # Свечение
        glow = pygame.Surface((dot_r * 4, dot_r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 40), (dot_r * 2, dot_r * 2), dot_r * 2)
        surface.blit(glow, (cx - dot_r * 2, dy - dot_r * 2))
