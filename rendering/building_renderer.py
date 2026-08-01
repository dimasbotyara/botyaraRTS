"""
botyaraRTS - rendering/building_renderer.py
Рендер всех зданий.
"""
import pygame
import math
from settings import *
from rendering.colors import *
from rendering.utils import *
from rendering.unit_renderer import UnitRenderer


class BuildingRenderer:
    """Рендер зданий."""

    @staticmethod
    def render_building(surface, camera, entity, anim_time):
        """Универсальный рендер любого здания."""
        sr = entity.get_screen_rect(camera)
        if sr.right < 0 or sr.left > camera.screen_w or \
           sr.bottom < 0 or sr.top > camera.screen_h:
            return

        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height
        zoom = camera.zoom
        tc = UnitRenderer.get_team_color(entity.player_id)

        # Тень
        shadow_surf = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 30),
                            (4, int(h * 0.6), w, int(h * 0.35)))
        surface.blit(shadow_surf, (sr.x - 4, sr.y))

        if entity.selected:
            sel_rect = sr.inflate(6, 6)
            sel_surf = pygame.Surface((sel_rect.width, sel_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(sel_surf, (*COLOR_SELECTION_BOX, 60), sel_surf.get_rect(),
                             border_radius=4)
            pygame.draw.rect(sel_surf, COLOR_SELECTION_BOX, sel_surf.get_rect(), 2,
                             border_radius=4)
            surface.blit(sel_surf, sel_rect.topleft)

        if not entity.is_completed:
            BuildingRenderer._render_construction(surface, sr, entity, tc, zoom, anim_time)
        else:
            BuildingRenderer._render_completed(surface, sr, entity, tc, zoom, anim_time)

        # HP bar
        if entity.hp < entity.max_hp or entity.selected:
            UnitRenderer.render_hp_bar(surface, cx, cy - int(h * 0.05), max(w // 2, 10),
                                       entity.hp, entity.max_hp, zoom,
                                       entity.shield, entity.max_shield)

        # Полоска производства
        if entity.is_completed and entity.production_queue:
            BuildingRenderer._render_production_bar(surface, sr, entity, zoom)

        # Rally point
        if entity.selected and entity.rally_point and entity.can_produce:
            rpx, rpy = camera.world_to_screen(*entity.rally_point)
            pygame.draw.line(surface, SciFiPalette.NEON_GREEN,
                             (cx, cy), (int(rpx), int(rpy)), 1)
            # Флажок
            flag_size = max(4, int(6 * zoom))
            pygame.draw.polygon(surface, SciFiPalette.NEON_GREEN, [
                (int(rpx), int(rpy) - flag_size * 2),
                (int(rpx) + flag_size, int(rpy) - flag_size),
                (int(rpx), int(rpy) - flag_size),
            ])
            pygame.draw.line(surface, SciFiPalette.NEON_GREEN,
                             (int(rpx), int(rpy) - flag_size * 2),
                             (int(rpx), int(rpy)), 1)

    @staticmethod
    def _render_construction(surface, sr, entity, tc, zoom, anim_time):
        """Здание в процессе постройки."""
        progress = entity.construction_progress / entity.build_time if entity.build_time > 0 else 0
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height

        # Каркас
        frame_color = SciFiPalette.STEEL_DARK
        pygame.draw.rect(surface, (20, 22, 25), sr)

        # Сетка каркаса
        grid_step = max(6, int(12 * zoom))
        for gx in range(sr.x, sr.right, grid_step):
            pygame.draw.line(surface, frame_color, (gx, sr.y), (gx, sr.bottom), 1)
        for gy in range(sr.y, sr.bottom, grid_step):
            pygame.draw.line(surface, frame_color, (sr.x, gy), (sr.right, gy), 1)

        # Заполнение снизу вверх
        fill_h = int(h * progress)
        if fill_h > 0:
            fill_rect = pygame.Rect(sr.x, sr.bottom - fill_h, w, fill_h)
            dim_color = darken(tc, 40)
            pygame.draw.rect(surface, dim_color, fill_rect)
            # Полоски строительства
            draw_stripe_pattern(surface, fill_rect,
                                dim_color, brighten(dim_color, 15),
                                stripe_width=max(3, int(6 * zoom)))

        # Рамка
        pygame.draw.rect(surface, frame_color, sr, 2)

        # Процент
        font = pygame.font.Font(None, max(14, int(18 * zoom)))
        pct_text = font.render(f"{int(progress * 100)}%", True, SciFiPalette.NEON_CYAN)
        surface.blit(pct_text, (cx - pct_text.get_width() // 2,
                                cy - pct_text.get_height() // 2))

        # Мигающий маяк стройки
        if int(anim_time * 2) % 2 == 0:
            pygame.draw.circle(surface, SciFiPalette.NEON_ORANGE,
                               (sr.right - 4, sr.y + 4), max(2, int(3 * zoom)))

    @staticmethod
    def _render_completed(surface, sr, entity, tc, zoom, anim_time):
        """Готовое здание."""
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height
        body_color = entity.color if hasattr(entity, 'color') else SciFiPalette.STEEL

        # 3D-эффект основания
        depth = max(3, int(6 * zoom))

        # Правая грань (тёмная)
        right_face = [
            (sr.right, sr.y + depth),
            (sr.right + depth, sr.y),
            (sr.right + depth, sr.bottom - depth),
            (sr.right, sr.bottom),
        ]
        pygame.draw.polygon(surface, darken(body_color, 40), right_face)

        # Верхняя грань (светлая)
        top_face = [
            (sr.x, sr.y),
            (sr.x + depth, sr.y - depth),
            (sr.right + depth, sr.y - depth),
            (sr.right, sr.y),
        ]
        pygame.draw.polygon(surface, brighten(body_color, 20), top_face)

        # Основная грань
        pygame.draw.rect(surface, body_color, sr)

        # Внутренняя детализация зависит от категории
        cat = getattr(entity, 'category', 'economy')

        if cat == 'economy':
            BuildingRenderer._detail_economy(surface, sr, entity, tc, zoom, anim_time)
        elif cat == 'production':
            BuildingRenderer._detail_production(surface, sr, entity, tc, zoom, anim_time)
        elif cat == 'research':
            BuildingRenderer._detail_research(surface, sr, entity, tc, zoom, anim_time)
        elif cat == 'defense':
            BuildingRenderer._detail_defense(surface, sr, entity, tc, zoom, anim_time)

        # Рамка командного цвета
        pygame.draw.rect(surface, tc, sr, 2)

        # Углы — болты
        bolt_r = max(1, int(2 * zoom))
        for corner in [(sr.x + 3, sr.y + 3), (sr.right - 3, sr.y + 3),
                        (sr.x + 3, sr.bottom - 3), (sr.right - 3, sr.bottom - 3)]:
            pygame.draw.circle(surface, brighten(body_color, 40), corner, bolt_r)

    @staticmethod
    def _detail_economy(surface, sr, entity, tc, zoom, anim_time):
        """Детали экономических зданий."""
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height

        name = getattr(entity, 'name', '')

        if 'Headquarters' in name or 'HQ' in name:
            # Антенна
            ant_h = int(h * 0.4)
            pygame.draw.line(surface, SciFiPalette.STEEL_LIGHT,
                             (cx, sr.y), (cx, sr.y - ant_h), max(1, int(2 * zoom)))
            # Мигающий огонёк
            blink = int(anim_time * 1.5) % 2 == 0
            if blink:
                pygame.draw.circle(surface, SciFiPalette.NEON_GREEN,
                                   (cx, sr.y - ant_h), max(2, int(3 * zoom)))
            # Окна
            win_size = max(3, int(8 * zoom))
            for row in range(2):
                for col in range(3):
                    wx = sr.x + int(w * 0.2) + col * int(w * 0.25)
                    wy = sr.y + int(h * 0.3) + row * int(h * 0.3)
                    win_color = SciFiPalette.NEON_CYAN if (row + col) % 2 == 0 else darken(SciFiPalette.NEON_CYAN, 30)
                    pygame.draw.rect(surface, win_color,
                                     (wx, wy, win_size, win_size))

        elif 'Supply' in name:
            # Ящики
            box_size = max(4, int(w * 0.25))
            for i in range(3):
                bx = sr.x + int(w * 0.15) + i * int(w * 0.25)
                by = cy - box_size // 2
                pygame.draw.rect(surface, darken(entity.color, 20),
                                 (bx, by, box_size, box_size))
                pygame.draw.rect(surface, brighten(entity.color, 10),
                                 (bx, by, box_size, box_size), 1)

        elif 'Refinery' in name or 'Storage' in name:
            # Цистерна
            tank_r = max(4, int(min(w, h) * 0.25))
            pygame.draw.circle(surface, darken(entity.color, 15), (cx, cy), tank_r)
            pygame.draw.circle(surface, brighten(entity.color, 15), (cx, cy), tank_r, 1)
            # Труба
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                             (cx + tank_r, cy), (sr.right - 2, cy),
                             max(2, int(3 * zoom)))

        elif 'Extractor' in name or 'Plasma' in name:
            # Плазменный поток
            pulse = (math.sin(anim_time * 3) + 1) / 2
            core_r = max(3, int(min(w, h) * 0.2))
            glow_alpha = int(30 + pulse * 40)
            glow_surf = pygame.Surface((core_r * 4, core_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*SciFiPalette.PLASMA_GLOW, glow_alpha),
                               (core_r * 2, core_r * 2), core_r * 2)
            surface.blit(glow_surf, (cx - core_r * 2, cy - core_r * 2))
            pygame.draw.circle(surface, SciFiPalette.PLASMA_SOURCE, (cx, cy), core_r)

        elif 'Trading' in name:
            # Весы / стрелки обмена
            arrow_size = max(3, int(6 * zoom))
            # →
            pygame.draw.polygon(surface, SciFiPalette.TITAN_ORE, [
                (cx - arrow_size, cy - arrow_size),
                (cx + arrow_size, cy - arrow_size // 2),
                (cx - arrow_size, cy),
            ])
            # ←
            pygame.draw.polygon(surface, SciFiPalette.PLASMA_GLOW, [
                (cx + arrow_size, cy),
                (cx - arrow_size, cy + arrow_size // 2),
                (cx + arrow_size, cy + arrow_size),
            ])

    @staticmethod
    def _detail_production(surface, sr, entity, tc, zoom, anim_time):
        """Детали производственных зданий."""
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height

        # Ворота
        gate_w = int(w * 0.4)
        gate_h = int(h * 0.35)
        gate_rect = pygame.Rect(cx - gate_w // 2, sr.bottom - gate_h, gate_w, gate_h)
        pygame.draw.rect(surface, darken(entity.color, 35), gate_rect)
        # Створки ворот
        pygame.draw.line(surface, SciFiPalette.STEEL_DARK,
                         (cx, gate_rect.y), (cx, gate_rect.bottom), 1)

        # Дым / пар из трубы
        if zoom > 0.5:
            chimney_x = sr.x + int(w * 0.8)
            chimney_y = sr.y
            pygame.draw.rect(surface, SciFiPalette.STEEL_DARK,
                             (chimney_x - max(2, int(3 * zoom)), chimney_y - int(h * 0.15),
                              max(4, int(6 * zoom)), int(h * 0.15)))

            # Дым
            for i in range(3):
                smoke_y = chimney_y - int(h * 0.15) - i * int(8 * zoom)
                smoke_x = chimney_x + int(math.sin(anim_time * 2 + i) * 4 * zoom)
                smoke_r = max(2, int((3 + i) * zoom))
                smoke_alpha = max(10, 40 - i * 12)
                smoke_surf = pygame.Surface((smoke_r * 4, smoke_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(smoke_surf, (150, 150, 150, smoke_alpha),
                                   (smoke_r * 2, smoke_r * 2), smoke_r)
                surface.blit(smoke_surf, (smoke_x - smoke_r * 2, smoke_y - smoke_r * 2))

        # Индикатор производства (конвейер)
        if entity.production_queue:
            conv_y = cy - int(h * 0.1)
            conv_offset = (anim_time * 30) % w
            for i in range(0, w, max(6, int(10 * zoom))):
                dx = sr.x + int((i + conv_offset) % w)
                dot_r = max(1, int(2 * zoom))
                pygame.draw.circle(surface, SciFiPalette.NEON_ORANGE,
                                   (dx, conv_y), dot_r)

    @staticmethod
    def _detail_research(surface, sr, entity, tc, zoom, anim_time):
        """Детали исследовательских зданий."""
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height

        # Голограмма (вращающиеся кольца)
        holo_r = max(5, int(min(w, h) * 0.25))
        ring_angle = anim_time * 45

        for i in range(2):
            ring_r = holo_r - i * max(2, int(4 * zoom))
            if ring_r < 2:
                continue
            num_pts = 12
            pts = []
            for j in range(num_pts):
                a = math.radians(ring_angle * (1 + i * 0.5) + j * (360 / num_pts))
                # Эллипс
                px = cx + int(math.cos(a) * ring_r)
                py = cy + int(math.sin(a) * ring_r * (0.4 + i * 0.2))
                pts.append((px, py))
            ring_color = SciFiPalette.NEON_CYAN if i == 0 else SciFiPalette.NEON_BLUE
            if len(pts) >= 3:
                pygame.draw.polygon(surface, ring_color, pts, 1)

        # Центральная точка
        core_pulse = (math.sin(anim_time * 3) + 1) / 2
        core_r = max(2, int(3 * zoom))
        pygame.draw.circle(surface, brighten(SciFiPalette.NEON_CYAN, int(core_pulse * 50)),
                           (cx, cy), core_r)

    @staticmethod
    def _detail_defense(surface, sr, entity, tc, zoom, anim_time):
        """Детали оборонительных зданий."""
        cx, cy = sr.centerx, sr.centery
        w, h = sr.width, sr.height
        name = getattr(entity, 'name', '')

        if 'Turret' in name or 'Bunker' in name or 'SAM' in name:
            # Пушка/ракета на крыше
            turret_r = max(3, int(min(w, h) * 0.2))
            pygame.draw.circle(surface, SciFiPalette.STEEL, (cx, cy), turret_r)
            pygame.draw.circle(surface, darken(SciFiPalette.STEEL, 20), (cx, cy), turret_r, 1)

            # Ствол (вращается к цели)
            gun_angle = anim_time * 15 if not hasattr(entity, 'attack_target') or \
                        not entity.attack_target else math.degrees(
                            math.atan2(entity.attack_target.y - entity.y,
                                       entity.attack_target.x - entity.x))
            gun_len = int(turret_r * 2.5)
            grad = math.radians(gun_angle)
            gx = cx + int(math.cos(grad) * gun_len)
            gy = cy + int(math.sin(grad) * gun_len)
            pygame.draw.line(surface, SciFiPalette.STEEL_DARK, (cx, cy), (gx, gy),
                             max(2, int(3 * zoom)))

        elif 'Wall' in name:
            # Текстура стены — блоки
            block_w = max(4, int(w * 0.3))
            block_h = max(3, int(h * 0.4))
            for row in range(max(1, h // block_h)):
                offset = (row % 2) * (block_w // 2)
                for col in range(-1, max(1, w // block_w) + 1):
                    bx = sr.x + col * block_w + offset
                    by = sr.y + row * block_h
                    if bx < sr.right and by < sr.bottom:
                        pygame.draw.rect(surface, darken(entity.color, 10),
                                         (bx, by, block_w - 1, block_h - 1))

        elif 'Shield' in name:
            # Купол-щит
            shield_r = int(max(w, h) * 0.6)
            pulse = (math.sin(anim_time * 2) + 1) / 2
            shield_alpha = int(15 + pulse * 20)
            shield_surf = pygame.Surface((shield_r * 2, shield_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*SciFiPalette.SHIELD_BLUE, shield_alpha),
                               (shield_r, shield_r), shield_r)
            pygame.draw.circle(shield_surf, (*SciFiPalette.SHIELD_BLUE, shield_alpha + 20),
                               (shield_r, shield_r), shield_r, 1)
            surface.blit(shield_surf, (cx - shield_r, cy - shield_r))

            # Ядро генератора
            core_r = max(3, int(min(w, h) * 0.15))
            pygame.draw.circle(surface, SciFiPalette.PLASMA_CORE, (cx, cy), core_r)

    @staticmethod
    def _render_production_bar(surface, sr, entity, zoom):
        """Полоска прогресса производства."""
        if not entity.production_queue:
            return

        bar_w = sr.width
        bar_h = max(3, int(4 * zoom))
        bx = sr.x
        by = sr.bottom + 3

        pygame.draw.rect(surface, (20, 25, 40), (bx, by, bar_w, bar_h))

        unit_class, build_time, elapsed = entity.production_queue[0]
        progress = elapsed / build_time if build_time > 0 else 0
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(surface, SciFiPalette.NEON_BLUE, (bx, by, fill_w, bar_h))

        # Количество в очереди
        if len(entity.production_queue) > 1:
            font = pygame.font.Font(None, max(12, int(14 * zoom)))
            q_text = font.render(f"+{len(entity.production_queue) - 1}", True, SciFiPalette.NEON_CYAN)
            surface.blit(q_text, (bx + bar_w + 3, by - 1))
