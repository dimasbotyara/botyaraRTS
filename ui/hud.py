"""
botyaraRTS - ui/hud.py
Основной HUD: ресурсы, панель управления, информация о выделенных юнитах.
"""
import pygame
from settings import *
from entities.building import ALL_BUILDINGS


class HUD:
    """Игровой интерфейс."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Панель управления (нижняя)
        self.panel_height = 180
        self.panel_rect = pygame.Rect(
            0, screen_h - self.panel_height,
            screen_w, self.panel_height
        )
        self.panel_surface = pygame.Surface(
            (screen_w, self.panel_height), pygame.SRCALPHA
        )

        # Вкладки строительства
        self.build_tabs = ['🏠 Economy', '⚔ Military', '🔬 Research', '🛡 Defense']
        self.build_tab_keys = ['economy', 'production', 'research', 'defense']
        self.current_tab = 0
        self.tab_rects = []

        # Кнопки юнитов в панели
        self.action_buttons = []
        self.button_size = 48
        self.button_margin = 4

        # Шрифты
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self._init_fonts()

        # Верхняя панель ресурсов
        self.resource_bar_height = 32

        # Слоты улучшений
        self.upgrade_slot_size = 40

    def _init_fonts(self):
        try:
            self.font_large = pygame.font.Font(None, 28)
            self.font_medium = pygame.font.Font(None, 22)
            self.font_small = pygame.font.Font(None, 18)
        except Exception:
            self.font_large = pygame.font.SysFont('arial', 20)
            self.font_medium = pygame.font.SysFont('arial', 16)
            self.font_small = pygame.font.SysFont('arial', 12)

    def is_point_on_panel(self, x, y):
        """Проверить, находится ли точка на панели UI."""
        if self.panel_rect.collidepoint(x, y):
            return True
        if y < self.resource_bar_height:
            return True
        return False

    def render(self, surface, game_state, selected_entities):
        """Отрисовка HUD."""
        self._render_resource_bar(surface, game_state)
        self._render_bottom_panel(surface, game_state, selected_entities)
        self._render_upgrade_slots(surface, game_state)

    def _render_resource_bar(self, surface, game_state):
        """Верхняя панель ресурсов."""
        player = game_state.players.get(game_state.local_player_id)
        if not player:
            return

        bar = pygame.Surface((self.screen_w, self.resource_bar_height), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 180))
        surface.blit(bar, (0, 0))

        x = 20

        # Титан
        titan_text = self.font_medium.render(
            f"⛏ Titan: {int(player.titan)}", True, COLOR_TITAN_ORE
        )
        surface.blit(titan_text, (x, 6))
        x += titan_text.get_width() + 30

        # Плазма
        plasma_text = self.font_medium.render(
            f"⚡ Plasma: {int(player.plasma)}", True, COLOR_PLASMA_GEYSER
        )
        surface.blit(plasma_text, (x, 6))
        x += plasma_text.get_width() + 30

        # Supply
        supply_color = COLOR_UI_TEXT if player.current_supply < player.max_supply else COLOR_UI_DANGER
        supply_text = self.font_medium.render(
            f"👥 {player.current_supply} / {player.max_supply} ({player.supply_cap})",
            True, supply_color
        )
        surface.blit(supply_text, (x, 6))
        x += supply_text.get_width() + 30

        # Время игры
        game_time = int(game_state.game_time)
        minutes = game_time // 60
        seconds = game_time % 60
        time_text = self.font_medium.render(
            f"⏱ {minutes:02d}:{seconds:02d}", True, COLOR_UI_TEXT_DIM
        )
        surface.blit(time_text, (self.screen_w - time_text.get_width() - 20, 6))

        # FPS
        fps_text = self.font_small.render(
            f"FPS: {int(game_state.clock.get_fps())}", True, COLOR_UI_TEXT_DIM
        )
        surface.blit(fps_text, (self.screen_w - fps_text.get_width() - 20, 20))

    def _render_bottom_panel(self, surface, game_state, selected_entities):
        """Нижняя панель управления."""
        self.panel_surface.fill((0, 0, 0, 0))

        # Фон панели
        panel_bg = pygame.Surface((self.screen_w, self.panel_height), pygame.SRCALPHA)
        opacity = int(255 * game_settings.get('ui_opacity'))
        panel_bg.fill((20, 25, 30, opacity))
        surface.blit(panel_bg, (0, self.screen_h - self.panel_height))

        # Рамка
        pygame.draw.line(surface, COLOR_UI_PANEL_BORDER,
                         (0, self.screen_h - self.panel_height),
                         (self.screen_w, self.screen_h - self.panel_height), 2)

        panel_y = self.screen_h - self.panel_height + 5

        if not selected_entities:
            # Показываем вкладки строительства
            self._render_build_tabs(surface, game_state, panel_y)
        elif len(selected_entities) == 1:
            # Информация об одном юните/здании
            self._render_single_info(surface, selected_entities[0], panel_y, game_state)
        else:
            # Группа юнитов
            self._render_group_info(surface, selected_entities, panel_y)

    def _render_build_tabs(self, surface, game_state, panel_y):
        """Вкладки строительства."""
        self.tab_rects = []
        tab_x = 10
        tab_width = 120
        tab_height = 28

        for i, tab_name in enumerate(self.build_tabs):
            rect = pygame.Rect(tab_x + i * (tab_width + 5), panel_y, tab_width, tab_height)
            self.tab_rects.append(rect)

            color = COLOR_UI_ACCENT if i == self.current_tab else COLOR_UI_PANEL
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=4)

            text = self.font_small.render(tab_name, True, COLOR_UI_TEXT)
            surface.blit(text, (rect.x + 5, rect.y + 6))

        # Кнопки зданий текущей вкладки
        self.action_buttons = []
        category = self.build_tab_keys[self.current_tab]
        buildings = ALL_BUILDINGS.get(category, [])

        btn_y = panel_y + 35
        btn_x = 10

        player = game_state.players.get(game_state.local_player_id)

        for i, building_class in enumerate(buildings):
            temp = building_class(0, 0)
            rect = pygame.Rect(btn_x + i * (self.button_size + self.button_margin),
                               btn_y, self.button_size, self.button_size)

            # Можно ли позволить?
            can_afford = True
            if player:
                cost_mult = player.get_upgrade_bonus('building_cost', 1.0)
                can_afford = player.can_afford(
                    int(temp.cost_titan * cost_mult),
                    int(temp.cost_plasma * cost_mult)
                )

            bg_color = temp.color if can_afford else (60, 60, 60)
            pygame.draw.rect(surface, bg_color, rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=4)

            # Название
            name_text = self.font_small.render(temp.name[:6], True, COLOR_UI_TEXT)
            surface.blit(name_text, (rect.x + 2, rect.y + 2))

            # Стоимость
            cost_text = self.font_small.render(f"{temp.cost_titan}", True, COLOR_TITAN_ORE)
            surface.blit(cost_text, (rect.x + 2, rect.y + self.button_size - 14))

            self.action_buttons.append({
                'rect': rect,
                'building_class': building_class,
                'enabled': can_afford,
            })

    def _render_single_info(self, surface, entity, panel_y, game_state):
        """Информация об одном выделенном объекте."""
        x = 10

        # Имя
        name_text = self.font_large.render(entity.name, True, COLOR_UI_TEXT)
        surface.blit(name_text, (x, panel_y))

        # HP
        hp_text = self.font_medium.render(
            f"HP: {int(entity.hp)} / {entity.max_hp}", True, COLOR_HP_BAR_FULL
        )
        surface.blit(hp_text, (x, panel_y + 25))

        # Щит
        if entity.max_shield > 0:
            shield_text = self.font_medium.render(
                f"Shield: {int(entity.shield)} / {entity.max_shield}", True, COLOR_SHIELD_BAR
            )
            surface.blit(shield_text, (x, panel_y + 42))

        # Для юнитов — статы
        if entity.is_unit:
            stats_x = 250
            dmg_text = self.font_small.render(
                f"DMG: {entity.attack_damage}  RNG: {entity.attack_range}  SPD: {int(entity.speed)}",
                True, COLOR_UI_TEXT_DIM
            )
            surface.blit(dmg_text, (stats_x, panel_y + 5))

            stance_text = self.font_small.render(
                f"Stance: {entity.stance}", True, COLOR_UI_TEXT_DIM
            )
            surface.blit(stance_text, (stats_x, panel_y + 22))

        # Для зданий — очередь производства
        if entity.is_building and entity.can_produce and entity.is_completed:
            self.action_buttons = []
            btn_x = 250
            btn_y = panel_y + 5

            if hasattr(entity, 'get_producible_units'):
                for i, unit_class in enumerate(entity.get_producible_units()):
                    temp = unit_class(0, 0)
                    rect = pygame.Rect(
                        btn_x + i * (self.button_size + self.button_margin),
                        btn_y, self.button_size, self.button_size
                    )

                    player = game_state.players.get(game_state.local_player_id)
                    can_afford = True
                    if player:
                        can_afford = player.can_afford(temp.cost_titan, temp.cost_plasma)
                        can_afford = can_afford and (
                            player.current_supply + temp.supply_cost <= player.max_supply
                        )

                    bg_color = temp.color if can_afford else (60, 60, 60)
                    pygame.draw.rect(surface, bg_color, rect, border_radius=4)
                    pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=4)

                    name_text = self.font_small.render(temp.name[:6], True, COLOR_UI_TEXT)
                    surface.blit(name_text, (rect.x + 2, rect.y + 2))

                    cost_text = self.font_small.render(
                        f"{temp.cost_titan}", True, COLOR_TITAN_ORE
                    )
                    surface.blit(cost_text, (rect.x + 2, rect.y + self.button_size - 14))

                    self.action_buttons.append({
                        'rect': rect,
                        'unit_class': unit_class,
                        'building': entity,
                        'enabled': can_afford,
                    })

            # Показываем очередь производства
            queue_y = btn_y + self.button_size + 10
            queue_x = 250
            for i, (unit_class, build_time, elapsed) in enumerate(entity.production_queue):
                temp = unit_class(0, 0)
                qr = pygame.Rect(queue_x + i * 30, queue_y, 25, 25)
                progress = elapsed / build_time if build_time > 0 else 0
                pygame.draw.rect(surface, (40, 40, 60), qr)
                fill_h = int(25 * progress)
                if fill_h > 0:
                    pygame.draw.rect(surface, COLOR_UI_ACCENT,
                                     (qr.x, qr.bottom - fill_h, 25, fill_h))
                pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, qr, 1)

    def _render_group_info(self, surface, entities, panel_y):
        """Информация о группе юнитов."""
        # Считаем типы
        type_counts = {}
        for entity in entities:
            name = entity.name
            if name not in type_counts:
                type_counts[name] = {'count': 0, 'color': entity.color}
            type_counts[name]['count'] += 1

        x = 10
        y = panel_y

        header = self.font_medium.render(
            f"Selected: {len(entities)} units", True, COLOR_UI_TEXT
        )
        surface.blit(header, (x, y))
        y += 22

        for name, data in type_counts.items():
            text = self.font_small.render(
                f"{name}: {data['count']}", True, COLOR_UI_TEXT_DIM
            )
            pygame.draw.rect(surface, data['color'], (x, y + 2, 10, 10))
            surface.blit(text, (x + 14, y))
            y += 16
            if y > self.screen_h - 20:
                break

    def _render_upgrade_slots(self, surface, game_state):
        """Слоты активных улучшений."""
        player = game_state.players.get(game_state.local_player_id)
        if not player:
            return

        slot_x = self.screen_w - (UPGRADE_SLOTS * (self.upgrade_slot_size + 5)) - 10
        slot_y = self.resource_bar_height + 5

        for i in range(UPGRADE_SLOTS):
            rect = pygame.Rect(slot_x + i * (self.upgrade_slot_size + 5),
                               slot_y, self.upgrade_slot_size, self.upgrade_slot_size)

            if i < len(player.active_upgrades):
                upgrade = player.active_upgrades[i]
                pygame.draw.rect(surface, upgrade.icon_color, rect, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=4)

                text = self.font_small.render(upgrade.name[:4], True, (0, 0, 0))
                surface.blit(text, (rect.x + 2, rect.y + 2))
            else:
                pygame.draw.rect(surface, (30, 35, 40), rect, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=4)

    def handle_click(self, pos, game_state, command_system):
        """Обработка клика по HUD."""
        x, y = pos

        # Вкладки строительства
        for i, rect in enumerate(self.tab_rects):
            if rect.collidepoint(x, y):
                self.current_tab = i
                return True

        # Кнопки действий
        for btn in self.action_buttons:
            if btn['rect'].collidepoint(x, y) and btn['enabled']:
                if 'building_class' in btn:
                    command_system.enter_build_mode(btn['building_class'])
                    return True
                elif 'unit_class' in btn and 'building' in btn:
                    btn['building'].queue_unit(btn['unit_class'], game_state)
                    return True

        return False

    def resize(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.panel_rect = pygame.Rect(
            0, screen_h - self.panel_height,
            screen_w, self.panel_height
        )
