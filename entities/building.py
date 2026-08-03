"""
botyaraRTS - entities/building.py
Базовый класс здания и все типы зданий.
"""
import pygame
import math
from entities.entity import Entity
from settings import *


class Building(Entity):
    """Базовый класс для всех зданий."""

    def __init__(self, x, y, player_id=0, size_tiles=2):
        super().__init__(x, y, player_id)
        self.is_building = True
        self.size_tiles = size_tiles
        self.width = size_tiles * TILE_SIZE
        self.height = size_tiles * TILE_SIZE
        self.radius = self.width // 2

        # Строительство
        self.is_completed = False
        self.construction_progress = 0
        self.build_time = 30.0  # секунд

        # Стоимость
        self.cost_titan = 100
        self.cost_plasma = 0

        # Supply (лимит населения)
        self.supply_provided = 0

        # Производство юнитов
        self.can_produce = False
        self.production_queue = []  # [(unit_class, build_time, elapsed_time), ...]
        self.rally_point = None  # (world_x, world_y)
        self.max_queue = 5

        # Принимает ресурсы (HQ, склад)
        self.accepts_resources = False

        # Апгрейды
        self.upgrades = {}  # {'upgrade_name': level}
        self.available_upgrades = []

        # Оборона
        self.attack_damage = 0
        self.attack_range = 0
        self.attack_cooldown = 0
        self.attack_timer = 0
        self.attack_target = None

        # Визуал
        self.armor_type = 'structure'

        # Категория (для UI)
        self.category = 'economy'  # economy, production, research, defense

    def update(self, dt, game_state):
        """Обновление здания."""
        super().update(dt, game_state)
        if not self.alive:
            return

        if not self.is_completed:
            return

        # Обновляем очередь производства
        if self.production_queue:
            self._update_production(dt, game_state)

        # Автоматическая атака (для турелей)
        if self.attack_damage > 0:
            self._update_auto_attack(dt, game_state)

    def _update_production(self, dt, game_state):
        """Обновление очереди производства."""
        if not self.production_queue:
            return

        unit_class, build_time, elapsed = self.production_queue[0]
        elapsed += dt
        self.production_queue[0] = (unit_class, build_time, elapsed)

        if elapsed >= build_time:
            # Создаём юнит
            self._spawn_unit(unit_class, game_state)
            self.production_queue.pop(0)

    def _spawn_unit(self, unit_class, game_state):
        """Выпустить готового юнита."""
        # Точка спавна — рядом со зданием
        spawn_x = self.x + self.width // 2 + TILE_SIZE
        spawn_y = self.y

        unit = unit_class(spawn_x, spawn_y, self.player_id)

        if hasattr(game_state, 'add_entity'):
            game_state.add_entity(unit)

        # Отправляем к rally point (если на ресурсе — рабочий сразу начинает добычу)
        if self.rally_point:
            rx, ry = self.rally_point
            tile_x = int(rx // TILE_SIZE)
            tile_y = int(ry // TILE_SIZE)
            tile = game_state.tilemap.get_tile(tile_x, tile_y)

            from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER
            from entities.worker import Worker

            if tile in (TILE_TITAN_ORE, TILE_PLASMA_GEYSER) and isinstance(unit, Worker):
                unit.command_harvest(tile_x, tile_y)
            else:
                unit.move_to_point(rx, ry, game_state.tilemap)

    def _update_auto_attack(self, dt, game_state):
        """Автоматическая стрельба (турели)."""
        if self.attack_timer > 0:
            self.attack_timer -= dt
            return

        if not hasattr(game_state, 'spatial_hash'):
            return

        # Ищем врага
        def is_target(e):
            return e.alive and e.is_enemy(self) and not (e.is_cloaked and not self.is_detector)

        target = game_state.spatial_hash.query_nearest(
            self.x, self.y, self.attack_range, filter_fn=is_target
        )

        if target:
            target.take_damage(self.attack_damage, 'normal', attacker=self)
            self.attack_timer = self.attack_cooldown
            if hasattr(game_state, 'add_projectile'):
                game_state.add_projectile(self.x, self.y, target.x, target.y,
                                          PLAYER_COLORS[self.player_id % len(PLAYER_COLORS)])

    def queue_unit(self, unit_class, game_state):
        """Добавить юнита в очередь производства."""
        if not self.can_produce or not self.is_completed:
            return False
        if len(self.production_queue) >= self.max_queue:
            return False

        # Проверяем ресурсы
        player = game_state.players.get(self.player_id)
        if not player:
            return False

        temp_unit = unit_class(0, 0)
        if player.titan < temp_unit.cost_titan or player.plasma < temp_unit.cost_plasma:
            return False
        if player.current_supply + temp_unit.supply_cost > player.max_supply:
            return False

        # Списываем ресурсы
        player.titan -= temp_unit.cost_titan
        player.plasma -= temp_unit.cost_plasma
        player.current_supply += temp_unit.supply_cost

        self.production_queue.append((unit_class, temp_unit.build_time, 0))
        return True

    def cancel_production(self, index=None):
        """Отменить производство (возврат ресурсов)."""
        if not self.production_queue:
            return

        idx = index if index is not None else len(self.production_queue) - 1
        if 0 <= idx < len(self.production_queue):
            self.production_queue.pop(idx)

    def complete_construction(self):
        """Завершить строительство."""
        self.is_completed = True
        self.hp = self.max_hp

    def set_rally_point(self, world_x, world_y):
        """Установить точку сбора."""
        self.rally_point = (world_x, world_y)

    def render(self, surface, camera):
        """Отрисовка здания."""
        if not self.visible:
            return

        screen_rect = self.get_screen_rect(camera)

        if screen_rect.right < 0 or screen_rect.left > camera.screen_w or \
           screen_rect.bottom < 0 or screen_rect.top > camera.screen_h:
            return

        player_color = PLAYER_COLORS[self.player_id % len(PLAYER_COLORS)]

        if not self.is_completed:
            # Недостроенное здание — полупрозрачное с прогрессом
            progress = self.construction_progress / self.build_time if self.build_time > 0 else 0
            built_height = int(screen_rect.height * progress)
            # Каркас
            pygame.draw.rect(surface, (60, 60, 60), screen_rect, 2)
            # Прогресс заполнения
            if built_height > 0:
                fill_rect = pygame.Rect(
                    screen_rect.x,
                    screen_rect.bottom - built_height,
                    screen_rect.width,
                    built_height
                )
                dim_color = tuple(c // 2 for c in player_color)
                pygame.draw.rect(surface, dim_color, fill_rect)
            # Процент
            font = pygame.font.Font(None, max(14, int(16 * camera.zoom)))
            text = font.render(f"{int(progress * 100)}%", True, COLOR_UI_TEXT)
            surface.blit(text, (screen_rect.centerx - text.get_width() // 2,
                                screen_rect.centery - text.get_height() // 2))
        else:
            # Готовое здание
            pygame.draw.rect(surface, player_color, screen_rect)
            inner = screen_rect.inflate(-4, -4)
            pygame.draw.rect(surface, self.color, inner)

            # Иконка категории
            icon_map = {
                'economy': '🏠',
                'production': '⚔',
                'research': '🔬',
                'defense': '🛡',
            }

        # Рамка выделения
        if self.selected:
            sel_rect = screen_rect.inflate(6, 6)
            pygame.draw.rect(surface, COLOR_SELECTION_BOX, sel_rect, 2)

            # Rally point
            if self.rally_point and self.can_produce:
                rpx, rpy = camera.world_to_screen(*self.rally_point)
                pygame.draw.line(surface, (0, 255, 0),
                                 (screen_rect.centerx, screen_rect.centery),
                                 (int(rpx), int(rpy)), 1)
                pygame.draw.circle(surface, (0, 255, 0), (int(rpx), int(rpy)), 4, 1)

    def render_production_bar(self, surface, camera):
        """Отрисовка полоски производства."""
        if not self.production_queue or not self.is_completed:
            return

        screen_rect = self.get_screen_rect(camera)
        bar_width = screen_rect.width
        bar_height = max(3, int(4 * camera.zoom))
        bar_x = screen_rect.x
        bar_y = screen_rect.bottom + 2

        # Фон
        pygame.draw.rect(surface, (30, 30, 60), (bar_x, bar_y, bar_width, bar_height))

        # Прогресс
        unit_class, build_time, elapsed = self.production_queue[0]
        progress = elapsed / build_time if build_time > 0 else 0
        prog_width = int(bar_width * progress)
        if prog_width > 0:
            pygame.draw.rect(surface, COLOR_UI_ACCENT, (bar_x, bar_y, prog_width, bar_height))


# =============================================================================
# Конкретные здания
# =============================================================================

class Headquarters(Building):
    """Главный командный центр."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=3)
        self.name = "Headquarters"
        self.color = (80, 90, 110)
        self.category = 'economy'

        self.max_hp = 1500
        self.hp = 1500
        self.vision_range = 18
        self.build_time = 60
        self.cost_titan = 400

        self.accepts_resources = True
        self.can_produce = True
        self.supply_provided = 15

        self.available_upgrades = ['orbital_scan', 'bunker_turret']

    def get_producible_units(self):
        from entities.worker import Worker
        return [Worker]


class SupplyDepot(Building):
    """Жилой блок — увеличивает лимит населения."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Supply Depot"
        self.color = (100, 110, 90)
        self.category = 'economy'

        self.max_hp = 400
        self.hp = 400
        self.vision_range = 3
        self.build_time = 20
        self.cost_titan = 100

        self.supply_provided = 10


class Refinery(Building):
    """Склад ресурсов для дальних месторождений."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Refinery"
        self.color = (130, 120, 80)
        self.category = 'economy'

        self.max_hp = 500
        self.hp = 500
        self.vision_range = 4
        self.build_time = 25
        self.cost_titan = 150

        self.accepts_resources = True


class PlasmaExtractor(Building):
    """Экстрактор плазмы — строится на гейзере."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Plasma Extractor"
        self.color = (60, 120, 180)
        self.category = 'economy'

        self.max_hp = 600
        self.hp = 600
        self.vision_range = 3
        self.build_time = 30
        self.cost_titan = 200


class TradingPost(Building):
    """Торговый пост — обмен ресурсов."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Trading Post"
        self.color = (150, 130, 70)
        self.category = 'economy'

        self.max_hp = 350
        self.hp = 350
        self.vision_range = 3
        self.build_time = 20
        self.cost_titan = 150

        self.exchange_rate = 3  # 3 титана = 1 плазма


class Barracks(Building):
    """Казармы — пехота."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Barracks"
        self.color = (140, 110, 90)
        self.category = 'production'

        self.max_hp = 800
        self.hp = 800
        self.vision_range = 5
        self.build_time = 35
        self.cost_titan = 200

        self.can_produce = True

    def get_producible_units(self):
        from entities.infantry import Scout, Trooper, Sniper, RocketSoldier, Medic, ExoSoldier
        return [Scout, Trooper, Sniper, RocketSoldier, Medic, ExoSoldier]


class Factory(Building):
    """Завод — наземная техника."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=3)
        self.name = "Factory"
        self.color = (110, 110, 100)
        self.category = 'production'

        self.max_hp = 1200
        self.hp = 1200
        self.vision_range = 5
        self.build_time = 45
        self.cost_titan = 300
        self.cost_plasma = 50

        self.can_produce = True

    def get_producible_units(self):
        from entities.vehicles import Buggy, Tank, Flamethrower, SiegeTank, MobileAA, MechWalker
        return [Buggy, Tank, Flamethrower, SiegeTank, MobileAA, MechWalker]


class Starport(Building):
    """Космопорт — авиация."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=3)
        self.name = "Starport"
        self.color = (100, 120, 150)
        self.category = 'production'

        self.max_hp = 1000
        self.hp = 1000
        self.vision_range = 6
        self.build_time = 50
        self.cost_titan = 350
        self.cost_plasma = 100

        self.can_produce = True

    def get_producible_units(self):
        from entities.aircraft import ScoutDrone, AttackHelicopter, Fighter, Bomber, Transport
        return [ScoutDrone, AttackHelicopter, Fighter, Bomber, Transport]


class SpecOpsLab(Building):
    """Лаборатория спецопераций."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Spec Ops Lab"
        self.color = (90, 70, 120)
        self.category = 'production'

        self.max_hp = 700
        self.hp = 700
        self.vision_range = 5
        self.build_time = 40
        self.cost_titan = 250
        self.cost_plasma = 100

        self.can_produce = True

    def get_producible_units(self):
        from entities.special_units import Saboteur, PsiUnit, MineDrone, SuperUnit
        return [Saboteur, PsiUnit, MineDrone, SuperUnit]


class Turret(Building):
    """Сторожевая вышка — базовая защита."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=1)
        self.name = "Turret"
        self.color = (140, 140, 120)
        self.category = 'defense'

        self.max_hp = 300
        self.hp = 300
        self.vision_range = 7
        self.build_time = 15
        self.cost_titan = 100

        self.attack_damage = 15
        self.attack_range = 192
        self.attack_cooldown = 1.0


class SAMSite(Building):
    """ПВО — только по воздуху."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=1)
        self.name = "SAM Site"
        self.color = (120, 150, 170)
        self.category = 'defense'

        self.max_hp = 250
        self.hp = 250
        self.vision_range = 9
        self.build_time = 20
        self.cost_titan = 120

        self.attack_damage = 30
        self.attack_range = 256
        self.attack_cooldown = 1.5
        self.is_detector = True

    def _update_auto_attack(self, dt, game_state):
        """Только по воздушным целям."""
        if self.attack_timer > 0:
            self.attack_timer -= dt
            return

        if not hasattr(game_state, 'spatial_hash'):
            return

        def is_air_target(e):
            return e.alive and e.is_flying and e.is_enemy(self)

        target = game_state.spatial_hash.query_nearest(
            self.x, self.y, self.attack_range, filter_fn=is_air_target
        )

        if target:
            target.take_damage(self.attack_damage, 'explosive', attacker=self)
            self.attack_timer = self.attack_cooldown


class Wall(Building):
    """Стена / Баррикада."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=1)
        self.name = "Wall"
        self.color = (100, 100, 100)
        self.category = 'defense'

        self.max_hp = 500
        self.hp = 500
        self.vision_range = 1
        self.build_time = 5
        self.cost_titan = 25


class ArtilleryBunker(Building):
    """Артиллерийский бункер — дальнобойная защита."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Artillery Bunker"
        self.color = (110, 90, 80)
        self.category = 'defense'

        self.max_hp = 600
        self.hp = 600
        self.vision_range = 5
        self.build_time = 35
        self.cost_titan = 250
        self.cost_plasma = 50

        self.attack_damage = 40
        self.attack_range = 384
        self.attack_cooldown = 3.0


class ShieldGenerator(Building):
    """Генератор силового поля."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Shield Generator"
        self.color = (70, 100, 180)
        self.category = 'defense'

        self.max_hp = 500
        self.hp = 500
        self.max_shield = 1000
        self.shield = 1000
        self.shield_regen = 10.0
        self.vision_range = 4
        self.build_time = 40
        self.cost_titan = 200
        self.cost_plasma = 100

        self.shield_radius = 192  # пикселей


class Armory(Building):
    """Арсенал — апгрейды урона и брони пехоты."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Armory"
        self.color = (150, 130, 100)
        self.category = 'research'

        self.max_hp = 600
        self.hp = 600
        self.vision_range = 3
        self.build_time = 30
        self.cost_titan = 200
        self.cost_plasma = 50


class EngineeringBay(Building):
    """Кузница техники — апгрейды для техники."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id, size_tiles=2)
        self.name = "Engineering Bay"
        self.color = (130, 140, 110)
        self.category = 'research'

        self.max_hp = 600
        self.hp = 600
        self.vision_range = 3
        self.build_time = 30
        self.cost_titan = 200
        self.cost_plasma = 75


# Словарь всех зданий для удобства
ALL_BUILDINGS = {
    'economy': [Headquarters, SupplyDepot, Refinery, PlasmaExtractor, TradingPost],
    'production': [Barracks, Factory, Starport, SpecOpsLab],
    'research': [Armory, EngineeringBay],
    'defense': [Turret, SAMSite, Wall, ArtilleryBunker, ShieldGenerator],
}
