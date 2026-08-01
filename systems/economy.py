"""
botyaraRTS - systems/economy.py
Экономическая система: ресурсы, лимит населения, игрок.
"""
from settings import *


class PlayerState:
    """Состояние одного игрока."""

    def __init__(self, player_id, start_titan=STARTING_TITAN,
                 start_plasma=STARTING_PLASMA):
        self.player_id = player_id
        self.titan = start_titan
        self.plasma = start_plasma
        self.current_supply = 0
        self.max_supply = STARTING_SUPPLY
        self.supply_cap = MAX_SUPPLY

        # Статистика
        self.total_titan_mined = 0
        self.total_plasma_mined = 0
        self.units_produced = 0
        self.units_lost = 0
        self.buildings_built = 0
        self.buildings_lost = 0

        # Улучшения
        self.active_upgrades = []  # до 3 штук
        self.upgrade_bonuses = {}  # {'worker_speed': 1.3, 'infantry_hp': 1.15, ...}

        # Исследования
        self.research = {
            'infantry_attack': 0,  # +1/+2/+3
            'infantry_armor': 0,
            'vehicle_attack': 0,
            'vehicle_armor': 0,
            'vehicle_speed': 0,
        }

        # Сетевые данные
        self.name = f"Player {player_id + 1}"
        self.color_index = player_id
        self.is_defeated = False

    def can_afford(self, titan_cost, plasma_cost=0):
        """Хватает ли ресурсов?"""
        return self.titan >= titan_cost and self.plasma >= plasma_cost

    def spend(self, titan_cost, plasma_cost=0):
        """Потратить ресурсы."""
        if not self.can_afford(titan_cost, plasma_cost):
            return False
        self.titan -= titan_cost
        self.plasma -= plasma_cost
        return True

    def add_titan(self, amount):
        self.titan += amount
        self.total_titan_mined += amount

    def add_plasma(self, amount):
        self.plasma += amount
        self.total_plasma_mined += amount

    def recalculate_supply(self, buildings):
        """Пересчитать лимит населения от зданий."""
        total = 0
        for building in buildings:
            if building.player_id == self.player_id and building.is_completed and building.alive:
                total += building.supply_provided
        self.max_supply = min(total, self.supply_cap)

    def recalculate_current_supply(self, units):
        """Пересчитать текущее использование supply."""
        total = 0
        for unit in units:
            if unit.player_id == self.player_id and unit.alive:
                total += unit.supply_cost
        self.current_supply = total

    def get_upgrade_bonus(self, key, default=1.0):
        """Получить множитель от улучшений."""
        return self.upgrade_bonuses.get(key, default)

    def serialize(self):
        return {
            'player_id': self.player_id,
            'titan': self.titan,
            'plasma': self.plasma,
            'current_supply': self.current_supply,
            'max_supply': self.max_supply,
            'name': self.name,
            'active_upgrades': [u.id for u in self.active_upgrades],
        }
