"""
botyaraRTS - ui/hud.py
Основной HUD: ресурсы, панель управления, информация о выделенных юнитах.
"""
import pygame
from settings import *
from entities.building import ALL_BUILDINGS
from localization import t, t_unit, t_building
from ui.font_utils import SmartFont


class HUD:
    """Игровой интерфейс."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Панель управления (нижняя центральная консоль)
        self.panel_height = 200
        self.panel_width = max(520, min(680, screen_w - 440)) if screen_w >= 900 else max(350, screen_w - 240)
        self.panel_x = (screen_w - self.panel_width) // 2
        self.panel_y = screen_h - self.panel_height - 10
        self.panel_rect = pygame.Rect(
            self.panel_x, self.panel_y,
            self.panel_width, self.panel_height
        )

        # Вкладки строительства
        self.build_tabs = [t('hud.tab_base'), t('hud.tab_defense'), t('hud.tab_advanced'), t('hud.tab_units')]
        self.build_tab_keys = ['economy', 'production', 'research', 'defense']
        self.current_tab = 0
        self.tab_rects = []

        # Кнопки юнитов в панели
        self.action_buttons = []
        self.button_size = 52
        self.button_margin = 6

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
        self.font_large = SmartFont(24, bold=True)
        self.font_medium = SmartFont(18, bold=True)
        self.font_small = SmartFont(14)

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
            t('hud.titan', amount=int(player.titan)), True, COLOR_TITAN_ORE
        )
        surface.blit(titan_text, (x, 6))
        x += titan_text.get_width() + 30

        # Плазма
        plasma_text = self.font_medium.render(
            t('hud.plasma', amount=int(player.plasma)), True, COLOR_PLASMA_GEYSER
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
            t('hud.fps', fps=int(game_state.clock.get_fps())), True, COLOR_UI_TEXT_DIM
        )
        surface.blit(fps_text, (self.screen_w - fps_text.get_width() - 20, 20))

    def _render_bottom_panel(self, surface, game_state, selected_entities):
        """Нижняя панель управления (красивая центрированная карточка)."""
        opacity = int(255 * game_settings.get('ui_opacity'))
        panel_bg = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_bg, (20, 25, 30, opacity), (0, 0, self.panel_width, self.panel_height), border_radius=12)
        pygame.draw.rect(panel_bg, COLOR_UI_PANEL_BORDER, (0, 0, self.panel_width, self.panel_height), 2, border_radius=12)
        surface.blit(panel_bg, (self.panel_x, self.panel_y))

        panel_y = self.panel_y + 12

        if not selected_entities:
            self.action_buttons = []
            self.tab_rects = []
            text = self.font_medium.render(t('hud.no_selection'), True, COLOR_UI_TEXT_DIM)
            surface.blit(text, (self.panel_x + self.panel_width // 2 - text.get_width() // 2, panel_y + 30))
        elif len(selected_entities) == 1:
            # Информация об одном юните/здании
            self._render_single_info(surface, selected_entities[0], panel_y, game_state)
        else:
            # Группа юнитов
            self._render_group_info(surface, selected_entities, panel_y)

    def _render_build_tabs(self, surface, game_state, panel_y, start_x=None):
        """Вкладки строительства."""
        if start_x is None:
            start_x = self.panel_x + 15
        self.tab_rects = []
        tab_x = start_x
        tab_width = 100
        tab_height = 26

        for i, tab_name in enumerate(self.build_tabs):
            rect = pygame.Rect(tab_x + i * (tab_width + 4), panel_y, tab_width, tab_height)
            self.tab_rects.append(rect)

            color = COLOR_UI_ACCENT if i == self.current_tab else COLOR_UI_PANEL
            pygame.draw.rect(surface, color, rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=6)

            text = self.font_small.render(tab_name, True, COLOR_UI_TEXT)
            surface.blit(text, (rect.x + 4, rect.y + 5))

        # Кнопки зданий текущей вкладки
        self.action_buttons = []
        category = self.build_tab_keys[self.current_tab]
        buildings = ALL_BUILDINGS.get(category, [])

        btn_y = panel_y + 36
        btn_x = start_x

        player = game_state.players.get(game_state.local_player_id)

        for i, building_class in enumerate(buildings):
            temp = building_class(0, 0)
            rect = pygame.Rect(btn_x + i * (self.button_size + self.button_margin),
                               btn_y, self.button_size, self.button_size)

            can_afford = True
            if player:
                cost_mult = player.get_upgrade_bonus('building_cost', 1.0)
                can_afford = player.can_afford(
                    int(temp.cost_titan * cost_mult),
                    int(temp.cost_plasma * cost_mult)
                )

            bg_color = temp.color if can_afford else (60, 60, 60)
            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=6)

            # Название
            display_name = t_building(temp.name)
            name_text = self.font_small.render(display_name[:7], True, COLOR_UI_TEXT)
            surface.blit(name_text, (rect.x + 2, rect.y + 2))

            # Стоимость
            cost_text = self.font_small.render(f"{temp.cost_titan}", True, COLOR_TITAN_ORE)
            surface.blit(cost_text, (rect.x + 2, rect.y + self.button_size - 16))

            self.action_buttons.append({
                'rect': rect,
                'building_class': building_class,
                'enabled': can_afford,
            })

    def _render_single_info(self, surface, entity, panel_y, game_state):
        """Информация об одном выделенном объекте."""
        x = self.panel_x + 15

        # Имя
        display_name = t_unit(entity.name) if entity.is_unit else t_building(entity.name)
        name_text = self.font_large.render(display_name, True, COLOR_UI_TEXT)
        surface.blit(name_text, (x, panel_y))

        # HP
        hp_text = self.font_medium.render(
            t('hud.hp', current=int(entity.hp), max=entity.max_hp), True, COLOR_HP_BAR_FULL
        )
        surface.blit(hp_text, (x, panel_y + 28))

        # Щит
        if entity.max_shield > 0:
            shield_text = self.font_medium.render(
                t('hud.shield', current=int(entity.shield), max=entity.max_shield), True, COLOR_SHIELD_BAR
            )
            surface.blit(shield_text, (x, panel_y + 48))

        # Для рабочего — отображаем кнопки строительства на панели справа
        if getattr(entity, 'can_build', False) or getattr(entity, 'name', '') == 'Worker':
            self._render_build_tabs(surface, game_state, panel_y, start_x=self.panel_x + 180)
            return

        # Для остальных юнитов — статы
        if entity.is_unit:
            stats_x = self.panel_x + 240
            dmg_text = self.font_small.render(
                t('hud.dmg_rng_spd', dmg=entity.attack_damage, rng=entity.attack_range, spd=int(entity.speed)),
                True, COLOR_UI_TEXT_DIM
            )
            surface.blit(dmg_text, (stats_x, panel_y + 5))

            stance_text = self.font_small.render(
                t('hud.stance', stance=t(f'stance.{entity.stance}')), True, COLOR_UI_TEXT_DIM
            )
            surface.blit(stance_text, (stats_x, panel_y + 25))

        # Для зданий — очередь производства
        if entity.is_building and entity.can_produce and entity.is_completed:
            self.action_buttons = []
            btn_x = self.panel_x + 240
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
                    pygame.draw.rect(surface, bg_color, rect, border_radius=6)
                    pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, rect, 1, border_radius=6)

                    display_name = t_unit(temp.name)
                    name_text = self.font_small.render(display_name[:7], True, COLOR_UI_TEXT)
                    surface.blit(name_text, (rect.x + 2, rect.y + 2))

                    cost_text = self.font_small.render(
                        f"{temp.cost_titan}", True, COLOR_TITAN_ORE
                    )
                    surface.blit(cost_text, (rect.x + 2, rect.y + self.button_size - 16))

                    self.action_buttons.append({
                        'rect': rect,
                        'unit_class': unit_class,
                        'building': entity,
                        'enabled': can_afford,
                    })

            # Показываем очередь производства
            queue_y = btn_y + self.button_size + 12
            queue_x = self.panel_x + 240
            for i, (unit_class, build_time, elapsed) in enumerate(entity.production_queue):
                temp = unit_class(0, 0)
                qr = pygame.Rect(queue_x + i * 32, queue_y, 28, 28)
                progress = elapsed / build_time if build_time > 0 else 0
                pygame.draw.rect(surface, (40, 40, 60), qr, border_radius=4)
                fill_h = int(28 * progress)
                if fill_h > 0:
                    pygame.draw.rect(surface, COLOR_UI_ACCENT,
                                     (qr.x, qr.bottom - fill_h, 28, fill_h), border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_PANEL_BORDER, qr, 1, border_radius=4)

    def _render_group_info(self, surface, entities, panel_y):
        """Информация о группе юнитов."""
        type_counts = {}
        for entity in entities:
            name = entity.name
            if name not in type_counts:
                type_counts[name] = {'count': 0, 'color': entity.color}
            type_counts[name]['count'] += 1

        x = self.panel_x + 15
        y = panel_y

        header = self.font_medium.render(
            t('hud.selected', count=len(entities)), True, COLOR_UI_TEXT
        )
        surface.blit(header, (x, y))
        y += 24

        for name, data in type_counts.items():
            text = self.font_small.render(
                f"{name}: {data['count']}", True, COLOR_UI_TEXT_DIM
            )
            pygame.draw.rect(surface, data['color'], (x, y + 2, 10, 10))
            surface.blit(text, (x + 14, y))
            y += 18
            if y > self.panel_y + self.panel_height - 20:
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
        self.panel_width = max(520, min(680, screen_w - 440)) if screen_w >= 900 else max(350, screen_w - 240)
        self.panel_x = (screen_w - self.panel_width) // 2
        self.panel_y = screen_h - self.panel_height - 10
        self.panel_rect = pygame.Rect(
            self.panel_x, self.panel_y,
            self.panel_width, self.panel_height
        )
