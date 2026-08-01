"""
botyaraRTS - rendering/projectile_renderer.py
Рендер снарядов, мин, взрывов и спецэффектов.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *


class ProjectileRenderer:
    """Рендер всех снарядов и эффектов."""

    @staticmethod
    def render_projectile(surface, camera, projectile, anim_time):
        """Трассер / снаряд."""
        if not projectile.alive:
            return

        sx, sy = camera.world_to_screen(projectile.x, projectile.y)
        zoom = camera.zoom

        # За экраном
        if sx < -50 or sx > camera.screen_w + 50 or \
           sy < -50 or sy > camera.screen_h + 50:
            return

        color = projectile.color
        size = max(2, int(3 * zoom))

        # Хвост (трейл)
        trail = projectile.trail
        if trail and len(trail) >= 2:
            for i in range(len(trail) - 1):
                t1x, t1y = camera.world_to_screen(trail[i][0], trail[i][1])
                t2x, t2y = camera.world_to_screen(trail[i + 1][0], trail[i + 1][1])
                alpha = (i + 1) / len(trail)
                trail_w = max(1, int(size * alpha * 0.6))
                trail_color = lerp_color(darken(color, 40), color, alpha)
                pygame.draw.line(surface, trail_color,
                                 (int(t1x), int(t1y)), (int(t2x), int(t2y)), trail_w)

        # Свечение вокруг снаряда
        glow_r = size * 2
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 40), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (int(sx) - glow_r, int(sy) - glow_r))

        # Ядро снаряда
        pygame.draw.circle(surface, brighten(color, 60), (int(sx), int(sy)), size)
        pygame.draw.circle(surface, (255, 255, 255), (int(sx), int(sy)), max(1, size - 1))

    @staticmethod
    def render_mine(surface, camera, mine, anim_time, is_owner=False):
        """Мина на земле (видна только хозяину)."""
        if not mine.alive:
            return

        sx, sy = camera.world_to_screen(mine.x, mine.y)
        zoom = camera.zoom

        if not is_owner:
            return  # Враг не видит мины

        size = max(3, int(5 * zoom))

        # Мерцание
        armed = mine.arm_timer >= mine.arm_time
        if armed:
            pulse = (math.sin(anim_time * 4) + 1) / 2
            color = lerp_color(SciFiPalette.NEON_RED, SciFiPalette.NEON_YELLOW, pulse)
        else:
            color = SciFiPalette.STEEL_DARK

        # Корпус мины
        pygame.draw.circle(surface, SciFiPalette.GUNMETAL, (int(sx), int(sy)), size)
        pygame.draw.circle(surface, color, (int(sx), int(sy)), max(1, size - 2))

        # Индикатор «вооружена»
        if armed and int(anim_time * 3) % 2 == 0:
            pygame.draw.circle(surface, SciFiPalette.NEON_RED, (int(sx), int(sy)),
                               max(1, size // 2))

        # Радиус срабатывания (при наведении, упрощённо)
        trigger_r = int(mine.trigger_radius * zoom)
        trigger_surf = pygame.Surface((trigger_r * 2, trigger_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(trigger_surf, (255, 50, 50, 15), (trigger_r, trigger_r), trigger_r)
        pygame.draw.circle(trigger_surf, (255, 50, 50, 40), (trigger_r, trigger_r), trigger_r, 1)
        surface.blit(trigger_surf, (int(sx) - trigger_r, int(sy) - trigger_r))

    @staticmethod
    def render_explosion(surface, x, y, radius, progress, camera):
        """Взрыв (progress от 0.0 до 1.0)."""
        sx, sy = camera.world_to_screen(x, y)
        zoom = camera.zoom

        current_r = int(radius * zoom * progress)
        if current_r < 1:
            return

        alpha = int(200 * (1 - progress))

        # Несколько слоёв
        explosion_surf = pygame.Surface((current_r * 4, current_r * 4), pygame.SRCALPHA)
        ec = (current_r * 2, current_r * 2)

        # Внешнее кольцо (дым)
        pygame.draw.circle(explosion_surf, (80, 60, 40, max(10, alpha // 3)),
                           ec, current_r)

        # Среднее кольцо (огонь)
        inner_r = int(current_r * 0.7)
        fire_color = lerp_color(SciFiPalette.FIRE_CORE, SciFiPalette.FIRE_RED, progress)
        pygame.draw.circle(explosion_surf, (*fire_color, max(10, alpha // 2)),
                           ec, inner_r)

        # Ядро
        core_r = int(current_r * 0.3)
        pygame.draw.circle(explosion_surf, (*SciFiPalette.FIRE_CORE, alpha),
                           ec, max(1, core_r))

        surface.blit(explosion_surf, (int(sx) - current_r * 2, int(sy) - current_r * 2))

    @staticmethod
    def render_delayed_effect(surface, camera, effect, anim_time):
        """Отложенный эффект (бомба тикает)."""
        if not effect.alive:
            return

        sx, sy = camera.world_to_screen(effect.x, effect.y)
        zoom = camera.zoom

        progress = effect.timer / effect.delay
        radius = int(effect.radius * zoom * 0.5)

        # Пульсирующий предупреждающий круг
        pulse = (math.sin(anim_time * 8 * (1 + progress * 2)) + 1) / 2
        warn_alpha = int(30 + pulse * 60 * progress)

        warn_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        warn_color = lerp_color(SciFiPalette.NEON_YELLOW, SciFiPalette.NEON_RED, progress)
        pygame.draw.circle(warn_surf, (*warn_color, warn_alpha), (radius, radius), radius)
        pygame.draw.circle(warn_surf, (*warn_color, min(255, warn_alpha + 40)),
                           (radius, radius), radius, 2)
        surface.blit(warn_surf, (int(sx) - radius, int(sy) - radius))

        # Таймер в центре
        remaining = effect.delay - effect.timer
        if zoom > 0.5 and remaining > 0:
            font = pygame.font.Font(None, max(14, int(18 * zoom)))
            time_text = font.render(f"{remaining:.1f}", True, warn_color)
            surface.blit(time_text, (int(sx) - time_text.get_width() // 2,
                                     int(sy) - time_text.get_height() // 2))

    @staticmethod
    def render_floating_text(surface, camera, text_obj, anim_time):
        """Всплывающий текст."""
        if not text_obj.alive:
            return

        sx, sy = camera.world_to_screen(text_obj.x, text_obj.y)
        alpha = 1.0 - (text_obj.timer / text_obj.duration)

        font = pygame.font.Font(None, 20)
        text_surf = font.render(text_obj.text, True, text_obj.color)

        if alpha < 1.0:
            text_surf.set_alpha(int(255 * max(0, alpha)))

        # Тень текста
        shadow_surf = font.render(text_obj.text, True, (0, 0, 0))
        shadow_surf.set_alpha(int(128 * max(0, alpha)))
        surface.blit(shadow_surf, (int(sx) + 1, int(sy) + 1))

        surface.blit(text_surf, (int(sx), int(sy)))
