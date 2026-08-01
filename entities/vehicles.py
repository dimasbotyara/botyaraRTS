"""
botyaraRTS - entities/vehicles.py
Наземная техника.
"""
import math
import random
import pygame
from entities.unit import Unit
from settings import *


class Buggy(Unit):
    """Багги — быстрая разведка."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Buggy"
        self.color = (180, 160, 80)
        self.unit_type = 'vehicle'

        self.max_hp = 90
        self.hp = 90
        self.speed = 140
        self.attack_damage = 8
        self.attack_range = 80
        self.attack_cooldown = 0.5
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 8
        self.can_attack_air = False

        self.cost_titan = 80
        self.supply_cost = 2
        self.build_time = 15

        # Пассивка: Таранный разгон
        self.momentum = 0  # накапливается при прямолинейном движении
        self.last_direction = None
        self.width = int(TILE_SIZE * 1.2)
        self.height = int(TILE_SIZE * 0.8)

    def update(self, dt, game_state):
        old_x, old_y = self.x, self.y
        super().update(dt, game_state)
        if self.alive and self.state == 'MOVE':
            dx = self.x - old_x
            dy = self.y - old_y
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                direction = math.atan2(dy, dx)
                if self.last_direction is not None:
                    diff = abs(direction - self.last_direction)
                    if diff < 0.2:
                        self.momentum = min(2.0, self.momentum + dt)
                    else:
                        self.momentum = 0
                self.last_direction = direction
            else:
                self.momentum = 0


class Tank(Unit):
    """Основной боевой танк — AoE урон."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Battle Tank"
        self.color = (100, 120, 80)
        self.unit_type = 'vehicle'

        self.max_hp = 250
        self.hp = 250
        self.speed = 55
        self.attack_damage = 30
        self.attack_range = 160
        self.attack_cooldown = 2.0
        self.armor_type = 'heavy'
        self.damage_type = 'explosive'
        self.vision_range = 6
        self.can_attack_air = False

        self.cost_titan = 200
        self.cost_plasma = 50
        self.supply_cost = 3
        self.build_time = 30

        self.aoe_radius = 48
        self.width = int(TILE_SIZE * 1.5)
        self.height = int(TILE_SIZE * 1.2)

        # Пассивка: Frontal Armor — 35% уменьшение урона спереди
        self.frontal_armor_reduction = 0.35

    def _perform_attack(self, target, game_state):
        """AoE атака."""
        damage = self._apply_damage_modifiers(self.attack_damage, target)
        target.take_damage(damage, self.damage_type, attacker=self)
        self.attack_count += 1

        # AoE — бьём всех рядом с целью
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                target.x, target.y, self.aoe_radius
            )
            for entity in nearby:
                if entity.id == target.id or entity.id == self.id:
                    continue
                if entity.is_flying:
                    continue
                aoe_damage = damage // 2
                entity.take_damage(aoe_damage, self.damage_type, attacker=self)

    def take_damage(self, damage, damage_type='normal', attacker=None):
        """Пассивка: Frontal Armor."""
        if attacker:
            angle_to_attacker = math.atan2(
                attacker.y - self.y, attacker.x - self.x
            )
            angle_diff = abs(math.degrees(angle_to_attacker) - self.facing_angle) % 360
            if angle_diff < 90 or angle_diff > 270:
                damage = int(damage * (1 - self.frontal_armor_reduction))
        return super().take_damage(damage, damage_type, attacker)


