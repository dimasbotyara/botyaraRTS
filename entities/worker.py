"""
botyaraRTS - entities/worker.py
Рабочий: добыча ресурсов, строительство.
"""
import math
from entities.unit import Unit
from settings import *


class Worker(Unit):
    """Рабочий юнит — основа экономики."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)

        self.name = "Worker"
        self.color = (180, 160, 100)
        self.unit_type = 'infantry'

        # Статы
        self.max_hp = 60
        self.hp = 60
        self.speed = 70
        self.attack_damage = 5
        self.attack_range = 32
        self.attack_cooldown = 1.5
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 5

        # Стоимость
        self.cost_titan = 50
        self.cost_plasma = 0
        self.build_time = 12.0
        self.supply_cost = 1

        # Добыча
        self.harvest_state = 'IDLE'  # IDLE, GOING_TO_RESOURCE, HARVESTING, RETURNING
        self.carrying_resource = None  # 'titan' или 'plasma'
        self.carrying_amount = 0
        self.max_carry = WORKER_HARVEST_AMOUNT
        self.harvest_timer = 0
        self.harvest_target = None  # (tile_x, tile_y) ресурса
        self.return_target = None   # (world_x, world_y) ближайшего HQ/склада

        # Строительство
        self.building_state = 'IDLE'  # IDLE, GOING_TO_BUILD, BUILDING
        self.build_target = None  # объект здания в процессе стройки
        self.build_speed = WORKER_BUILD_SPEED

        # Пассивка: Задруга (Ganging Up)
        self.gang_bonus = 0  # рассчитывается динамически

    def update(self, dt, game_state):
        """Обновление рабочего."""
        if not self.alive:
            Entity.update(self, dt, game_state)
            return

        # Обновляем бонус «задруги»
        self._update_gang_bonus(game_state)

        # Если мы в режиме добычи
        if self.harvest_state != 'IDLE':
            self._update_harvest(dt, game_state)
            return

        # Если мы в режиме строительства
        if self.building_state != 'IDLE':
            self._update_building(dt, game_state)
            return

        # Иначе — обычное поведение юнита
        super().update(dt, game_state)

    def _update_gang_bonus(self, game_state):
        """Пассивка: +5% скорость за каждого рабочего рядом (до +30%)."""
        if not hasattr(game_state, 'spatial_hash'):
            return

        nearby = game_state.spatial_hash.query_radius(self.x, self.y, 96)
        worker_count = sum(
            1 for e in nearby
            if isinstance(e, Worker) and e.alive and e.player_id == self.player_id
            and e.id != self.id
        )
        self.gang_bonus = min(0.30, worker_count * 0.05)

    def _update_harvest(self, dt, game_state):
        """Цикл добычи ресурсов."""
        speed_mult = 1.0 + self.gang_bonus

        if self.harvest_state == 'GOING_TO_RESOURCE':
            if not self.harvest_target:
                self.harvest_state = 'IDLE'
                return

            tx, ty = self.harvest_target
            target_x = tx * TILE_SIZE + TILE_SIZE // 2
            target_y = ty * TILE_SIZE + TILE_SIZE // 2

            arrived = self._move_towards(target_x, target_y, dt * speed_mult)
            if arrived:
                # Определяем тип ресурса
                tile = game_state.tilemap.get_tile(tx, ty)
                from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER
                if tile == TILE_TITAN_ORE:
                    self.carrying_resource = 'titan'
                elif tile == TILE_PLASMA_GEYSER:
                    self.carrying_resource = 'plasma'
                else:
                    self.harvest_state = 'IDLE'
                    return
                self.harvest_state = 'HARVESTING'
                self.harvest_timer = 0

        elif self.harvest_state == 'HARVESTING':
            self.harvest_timer += dt * speed_mult
            if self.harvest_timer >= WORKER_HARVEST_TIME:
                self.carrying_amount = self.max_carry
                self.harvest_state = 'RETURNING'
                # Находим ближайший HQ
                self.return_target = self._find_nearest_drop_off(game_state)
                if not self.return_target:
                    self.harvest_state = 'IDLE'

        elif self.harvest_state == 'RETURNING':
            if not self.return_target:
                self.harvest_state = 'IDLE'
                return

            arrived = self._move_towards(
                self.return_target[0], self.return_target[1], dt * speed_mult
            )
            if arrived:
                # Сдаём ресурсы
                if hasattr(game_state, 'players'):
                    player = game_state.players.get(self.player_id)
                    if player:
                        if self.carrying_resource == 'titan':
                            player.titan += self.carrying_amount
                        elif self.carrying_resource == 'plasma':
                            player.plasma += self.carrying_amount

                self.carrying_amount = 0
                self.carrying_resource = None

                # Идём обратно к ресурсу
                if self.harvest_target:
                    self.harvest_state = 'GOING_TO_RESOURCE'
                else:
                    self.harvest_state = 'IDLE'

    def _update_building(self, dt, game_state):
        """Цикл строительства."""
        speed_mult = 1.0 + self.gang_bonus

        if self.building_state == 'GOING_TO_BUILD':
            if not self.build_target or not self.build_target.alive:
                self.building_state = 'IDLE'
                return

            arrived = self._move_towards(
                self.build_target.x, self.build_target.y, dt * speed_mult
            )
            if arrived or self.distance_to(self.build_target) < TILE_SIZE * 2:
                self.building_state = 'BUILDING'

        elif self.building_state == 'BUILDING':
            if not self.build_target or not self.build_target.alive:
                self.building_state = 'IDLE'
                return

            if hasattr(self.build_target, 'construction_progress'):
                self.build_target.construction_progress += dt * self.build_speed * speed_mult
                if self.build_target.construction_progress >= self.build_target.build_time:
                    self.build_target.complete_construction()
                    self.building_state = 'IDLE'

    def _find_nearest_drop_off(self, game_state):
        """Найти ближайшее здание для сдачи ресурсов."""
        if not hasattr(game_state, 'buildings'):
            return None

        nearest = None
        min_dist = float('inf')

        for building in game_state.buildings:
            if building.player_id != self.player_id:
                continue
            if not building.alive or not building.is_completed:
                continue
            if not building.accepts_resources:
                continue

            dist = self.distance_to(building)
            if dist < min_dist:
                min_dist = dist
                nearest = building

        if nearest:
            return (nearest.x, nearest.y)
        return None

    def command_harvest(self, tile_x, tile_y):
        """Приказ идти добывать ресурс."""
        self.harvest_target = (tile_x, tile_y)
        self.harvest_state = 'GOING_TO_RESOURCE'
        self.state = 'IDLE'
        self.attack_target = None

    def command_build(self, building):
        """Приказ идти строить здание."""
        self.build_target = building
        self.building_state = 'GOING_TO_BUILD'
        self.state = 'IDLE'
        self.attack_target = None

    def render(self, surface, camera):
        """Отрисовка рабочего."""
        super().render(surface, camera)

        if not self.alive:
            return

        # Индикатор несомого ресурса
        if self.carrying_amount > 0:
            screen_rect = self.get_screen_rect(camera)
            resource_color = COLOR_TITAN_ORE if self.carrying_resource == 'titan' else COLOR_PLASMA_GEYSER
            dot_size = max(3, int(4 * camera.zoom))
            pygame.draw.circle(
                surface, resource_color,
                (screen_rect.centerx, screen_rect.top - 2),
                dot_size
            )
