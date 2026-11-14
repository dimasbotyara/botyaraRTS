"""
botyaraRTS - ai/strategies.py
Стратегии ИИ: билд-ордера, целевой состав армии, тайминги атак.

Каждая стратегия — словарь:
  worker_target      сколько рабочих держать
  build_order        порядок постройки зданий (классы из entities.building)
  building_limits    {класс: максимум} — билд-ордер зацикливается с учётом лимитов
  army_composition   [(unit_class, доля), ...] — очередь производства
  attack_min_army    минимальная сила группы для атаки (в «стоимости» юнитов)
  attack_time        earliest тайминг атаки, сек
  defend_radius      радиус реакции на вторжение (px)
  turret_target      целевое число турелей у базы
  harass             диверсионные рейды по рабочим
  desperate_allin    в отчаянном режиме атаковать всем
"""

from entities.building import (
    SupplyDepot, Refinery, Barracks, Factory, Starport, SpecOpsLab,
    Turret, SAMSite, Wall, ArtilleryBunker, ShieldGenerator,
)
from entities.infantry import Scout, Trooper, Sniper, RocketSoldier, Medic, ExoSoldier
from entities.vehicles import Buggy, Tank, Flamethrower, SiegeTank, MobileAA, MechWalker
from entities.aircraft import ScoutDrone, AttackHelicopter, Fighter, Bomber, Transport
from entities.special_units import Saboteur, PsiUnit, MineDrone, SuperUnit

STRATEGY_IDS = ['balanced', 'rush', 'defense', 'air_only',
                'eco', 'swarm', 'tech', 'siege', 'harass']

