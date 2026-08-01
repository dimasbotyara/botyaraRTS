"""
botyaraRTS - rendering/infantry_renderer.py
Рендер пехотных юнитов: Разведчик, Штурмовик, Снайпер, Ракетчик, Медик, Экзо.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *
from rendering.unit_renderer import UnitRenderer


class InfantryRenderer:
    """Рендер всей пехоты."""

    @staticmethod
    def render_worker(surface, camera, entity, anim_time):
        """Рабочий — маленький робот с клешнями."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(5, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)

        # Тень
        UnitRenderer.render_shadow(surface, cx, cy, sr.width, sr.height, zoom)

        # Выделение
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Тело — округлый корпус
        body_color = SciFiPalette.STEEL
        pygame.draw.circle(surface, darken(body_color, 15), (cx, cy + 1), r)  # тень
        pygame.draw.circle(surface, body_color, (cx, cy), r)

        # Верхняя полусфера (светлая)
        half_r = int(r * 0.7)
        pygame.draw.circle(surface, brighten(body_color, 25), (cx, cy - int(r * 0.15)), half_r)

        # Командный цвет — полоска на корпусе
        stripe_h = max(2, r // 3)
        pygame.draw.rect(surface, tc,
                         (cx - r + 2, cy - stripe_h // 2, (r - 2) * 2, stripe_h))

        # Глаз / визор
        visor_w = max(3, int(r * 0.6))
        visor_h = max(2, int(r * 0.25))
        visor_color = SciFiPalette.NEON_CYAN
        pygame.draw.ellipse(surface, visor_color,
                            (cx - visor_w // 2, cy - int(r * 0.4) - visor_h // 2,
                             visor_w, visor_h))
        # Блик визора
        pygame.draw.ellipse(surface, brighten(visor_color, 80),
                            (cx - visor_w // 4, cy - int(r * 0.4) - visor_h // 4,
                             visor_w // 2, visor_h // 2))

        # Клешни / руки (анимация при добыче)
        angle = entity.facing_angle
        arm_len = int(r * 0.7)
        arm_color = SciFiPalette.STEEL_DARK

        # Движение клешней при добыче
        arm_anim = 0
        if hasattr(entity, 'harvest_state') and entity.harvest_state == 'HARVESTING':
            arm_anim = math.sin(anim_time * 6) * 15

        for side in [-1, 1]:
            arm_angle = angle + 90 * side + arm_anim * side
            rad = math.radians(arm_angle)
            ax = cx + int(math.cos(rad) * arm_len)
            ay = cy + int(math.sin(rad) * arm_len)
            pygame.draw.line(surface, arm_color, (cx, cy), (ax, ay), max(2, int(2 * zoom)))
            # Клешня на конце
            pygame.draw.circle(surface, brighten(arm_color, 20), (ax, ay), max(2, int(3 * zoom)))

        # Ресурс на спине
        if hasattr(entity, 'carrying_amount') and entity.carrying_amount > 0:
            UnitRenderer.render_carry_indicator(
                surface, cx, cy, r, entity.carrying_resource, zoom
            )

        # HP
        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_scout(surface, camera, entity, anim_time):
        """Разведчик — стройный, быстрый силуэт с антенной."""
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

        # Невидимость — мерцание
        alpha = 255
        if entity.is_cloaked:
            alpha = int(40 + 30 * math.sin(anim_time * 3))

        # Тело — вытянутый ромб
        body_color = (70, 100, 70)
        body_pts = rotate_points(cx, cy, [
            (cx, cy - int(r * 1.2)),   # верх (нос)
            (cx - int(r * 0.6), cy),   # лево
            (cx, cy + int(r * 0.8)),   # низ
            (cx + int(r * 0.6), cy),   # право
        ], angle)

        if alpha < 255:
            body_surf = pygame.Surface((sr.width * 3, sr.height * 3), pygame.SRCALPHA)
            offset = (sr.width * 3 // 2, sr.height * 3 // 2)
            shifted_pts = [(p[0] - cx + offset[0], p[1] - cy + offset[1]) for p in body_pts]
            pygame.draw.polygon(body_surf, (*body_color, alpha), shifted_pts)
            pygame.draw.polygon(body_surf, (*brighten(body_color, 30), alpha), shifted_pts, 1)
            surface.blit(body_surf, (cx - offset[0], cy - offset[1]))
        else:
            pygame.draw.polygon(surface, body_color, body_pts)
            pygame.draw.polygon(surface, brighten(body_color, 30), body_pts, 1)

        # Командный маркер
        if alpha >= 200:
            pygame.draw.circle(surface, tc, (cx, cy), max(2, int(r * 0.3)))

        # Антенна
        if alpha >= 200:
            ant_len = int(r * 0.8)
            ant_end_x = cx + int(math.cos(math.radians(angle - 30)) * ant_len)
            ant_end_y = cy + int(math.sin(math.radians(angle - 30)) * ant_len) - int(r * 0.5)
            pygame.draw.line(surface, SciFiPalette.STEEL_LIGHT,
                             (cx, cy - int(r * 0.5)), (ant_end_x, ant_end_y), 1)
            # Мигающий огонёк
            if int(anim_time * 4) % 2 == 0:
                pygame.draw.circle(surface, SciFiPalette.NEON_GREEN,
                                   (ant_end_x, ant_end_y), max(1, int(2 * zoom)))

        # Радиус обзора (при выделении)
        if entity.selected and zoom > 0.5:
            vis_r = int(entity.vision_range * TILE_SIZE * zoom)
            vis_surf = pygame.Surface((vis_r * 2, vis_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(vis_surf, (0, 255, 120, 15), (vis_r, vis_r), vis_r)
            pygame.draw.circle(vis_surf, (0, 255, 120, 40), (vis_r, vis_r), vis_r, 1)
            surface.blit(vis_surf, (cx - vis_r, cy - vis_r))

        if alpha >= 200:
            UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_trooper(surface, camera, entity, anim_time):
        """Штурмовик — базовый солдат с винтовкой."""
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

        # Тело — круг (шлем)
        body_color = SciFiPalette.GUNMETAL
        pygame.draw.circle(surface, darken(body_color, 10), (cx, cy + 1), r)
        pygame.draw.circle(surface, body_color, (cx, cy), r)

        # Броня — внутренний круг командного цвета
        inner_r = int(r * 0.65)
        pygame.draw.circle(surface, tc, (cx, cy), inner_r)
        pygame.draw.circle(surface, darken(tc, 30), (cx, cy), inner_r, 1)

        # Визор
        visor_w = max(3, int(r * 0.7))
        visor_h = max(2, int(r * 0.2))
        visor_y = cy - int(r * 0.25)
        pygame.draw.rect(surface, SciFiPalette.NEON_BLUE,
                         (cx - visor_w // 2, visor_y, visor_w, visor_h),
                         border_radius=1)

        # Оружие — линия от центра в направлении взгляда
        gun_len = int(r * 1.3)
        rad = math.radians(angle)
        gx = cx + int(math.cos(rad) * gun_len)
        gy = cy + int(math.sin(rad) * gun_len)
        gun_color = SciFiPalette.STEEL_DARK
        pygame.draw.line(surface, gun_color, (cx, cy), (gx, gy), max(2, int(3 * zoom)))

        # Дуло
        pygame.draw.circle(surface, brighten(gun_color, 30), (gx, gy), max(1, int(2 * zoom)))

        # Вспышка выстрела
        if entity.state == 'ATTACK' and entity.attack_timer > entity.attack_cooldown * 0.7:
            flash_r = max(3, int(5 * zoom))
            flash_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 230, 150, 180),
                               (flash_r * 2, flash_r * 2), flash_r)
            pygame.draw.circle(flash_surf, (255, 255, 200, 100),
                               (flash_r * 2, flash_r * 2), flash_r * 2)
            surface.blit(flash_surf, (gx - flash_r * 2, gy - flash_r * 2))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)
        if entity.selected:
            UnitRenderer.render_stance_icon(surface, cx, cy, r, entity.stance, zoom)

    @staticmethod
    def render_sniper(surface, camera, entity, anim_time):
        """Снайпер — тонкий силуэт с длинной винтовкой."""
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

        # Тело — вертикальный овал (стоящий)
        body_color = (60, 70, 90)
        body_h = int(r * 1.3)
        body_w = int(r * 0.8)
        pygame.draw.ellipse(surface, body_color,
                            (cx - body_w // 2, cy - body_h // 2, body_w, body_h))

        # Капюшон / камуфляж
        hood_color = darken(body_color, 15)
        hood_r = int(r * 0.45)
        pygame.draw.circle(surface, hood_color, (cx, cy - int(r * 0.4)), hood_r)

        # Командная полоска
        stripe_w = max(2, int(body_w * 0.6))
        pygame.draw.rect(surface, tc,
                         (cx - stripe_w // 2, cy - 1, stripe_w, max(2, int(3 * zoom))))

        # Прицел-глаз (красная точка)
        pygame.draw.circle(surface, SciFiPalette.NEON_RED,
                           (cx, cy - int(r * 0.4)), max(1, int(2 * zoom)))

        # Длинная винтовка
        gun_len = int(r * 2.0)
        rad = math.radians(angle)
        gx = cx + int(math.cos(rad) * gun_len)
        gy = cy + int(math.sin(rad) * gun_len)
        pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (gx, gy),
                         max(2, int(2 * zoom)))

        # Прицел на конце
        scope_r = max(2, int(3 * zoom))
        pygame.draw.circle(surface, SciFiPalette.NEON_RED, (gx, gy), scope_r, 1)
        pygame.draw.circle(surface, (255, 0, 0, 100), (gx, gy), max(1, scope_r // 2))

        # Лазерная линия прицеливания (при атаке)
        if entity.state == 'ATTACK' and entity.attack_target:
            tx, ty_t = camera.world_to_screen(entity.attack_target.x, entity.attack_target.y)
            laser_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(laser_surf, (255, 0, 0, 60), (gx, gy), (int(tx), int(ty_t)), 1)
            surface.blit(laser_surf, (0, 0))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_rocket_soldier(surface, camera, entity, anim_time):
        """Ракетчик — с трубой базуки на плече."""
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

        # Тело
        body_color = (90, 75, 55)
        pygame.draw.circle(surface, body_color, (cx, cy), r)
        pygame.draw.circle(surface, tc, (cx, cy), int(r * 0.5))

        # Визор
        pygame.draw.rect(surface, SciFiPalette.NEON_ORANGE,
                         (cx - int(r * 0.35), cy - int(r * 0.35),
                          int(r * 0.7), max(2, int(r * 0.2))),
                         border_radius=1)

        # Базука — толстая труба
        rad = math.radians(angle)
        tube_len = int(r * 1.5)
        tube_w = max(3, int(5 * zoom))
        gx = cx + int(math.cos(rad) * tube_len)
        gy = cy + int(math.sin(rad) * tube_len)

        # Задний конец
        bx = cx - int(math.cos(rad) * int(r * 0.4))
        by = cy - int(math.sin(rad) * int(r * 0.4))

        pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (bx, by), (gx, gy), tube_w)

        # Набалдашник дула
        pygame.draw.circle(surface, SciFiPalette.STEEL, (gx, gy), max(2, tube_w // 2 + 1))

        # Выхлоп при выстреле
        if entity.state == 'ATTACK' and entity.attack_timer > entity.attack_cooldown * 0.6:
            draw_exhaust(surface, bx, by, angle, length=int(12 * zoom),
                         spread=int(4 * zoom), time_val=anim_time)

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_medic(surface, camera, entity, anim_time):
        """Медик — белый с крестом и зелёной аурой."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(5, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)

        UnitRenderer.render_shadow(surface, cx, cy, sr.width, sr.height, zoom)

        # Аура лечения (пульсирующая)
        if hasattr(entity, 'heal_range'):
            aura_r = int(entity.heal_range * zoom)
            pulse = (math.sin(anim_time * 2) + 1) / 2
            aura_alpha = int(15 + pulse * 15)
            aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (0, 200, 80, aura_alpha),
                               (aura_r, aura_r), aura_r)
            # Кольцо
            ring_alpha = int(30 + pulse * 30)
            pygame.draw.circle(aura_surf, (0, 255, 100, ring_alpha),
                               (aura_r, aura_r), aura_r, 1)
            surface.blit(aura_surf, (cx - aura_r, cy - aura_r))

        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Тело — белое
        body_color = (220, 225, 230)
        pygame.draw.circle(surface, body_color, (cx, cy), r)
        pygame.draw.circle(surface, darken(body_color, 20), (cx, cy), r, 1)

        # Красный/зелёный крест
        cross_size = max(2, int(r * 0.5))
        cross_w = max(1, int(cross_size * 0.35))
        cross_color = SciFiPalette.HEAL_GREEN

        pygame.draw.rect(surface, cross_color,
                         (cx - cross_w // 2, cy - cross_size, cross_w, cross_size * 2))
        pygame.draw.rect(surface, cross_color,
                         (cx - cross_size, cy - cross_w // 2, cross_size * 2, cross_w))

        # Командная полоска
        pygame.draw.arc(surface, tc,
                        (cx - r, cy - r, r * 2, r * 2),
                        math.radians(200), math.radians(340), max(2, int(3 * zoom)))

        # Частицы лечения
        if zoom > 0.6:
            num_particles = 3
            for i in range(num_particles):
                p_angle = anim_time * 1.5 + i * (2 * math.pi / num_particles)
                p_dist = int(r * 1.3 + math.sin(anim_time * 2 + i) * r * 0.3)
                px = cx + int(math.cos(p_angle) * p_dist)
                py = cy + int(math.sin(p_angle) * p_dist)
                p_alpha = int(150 + math.sin(anim_time * 3 + i * 2) * 80)
                p_size = max(1, int(2 * zoom))
                p_surf = pygame.Surface((p_size * 4, p_size * 4), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (0, 255, 100, max(10, p_alpha)),
                                   (p_size * 2, p_size * 2), p_size)
                surface.blit(p_surf, (px - p_size * 2, py - p_size * 2))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_exo_soldier(surface, camera, entity, anim_time):
        """Экзо-солдат — массивный, с минигана."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(7, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.2), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Массивное тело — квадрат со скруглениями
        body_color = (80, 85, 100)
        body_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        pygame.draw.rect(surface, darken(body_color, 15), body_rect.move(1, 1),
                         border_radius=max(2, r // 3))
        pygame.draw.rect(surface, body_color, body_rect,
                         border_radius=max(2, r // 3))

        # Бронепластины
        plate_color = brighten(body_color, 15)
        plate_h = max(2, r // 3)
        pygame.draw.rect(surface, plate_color,
                         (cx - r + 2, cy - r + 2, r * 2 - 4, plate_h),
                         border_radius=1)
        pygame.draw.rect(surface, plate_color,
                         (cx - r + 2, cy + r - plate_h - 2, r * 2 - 4, plate_h),
                         border_radius=1)

        # Командный цвет — большая метка
        marker_r = int(r * 0.35)
        pygame.draw.circle(surface, tc, (cx, cy), marker_r)

        # Визор (широкий, красный)
        visor_w = int(r * 0.8)
        visor_h = max(2, int(r * 0.2))
        pygame.draw.rect(surface, SciFiPalette.NEON_RED,
                         (cx - visor_w // 2, cy - int(r * 0.5), visor_w, visor_h),
                         border_radius=1)

        # Миниган — три ствола
        rad = math.radians(angle)
        gun_len = int(r * 1.4)
        gun_base_x = cx + int(math.cos(rad) * r * 0.5)
        gun_base_y = cy + int(math.sin(rad) * r * 0.5)
        gun_end_x = cx + int(math.cos(rad) * gun_len)
        gun_end_y = cy + int(math.sin(rad) * gun_len)

        # Вращение стволов
        spin_speed = 0
        if entity.state == 'ATTACK':
            spin_speed = anim_time * 15

        perp_rad = rad + math.pi / 2
        barrel_offset = max(1, int(3 * zoom))

        for i in range(3):
            barrel_angle = spin_speed + i * (2 * math.pi / 3)
            bx = int(math.cos(perp_rad) * math.cos(barrel_angle) * barrel_offset)
            by = int(math.sin(perp_rad) * math.cos(barrel_angle) * barrel_offset)
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                             (gun_base_x + bx, gun_base_y + by),
                             (gun_end_x + bx, gun_end_y + by),
                             max(1, int(2 * zoom)))

        # Кожух минигана
        pygame.draw.line(surface, SciFiPalette.STEEL,
                         (gun_base_x, gun_base_y),
                         (gun_end_x, gun_end_y),
                         max(3, int(4 * zoom)))

        # Наплечники
        shoulder_r = max(3, int(r * 0.35))
        for side in [-1, 1]:
            sx_s = cx + int(math.cos(rad + math.pi / 2 * side) * r * 0.9)
            sy_s = cy + int(math.sin(rad + math.pi / 2 * side) * r * 0.9)
            pygame.draw.circle(surface, SciFiPalette.STEEL_DARK, (sx_s, sy_s), shoulder_r)
            pygame.draw.circle(surface, tc, (sx_s, sy_s), max(1, shoulder_r - 2))

        # Вспышки при стрельбе
        if entity.state == 'ATTACK' and entity.attack_timer > entity.attack_cooldown * 0.5:
            flash_r = max(3, int(6 * zoom))
            flash_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 200, 100, 200),
                               (flash_r * 2, flash_r * 2), flash_r)
            surface.blit(flash_surf, (gun_end_x - flash_r * 2, gun_end_y - flash_r * 2))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom,
                                   entity.shield, entity.max_shield)
        if entity.selected:
            UnitRenderer.render_stance_icon(surface, cx, cy, r, entity.stance, zoom)
