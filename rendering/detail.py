"""
botyaraRTS - rendering/detail.py
Общие визуальные эффекты высокого уровня: дым и искры повреждений,
свечение щитов. Накладываются поверх базовых рендеров сущностей.
"""
import math
import pygame
from settings import *
from rendering.colors import SciFiPalette, brighten


def _entity_phase(entity):
    """Стабильная псевдофаза сущности (детерминированный «рандом» визуала)."""
    return (entity.id * 2654435761) % 1000 / 1000.0


class DamageFX:
    """Дым и искры у повреждённых сущностей (юниты и здания)."""

    @staticmethod
    def render(surface, camera, entity, anim_time):
        frac = entity.hp / entity.max_hp if entity.max_hp > 0 else 1.0
        if frac >= 0.65 or not entity.alive:
            return

        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        radius = max(4, sr.width // 2)
        phase = _entity_phase(entity)

        # Интенсивность: чем меньше HP, тем больше дыма
        if frac < 0.30:
            puff_count = 3
            fire = True
        elif frac < 0.50:
            puff_count = 2
            fire = True
        else:
            puff_count = 1
            fire = False

        zoom = camera.zoom
        for i in range(puff_count):
            # Дым поднимается и дрейфует
            speed = 0.5 + phase * 0.4 + i * 0.23
            t = (anim_time * speed + phase * 3 + i * 1.7) % 2.0  # 0..2
            rise = t * radius * 1.1
            drift = math.sin(anim_time * 1.3 + phase * 6 + i * 2.1) * radius * 0.35

            px = cx + int(drift) - radius // 3
            py = cy - int(rise) + radius // 4
            pr = max(2, int((3 + i + t * 2.5) * zoom))
            alpha = max(0, int(70 - t * 32))

            if alpha > 4 and pr > 1:
                puff = pygame.Surface((pr * 4, pr * 4), pygame.SRCALPHA)
                # Тёмный дым у повреждённой техники, серый — у зданий
                smoke_col = (40, 38, 36) if not entity.is_building else (120, 118, 115)
                pygame.draw.circle(puff, (*smoke_col, alpha),
                                   (pr * 2, pr * 2), pr)
                surface.blit(puff, (px - pr * 2, py - pr * 2))

            # Огонёк в эпицентре при критических повреждениях
            if fire and i == 0:
                flicker = (math.sin(anim_time * 11 + phase * 9) + 1) / 2
                fr = max(1, int(radius * 0.22 * (0.6 + flicker * 0.5)))
                fa = int(120 + flicker * 80)
                fire_surf = pygame.Surface((fr * 4, fr * 4), pygame.SRCALPHA)
                pygame.draw.circle(fire_surf, (*SciFiPalette.FIRE_ORANGE, fa),
                                   (fr * 2, fr * 2), fr)
                pygame.draw.circle(fire_surf, (*SciFiPalette.FIRE_CORE, min(255, fa + 60)),
                                   (fr * 2, fr * 2), max(1, fr // 2))
                surface.blit(fire_surf, (cx - fr * 2, cy - fr * 2 - radius // 6))

        # Редкие искры при сильном повреждении
        if frac < 0.35:
            spark_phase = (anim_time * 3 + phase * 7) % 1.0
            if spark_phase < 0.35:
                ang = phase * math.tau + spark_phase * 5
                dist = radius * (0.4 + spark_phase)
                sx = cx + int(math.cos(ang) * dist)
                sy = cy + int(math.sin(ang) * dist * 0.6) - radius // 4
                sr_ = max(1, int(2 * zoom))
                sa = int(255 * (1 - spark_phase / 0.35))
                pygame.draw.circle(surface, (255, 200, 80, sa) if sa < 255 else (255, 200, 80),
                                   (sx, sy), sr_)


class ShieldFX:
    """Полупрозрачный щит вокруг сущностей с энергощитом."""

    @staticmethod
    def render(surface, camera, entity, anim_time):
        if not entity.alive or entity.shield <= 0:
            return
        max_shield = getattr(entity, 'max_shield', 0)
        if max_shield <= 0:
            return

        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        frac = entity.shield / max_shield
        cx, cy = sr.centerx, sr.centery
        radius = int(max(sr.width, sr.height) * 0.75) + 3

        pulse = (math.sin(anim_time * 4 + entity.id) + 1) / 2
        alpha = int(12 + frac * 26 + pulse * 8)

        shield_surf = pygame.Surface((radius * 2 + 6, radius * 2 + 6), pygame.SRCALPHA)
        rect = shield_surf.get_rect()
        pygame.draw.ellipse(shield_surf, (*SciFiPalette.SHIELD_BLUE, alpha), rect)
        # Яркая дуга по верху
        pygame.draw.arc(shield_surf,
                        (*brighten(SciFiPalette.SHIELD_BLUE, 60), min(255, alpha * 3)),
                        rect.inflate(-4, -4), math.pi * 0.15, math.pi * 0.85, 2)
        surface.blit(shield_surf, (cx - radius - 3, cy - radius - 3))
