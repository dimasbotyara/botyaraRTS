"""
botyaraRTS - entities/aircraft.py
Авиация — игнорирует ландшафт, летает напрямую.
"""
import math
import random
import pygame
from entities.unit import Unit
from settings import *


class AircraftUnit(Unit):
    """Базовый класс для всей авиации."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.is_flying = True
        self.unit_type = 'aircraft'

    def move_to_point(self, world_x, world_y, tilemap, attack_move=False, shift=False):
        """Авиация летит напрямую — без A*! Поддерживает Shift-очередь."""
        if not hasattr(self, 'command_queue'):
            self.command_queue = []

        if shift and self.state != 'IDLE':
            self.command_queue.append(('move', (world_x, world_y, tilemap, attack_move)))
            return True

        self.command_queue.clear()
        # Летим напрямую к цели
        self.path = [(int(world_x // TILE_SIZE), int(world_y // TILE_SIZE))]
        self.path_index = 0
        self.state = 'MOVE'
        self.attack_target = None
        self.move_target = (world_x, world_y)
        return True

    def _state_move(self, dt, game_state):
        """Летим напрямую к цели."""
        if not self.move_target:
            self.state = 'IDLE'
            return

        arrived = self._move_towards(self.move_target[0], self.move_target[1], dt)
        if arrived:
            self.state = 'IDLE'
            self.move_target = None

        # Агрессивный стенс
        if self.stance == 'AGGRESSIVE':
            enemy = self._find_enemy_in_range(game_state, self.aggro_range)
            if enemy:
                self.origin_point = (self.x, self.y)
                self.attack_target = enemy
                self.state = 'PURSUIT'


class ScoutDrone(AircraftUnit):
    """Дрон-разведчик — невидимый шпион, бонус дальности союзникам."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Scout Drone"
        self.color = (150, 200, 220)

        self.max_hp = 30
        self.hp = 30
        self.speed = 120
        self.attack_damage = 0
        self.attack_range = 0
        self.armor_type = 'light'
        self.vision_range = 12
        self.is_cloaked = True
        self.is_detector = True

        self.cost_titan = 60
        self.cost_plasma = 20
        self.supply_cost = 1
        self.build_time = 15

        self.relay_range = 160  # радиус бонуса дальности
        self.relay_bonus = 0.2  # +20%


class AttackHelicopter(AircraftUnit):
    """Штурмовой вертолёт — стреляет на ходу!"""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Attack Helicopter"
        self.color = (120, 150, 100)

        self.max_hp = 120
        self.hp = 120
        self.speed = 100
        self.attack_damage = 18
        self.attack_range = 128
        self.attack_cooldown = 1.0
        self.armor_type = 'light'
        self.damage_type = 'explosive'
        self.vision_range = 8
        self.can_attack_ground = True
        self.can_attack_air = False

        self.cost_titan = 180
        self.cost_plasma = 60
        self.supply_cost = 3
        self.build_time = 25

    def _state_move(self, dt, game_state):
        """Пассивка: стреляет на ходу."""
        super()._state_move(dt, game_state)
        # Даже во время движения ищем врагов
        if self.state == 'MOVE' and self.attack_timer <= 0:
            enemy = self._find_enemy_in_range(game_state, self.attack_range)
            if enemy and not enemy.is_flying:
                self._perform_attack(enemy, game_state)
                self.attack_timer = self.attack_cooldown


class Fighter(AircraftUnit):
    """Истребитель — только воздушные цели, шанс уклонения."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Fighter"
        self.color = (180, 180, 220)

        self.max_hp = 100
        self.hp = 100
        self.speed = 150
        self.attack_damage = 22
        self.attack_range = 160
        self.attack_cooldown = 1.2
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 9
        self.can_attack_ground = False
        self.can_attack_air = True

        self.cost_titan = 150
        self.cost_plasma = 50
        self.supply_cost = 2
        self.build_time = 22

        self.evasion_chance = 0.2  # 20% уклонение от ракет

    def take_damage(self, damage, damage_type='normal', attacker=None):
        """Пассивка: 20% уклонение от ракет."""
        if damage_type == 'explosive' and random.random() < self.evasion_chance:
            return 0  # Увернулся!
        return super().take_damage(damage, damage_type, attacker)


class Bomber(AircraftUnit):
    """Бомбардировщик — бомбит наземные цели, при смерти падает."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Bomber"
        self.color = (140, 100, 80)

        self.max_hp = 180
        self.hp = 180
        self.speed = 60
        self.attack_damage = 60
        self.attack_range = 80
        self.attack_cooldown = 3.0
        self.armor_type = 'heavy'
        self.damage_type = 'siege'
        self.vision_range = 6
        self.can_attack_ground = True
        self.can_attack_air = False
        self.aoe_radius = 64

        self.cost_titan = 250
        self.cost_plasma = 100
        self.supply_cost = 4
        self.build_time = 35

    def _perform_attack(self, target, game_state):
        """Бомбит по площади."""
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                target.x, target.y, self.aoe_radius
            )
            for entity in nearby:
                if entity.id == self.id:
                    continue
                if entity.is_flying:
                    continue
                damage = self._apply_damage_modifiers(self.attack_damage, entity)
                entity.take_damage(damage, self.damage_type, attacker=self)
        self.attack_count += 1
        if hasattr(game_state, 'camera'):
            game_state.camera.shake(6, 0.3)

    def die(self, killer=None):
        """Пассивка: при смерти падает и взрывается."""
        # AoE урон в точке смерти
        self.alive = False
        self.death_timer = 0
        # Камикадзе-взрыв будет обработан в game_state


class Transport(AircraftUnit):
    """Десантный корабль — перевозит юнитов."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Transport"
        self.color = (160, 160, 120)

        self.max_hp = 200
        self.hp = 200
        self.speed = 75
        self.attack_damage = 0
        self.attack_range = 0
        self.armor_type = 'heavy'
        self.vision_range = 5

        self.cost_titan = 200
        self.cost_plasma = 50
        self.supply_cost = 2
        self.build_time = 30

        # Грузовой отсек
        self.cargo = []  # список юнитов внутри
        self.max_cargo_slots = 8  # 8 пехотинцев или 2 танка
        self.width = int(TILE_SIZE * 2)
        self.height = int(TILE_SIZE * 1.5)

    def load_unit(self, unit):
        """Загрузить юнит."""
        cargo_size = 1 if unit.unit_type == 'infantry' else 4
        current_load = sum(1 if u.unit_type == 'infantry' else 4 for u in self.cargo)
        if current_load + cargo_size <= self.max_cargo_slots:
            self.cargo.append(unit)
            unit.visible = False
            return True
        return False

    def unload_all(self, game_state):
        """Выгрузить всех."""
        for i, unit in enumerate(self.cargo):
            angle = (i / max(len(self.cargo), 1)) * math.pi * 2
            unit.x = self.x + math.cos(angle) * TILE_SIZE * 2
            unit.y = self.y + math.sin(angle) * TILE_SIZE * 2
            unit.visible = True
            unit.state = 'IDLE'
        self.cargo.clear()
