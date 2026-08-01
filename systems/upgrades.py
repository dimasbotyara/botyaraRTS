"""
botyaraRTS - systems/upgrades.py
Система рандомных улучшений (карточки).
"""
import random
from settings import *


class Upgrade:
    """Одно улучшение (карточка)."""

    def __init__(self, id, name, description, tier, icon_color, apply_fn, remove_fn=None):
        self.id = id
        self.name = name
        self.description = description
        self.tier = tier  # 1, 2, 3
        self.icon_color = icon_color
        self.apply_fn = apply_fn      # функция(player_state, game_state)
        self.remove_fn = remove_fn    # функция для снятия эффекта

    def apply(self, player_state, game_state):
        if self.apply_fn:
            self.apply_fn(player_state, game_state)

    def remove(self, player_state, game_state):
        if self.remove_fn:
            self.remove_fn(player_state, game_state)


def _create_all_upgrades():
    """Создать все 30+ улучшений."""
    upgrades = []

    # === TIER 1 (Ранняя игра) ===

    upgrades.append(Upgrade(
        'industrialization', 'Industrialization',
        'Workers build 30% faster',
        tier=1, icon_color=(200, 180, 60),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'worker_build_speed': 1.3}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('worker_build_speed', None),
    ))

    upgrades.append(Upgrade(
        'forced_march', 'Forced March',
        'Infantry moves 20% faster',
        tier=1, icon_color=(100, 200, 100),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'infantry_speed': 1.2}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('infantry_speed', None),
    ))

    upgrades.append(Upgrade(
        'economic_blueprints', 'Economic Blueprints',
        'All buildings cost 15% less',
        tier=1, icon_color=(100, 180, 220),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'building_cost': 0.85}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('building_cost', None),
    ))

    upgrades.append(Upgrade(
        'recon_data', 'Recon Data',
        'Vision range +50%',
        tier=1, icon_color=(220, 220, 100),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'vision_range': 1.5}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('vision_range', None),
    ))

    upgrades.append(Upgrade(
        'steel_helmets', 'Steel Helmets',
        'Infantry HP +15%',
        tier=1, icon_color=(150, 150, 170),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'infantry_hp': 1.15}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('infantry_hp', None),
    ))

    upgrades.append(Upgrade(
        'deep_drilling', 'Deep Drilling',
        'Workers bring +20% more plasma',
        tier=1, icon_color=(80, 150, 220),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'plasma_harvest': 1.2}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('plasma_harvest', None),
    ))

    upgrades.append(Upgrade(
        'mobilization', 'Mobilization',
        'Barracks production +35% faster',
        tier=1, icon_color=(180, 120, 80),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'barracks_speed': 1.35}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('barracks_speed', None),
    ))

    upgrades.append(Upgrade(
        'tempering', 'Tempering',
        'Buildings auto-repair 1% HP/sec out of combat',
        tier=1, icon_color=(160, 160, 140),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'building_regen': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('building_regen', None),
    ))

    upgrades.append(Upgrade(
        'camo_nets', 'Camo Nets',
        'Turrets visible to enemy only at close range',
        tier=1, icon_color=(80, 120, 80),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'turret_stealth': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('turret_stealth', None),
    ))

    upgrades.append(Upgrade(
        'bulk_purchase', 'Bulk Purchase',
        'Supply from depots +50%',
        tier=1, icon_color=(200, 200, 150),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'supply_bonus': 1.5}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('supply_bonus', None),
    ))

    # === TIER 2 (Мид-гейм) ===

    upgrades.append(Upgrade(
        'reactive_ammo', 'Reactive Ammo',
        'Vehicle attack range +25%',
        tier=2, icon_color=(220, 150, 50),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'vehicle_range': 1.25}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('vehicle_range', None),
    ))

    upgrades.append(Upgrade(
        'field_hospital', 'Field Hospital',
        'Units regen 2% HP/sec after 5s out of combat',
        tier=2, icon_color=(100, 220, 100),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'unit_regen': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('unit_regen', None),
    ))

    upgrades.append(Upgrade(
        'titanium_alloy', 'Titanium Alloy',
        'Heavy vehicles ignore first 10 damage',
        tier=2, icon_color=(170, 170, 190),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'heavy_armor': 10}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('heavy_armor', None),
    ))

    upgrades.append(Upgrade(
        'black_market', 'Black Market',
        '+15 Titan every 10 seconds',
        tier=2, icon_color=(80, 60, 80),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'passive_income': 15}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('passive_income', None),
    ))

    upgrades.append(Upgrade(
        'explosive_death', 'Explosive Death',
        'Your units explode on death dealing AoE damage',
        tier=2, icon_color=(255, 100, 50),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'death_explosion': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('death_explosion', None),
    ))

    upgrades.append(Upgrade(
        'one_for_all', 'One For All',
        '+2% armor per nearby allied unit',
        tier=2, icon_color=(100, 150, 200),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'pack_armor': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('pack_armor', None),
    ))

    upgrades.append(Upgrade(
        'laser_targeting', 'Laser Targeting',
        '+30% damage vs High Ground units',
        tier=2, icon_color=(255, 50, 50),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'anti_highground': 1.3}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('anti_highground', None),
    ))

    upgrades.append(Upgrade(
        'critical_overheat', 'Critical Overheat',
        'Every 4th attack deals 200% damage',
        tier=2, icon_color=(255, 180, 0),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'crit_every_4': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('crit_every_4', None),
    ))

    upgrades.append(Upgrade(
        'spy_network', 'Spy Network',
        'Minimap reveals fully every 2 minutes for 5 sec',
        tier=2, icon_color=(150, 100, 180),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'spy_reveal': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('spy_reveal', None),
    ))

    upgrades.append(Upgrade(
        'scrap_collection', 'Scrap Collection',
        'Destroying enemies refunds 25% of their cost',
        tier=2, icon_color=(180, 180, 80),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'scrap_refund': 0.25}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('scrap_refund', None),
    ))

    # === TIER 3 (Лейт-гейм) ===

    upgrades.append(Upgrade(
        'nanite_vampirism', 'Nanite Vampirism',
        '25% of damage dealt heals your units',
        tier=3, icon_color=(200, 0, 50),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'vampirism': 0.25}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('vampirism', None),
    ))

    upgrades.append(Upgrade(
        'nuclear_protocol', 'Nuclear Protocol',
        'Every 10th siege attack creates mini-nuke',
        tier=3, icon_color=(255, 255, 0),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'nuke_protocol': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('nuke_protocol', None),
    ))

    upgrades.append(Upgrade(
        'absolute_shield', 'Absolute Shield',
        'HQ and turrets get 1000 shield (60s recharge)',
        tier=3, icon_color=(0, 150, 255),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'absolute_shield': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('absolute_shield', None),
    ))

    upgrades.append(Upgrade(
        'overclocking', 'Overclocking',
        'Attack speed +40%, but take +10% damage',
        tier=3, icon_color=(255, 100, 0),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'overclock_speed': 1.4, 'overclock_vuln': 1.1}),
        remove_fn=lambda p, g: [p.upgrade_bonuses.pop(k, None) for k in ('overclock_speed', 'overclock_vuln')],
    ))

    upgrades.append(Upgrade(
        'air_supremacy', 'Air Supremacy',
        'Aircraft 40% cheaper and 30% faster',
        tier=3, icon_color=(150, 200, 255),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'air_cost': 0.6, 'air_speed': 1.3}),
        remove_fn=lambda p, g: [p.upgrade_bonuses.pop(k, None) for k in ('air_cost', 'air_speed')],
    ))

    upgrades.append(Upgrade(
        'cloning', 'Cloning',
        '20% chance to produce 2 units for price of 1',
        tier=3, icon_color=(100, 255, 200),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'clone_chance': 0.2}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('clone_chance', None),
    ))

    upgrades.append(Upgrade(
        'kamikaze_drones', 'Kamikaze Drones',
        'Destroyed buildings spawn 3 attack drones',
        tier=3, icon_color=(255, 150, 0),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'kamikaze_drones': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('kamikaze_drones', None),
    ))

    upgrades.append(Upgrade(
        'orbital_strike', 'Orbital Strike',
        'Call a laser strike anywhere every 3 minutes',
        tier=3, icon_color=(255, 50, 50),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'orbital_strike': True, 'orbital_cd': 0}),
        remove_fn=lambda p, g: [p.upgrade_bonuses.pop(k, None) for k in ('orbital_strike', 'orbital_cd')],
    ))

    upgrades.append(Upgrade(
        'energy_drain', 'Energy Drain',
        'Your attacks drain enemy resources',
        tier=3, icon_color=(200, 50, 200),
        apply_fn=lambda p, g: p.upgrade_bonuses.update({'resource_drain': True}),
        remove_fn=lambda p, g: p.upgrade_bonuses.pop('resource_drain', None),
    ))

    upgrades.append(Upgrade(
        'unlimited_control', 'Unlimited Control',
        'Max supply increased from 200 to 300',
        tier=3, icon_color=(255, 255, 255),
        apply_fn=lambda p, g: setattr(p, 'supply_cap', 300),
        remove_fn=lambda p, g: setattr(p, 'supply_cap', MAX_SUPPLY),
    ))

    return upgrades


