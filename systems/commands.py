"""
botyaraRTS - systems/commands.py
Обработка команд строительства и приказов.
"""
import pygame
from settings import *
from entities.building import *


class CommandSystem:
    """Управление командами (строительство, приказы)."""

    def __init__(self):
        # Режим строительства
        self.build_mode = False
        self.build_class = None  # класс здания
        self.build_preview_pos = None  # (tile_x, tile_y)
        self.build_valid = False

    def enter_build_mode(self, building_class):
        """Войти в режим строительства."""
        self.build_mode = True
        self.build_class = building_class

    def cancel_build_mode(self):
        """Отменить режим строительства."""
        self.build_mode = False
        self.build_class = None
        self.build_preview_pos = None

    def update_build_preview(self, mouse_pos, camera, tilemap):
        """Обновить превью здания под курсором."""
        if not self.build_mode:
            return

        world_x, world_y = camera.screen_to_world(*mouse_pos)
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)

        self.build_preview_pos = (tile_x, tile_y)

        # Проверяем можно ли строить
        temp = self.build_class(0, 0)
        self.build_valid = tilemap.is_buildable(tile_x, tile_y, temp.size_tiles)

    def try_place_building(self, game_state, player_id):
        """Попытаться поставить здание."""
        if not self.build_mode or not self.build_preview_pos or not self.build_valid:
            return False

        tx, ty = self.build_preview_pos
        player = game_state.players.get(player_id)
        if not player:
            return False

        # Создаём временный экземпляр для проверки стоимости
        temp = self.build_class(0, 0)

        # Бонус от улучшения
        cost_mult = player.get_upgrade_bonus('building_cost', 1.0)
        titan_cost = int(temp.cost_titan * cost_mult)
        plasma_cost = int(temp.cost_plasma * cost_mult)

        if not player.can_afford(titan_cost, plasma_cost):
            return False

        # Списываем ресурсы
        player.spend(titan_cost, plasma_cost)

        # Создаём здание
        world_x = tx * TILE_SIZE + (temp.size_tiles * TILE_SIZE) // 2
        world_y = ty * TILE_SIZE + (temp.size_tiles * TILE_SIZE) // 2

        building = self.build_class(world_x, world_y, player_id)
        building.construction_progress = 0
        building.hp = int(building.max_hp * 0.1)  # Начинает с 10% HP

        game_state.add_entity(building)

        # Отправляем ближайшего рабочего строить
        self._send_worker_to_build(building, game_state, player_id)

        player.buildings_built += 1

        # Не выходим из режима строительства если зажат Shift
        keys = pygame.key.get_pressed()
        if not (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            self.cancel_build_mode()

        return True

    def _send_worker_to_build(self, building, game_state, player_id):
        """Найти и отправить ближайшего свободного рабочего."""
        from entities.worker import Worker

        nearest_worker = None
        min_dist = float('inf')

        for entity in game_state.get_all_entities():
            if isinstance(entity, Worker) and entity.player_id == player_id and entity.alive:
                if entity.building_state == 'IDLE' and entity.harvest_state == 'IDLE' and \
                   entity.state == 'IDLE':
                    dist = entity.distance_to(building)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_worker = entity

        if nearest_worker:
            nearest_worker.command_build(building)

    def render_build_preview(self, surface, camera, tilemap):
        """Отрисовка превью здания."""
        if not self.build_mode or not self.build_preview_pos:
            return

        tx, ty = self.build_preview_pos
        temp = self.build_class(0, 0)
        size = temp.size_tiles

        for dy in range(size):
            for dx in range(size):
                wx = (tx + dx) * TILE_SIZE
                wy = (ty + dy) * TILE_SIZE
                sx, sy = camera.world_to_screen(wx, wy)
                tile_size = int(TILE_SIZE * camera.zoom)

                can_build = tilemap.is_buildable(tx + dx, ty + dy, 1)
                color = (0, 200, 0, 80) if can_build else (200, 0, 0, 80)

                preview = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                preview.fill(color)
                surface.blit(preview, (int(sx), int(sy)))

                border_color = (0, 255, 0) if self.build_valid else (255, 0, 0)
                pygame.draw.rect(surface, border_color,
                                 (int(sx), int(sy), tile_size, tile_size), 1)
