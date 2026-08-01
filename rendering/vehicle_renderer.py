"""
botyaraRTS - rendering/vehicle_renderer.py
Рендер наземной техники: Багги, Танк, Огнемёт, Осадка, ПВО, Мех.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *
from rendering.unit_renderer import UnitRenderer


class VehicleRenderer:
    """Рендер всей наземной техники."""

    @staticmethod
    def render_buggy(surface, camera, entity, anim_time):
        """Багги — быстрая машинка с колёсами."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(6, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.3), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Корпус — вытянутый прямоугольник повёрнутый
        body_w = int(r * 1.6)
        body_h = int(r * 0.9)
        body_color = (170, 155, 70)

        body_pts = rotate_points(cx, cy, [
            (cx - body_w // 2, cy - body_h // 2),
            (cx + body_w // 2, cy - body_h // 2),
            (cx + body_w // 2 + int(body_h * 0.2), cy),
            (cx + body_w // 2, cy + body_h // 2),
            (cx - body_w // 2, cy + body_h // 2),
        ], angle)

        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, darken(body_color, 25), body_pts, 1)

        # Командная полоска
        stripe_pts = rotate_points(cx, cy, [
            (cx - body_w // 4, cy - body_h // 2 + 1),
            (cx + body_w // 4, cy - body_h // 2 + 1),
            (cx + body_w // 4, cy - body_h // 2 + max(2, body_h // 4)),
            (cx - body_w // 4, cy - body_h // 2 + max(2, body_h // 4)),
        ], angle)
        pygame.draw.polygon(surface, tc, stripe_pts)

        # Колёса (4 штуки)
        wheel_r = max(2, int(r * 0.25))
        wheel_positions = [
            (-body_w // 2 + wheel_r, -body_h // 2 - 1),
            (body_w // 2 - wheel_r, -body_h // 2 - 1),
            (-body_w // 2 + wheel_r, body_h // 2 + 1),
            (body_w // 2 - wheel_r, body_h // 2 + 1),
        ]
        for wx_off, wy_off in wheel_positions:
            wx, wy = rotate_point(cx, cy, cx + wx_off, cy + wy_off, angle)
            pygame.draw.circle(surface, (30, 30, 30), (int(wx), int(wy)), wheel_r)
            pygame.draw.circle(surface, (60, 60, 60), (int(wx), int(wy)), wheel_r, 1)

        # Турель сверху
        turret_r = max(2, int(r * 0.3))
        pygame.draw.circle(surface, SciFiPalette.STEEL, (cx, cy), turret_r)
        gun_len = int(r * 0.9)
        gx = cx + int(math.cos(rad) * gun_len)
        gy = cy + int(math.sin(rad) * gun_len)
        pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (gx, gy),
                         max(1, int(2 * zoom)))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_tank(surface, camera, entity, anim_time):
        """Танк — массивный с поворотной башней."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(8, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.4), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Гусеницы
        track_w = int(r * 1.6)
        track_h = int(r * 0.35)
        track_color = (40, 40, 35)

        for side in [-1, 1]:
            track_pts = rotate_points(cx, cy, [
                (cx - track_w // 2, cy + side * int(r * 0.55) - track_h // 2),
                (cx + track_w // 2, cy + side * int(r * 0.55) - track_h // 2),
                (cx + track_w // 2, cy + side * int(r * 0.55) + track_h // 2),
                (cx - track_w // 2, cy + side * int(r * 0.55) + track_h // 2),
            ], angle)
            pygame.draw.polygon(surface, track_color, track_pts)
            # Звенья гусениц
            if zoom > 0.5:
                num_links = max(3, track_w // int(6 * zoom))
                for i in range(num_links):
                    t = i / num_links
                    link_x = cx - track_w // 2 + int(t * track_w)
                    link_y = cy + side * int(r * 0.55)
                    lx, ly = rotate_point(cx, cy, link_x, link_y, angle)
                    pygame.draw.circle(surface, brighten(track_color, 20),
                                       (int(lx), int(ly)), max(1, int(2 * zoom)))

        # Корпус
        hull_w = int(r * 1.3)
        hull_h = int(r * 0.8)
        hull_color = (80, 95, 70)
        hull_pts = rotate_points(cx, cy, [
            (cx - hull_w // 2, cy - hull_h // 2),
            (cx + hull_w // 2 + int(hull_h * 0.15), cy - hull_h // 2 + int(hull_h * 0.15)),
            (cx + hull_w // 2 + int(hull_h * 0.15), cy + hull_h // 2 - int(hull_h * 0.15)),
            (cx + hull_w // 2, cy + hull_h // 2),
            (cx - hull_w // 2, cy + hull_h // 2),
        ], angle)
        pygame.draw.polygon(surface, hull_color, hull_pts)
        pygame.draw.polygon(surface, darken(hull_color, 20), hull_pts, 1)

        # Верхняя бронеплита (светлее)
        top_plate = rotate_points(cx, cy, [
            (cx - hull_w // 3, cy - hull_h // 3),
            (cx + hull_w // 3, cy - hull_h // 3),
            (cx + hull_w // 3, cy + hull_h // 4),
            (cx - hull_w // 3, cy + hull_h // 4),
        ], angle)
        pygame.draw.polygon(surface, brighten(hull_color, 15), top_plate)

        # Командный маркер
        pygame.draw.polygon(surface, tc, rotate_points(cx, cy, [
            (cx - hull_w // 4, cy - hull_h // 2 + 1),
            (cx, cy - hull_h // 2 + 1),
            (cx, cy - hull_h // 2 + max(2, hull_h // 5)),
            (cx - hull_w // 4, cy - hull_h // 2 + max(2, hull_h // 5)),
        ], angle))

        # Башня
        turret_r = max(4, int(r * 0.4))
        pygame.draw.circle(surface, brighten(hull_color, 10), (cx, cy), turret_r)
        pygame.draw.circle(surface, darken(hull_color, 10), (cx, cy), turret_r, 1)

        # Пушка
        gun_len = int(r * 1.6)
        gun_w = max(3, int(4 * zoom))
        gx = cx + int(math.cos(rad) * gun_len)
        gy = cy + int(math.sin(rad) * gun_len)
        pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (gx, gy), gun_w)

        # Набалдашник / дульный тормоз
        muzzle_r = max(2, gun_w)
        pygame.draw.circle(surface, SciFiPalette.STEEL, (gx, gy), muzzle_r)

        # Вспышка
        if entity.state == 'ATTACK' and entity.attack_timer > entity.attack_cooldown * 0.6:
            flash_r = max(5, int(10 * zoom))
            flash_surf = pygame.Surface((flash_r * 4, flash_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 220, 100, 200),
                               (flash_r * 2, flash_r * 2), flash_r)
            pygame.draw.circle(flash_surf, (255, 255, 200, 100),
                               (flash_r * 2, flash_r * 2), flash_r * 2)
            surface.blit(flash_surf, (gx - flash_r * 2, gy - flash_r * 2))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)
        if entity.selected:
            UnitRenderer.render_stance_icon(surface, cx, cy, r, entity.stance, zoom)

    @staticmethod
    def render_flamethrower(surface, camera, entity, anim_time):
        """Огнемётная машина — с языками пламени."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(7, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.3), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Корпус — округлый
        body_color = (120, 80, 40)
        hull_w = int(r * 1.4)
        hull_h = int(r * 1.0)
        hull_pts = rotate_points(cx, cy, [
            (cx - hull_w // 2, cy - hull_h // 2),
            (cx + hull_w // 2, cy - hull_h // 2),
            (cx + hull_w // 2, cy + hull_h // 2),
            (cx - hull_w // 2, cy + hull_h // 2),
        ], angle)
        pygame.draw.polygon(surface, body_color, hull_pts)
        pygame.draw.polygon(surface, darken(body_color, 25), hull_pts, 1)

        # Топливный бак на крыше (оранжевый цилиндр)
        tank_w = int(r * 0.5)
        tank_h = int(r * 0.8)
        tank_pts = rotate_points(cx, cy, [
            (cx - tank_w // 2, cy - tank_h // 4),
            (cx + tank_w // 2, cy - tank_h // 4),
            (cx + tank_w // 2, cy + tank_h // 4),
            (cx - tank_w // 2, cy + tank_h // 4),
        ], angle)
        pygame.draw.polygon(surface, SciFiPalette.FIRE_ORANGE, tank_pts)

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy), max(2, int(r * 0.25)))

        # Огнемёт (сопло)
        nozzle_len = int(r * 1.2)
        nozzle_w = max(3, int(5 * zoom))
        nx = cx + int(math.cos(rad) * nozzle_len)
        ny = cy + int(math.sin(rad) * nozzle_len)
        pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (nx, ny), nozzle_w)

        # Пламя при атаке
        if entity.state == 'ATTACK':
            flame_len = int(r * 2.0)
            num_flames = 8
            flame_surf = pygame.Surface((int(flame_len * 3), int(flame_len * 3)), pygame.SRCALPHA)
            fc = (flame_len * 3 // 2, flame_len * 3 // 2)

            for i in range(num_flames):
                f_offset = (i / num_flames) * flame_len
                f_spread = math.sin(anim_time * 12 + i * 1.5) * int(r * 0.4) * (f_offset / flame_len)
                fx = fc[0] + int(math.cos(rad) * f_offset + math.cos(rad + math.pi / 2) * f_spread)
                fy = fc[1] + int(math.sin(rad) * f_offset + math.sin(rad + math.pi / 2) * f_spread)

                t = f_offset / flame_len
                f_color = lerp_color(SciFiPalette.FIRE_CORE, SciFiPalette.FIRE_RED, t)
                f_r = max(2, int((1 - t * 0.5) * r * 0.4))
                f_alpha = int(200 * (1 - t))
                pygame.draw.circle(flame_surf, (*f_color, f_alpha), (fx, fy), f_r)

            surface.blit(flame_surf, (nx - flame_len * 3 // 2, ny - flame_len * 3 // 2))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_siege_tank(surface, camera, entity, anim_time):
        """Осадная артиллерия — два режима."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(8, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        is_siege = hasattr(entity, 'siege_mode') and entity.siege_mode

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * (1.6 if is_siege else 1.4)),
                                   sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        if is_siege:
            # Режим осады — разложенные опоры
            body_color = (70, 80, 70)
            hull_w = int(r * 1.8)
            hull_h = int(r * 1.4)

            # Опорные лапы
            leg_len = int(r * 0.8)
            for leg_angle in [-45, -135, 45, 135]:
                la = math.radians(angle + leg_angle)
                lx1 = cx + int(math.cos(la) * r * 0.5)
                ly1 = cy + int(math.sin(la) * r * 0.5)
                lx2 = cx + int(math.cos(la) * (r * 0.5 + leg_len))
                ly2 = cy + int(math.sin(la) * (r * 0.5 + leg_len))
                pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                                 (lx1, ly1), (lx2, ly2), max(2, int(3 * zoom)))
                pygame.draw.circle(surface, SciFiPalette.STEEL, (lx2, ly2),
                                   max(2, int(3 * zoom)))

            # Корпус
            hull_pts = rotate_points(cx, cy, [
                (cx - hull_w // 2, cy - hull_h // 2),
                (cx + hull_w // 2, cy - hull_h // 2),
                (cx + hull_w // 2, cy + hull_h // 2),
                (cx - hull_w // 2, cy + hull_h // 2),
            ], angle)
            pygame.draw.polygon(surface, body_color, hull_pts)
            pygame.draw.polygon(surface, tc, rotate_points(cx, cy, [
                (cx - hull_w // 3, cy - hull_h // 2 + 1),
                (cx + hull_w // 3, cy - hull_h // 2 + 1),
                (cx + hull_w // 3, cy - hull_h // 2 + max(2, hull_h // 6)),
                (cx - hull_w // 3, cy - hull_h // 2 + max(2, hull_h // 6)),
            ], angle))

            # Огромная пушка
            gun_len = int(r * 2.5)
            gun_w = max(4, int(6 * zoom))
            gx = cx + int(math.cos(rad) * gun_len)
            gy = cy + int(math.sin(rad) * gun_len)
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (gx, gy), gun_w)

            # Набалдашник
            pygame.draw.circle(surface, SciFiPalette.STEEL, (gx, gy),
                               max(3, gun_w + 1))

            # Индикатор "осада"
            pygame.draw.circle(surface, SciFiPalette.NEON_RED, (cx, cy), max(3, int(4 * zoom)))

        else:
            # Мобильный режим — компактный
            VehicleRenderer.render_tank(surface, camera, entity, anim_time)
            # Дорисовываем дополнительные штуки на башне
            turret_r = max(2, int(r * 0.25))
            pygame.draw.circle(surface, SciFiPalette.NEON_ORANGE, (cx, cy), turret_r, 1)

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_mobile_aa(surface, camera, entity, anim_time):
        """Мобильная ПВО — радар + ракеты."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(7, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.3), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Платформа
        body_color = (100, 120, 140)
        hull_pts = rotate_points(cx, cy, [
            (cx - int(r * 0.8), cy - int(r * 0.6)),
            (cx + int(r * 0.8), cy - int(r * 0.6)),
            (cx + int(r * 0.8), cy + int(r * 0.6)),
            (cx - int(r * 0.8), cy + int(r * 0.6)),
        ], angle)
        pygame.draw.polygon(surface, body_color, hull_pts)
        pygame.draw.polygon(surface, tc, rotate_points(cx, cy, [
            (cx - int(r * 0.3), cy - int(r * 0.6) + 1),
            (cx + int(r * 0.3), cy - int(r * 0.6) + 1),
            (cx + int(r * 0.3), cy - int(r * 0.6) + max(2, int(r * 0.15))),
            (cx - int(r * 0.3), cy - int(r * 0.6) + max(2, int(r * 0.15))),
        ], angle))

        # Ракетные контейнеры (по бокам)
        for side in [-1, 1]:
            mx = cx + int(math.cos(rad + math.pi / 2 * side) * r * 0.6)
            my = cy + int(math.sin(rad + math.pi / 2 * side) * r * 0.6)
            container_pts = rotate_points(mx, my, [
                (mx - int(r * 0.15), my - int(r * 0.4)),
                (mx + int(r * 0.15), my - int(r * 0.4)),
                (mx + int(r * 0.15), my + int(r * 0.4)),
                (mx - int(r * 0.15), my + int(r * 0.4)),
            ], angle)
            pygame.draw.polygon(surface, SciFiPalette.STEEL_DARK, container_pts)
            # Ракеты внутри
            for j in range(3):
                ry = my - int(r * 0.25) + j * int(r * 0.2)
                rx, rry = rotate_point(mx, my, mx, ry, angle)
                pygame.draw.circle(surface, SciFiPalette.NEON_RED, (int(rx), int(rry)),
                                   max(1, int(2 * zoom)))

        # Радарная тарелка (вращающаяся)
        radar_angle = anim_time * 120  # градусов в секунду
        radar_len = int(r * 0.6)
        rrad = math.radians(radar_angle)
        rx = cx + int(math.cos(rrad) * radar_len)
        ry = cy + int(math.sin(rrad) * radar_len)
        pygame.draw.line(surface, SciFiPalette.NEON_GREEN, (cx, cy), (rx, ry), 1)
        pygame.draw.circle(surface, SciFiPalette.NEON_GREEN, (cx, cy), max(2, int(3 * zoom)), 1)

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_mech_walker(surface, camera, entity, anim_time):
        """Шагоход-мех — двуногий робот."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        r = max(9, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        UnitRenderer.render_shadow(surface, cx, cy, int(sr.width * 1.2), sr.height, zoom)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy, r, zoom, tc)

        # Ноги (анимация ходьбы)
        walk_phase = anim_time * 4 if entity.state == 'MOVE' else 0
        leg_len = int(r * 0.9)
        knee_len = int(r * 0.6)
        foot_size = max(3, int(4 * zoom))

        for side_idx, side in enumerate([-1, 1]):
            phase = walk_phase + side_idx * math.pi
            knee_swing = math.sin(phase) * 15

            hip_x = cx + int(math.cos(rad + math.pi / 2 * side) * r * 0.3)
            hip_y = cy + int(math.sin(rad + math.pi / 2 * side) * r * 0.3)

            knee_angle = angle + 90 + knee_swing * side
            knee_rad = math.radians(knee_angle)
            knee_x = hip_x + int(math.cos(knee_rad) * knee_len * 0.5)
            knee_y = hip_y + int(math.sin(knee_rad) * knee_len * 0.5)

            foot_x = knee_x + int(math.cos(math.radians(90)) * knee_len * 0.5)
            foot_y = knee_y + int(math.sin(math.radians(90)) * knee_len * 0.5)

            # Верхняя нога
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                             (int(hip_x), int(hip_y)), (int(knee_x), int(knee_y)),
                             max(3, int(4 * zoom)))
            # Нижняя нога
            pygame.draw.line(surface, SciFiPalette.STEEL,
                             (int(knee_x), int(knee_y)), (int(foot_x), int(foot_y)),
                             max(2, int(3 * zoom)))
            # Сустав
            pygame.draw.circle(surface, SciFiPalette.NEON_BLUE,
                               (int(knee_x), int(knee_y)), max(2, int(3 * zoom)))
            # Стопа
            pygame.draw.circle(surface, SciFiPalette.STEEL_DARK,
                               (int(foot_x), int(foot_y)), foot_size)

        # Торс — шестиугольник
        torso_r = int(r * 0.6)
        torso_pts = []
        for i in range(6):
            a = math.radians(angle + i * 60 + 30)
            px = cx + int(math.cos(a) * torso_r)
            py = cy + int(math.sin(a) * torso_r)
            torso_pts.append((px, py))
        body_color = (90, 85, 105)
        pygame.draw.polygon(surface, body_color, torso_pts)
        pygame.draw.polygon(surface, darken(body_color, 20), torso_pts, 2)

        # Командный цвет — центр
        pygame.draw.circle(surface, tc, (cx, cy), max(3, int(r * 0.25)))

        # Визор
        visor_w = int(torso_r * 0.8)
        visor_pts = rotate_points(cx, cy, [
            (cx - visor_w // 2, cy - int(torso_r * 0.4)),
            (cx + visor_w // 2, cy - int(torso_r * 0.4)),
            (cx + visor_w // 3, cy - int(torso_r * 0.2)),
            (cx - visor_w // 3, cy - int(torso_r * 0.2)),
        ], angle)
        pygame.draw.polygon(surface, SciFiPalette.NEON_BLUE, visor_pts)

        # Ракетные подвесы на плечах
        for side in [-1, 1]:
            sx_p = cx + int(math.cos(rad + math.pi / 2 * side) * torso_r * 0.8)
            sy_p = cy + int(math.sin(rad + math.pi / 2 * side) * torso_r * 0.8) - int(r * 0.3)
            pygame.draw.rect(surface, SciFiPalette.STEEL_DARK,
                             (int(sx_p) - max(2, int(4 * zoom)),
                              int(sy_p) - max(2, int(6 * zoom)),
                              max(4, int(8 * zoom)), max(4, int(12 * zoom))))

        UnitRenderer.render_hp_bar(surface, cx, cy, r, entity.hp, entity.max_hp, zoom)
        if entity.selected:
            UnitRenderer.render_stance_icon(surface, cx, cy, r, entity.stance, zoom)
