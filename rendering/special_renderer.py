"""
botyaraRTS - rendering/special_renderer.py
Рендер спец-юнитов: Диверсант, Пси-юнит, Заминщик, Суперюнит.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *
from rendering.unit_renderer import UnitRenderer


class SpecialRenderer:
    """Рендер спец-юнитов."""

    @staticmethod
    def render_saboteur(surface, camera, entity, anim_time):
        """Диверсант — теневой силуэт с ножом."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(5, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle

        UnitRenderer.render_shadow(surface, cx, cy, sr.width, sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        alpha = 255
        if entity.is_cloaked:
            alpha = int(35 + 30 * math.sin(anim_time * 2.5))

        # Тело — тёмный ромб
        body_color = (40, 35, 50)
        body_pts = rotate_points(cx, cy, [
            (cx, cy - int(r * 1.1)),
            (cx + int(r * 0.55), cy),
            (cx, cy + int(r * 0.7)),
            (cx - int(r * 0.55), cy),
        ], angle)

        s = pygame.Surface((sr.width * 4, sr.height * 4), pygame.SRCALPHA)
        offset = (sr.width * 2, sr.height * 2)
        shifted = [(p[0] - cx + offset[0], p[1] - cy + offset[1]) for p in body_pts]
        pygame.draw.polygon(s, (*body_color, alpha), shifted)
        pygame.draw.polygon(s, (*brighten(body_color, 40), alpha), shifted, 1)

        # Нож
        knife_len = int(r * 0.9)
        rad = math.radians(angle)
        kx = offset[0] + int(math.cos(rad) * knife_len)
        ky = offset[1] + int(math.sin(rad) * knife_len)
        pygame.draw.line(s, (*SciFiPalette.CHROME, alpha), offset, (kx, ky),
                         max(1, int(2 * zoom)))
        # Остриё
        tip_len = max(2, int(3 * zoom))
        kx2 = kx + int(math.cos(rad) * tip_len)
        ky2 = ky + int(math.sin(rad) * tip_len)
        pygame.draw.line(s, (255, 255, 255, alpha), (kx, ky), (kx2, ky2), 1)

        # Глаза (два красных огонька)
        for side in [-1, 1]:
            ex = offset[0] + int(math.cos(rad + math.pi / 2 * side) * int(r * 0.2))
            ey = offset[1] + int(math.sin(rad + math.pi / 2 * side) * int(r * 0.2)) - int(r * 0.3)
            pygame.draw.circle(s, (*SciFiPalette.NEON_RED, alpha),
                               (int(ex), int(ey)), max(1, int(2 * zoom)))

        # Командная точка
        pygame.draw.circle(s, (*tc, alpha), offset, max(1, int(r * 0.15)))

        surface.blit(s, (cx - offset[0], cy - offset[1]))

        if alpha > 100:
            UnitRenderer.render_hp_bar(surface, cx, cy, r,
                                       entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_psi_unit(surface, camera, entity, anim_time):
        """Пси-юнит — парящий маг с энергетическими кольцами."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = math.sin(anim_time * 2) * 3
        cy_draw = int(cy + hover)
        r = max(6, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)

        UnitRenderer.render_shadow(surface, cx, cy + 4, sr.width, sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Энергетическая аура
        aura_r = int(r * 1.5)
        aura_surf = pygame.Surface((aura_r * 3, aura_r * 3), pygame.SRCALPHA)
        ac = (aura_r * 3 // 2, aura_r * 3 // 2)
        pulse = (math.sin(anim_time * 1.8) + 1) / 2

        # Вращающиеся кольца
        for ring_idx in range(2):
            ring_r = int(aura_r * (0.8 + ring_idx * 0.3))
            ring_angle = anim_time * (60 + ring_idx * 40)
            ring_alpha = int(40 + pulse * 30)
            ring_color = SciFiPalette.NEON_PURPLE if ring_idx == 0 else (200, 100, 255)

            num_dots = 8
            for i in range(num_dots):
                dot_angle = math.radians(ring_angle + i * (360 / num_dots))
                dx = ac[0] + int(math.cos(dot_angle) * ring_r)
                dy = ac[1] + int(math.sin(dot_angle) * ring_r * 0.4)  # эллипс
                dot_r = max(1, int(2 * zoom))
                pygame.draw.circle(aura_surf, (*ring_color, ring_alpha),
                                   (dx, dy), dot_r)

        surface.blit(aura_surf, (cx - aura_r * 3 // 2, cy_draw - aura_r * 3 // 2))

        # Тело — парящая фигура
        body_color = (120, 60, 160)
        body_pts = rotate_points(cx, cy_draw, [
            (cx, cy_draw - int(r * 1.0)),
            (cx + int(r * 0.5), cy_draw - int(r * 0.2)),
            (cx + int(r * 0.6), cy_draw + int(r * 0.6)),
            (cx, cy_draw + int(r * 0.3)),
            (cx - int(r * 0.6), cy_draw + int(r * 0.6)),
            (cx - int(r * 0.5), cy_draw - int(r * 0.2)),
        ], entity.facing_angle)
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, brighten(body_color, 30), body_pts, 1)

        # «Третий глаз» — светящийся шар
        eye_r = max(2, int(r * 0.25))
        eye_pulse = int(pulse * 40)
        eye_color = brighten(SciFiPalette.NEON_PURPLE, eye_pulse)
        pygame.draw.circle(surface, eye_color, (cx, cy_draw - int(r * 0.5)), eye_r)
        # Свечение
        glow_surf = pygame.Surface((eye_r * 6, eye_r * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*eye_color, 50), (eye_r * 3, eye_r * 3), eye_r * 3)
        surface.blit(glow_surf, (cx - eye_r * 3, cy_draw - int(r * 0.5) - eye_r * 3))

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy_draw), max(2, int(r * 0.18)))

        # Полоска энергии
        if hasattr(entity, 'energy') and hasattr(entity, 'max_energy'):
            bar_w = int(r * 2.0)
            bar_h = max(2, int(3 * zoom))
            bx = cx - bar_w // 2
            by = cy_draw + int(r * 1.1)
            pygame.draw.rect(surface, (20, 10, 40), (bx, by, bar_w, bar_h))
            e_ratio = entity.energy / entity.max_energy if entity.max_energy > 0 else 0
            e_fill = int(bar_w * e_ratio)
            if e_fill > 0:
                pygame.draw.rect(surface, SciFiPalette.NEON_PURPLE, (bx, by, e_fill, bar_h))

        UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                   entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_mine_drone(surface, camera, entity, anim_time):
        """Заминщик — маленький робот с бункером для мин."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(5, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle

        UnitRenderer.render_shadow(surface, cx, cy, sr.width, sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Шасси — квадратное
        body_color = (100, 100, 60)
        body_r = int(r * 0.8)
        body_rect_pts = rotate_points(cx, cy, [
            (cx - body_r, cy - body_r),
            (cx + body_r, cy - body_r),
            (cx + body_r, cy + body_r),
            (cx - body_r, cy + body_r),
        ], angle)
        pygame.draw.polygon(surface, body_color, body_rect_pts)
        pygame.draw.polygon(surface, darken(body_color, 20), body_rect_pts, 1)

        # Командный маркер
        pygame.draw.circle(surface, tc, (cx, cy), max(2, int(r * 0.25)))

        # Бункер для мин (сзади)
        rad = math.radians(angle + 180)
        bunker_x = cx + int(math.cos(rad) * body_r * 0.5)
        bunker_y = cy + int(math.sin(rad) * body_r * 0.5)
        bunker_r = max(3, int(r * 0.35))
        pygame.draw.circle(surface, SciFiPalette.STEEL_DARK, (int(bunker_x), int(bunker_y)), bunker_r)

        # Индикатор мин
        if hasattr(entity, 'mine_count'):
            for i in range(entity.mine_count):
                dot_angle = (i / max(entity.max_mines, 1)) * math.pi * 2 - math.pi / 2
                dx = int(bunker_x) + int(math.cos(dot_angle) * (bunker_r - 2))
                dy = int(bunker_y) + int(math.sin(dot_angle) * (bunker_r - 2))
                pygame.draw.circle(surface, SciFiPalette.NEON_YELLOW, (dx, dy),
                                   max(1, int(1.5 * zoom)))

        # Антенна предупреждения
        ant_x = cx + int(math.cos(math.radians(angle)) * body_r)
        ant_y = cy + int(math.sin(math.radians(angle)) * body_r) - int(r * 0.5)
        pygame.draw.line(surface, SciFiPalette.STEEL_LIGHT, (cx, cy - int(r * 0.3)),
                         (int(ant_x), int(ant_y)), 1)
        if int(anim_time * 3) % 2 == 0:
            pygame.draw.circle(surface, SciFiPalette.NEON_ORANGE,
                               (int(ant_x), int(ant_y)), max(1, int(2 * zoom)))

        UnitRenderer.render_hp_bar(surface, cx, cy, r,
                                   entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_super_unit(surface, camera, entity, anim_time):
        """Суперюнит «Каратель» — огромный титан."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(14, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        # Большая тень
        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.5),
                                   int(sr.height * 1.2), zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Ноги-опоры (4 шт с анимацией)
        walk_phase = anim_time * 2 if entity.state == 'MOVE' else 0
        leg_len = int(r * 0.7)
        for i in range(4):
            leg_angle = angle + i * 90 + 45
            swing = math.sin(walk_phase + i * math.pi / 2) * 8
            la = math.radians(leg_angle + swing)

            hip_x = cx + int(math.cos(la) * r * 0.4)
            hip_y = cy + int(math.sin(la) * r * 0.4)
            foot_x = cx + int(math.cos(la) * (r * 0.4 + leg_len))
            foot_y = cy + int(math.sin(la) * (r * 0.4 + leg_len))

            pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                             (int(hip_x), int(hip_y)), (int(foot_x), int(foot_y)),
                             max(3, int(5 * zoom)))
            # Сустав
            mid_x = (hip_x + foot_x) // 2
            mid_y = (hip_y + foot_y) // 2
            pygame.draw.circle(surface, SciFiPalette.NEON_RED,
                               (int(mid_x), int(mid_y)), max(2, int(3 * zoom)))
            # Стопа
            pygame.draw.circle(surface, SciFiPalette.STEEL,
                               (int(foot_x), int(foot_y)), max(3, int(5 * zoom)))

        # Центральный корпус — восьмиугольник
        body_color = (70, 60, 80)
        body_pts = []
        for i in range(8):
            a = math.radians(angle + i * 45 + 22.5)
            body_r = int(r * 0.65)
            px = cx + int(math.cos(a) * body_r)
            py = cy + int(math.sin(a) * body_r)
            body_pts.append((px, py))
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, brighten(body_color, 20), body_pts, 2)

        # Бронеплиты (верхняя)
        plate_color = brighten(body_color, 25)
        plate_r = int(r * 0.5)
        plate_pts = []
        for i in range(6):
            a = math.radians(angle + i * 60)
            px = cx + int(math.cos(a) * plate_r)
            py = cy + int(math.sin(a) * plate_r)
            plate_pts.append((px, py))
        pygame.draw.polygon(surface, plate_color, plate_pts)

        # Командная эмблема
        emblem_r = max(4, int(r * 0.2))
        pygame.draw.circle(surface, tc, (cx, cy), emblem_r)
        pygame.draw.circle(surface, brighten(tc, 50), (cx, cy), emblem_r, 1)

        # Визор — широкий красный
        visor_w = int(r * 0.6)
        visor_h = max(3, int(r * 0.12))
        visor_pts = rotate_points(cx, cy, [
            (cx - visor_w // 2, cy - int(r * 0.3)),
            (cx + visor_w // 2, cy - int(r * 0.3)),
            (cx + visor_w // 2, cy - int(r * 0.3) + visor_h),
            (cx - visor_w // 2, cy - int(r * 0.3) + visor_h),
        ], angle)
        pulse = (math.sin(anim_time * 2) + 1) / 2
        visor_color = brighten(SciFiPalette.NEON_RED, int(pulse * 40))
        pygame.draw.polygon(surface, visor_color, visor_pts)

        # Двойные пушки
        gun_len = int(r * 1.3)
        gun_w = max(3, int(5 * zoom))
        for side in [-1, 1]:
            gun_off = int(r * 0.25) * side
            base_x = cx + int(math.cos(rad + math.pi / 2) * gun_off)
            base_y = cy + int(math.sin(rad + math.pi / 2) * gun_off)
            gx = base_x + int(math.cos(rad) * gun_len)
            gy = base_y + int(math.sin(rad) * gun_len)
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                             (int(base_x), int(base_y)), (int(gx), int(gy)), gun_w)
            pygame.draw.circle(surface, SciFiPalette.STEEL, (int(gx), int(gy)),
                               max(2, gun_w))

            # Вспышка
            if entity.state == 'ATTACK' and entity.attack_timer > entity.attack_cooldown * 0.5:
                flash_r = max(5, int(10 * zoom))
                flash_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(flash_surf, (255, 200, 100, 220),
                                   (flash_r * 2, flash_r * 2), flash_r)
                pygame.draw.circle(flash_surf, (255, 255, 200, 120),
                                   (flash_r * 2, flash_r * 2), flash_r * 2)
                surface.blit(flash_surf, (int(gx) - flash_r * 2, int(gy) - flash_r * 2))

        # Силовой щит (видимый при наличии)
        if entity.shield > 0:
            shield_ratio = entity.shield / entity.max_shield if entity.max_shield > 0 else 0
            shield_r = int(r * 1.3)
            shield_alpha = int(20 + shield_ratio * 40)
            shield_surf = pygame.Surface((shield_r * 2, shield_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*SciFiPalette.SHIELD_BLUE, shield_alpha),
                               (shield_r, shield_r), shield_r)
            pygame.draw.circle(shield_surf, (*SciFiPalette.SHIELD_BLUE, shield_alpha + 20),
                               (shield_r, shield_r), shield_r, 2)
            surface.blit(shield_surf, (cx - shield_r, cy - shield_r))

        UnitRenderer.render_hp_bar(surface, cx, cy, r,
                                   entity.hp, entity.max_hp, zoom,
                                   entity.shield, entity.max_shield)
        if entity.selected:
            UnitRenderer.render_stance_icon(surface, cx, cy, r, entity.stance, zoom)