# Глобальный список всех улучшений
ALL_UPGRADES = _create_all_upgrades()


class UpgradeSystem:
    """Управление системой улучшений."""

    def __init__(self):
        self.all_upgrades = ALL_UPGRADES
        self.upgrade_timer = 0
        self.next_upgrade_time = 0  # первое — на старте
        self.is_choosing = False
        self.current_choices = []  # 3 карточки
        self.choosing_player_id = None

    def update(self, dt, game_time, game_state):
        """Проверяем не пора ли дать выбор."""
        if self.is_choosing:
            return

        if game_time >= self.next_upgrade_time:
            self.next_upgrade_time = game_time + UPGRADE_INTERVAL
            self._offer_choices(game_state.local_player_id, game_time, game_state)

    def _offer_choices(self, player_id, game_time, game_state):
        """Предложить 3 случайных улучшения."""
        player = game_state.players.get(player_id)
        if not player:
            return

        # Определяем тир
        tier = 1
        if game_time >= UPGRADE_TIER_THRESHOLDS[3]:
            tier = 3
        elif game_time >= UPGRADE_TIER_THRESHOLDS[2]:
            tier = 2

        # Фильтруем по тиру (можно предложить текущий или ниже)
        available = [u for u in self.all_upgrades if u.tier <= tier]

        # Убираем те, что уже активны
        active_ids = {u.id for u in player.active_upgrades}
        available = [u for u in available if u.id not in active_ids]

        if len(available) < UPGRADE_CHOICES:
            self.current_choices = available
        else:
            self.current_choices = random.sample(available, UPGRADE_CHOICES)

        if self.current_choices:
            self.is_choosing = True
            self.choosing_player_id = player_id

    def select_upgrade(self, index, game_state, replace_index=None):
        """Игрок выбрал карточку."""
        if index < 0 or index >= len(self.current_choices):
            return

        player = game_state.players.get(self.choosing_player_id)
        if not player:
            return

        upgrade = self.current_choices[index]

        if len(player.active_upgrades) < UPGRADE_SLOTS:
            # Есть свободный слот
            player.active_upgrades.append(upgrade)
            upgrade.apply(player, game_state)
        elif replace_index is not None and 0 <= replace_index < len(player.active_upgrades):
            # Заменяем существующий
            old = player.active_upgrades[replace_index]
            old.remove(player, game_state)
            player.active_upgrades[replace_index] = upgrade
            upgrade.apply(player, game_state)
        else:
            return

        self.is_choosing = False
        self.current_choices = []

    def skip_upgrade(self, game_state):
        """Пропустить выбор (получить компенсацию)."""
        player = game_state.players.get(self.choosing_player_id)
        if player:
            player.titan += UPGRADE_COMPENSATION
        self.is_choosing = False
        self.current_choices = []