class Flamethrower(Unit):
    """Огнемётная машина — AoE по пехоте, дожигание."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Flamethrower"
        self.color = (220, 100, 30)
        self.unit_type = 'vehicle'

        self.max_hp = 150
        self.hp = 150
        self.speed = 65
        self.attack_damage = 12
        self.attack_range = 80
        self.attack_cooldown = 0.3
        self.armor_type = 'medium'
        self.damage_type = 'energy'
        self.vision_range = 5
        self.can_attack_air = False

        self.cost_titan = 120
        self.cost_plasma = 40
        self.supply_cost = 2
        self.build_time = 20

        self.aoe_radius = 64
        self.width = int(TILE_SIZE * 1.3)
        self.height = int(TILE_SIZE * 1.0)

    def _perform_attack(self, target, game_state):
        """AoE огнём + дожигание."""
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                target.x, target.y, self.aoe_radius
            )
            for entity in nearby:
                if entity.id == self.id or entity.is_ally(self):
                    continue
                if entity.is_flying:
                    continue
                damage = self._apply_damage_modifiers(self.attack_damage, entity)
                entity.take_damage(damage, self.damage_type, attacker=self)

                # Afterburn — ставим DoT
                if hasattr(entity, 'burn_timer'):
                    entity.burn_timer = 3.0
                    entity.burn_dps = 4
        self.attack_count += 1


class SiegeTank(Unit):
    """Осадная артиллерия — режим осады."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Siege Artillery"
        self.color = (90, 90, 70)
        self.unit_type = 'vehicle'

        self.max_hp = 200
        self.hp = 200
        self.speed = 50
        self.armor_type = 'heavy'
        self.vision_range = 7

        self.cost_titan = 250
        self.cost_plasma = 75
        self.supply_cost = 4
        self.build_time = 35

        self.width = int(TILE_SIZE * 1.5)
        self.height = int(TILE_SIZE * 1.3)

        # Мобильный режим
        self.attack_damage = 15
        self.attack_range = 128
        self.attack_cooldown = 1.5
        self.damage_type = 'explosive'
        self.can_attack_air = False

        # Режим осады
        self.siege_mode = False
        self.siege_damage = 70
        self.siege_range = 480
        self.siege_cooldown = 3.0
        self.siege_aoe = 64
        self.siege_deploy_time = 2.0
        self.deploy_timer = 0

    def toggle_siege(self):
        """Переключить режим осады."""
        if self.deploy_timer > 0:
            return

        self.siege_mode = not self.siege_mode
        self.deploy_timer = self.siege_deploy_time

        if self.siege_mode:
            self.speed = 0
            self.attack_damage = self.siege_damage
            self.attack_range = self.siege_range
            self.attack_cooldown = self.siege_cooldown
            self.damage_type = 'siege'
        else:
            self.speed = 50
            self.attack_damage = 15
            self.attack_range = 128
            self.attack_cooldown = 1.5
            self.damage_type = 'explosive'

    def update(self, dt, game_state):
        if self.deploy_timer > 0:
            self.deploy_timer -= dt
            return
        super().update(dt, game_state)

    def _perform_attack(self, target, game_state):
        """В осаде — AoE + стан."""
        damage = self._apply_damage_modifiers(self.attack_damage, target)
        target.take_damage(damage, self.damage_type, attacker=self)
        self.attack_count += 1

        if self.siege_mode and hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                target.x, target.y, self.siege_aoe
            )
            for entity in nearby:
                if entity.id == target.id or entity.id == self.id:
                    continue
                aoe_damage = damage // 2
                entity.take_damage(aoe_damage, self.damage_type, attacker=self)

            if hasattr(game_state, 'camera'):
                game_state.camera.shake(8, 0.4)


class MobileAA(Unit):
    """Мобильная ПВО — только по воздуху."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Mobile AA"
        self.color = (150, 180, 200)
        self.unit_type = 'vehicle'

        self.max_hp = 120
        self.hp = 120
        self.speed = 70
        self.attack_damage = 25
        self.attack_range = 224
        self.attack_cooldown = 1.0
        self.armor_type = 'medium'
        self.damage_type = 'explosive'
        self.vision_range = 8
        self.can_attack_air = True
        self.can_attack_ground = False
        self.is_detector = True

        self.cost_titan = 120
        self.cost_plasma = 30
        self.supply_cost = 2
        self.build_time = 20


class MechWalker(Unit):
    """Шагоход-мех — эффективен против бронированной техники."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Mech Walker"
        self.color = (130, 100, 130)
        self.unit_type = 'vehicle'

        self.max_hp = 300
        self.hp = 300
        self.speed = 40
        self.attack_damage = 40
        self.attack_range = 176
        self.attack_cooldown = 2.5
        self.armor_type = 'heavy'
        self.damage_type = 'explosive'
        self.vision_range = 7
        self.can_attack_air = True

        self.cost_titan = 300
        self.cost_plasma = 100
        self.supply_cost = 5
        self.build_time = 40

        self.width = int(TILE_SIZE * 1.8)
        self.height = int(TILE_SIZE * 1.8)
