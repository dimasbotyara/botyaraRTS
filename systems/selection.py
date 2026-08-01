"""
botyaraRTS - systems/selection.py
Система выделения юнитов: рамка, клик, двойной клик, группы.
"""
import pygame
import time
from settings import *


class SelectionSystem:
    """Управление выделением юнитов и зданий."""

    def __init__(self):
        # Текущий выбор
        self.selected_entities = []

        # Рамка выделения
        self.is_dragging = False
        self.drag_start = None  # (screen_x, screen_y)
        self.drag_current = None
        self.min_drag_distance = 5

        # Двойной клик
        self.last_click_time = 0
        self.last_click_pos = None
        self.double_click_speed = 0.3

        # Группы (Ctrl+1..9)
        self.groups = {}  # {1: [entity, ...], 2: [...], ...}
        self.last_group_press = {}  # {номер: время} для двойного нажатия

    def handle_mouse_down(self, pos, button, camera, game_state):
        """Обработка нажатия мыши."""
        if button == 1:  # ЛКМ
            # Проверяем миникарту
            if hasattr(game_state, 'minimap') and game_state.minimap.is_point_on_minimap(*pos):
                return

            # Проверяем UI панель
            if hasattr(game_state, 'hud') and game_state.hud.is_point_on_panel(*pos):
                return

            self.is_dragging = True
            self.drag_start = pos
            self.drag_current = pos

    def handle_mouse_up(self, pos, button, camera, game_state, keys):
        """Обработка отпускания мыши."""
        if button == 1:  # ЛКМ
            if self.is_dragging:
                if self.drag_start and self._get_drag_distance() > self.min_drag_distance:
                    # Выделение рамкой
                    self._select_in_rect(camera, game_state, keys)
                else:
                    # Клик
                    self._handle_click(pos, camera, game_state, keys)

                self.is_dragging = False
                self.drag_start = None
                self.drag_current = None

        elif button == 3:  # ПКМ
            self._handle_right_click(pos, camera, game_state, keys)

    def handle_mouse_move(self, pos):
        """Обновление позиции при перетаскивании."""
        if self.is_dragging:
            self.drag_current = pos

    def _get_drag_distance(self):
        """Расстояние перетаскивания."""
        if not self.drag_start or not self.drag_current:
            return 0
        dx = self.drag_current[0] - self.drag_start[0]
        dy = self.drag_current[1] - self.drag_start[1]
        return (dx * dx + dy * dy) ** 0.5

    def _handle_click(self, pos, camera, game_state, keys):
        """Обработка одиночного клика."""
        world_x, world_y = camera.screen_to_world(*pos)

        # Проверяем двойной клик
        current_time = time.time()
        is_double_click = False
        if self.last_click_pos:
            dx = pos[0] - self.last_click_pos[0]
            dy = pos[1] - self.last_click_pos[1]
            if (dx * dx + dy * dy) < 400 and \
               (current_time - self.last_click_time) < self.double_click_speed:
                is_double_click = True

        self.last_click_time = current_time
        self.last_click_pos = pos

        # Ищем объект под курсором
        clicked_entity = self._find_entity_at(world_x, world_y, game_state)

        if is_double_click and clicked_entity and clicked_entity.is_unit:
            # Двойной клик — выделить всех одинаковых юнитов на экране
            self._select_all_same_type(clicked_entity, camera, game_state)
            return

        # Shift — добавить/убрать из выделения
        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if clicked_entity:
            if shift_held:
                if clicked_entity in self.selected_entities:
                    self._deselect(clicked_entity)
                else:
                    self._add_to_selection(clicked_entity)
            else:
                self._select_single(clicked_entity)
        else:
            if not shift_held:
                self.clear_selection()

    def _handle_right_click(self, pos, camera, game_state, keys):
        """ПКМ — контекстная команда."""
        if not self.selected_entities:
            return

        world_x, world_y = camera.screen_to_world(*pos)
        target_entity = self._find_entity_at(world_x, world_y, game_state)

        # Проверяем только свои юниты
        own_units = [e for e in self.selected_entities
                     if e.is_unit and e.player_id == game_state.local_player_id]
        own_buildings = [e for e in self.selected_entities
                         if e.is_building and e.player_id == game_state.local_player_id]

        if target_entity:
            if target_entity.player_id != game_state.local_player_id:
                # Вражеский объект — атака
                for unit in own_units:
                    unit.attack_target_entity(target_entity)
            else:
                # Свой объект — ??? (ремонт, загрузка в транспорт)
                pass
        else:
            # Клик по земле
            # Проверяем ресурсы
            tile_x = int(world_x // TILE_SIZE)
            tile_y = int(world_y // TILE_SIZE)
            tile = game_state.tilemap.get_tile(tile_x, tile_y)

            from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER
            from entities.worker import Worker

            if tile in (TILE_TITAN_ORE, TILE_PLASMA_GEYSER):
                # Отправляем рабочих на добычу
                for unit in own_units:
                    if isinstance(unit, Worker):
                        unit.command_harvest(tile_x, tile_y)
                    else:
                        unit.move_to_point(world_x, world_y, game_state.tilemap)
            else:
                # Приказ движения
                for unit in own_units:
                    unit.move_to_point(world_x, world_y, game_state.tilemap)

                # Rally point для зданий
                for building in own_buildings:
                    if building.can_produce:
                        building.set_rally_point(world_x, world_y)

    def _select_in_rect(self, camera, game_state, keys):
        """Выделение рамкой."""
        if not self.drag_start or not self.drag_current:
            return

        # Экранные координаты рамки
        x1 = min(self.drag_start[0], self.drag_current[0])
        y1 = min(self.drag_start[1], self.drag_current[1])
        x2 = max(self.drag_start[0], self.drag_current[0])
        y2 = max(self.drag_start[1], self.drag_current[1])

        # Мировые координаты
        wx1, wy1 = camera.screen_to_world(x1, y1)
        wx2, wy2 = camera.screen_to_world(x2, y2)

        world_rect = pygame.Rect(wx1, wy1, wx2 - wx1, wy2 - wy1)

        shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if not shift_held:
            self.clear_selection()

        # Ищем юнитов в рамке (только своих)
        if hasattr(game_state, 'spatial_hash'):
            entities = game_state.spatial_hash.query_rect(world_rect)
            for entity in entities:
                if entity.alive and entity.player_id == game_state.local_player_id:
                    if entity.is_unit:
                        self._add_to_selection(entity)

        # Если нет юнитов — выделяем здания
        if not self.selected_entities:
            if hasattr(game_state, 'spatial_hash'):
                entities = game_state.spatial_hash.query_rect(world_rect)
                for entity in entities:
                    if entity.alive and entity.is_building and \
                       entity.player_id == game_state.local_player_id:
                        self._add_to_selection(entity)

    def _select_all_same_type(self, reference, camera, game_state):
        """Выделить всех юнитов того же типа на экране."""
        self.clear_selection()
        visible_rect = camera.get_visible_rect()

        if hasattr(game_state, 'spatial_hash'):
            entities = game_state.spatial_hash.query_rect(visible_rect)
            for entity in entities:
                if entity.alive and entity.__class__ == reference.__class__ and \
                   entity.player_id == game_state.local_player_id:
                    self._add_to_selection(entity)

    def _find_entity_at(self, world_x, world_y, game_state):
        """Найти объект в точке."""
        if hasattr(game_state, 'spatial_hash'):
            nearest = game_state.spatial_hash.query_nearest(
                world_x, world_y, TILE_SIZE * 2
            )
            if nearest and nearest.distance_to_point(world_x, world_y) < nearest.radius + 8:
                return nearest
        return None

    def _select_single(self, entity):
        """Выделить один объект."""
        self.clear_selection()
        self._add_to_selection(entity)

    def _add_to_selection(self, entity):
        """Добавить в выделение."""
        if entity not in self.selected_entities:
            entity.selected = True
            self.selected_entities.append(entity)

    def _deselect(self, entity):
        """Убрать из выделения."""
        entity.selected = False
        if entity in self.selected_entities:
            self.selected_entities.remove(entity)

    def clear_selection(self):
        """Очистить всё выделение."""
        for entity in self.selected_entities:
            entity.selected = False
        self.selected_entities.clear()

    def handle_group_key(self, number, keys):
        """Обработка горячих клавиш групп (Ctrl+1..9, 1..9)."""
        ctrl = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        current_time = time.time()

        if ctrl:
            # Ctrl+N — сохранить группу
            if self.selected_entities:
                self.groups[number] = list(self.selected_entities)
        else:
            # N — вызвать группу
            if number in self.groups:
                # Убираем мёртвых
                self.groups[number] = [e for e in self.groups[number] if e.alive]

                if self.groups[number]:
                    self.clear_selection()
                    for entity in self.groups[number]:
                        self._add_to_selection(entity)

                    # Двойное нажатие — центрировать камеру
                    last_press = self.last_group_press.get(number, 0)
                    if current_time - last_press < 0.4:
                        return self._get_group_center(number)

                    self.last_group_press[number] = current_time

        return None

    def _get_group_center(self, number):
        """Центр группы для камеры."""
        group = self.groups.get(number, [])
        if not group:
            return None
        cx = sum(e.x for e in group) / len(group)
        cy = sum(e.y for e in group) / len(group)
        return (cx, cy)

    def render_selection_box(self, surface):
        """Отрисовка рамки выделения."""
        if not self.is_dragging or not self.drag_start or not self.drag_current:
            return
        if self._get_drag_distance() < self.min_drag_distance:
            return

        x1, y1 = self.drag_start
        x2, y2 = self.drag_current
        rect = pygame.Rect(
            min(x1, x2), min(y1, y2),
            abs(x2 - x1), abs(y2 - y1)
        )

        # Полупрозрачная заливка
        fill_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fill_surface.fill((0, 255, 100, 30))
        surface.blit(fill_surface, rect.topleft)

        # Рамка
        pygame.draw.rect(surface, COLOR_SELECTION_BOX, rect, 1)

    def update(self):
        """Очистка мёртвых из выделения."""
        self.selected_entities = [e for e in self.selected_entities if e.alive]
