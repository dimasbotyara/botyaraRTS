"""
botyaraRTS - entities/special_units.py
Спец-юниты: диверсант, пси-юнит, заминщик, супер-юнит.
"""
import math
import random
import pygame
from entities.unit import Unit
from entities.aircraft import AircraftUnit
from settings import *


class Saboteur(Unit):
    """Диверсант — невидимый, закладывает бомбы."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Saboteur"
        self.color = (80, 60, 100)
        self.unit_type = 'special'

        self.max_hp = 60
        self.hp = 60
        self.speed = 90
        self.attack_damage = 100  # бомба
        self.attack_range = 32
        self.attack_cooldown = 5.0
        self.armor_type = 'light'
        self.damage_type = 'siege'
        self.vision_range = 6
        self.is_cloaked = True

        self.cost_titan = 100
        self.cost_plasma = 75
        self.supply_cost = 2
        self.build_time = 30

        self.bomb_timer = 0
        self.bomb_cooldown = 15.0
        self.bomb_damage = 200

    def _perform_attack(self, target, game_state):
        """Снимаем стелс при атаке."""
        self.is_cloaked = False
        super()._perform_attack(target, game_state)

    def plant_bomb(self, game_state):
        """Заложить бомбу (активная способность)."""
        if self.bomb_timer > 0:
            return False
        self.bomb_timer = self.bomb_cooldown
        # Бомба взрывается через 3 секунды
        if hasattr(game_state, 'add_delayed_effect'):
            game_state.add_delayed_effect(
                delay=3.0,
                x=self.x, y=self.y,
                radius=96,
                damage=self.bomb_damage,
                damage_type='siege',
                owner_id=self.player_id
            )
        self.is_cloaked = False
        return True

    def update(self, dt, game_state):
        super().update(dt, game_state)
        if self.bomb_timer > 0:
            self.bomb_timer -= dt
        # Восстанавливаем стелс вне боя
        if self.state == 'IDLE' and self.attack_timer <= 0:
            self.is_cloaked = True


class PsiUnit(Unit):
    """Ментальный маг — контроль разума, щиты."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Psi Operative"
        self.color = (160, 80, 200)
        self.unit_type = 'special'

        self.max_hp = 80
        self.hp = 80
        self.speed = 65
        self.attack_damage = 15
        self.attack_range = 128
        self.attack_cooldown = 1.5
        self.armor_type = 'light'
        self.damage_type = 'energy'
        self.vision_range = 8

        self.cost_titan = 150
        self.cost_plasma = 100
        self.supply_cost = 3
        self.build_time = 35

        # Энергия для способностей
        self.energy = 100
        self.max_energy = 100
        self.energy_regen = 2.0  # в секунду

        # Способности
        self.mind_control_cost = 75
        self.shield_cost = 40
        self.shield_amount = 100

    def update(self, dt, game_state):
        super().update(dt, game_state)
        if self.alive:
            self.energy = min(self.max_energy, self.energy + self.energy_regen * dt)

    def cast_mind_control(self, target):
        """Контроль разума — переводит юнит на свою сторону."""
        if self.energy < self.mind_control_cost:
            return False
        if target.is_building or not target.alive:
            return False
        self.energy -= self.mind_control_cost
        target.player_id = self.player_id
        return True

    def cast_shield(self, target):
        """Защитный щит на союзника."""
        if self.energy < self.shield_cost:
            return False
        if not target.alive:
            return False
        self.energy -= self.shield_cost
        target.max_shield = max(target.max_shield, self.shield_amount)
        target.shield = self.shield_amount
        return True


class MineDrone(Unit):
    """Дрон-заминщик — ставит мины."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Mine Layer"
        self.color = (120, 120, 60)
        self.unit_type = 'special'

        self.max_hp = 50
        self.hp = 50
        self.speed = 80
        self.attack_damage = 5
        self.attack_range = 48
        self.attack_cooldown = 1.0
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 5

        self.cost_titan = 60
        self.cost_plasma = 30
        self.supply_cost = 1
        self.build_time = 15

        self.mine_count = 5
        self.max_mines = 5
        self.mine_recharge = 10.0
        self.mine_timer = 0
        self.mine_damage = 80

    def update(self, dt, game_state):
        super().update(dt, game_state)
        if self.alive and self.mine_count < self.max_mines:
            self.mine_timer += dt
            if self.mine_timer >= self.mine_recharge:
                self.mine_count += 1
                self.mine_timer = 0

    def place_mine(self, game_state):
        """Поставить мину."""
        if self.mine_count <= 0:
            return False
        self.mine_count -= 1
        if hasattr(game_state, 'add_mine'):
            game_state.add_mine(self.x, self.y, self.mine_damage, self.player_id)
        return True


class SuperUnit(Unit):
    """СУПЕР-ЮНИТ — Каратель. Огромный, дорогой, разрушительный."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Punisher"
        self.color = (200, 50, 50)
        self.unit_type = 'vehicle'

        self.max_hp = 1500
        self.hp = 1500
        self.max_shield = 500
        self.shield = 500
        self.shield_regen = 5.0
        self.speed = 30
        self.attack_damage = 80
        self.attack_range = 192
        self.attack_cooldown = 1.5
        self.armor_type = 'heavy'
        self.damage_type = 'siege'
        self.vision_range = 10
        self.can_attack_air = True
        self.aoe_radius = 80

        self.cost_titan = 800
        self.cost_plasma = 400
        self.supply_cost = 12
        self.build_time = 120

        self.width = int(TILE_SIZE * 3)
        self.height = int(TILE_SIZE * 3)

    def _perform_attack(self, target, game_state):
        """Массированный AoE удар."""
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                target.x, target.y, self.aoe_radius
            )
            for entity in nearby:
                if entity.id == self.id or entity.is_ally(self):
                    continue
                damage = self._apply_damage_modifiers(self.attack_damage, entity)
                entity.take_damage(damage, self.damage_type, attacker=self)

        self.attack_count += 1
        if hasattr(game_state, 'camera'):
            game_state.camera.shake(10, 0.5)