STRATEGIES = {
    # Сбалансированный: смешанные силы, постепенный технический рост
    'balanced': {
        'worker_target': 14,
        'build_order': [SupplyDepot, Refinery, Barracks, Barracks, Turret,
                        Factory, SupplyDepot, Barracks, Starport, Turret,
                        Factory, SupplyDepot],
        'building_limits': {Barracks: 3, Factory: 2, Starport: 1,
                            Turret: 3, Refinery: 1, SupplyDepot: 8},
        'army_composition': [(Trooper, 3), (RocketSoldier, 2), (Medic, 1),
                             (Tank, 2), (SiegeTank, 1), (AttackHelicopter, 1)],
        'attack_min_army': 8,
        'attack_time': 300,
        'defend_radius': 380,
        'turret_target': 3,
        'harass': False,
    },

    # Ранняя атака: казармы как можно быстрее, постоянное давление пехотой
    'rush': {
        'worker_target': 12,
        'build_order': [Barracks, SupplyDepot, Barracks, Refinery, Barracks,
                        SupplyDepot, Barracks, Turret, Factory],
        'building_limits': {Barracks: 4, Factory: 1, Turret: 1,
                            Refinery: 1, SupplyDepot: 8},
        'army_composition': [(Scout, 2), (Trooper, 4), (RocketSoldier, 2), (Medic, 1)],
        'attack_min_army': 4,
        'attack_time': 150,
        'defend_radius': 340,
        'turret_target': 1,
        'harass': False,
    },

    # Оборона: турели, стены, бункеры; контратака только при перевесе
    'defense': {
        'worker_target': 15,
        'build_order': [SupplyDepot, Refinery, Barracks, Turret, Turret,
                        Wall, Wall, ArtilleryBunker, SupplyDepot, Turret,
                        SAMSite, ArtilleryBunker, ShieldGenerator, Factory],
        'building_limits': {Turret: 6, SAMSite: 2, ArtilleryBunker: 3,
                            Wall: 12, Barracks: 2, Factory: 1,
                            Refinery: 1, SupplyDepot: 8, ShieldGenerator: 1},
        'army_composition': [(Trooper, 3), (RocketSoldier, 2), (Sniper, 2),
                             (Tank, 2), (MobileAA, 1)],
        'attack_min_army': 12,
        'attack_time': 480,
        'defend_radius': 460,
        'turret_target': 6,
        'harass': False,
    },

    # Только авиация: быстрый космопорт, воздушный раш
    'air_only': {
        'worker_target': 13,
        'build_order': [SupplyDepot, Refinery, Starport, SupplyDepot,
                        Starport, Turret, SAMSite, Starport, Turret],
        'building_limits': {Starport: 3, Turret: 2, SAMSite: 1,
                            Refinery: 1, SupplyDepot: 8},
        'army_composition': [(Fighter, 3), (AttackHelicopter, 3), (Bomber, 2)],
        'attack_min_army': 5,
        'attack_time': 300,
        'defend_radius': 360,
        'turret_target': 2,
        'harass': False,
    },

    # Экономист: много рабочих, дальние месторождения, поздняя тяжёлая армия
    'eco': {
        'worker_target': 20,
        'build_order': [SupplyDepot, Refinery, Refinery, Barracks, SupplyDepot,
                        Turret, Factory, SupplyDepot, Starport, Factory,
                        MechWalker, Turret],
        'building_limits': {Refinery: 2, Barracks: 2, Factory: 3, Starport: 1,
                            Turret: 3, SupplyDepot: 9},
        'army_composition': [(Trooper, 2), (Tank, 3), (MechWalker, 2),
                             (SiegeTank, 1), (Medic, 1)],
        'attack_min_army': 10,
        'attack_time': 420,
        'defend_radius': 360,
        'turret_target': 3,
        'harass': False,
    },

    # Рой: волны дешёвой пехоты без остановки
    'swarm': {
        'worker_target': 16,
        'build_order': [SupplyDepot, Barracks, Barracks, SupplyDepot, Barracks,
                        Refinery, SupplyDepot, Barracks, Barracks, SupplyDepot,
                        Turret, Barracks],
        'building_limits': {Barracks: 5, Turret: 1, Refinery: 1, SupplyDepot: 10},
        'army_composition': [(Scout, 3), (Trooper, 5), (RocketSoldier, 1)],
        'attack_min_army': 6,
        'attack_time': 180,
        'defend_radius': 340,
        'turret_target': 1,
        'harass': False,
    },

    # Технарь: Spec Ops Lab и «Punisher» под прикрытием турелей
    'tech': {
        'worker_target': 16,
        'build_order': [SupplyDepot, Refinery, Barracks, Turret, Turret,
                        SpecOpsLab, SupplyDepot, Turret, SAMSite, SpecOpsLab,
                        ShieldGenerator, Starport],
        'building_limits': {SpecOpsLab: 2, Turret: 4, SAMSite: 2, Barracks: 2,
                            Refinery: 1, SupplyDepot: 8, ShieldGenerator: 1,
                            Starport: 1},
        'army_composition': [(Trooper, 3), (RocketSoldier, 2), (Sniper, 1),
                             (Saboteur, 1), (PsiUnit, 1), (SuperUnit, 1),
                             (AttackHelicopter, 1)],
        'attack_min_army': 7,
        'attack_time': 420,
        'defend_radius': 420,
        'turret_target': 4,
        'harass': False,
    },

    # Осада: осадная артиллерия + бункеры, медленный продавливающий пуш
    'siege': {
        'worker_target': 15,
        'build_order': [SupplyDepot, Refinery, Factory, Turret, SupplyDepot,
                        Turret, Factory, ArtilleryBunker, SAMSite,
                        ArtilleryBunker, SupplyDepot, Factory],
        'building_limits': {Factory: 3, ArtilleryBunker: 3, Turret: 4,
                            SAMSite: 1, Refinery: 1, SupplyDepot: 8},
        'army_composition': [(Trooper, 3), (SiegeTank, 3), (Tank, 2),
                             (MobileAA, 1), (Medic, 1)],
        'attack_min_army': 8,
        'attack_time': 360,
        'defend_radius': 420,
        'turret_target': 4,
        'harass': False,
    },

    # Диверсии: снайперы и диверсанты по рабочим, минные поля, избегание боя
    'harass': {
        'worker_target': 13,
        'build_order': [SupplyDepot, Refinery, Barracks, SpecOpsLab, SupplyDepot,
                        Turret, Barracks, SpecOpsLab, Turret, Starport],
        'building_limits': {Barracks: 2, SpecOpsLab: 2, Turret: 2,
                            Refinery: 1, SupplyDepot: 7, Starport: 1},
        'army_composition': [(Sniper, 3), (Saboteur, 2), (MineDrone, 2),
                             (Trooper, 3), (AttackHelicopter, 1)],
        'attack_min_army': 5,
        'attack_time': 240,
        'defend_radius': 340,
        'turret_target': 2,
        'harass': True,
    },
}


def resolve_strategy(name, rng):
    """Детерминированный выбор стратегии: 'random' — через gs.rng."""
    if name in STRATEGIES:
        return name
    return rng.choice(STRATEGY_IDS)


def get_strategy(name):
    """Конфиг стратегии по id (с безопасным фолбэком)."""
    return STRATEGIES.get(name, STRATEGIES['balanced'])
