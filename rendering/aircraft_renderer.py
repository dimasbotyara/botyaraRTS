"""
botyaraRTS - rendering/aircraft_renderer.py
Рендер авиации: Дрон, Вертолёт, Истребитель, Бомбардировщик, Транспорт.
Все летают → рисуем тень на земле отдельно + парящий силуэт.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *
from rendering.unit_renderer import UnitRenderer


class AircraftRenderer:
    """Рендер всей авиации."""

    @staticmethod
    def _render_flight_shadow(surface, cx, cy, width, height, zoom, altitude=8):
        """Тень самолёта на земле (смещена вниз)."""
        shadow_w = int(width * 0.7)
        shadow_h = int(height * 0.25)
        offset_y = int(altitude * zoom)
        shadow_surf = pygame.Surface((shadow_w + 4, shadow_h + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 25),
                            (2, 2, shadow_w, shadow_h))
        surface.blit(shadow_surf,
                     (cx - shadow_w // 2 - 2, cy + offset_y + int(height * 0.4)))

    @staticmethod
    def _hover_offset(anim_time, speed=2.0, amplitude=3.0):
        """Вертикальное покачивание в воздухе."""
        return math.sin(anim_time * speed) * amplitude

    @staticmethod
    def render_scout_drone(surface, camera, entity, anim_time):
        """Дрон-разведчик — маленький, невидимый, 4 пропеллера."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = AircraftRenderer._hover_offset(anim_time, 3.0, 2.0)
        cy_draw = int(cy + hover)
        r = max(5, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)

        AircraftRenderer._render_flight_shadow(surface, cx, cy, sr.width, sr.height, zoom, 10)

        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Невидимость
        alpha = 255
        if entity.is_cloaked:
            alpha = int(30 + 25 * math.sin(anim_time * 4))

        drone_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        dc = (r * 2, r * 2)

        # Центральный корпус — маленький ромб
        body_size = int(r * 0.5)
        body_pts = [
            (dc[0], dc[1] - body_size),
            (dc[0] + body_size, dc[1]),
            (dc[0], dc[1] + body_size),
            (dc[0] - body_size, dc[1]),
        ]
        pygame.draw.polygon(drone_surf, (*SciFiPalette.STEEL, alpha), body_pts)

        # 4 луча к пропеллерам
        arm_len = int(r * 0.8)
        prop_r = max(2, int(r * 0.35))
        prop_speed = anim_time * 25

        for i in range(4):
            arm_angle = entity.facing_angle + i * 90 + 45
            arm_rad = math.radians(arm_angle)
            ax = dc[0] + int(math.cos(arm_rad) * arm_len)
            ay = dc[1] + int(math.sin(arm_rad) * arm_len)

            # Луч
            pygame.draw.line(drone_surf, (*SciFiPalette.STEEL_DARK, alpha),
                             dc, (ax, ay), max(1, int(2 * zoom)))

            # Моторчик
            pygame.draw.circle(drone_surf, (*SciFiPalette.GUNMETAL, alpha),
                               (ax, ay), max(2, int(3 * zoom)))

            # Пропеллер (вращающийся)
            for blade in range(2):
                b_angle = prop_speed + i * 30 + blade * 180
                b_rad = math.radians(b_angle)
                bx1 = ax + int(math.cos(b_rad) * prop_r)
                by1 = ay + int(math.sin(b_rad) * prop_r)
                bx2 = ax - int(math.cos(b_rad) * prop_r)
                by2 = ay - int(math.sin(b_rad) * prop_r)
                pygame.draw.line(drone_surf, (*brighten(SciFiPalette.STEEL, 30), min(255, alpha + 30)),
                                 (bx1, by1), (bx2, by2), 1)

        # Центральный «глаз» — сенсор
        eye_color = SciFiPalette.NEON_GREEN if not entity.is_cloaked else SciFiPalette.NEON_CYAN
        eye_r = max(1, int(r * 0.2))
        pygame.draw.circle(drone_surf, (*eye_color, alpha), dc, eye_r)
        # Свечение сенсора
        pygame.draw.circle(drone_surf, (*eye_color, alpha // 4), dc, eye_r * 2)

        # Командный маркер
        marker_r = max(1, int(r * 0.15))
        pygame.draw.circle(drone_surf, (*tc, alpha),
                           (dc[0], dc[1] + body_size + 2), marker_r)

        surface.blit(drone_surf, (cx - r * 2, cy_draw - r * 2))

        # Радиус ретрансляции (при выделении)
        if entity.selected and hasattr(entity, 'relay_range') and zoom > 0.4:
            relay_r = int(entity.relay_range * zoom)
            relay_surf = pygame.Surface((relay_r * 2, relay_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(relay_surf, (0, 200, 255, 15), (relay_r, relay_r), relay_r)
            pygame.draw.circle(relay_surf, (0, 200, 255, 40), (relay_r, relay_r), relay_r, 1)
            surface.blit(relay_surf, (cx - relay_r, cy_draw - relay_r))

        if alpha > 100:
            UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                       entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_attack_helicopter(surface, camera, entity, anim_time):
        """Штурмовой вертолёт — нос вниз, с ракетами."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = AircraftRenderer._hover_offset(anim_time, 2.5, 3.0)
        cy_draw = int(cy + hover)
        r = max(7, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        AircraftRenderer._render_flight_shadow(surface, cx, cy, sr.width, sr.height, zoom, 12)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Фюзеляж — вытянутый овал
        body_w = int(r * 1.6)
        body_h = int(r * 0.7)
        body_color = (90, 110, 80)

        body_pts = rotate_points(cx, cy_draw, [
            (cx + int(body_w * 0.5), cy_draw),
            (cx + int(body_w * 0.3), cy_draw - int(body_h * 0.5)),
            (cx - int(body_w * 0.4), cy_draw - int(body_h * 0.4)),
            (cx - int(body_w * 0.5), cy_draw),
            (cx - int(body_w * 0.4), cy_draw + int(body_h * 0.4)),
            (cx + int(body_w * 0.3), cy_draw + int(body_h * 0.5)),
        ], angle)
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, darken(body_color, 20), body_pts, 1)

        # Кокпит (стекло)
        cockpit_pts = rotate_points(cx, cy_draw, [
            (cx + int(body_w * 0.35), cy_draw),
            (cx + int(body_w * 0.15), cy_draw - int(body_h * 0.25)),
            (cx + int(body_w * 0.15), cy_draw + int(body_h * 0.25)),
        ], angle)
        pygame.draw.polygon(surface, SciFiPalette.NEON_CYAN, cockpit_pts)

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy_draw), max(2, int(r * 0.2)))

        # Хвост
        tail_len = int(body_w * 0.6)
        tx_t = cx - int(math.cos(rad) * tail_len)
        ty_t = cy_draw - int(math.sin(rad) * tail_len)
        pygame.draw.line(surface, darken(body_color, 10), (cx, cy_draw),
                         (int(tx_t), int(ty_t)), max(2, int(3 * zoom)))

        # Хвостовой ротор
        tail_rotor_r = max(2, int(r * 0.2))
        t_blade = anim_time * 30
        for b in range(2):
            ba = math.radians(t_blade + b * 180)
            bx1 = int(tx_t) + int(math.cos(ba) * tail_rotor_r)
            by1 = int(ty_t) + int(math.sin(ba) * tail_rotor_r)
            bx2 = int(tx_t) - int(math.cos(ba) * tail_rotor_r)
            by2 = int(ty_t) - int(math.sin(ba) * tail_rotor_r)
            pygame.draw.line(surface, SciFiPalette.STEEL_LIGHT, (bx1, by1), (bx2, by2), 1)

        # Главный ротор (вращение)
        main_rotor_r = int(r * 1.0)
        rotor_surf = pygame.Surface((main_rotor_r * 3, main_rotor_r * 3), pygame.SRCALPHA)
        rc = (main_rotor_r * 3 // 2, main_rotor_r * 3 // 2)
        rotor_speed = anim_time * 20
        for b in range(3):
            ba = math.radians(rotor_speed + b * 120)
            bx = rc[0] + int(math.cos(ba) * main_rotor_r)
            by = rc[1] + int(math.sin(ba) * main_rotor_r)
            pygame.draw.line(rotor_surf, (*SciFiPalette.STEEL_LIGHT, 120),
                             rc, (bx, by), max(1, int(2 * zoom)))
        pygame.draw.circle(rotor_surf, (*SciFiPalette.STEEL, 180), rc,
                           max(2, int(3 * zoom)))
        surface.blit(rotor_surf, (cx - main_rotor_r * 3 // 2,
                                  cy_draw - main_rotor_r * 3 // 2))

        # Ракетные подвесы
        for side in [-1, 1]:
            wing_x = cx + int(math.cos(rad + math.pi / 2 * side) * body_h * 0.7)
            wing_y = cy_draw + int(math.sin(rad + math.pi / 2 * side) * body_h * 0.7)
            # Пилон
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy_draw),
                             (int(wing_x), int(wing_y)), max(1, int(2 * zoom)))
            # Ракеты
            for j in range(2):
                rr_x = wing_x + int(math.cos(rad) * (j * int(4 * zoom) - int(2 * zoom)))
                rr_y = wing_y + int(math.sin(rad) * (j * int(4 * zoom) - int(2 * zoom)))
                pygame.draw.circle(surface, SciFiPalette.NEON_RED,
                                   (int(rr_x), int(rr_y)), max(1, int(2 * zoom)))

        UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                   entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_fighter(surface, camera, entity, anim_time):
        """Истребитель — быстрый треугольник с крыльями-стрелками."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = AircraftRenderer._hover_offset(anim_time, 3.5, 2.0)
        cy_draw = int(cy + hover)
        r = max(6, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle

        AircraftRenderer._render_flight_shadow(surface, cx, cy, sr.width, sr.height, zoom, 14)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Корпус — острый треугольник (стрелка)
        body_color = (150, 150, 180)
        nose_len = int(r * 1.4)
        wing_span = int(r * 1.2)
        tail_len = int(r * 0.8)

        body_pts = rotate_points(cx, cy_draw, [
            (cx + nose_len, cy_draw),              # нос
            (cx - int(r * 0.3), cy_draw - wing_span),  # левое крыло
            (cx - tail_len, cy_draw - int(r * 0.2)),    # левый хвост
            (cx - tail_len, cy_draw + int(r * 0.2)),    # правый хвост
            (cx - int(r * 0.3), cy_draw + wing_span),   # правое крыло
        ], angle)
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, darken(body_color, 25), body_pts, 1)

        # Центральная «спина» (светлая)
        spine_pts = rotate_points(cx, cy_draw, [
            (cx + nose_len - int(r * 0.2), cy_draw),
            (cx, cy_draw - int(r * 0.15)),
            (cx - tail_len + int(r * 0.2), cy_draw),
            (cx, cy_draw + int(r * 0.15)),
        ], angle)
        pygame.draw.polygon(surface, brighten(body_color, 20), spine_pts)

        # Кокпит
        cockpit_pts = rotate_points(cx, cy_draw, [
            (cx + int(nose_len * 0.5), cy_draw),
            (cx + int(nose_len * 0.2), cy_draw - int(r * 0.12)),
            (cx + int(nose_len * 0.2), cy_draw + int(r * 0.12)),
        ], angle)
        pygame.draw.polygon(surface, SciFiPalette.NEON_BLUE, cockpit_pts)

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy_draw), max(2, int(r * 0.2)))

        # Двигатели (свечение сзади)
        rad = math.radians(angle)
        for side in [-1, 0, 1]:
            if side == 0:
                continue
            eng_x = cx - int(math.cos(rad) * tail_len * 0.8) + \
                    int(math.cos(rad + math.pi / 2) * side * int(r * 0.15))
            eng_y = cy_draw - int(math.sin(rad) * tail_len * 0.8) + \
                    int(math.sin(rad + math.pi / 2) * side * int(r * 0.15))
            draw_exhaust(surface, int(eng_x), int(eng_y), angle,
                         length=int(8 * zoom), spread=int(3 * zoom), time_val=anim_time)

        # Форсаж (при движении)
        if entity.state == 'MOVE' or entity.state == 'PURSUIT':
            for side in [-1, 1]:
                eng_x = cx - int(math.cos(rad) * tail_len) + \
                        int(math.cos(rad + math.pi / 2) * side * int(r * 0.2))
                eng_y = cy_draw - int(math.sin(rad) * tail_len) + \
                        int(math.sin(rad + math.pi / 2) * side * int(r * 0.2))
                draw_exhaust(surface, int(eng_x), int(eng_y), angle,
                             length=int(14 * zoom), spread=int(5 * zoom), time_val=anim_time)

        UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                   entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_bomber(surface, camera, entity, anim_time):
        """Бомбардировщик — массивный с бомболюком."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = AircraftRenderer._hover_offset(anim_time, 1.5, 4.0)
        cy_draw = int(cy + hover)
        r = max(9, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        AircraftRenderer._render_flight_shadow(surface, cx, cy,
                                                int(sr.width * 1.4), sr.height, zoom, 16)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Массивный корпус
        body_color = (100, 85, 70)
        body_w = int(r * 1.8)
        body_h = int(r * 0.9)

        body_pts = rotate_points(cx, cy_draw, [
            (cx + int(body_w * 0.4), cy_draw),
            (cx + int(body_w * 0.2), cy_draw - int(body_h * 0.4)),
            (cx - int(body_w * 0.3), cy_draw - int(body_h * 0.5)),
            (cx - int(body_w * 0.5), cy_draw - int(body_h * 0.3)),
            (cx - int(body_w * 0.5), cy_draw + int(body_h * 0.3)),
            (cx - int(body_w * 0.3), cy_draw + int(body_h * 0.5)),
            (cx + int(body_w * 0.2), cy_draw + int(body_h * 0.4)),
        ], angle)
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, darken(body_color, 20), body_pts, 1)

        # Крылья — широкие
        wing_span = int(r * 1.5)
        for side in [-1, 1]:
            wing_pts = rotate_points(cx, cy_draw, [
                (cx, cy_draw + side * int(body_h * 0.3)),
                (cx - int(r * 0.5), cy_draw + side * wing_span),
                (cx - int(r * 0.8), cy_draw + side * wing_span),
                (cx - int(r * 0.4), cy_draw + side * int(body_h * 0.3)),
            ], angle)
            pygame.draw.polygon(surface, darken(body_color, 10), wing_pts)
            pygame.draw.polygon(surface, darken(body_color, 25), wing_pts, 1)

            # Двигатели на крыльях
            eng_x = cx - int(math.cos(rad) * r * 0.3) + \
                    int(math.cos(rad + math.pi / 2) * side * wing_span * 0.6)
            eng_y = cy_draw - int(math.sin(rad) * r * 0.3) + \
                    int(math.sin(rad + math.pi / 2) * side * wing_span * 0.6)
            eng_r = max(3, int(r * 0.15))
            pygame.draw.circle(surface, SciFiPalette.GUNMETAL, (int(eng_x), int(eng_y)), eng_r)
            draw_exhaust(surface, int(eng_x), int(eng_y), angle,
                         length=int(10 * zoom), spread=int(4 * zoom), time_val=anim_time)

        # Бомболюк (нижняя тёмная зона)
        bomb_pts = rotate_points(cx, cy_draw, [
            (cx + int(body_w * 0.1), cy_draw - int(body_h * 0.15)),
            (cx - int(body_w * 0.2), cy_draw - int(body_h * 0.15)),
            (cx - int(body_w * 0.2), cy_draw + int(body_h * 0.15)),
            (cx + int(body_w * 0.1), cy_draw + int(body_h * 0.15)),
        ], angle)
        pygame.draw.polygon(surface, darken(body_color, 30), bomb_pts)

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy_draw), max(3, int(r * 0.2)))

        UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                   entity.hp, entity.max_hp, zoom)

    @staticmethod
    def render_transport(surface, camera, entity, anim_time):
        """Транспорт — грузовой корабль с грузовым отсеком."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        hover = AircraftRenderer._hover_offset(anim_time, 1.8, 3.5)
        cy_draw = int(cy + hover)
        r = max(10, sr.width // 2)
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)
        angle = entity.facing_angle
        rad = math.radians(angle)

        AircraftRenderer._render_flight_shadow(surface, cx, cy,
                                                int(sr.width * 1.3), sr.height, zoom, 14)
        if entity.selected:
            UnitRenderer.render_selection_indicator(surface, cx, cy_draw, r, zoom, tc)

        # Прямоугольный корпус
        body_color = (130, 130, 110)
        body_w = int(r * 1.6)
        body_h = int(r * 1.0)

        body_pts = rotate_points(cx, cy_draw, [
            (cx + int(body_w * 0.4), cy_draw - int(body_h * 0.3)),
            (cx + int(body_w * 0.5), cy_draw),
            (cx + int(body_w * 0.4), cy_draw + int(body_h * 0.3)),
            (cx - int(body_w * 0.5), cy_draw + int(body_h * 0.4)),
            (cx - int(body_w * 0.5), cy_draw - int(body_h * 0.4)),
        ], angle)
        pygame.draw.polygon(surface, body_color, body_pts)
        pygame.draw.polygon(surface, darken(body_color, 20), body_pts, 1)

        # Грузовой отсек (тёмный центр)
        cargo_color = darken(body_color, 35)
        cargo_w = int(body_w * 0.5)
        cargo_h = int(body_h * 0.5)
        cargo_pts = rotate_points(cx, cy_draw, [
            (cx + int(cargo_w * 0.3), cy_draw - int(cargo_h * 0.5)),
            (cx + int(cargo_w * 0.3), cy_draw + int(cargo_h * 0.5)),
            (cx - int(cargo_w * 0.4), cy_draw + int(cargo_h * 0.5)),
            (cx - int(cargo_w * 0.4), cy_draw - int(cargo_h * 0.5)),
        ], angle)
        pygame.draw.polygon(surface, cargo_color, cargo_pts)

        # Количество груза
        if hasattr(entity, 'cargo') and entity.cargo:
            cargo_count = len(entity.cargo)
            dots_per_row = 4
            dot_r = max(1, int(2 * zoom))
            for i in range(min(cargo_count, 8)):
                row = i // dots_per_row
                col = i % dots_per_row
                dx = cx - int(cargo_w * 0.2) + col * int(dot_r * 3)
                dy = cy_draw - int(cargo_h * 0.2) + row * int(dot_r * 3)
                ddx, ddy = rotate_point(cx, cy_draw, dx, dy, angle)
                pygame.draw.circle(surface, SciFiPalette.NEON_GREEN,
                                   (int(ddx), int(ddy)), dot_r)

        # Двигатели
        for side in [-1, 1]:
            eng_x = cx - int(math.cos(rad) * body_w * 0.3) + \
                    int(math.cos(rad + math.pi / 2) * side * body_h * 0.35)
            eng_y = cy_draw - int(math.sin(rad) * body_w * 0.3) + \
                    int(math.sin(rad + math.pi / 2) * side * body_h * 0.35)
            pygame.draw.circle(surface, SciFiPalette.GUNMETAL,
                               (int(eng_x), int(eng_y)), max(3, int(4 * zoom)))
            draw_exhaust(surface, int(eng_x), int(eng_y), angle,
                         length=int(12 * zoom), spread=int(5 * zoom), time_val=anim_time)

        # Командная метка
        pygame.draw.circle(surface, tc, (cx, cy_draw), max(3, int(r * 0.2)))

        UnitRenderer.render_hp_bar(surface, cx, cy_draw, r,
                                   entity.hp, entity.max_hp, zoom)
