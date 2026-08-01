"""
botyaraRTS - entities/infantry.py
Все пехотные юниты.
"""
import math
import random
import pygame
from entities.unit import Unit
from settings import *


class Scout(Unit):
    """Разведчик — быстрый, невидимый когда стоит на месте."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Scout"
        self.color = (100, 200, 100)
        self.unit_type = 'infantry'

        self.max_hp = 40
        self.hp = 40
        self.speed = 130
        self.attack_damage = 6
        self.attack_range = 64
        self.attack_cooldown = 0.8
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 10
        self.can_attack_air = True

        self.cost_titan = 40
        self.supply_cost = 1
        self.build_time = 8

        # Пассивка: камуфляж
        self.cloak_timer = 0
        self.cloak_delay = 3.0  # секунд неподвижности до невидимости
        self.cloak_detection_range = 64  # враг видит его только вблизи

    def update(self, dt, game_state):
        super().update(dt, game_state)
        if not self.alive:
            return

        # Камуфляж
        if self.state == 'IDLE':
            self.cloak_timer += dt
            if self.cloak_timer >= self.cloak_delay:
                self.is_cloaked = True
        else:
            self.cloak_timer = 0
            self.is_cloaked = False

    def _perform_attack(self, target, game_state):
        self.is_cloaked = False
        self.cloak_timer = 0
        super()._perform_attack(target, game_state)


class Trooper(Unit):
    """Штурмовик — базовый солдат."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Trooper"
        self.color = (120, 140, 160)
        self.unit_type = 'infantry'

        self.max_hp = 80
        self.hp = 80
        self.speed = 85
        self.attack_damage = 10
        self.attack_range = 96
        self.attack_cooldown = 0.8
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 6
        self.can_attack_air = True

        self.cost_titan = 50
        self.supply_cost = 1
        self.build_time = 10

    def _perform_attack(self, target, game_state):
        """Пассивка: Suppression — каждая 5-я пуля замедляет."""
        super()._perform_attack(target, game_state)
        if self.attack_count % 5 == 0 and hasattr(target, 'speed'):
            original = getattr(target, '_original_speed', target.speed)
            target._original_speed = original
            target.speed = original * 0.85
            # Сбросится через 1 секунду (упрощённо)


class Sniper(Unit):
    """Снайпер — огромный урон по пехоте, дальний бой."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Sniper"
        self.color = (80, 100, 130)
        self.unit_type = 'infantry'

        self.max_hp = 45
        self.hp = 45
        self.speed = 60
        self.attack_damage = 35
        self.attack_range = 256
        self.attack_cooldown = 2.5
        self.armor_type = 'light'
        self.damage_type = 'normal'
        self.vision_range = 10
        self.can_attack_air = False

        self.cost_titan = 100
        self.cost_plasma = 25
        self.supply_cost = 2
        self.build_time = 18

    def _perform_attack(self, target, game_state):
        """Пассивка: Execution — +50% урона если цель ниже 30% HP."""
        damage = self.attack_damage
        if target.hp / target.max_hp < 0.3:
            damage = int(damage * 1.5)

        # Промах по высоте
        my_h = game_state.tilemap.get_height(*self.get_tile_pos())
        t_h = game_state.tilemap.get_height(*target.get_tile_pos())
        if t_h > my_h and not self.is_flying:
            if random.random() < 0.25:
                return

        damage = self._apply_damage_modifiers(damage, target)
        target.take_damage(damage, self.damage_type, attacker=self)
        self.attack_count += 1


class RocketSoldier(Unit):
    """Ракетчик — урон по технике и зданиям."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Rocket Soldier"
        self.color = (160, 100, 60)
        self.unit_type = 'infantry'

        self.max_hp = 65
        self.hp = 65
        self.speed = 55
        self.attack_damage = 25
        self.attack_range = 160
        self.attack_cooldown = 2.0
        self.armor_type = 'light'
        self.damage_type = 'explosive'
        self.vision_range = 6
        self.can_attack_air = True

        self.cost_titan = 75
        self.cost_plasma = 25
        self.supply_cost = 2
        self.build_time = 15


class Medic(Unit):
    """Медик — лечит союзников, не атакует."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Medic"
        self.color = (100, 220, 100)
        self.unit_type = 'infantry'

        self.max_hp = 50
        self.hp = 50
        self.speed = 75
        self.attack_damage = 0
        self.attack_range = 0
        self.armor_type = 'light'
        self.vision_range = 6

        self.cost_titan = 60
        self.cost_plasma = 20
        self.supply_cost = 1
        self.build_time = 12

        # Лечение
        self.heal_range = 96  # пикселей
        self.heal_rate = 8.0  # HP/сек
        self.heal_timer = 0

    def update(self, dt, game_state):
        """Медик лечит вместо атаки."""
        Entity.update(self, dt, game_state)
        if not self.alive:
            return

        # Обновляем FSM для движения
        if self.state == 'MOVE':
            self._state_move(dt, game_state)
        elif self.state == 'IDLE':
            pass

        # Аура лечения
        self._heal_nearby(dt, game_state)

    def _heal_nearby(self, dt, game_state):
        """Пассивно лечим всех рядом."""
        if not hasattr(game_state, 'spatial_hash'):
            return

        nearby = game_state.spatial_hash.query_radius(self.x, self.y, self.heal_range)
        for entity in nearby:
            if not entity.alive or entity.id == self.id:
                continue
            if entity.player_id != self.player_id:
                continue
            if entity.hp >= entity.max_hp:
                continue

            heal_amount = self.heal_rate * dt

            # Медиков и себя лечит в 2 раза хуже
            if isinstance(entity, Medic):
                heal_amount *= 0.5
            # Летающие - в 1.5 раза хуже
            elif entity.is_flying:
                heal_amount /= 1.5
            # Очень слабые юниты - в 2 раза лучше
            elif entity.max_hp <= 50:
                heal_amount *= 2.0

            entity.heal(heal_amount)

    def render(self, surface, camera):
        """Медик с зелёной аурой."""
        super().render(surface, camera)
        if not self.alive:
            return

        # Зелёная аура
        screen_rect = self.get_screen_rect(camera)
        aura_radius = int(self.heal_range * camera.zoom)
        center = (screen_rect.centerx, screen_rect.centery)

        aura_surface = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surface, (0, 200, 0, 25), (aura_radius, aura_radius), aura_radius)
        surface.blit(aura_surface, (center[0] - aura_radius, center[1] - aura_radius))


class ExoSoldier(Unit):
    """Экзо-солдат — тяжёлая пехота с миниганом."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.name = "Exo Soldier"
        self.color = (100, 100, 140)
        self.unit_type = 'infantry'

        self.max_hp = 200
        self.hp = 200
        self.speed = 45
        self.attack_damage = 15
        self.attack_range = 112
        self.attack_cooldown = 0.3
        self.armor_type = 'heavy'
        self.damage_type = 'normal'
        self.vision_range = 5
        self.can_attack_air = True

        self.cost_titan = 150
        self.cost_plasma = 50
        self.supply_cost = 3
        self.build_time = 25

        # Пассивка: Heavy Plating — игнорирует первые 5 урона
        self.damage_reduction = 5

    def take_damage(self, damage, damage_type='normal', attacker=None):
        """Пассивка: игнорирует мелкий урон."""
        if damage_type == 'normal':
            damage = max(0, damage - self.damage_reduction)
        return super().take_damage(damage, damage_type, attacker)
