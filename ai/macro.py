"""
botyaraRTS - ai/macro.py
Макро-менеджер ИИ: рабочие, билд-ордер, supply, размещение зданий.

Все решения принимаются по «тикам мышления» мозга и через gs.rng —
детерминированно.
"""
import math
from settings import *
from systems.commands import place_building_at
from ai.strategies import get_strategy
from entities.building import SupplyDepot, Turret, ArtilleryBunker

from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER


def _footprint_free_of_buildings(gs, tx, ty, size_tiles):
    """Проверить, что footprint не пересекается с уже стоящими зданиями."""
    import pygame as _pygame
    rect = _pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE,
                        size_tiles * TILE_SIZE, size_tiles * TILE_SIZE)
    for b in gs.buildings:
        if not b.alive:
            continue
        other = _pygame.Rect(b.x - b.width // 2, b.y - b.height // 2,
                             b.width, b.height)
        if rect.colliderect(other):
            return False
    return True


def find_build_spot(gs, player_id, size_tiles, max_radius=22):
    """Найти свободное место для здания вокруг базы игрока (спираль)."""
    base = _get_main_base(gs, player_id)
    if not base:
        return None
    btx, bty = gs.tilemap.world_to_tile(base.x, base.y)

    for r in range(4, max_radius):
        # перебираем периметр квадрата со стороной 2r
        candidates = []
        for dx in range(-r, r + 1):
            for dy in (-r, r):
                candidates.append((btx + dx, bty + dy))
        for dy in range(-r + 1, r):
            for dx in (-r, r):
                candidates.append((btx + dx, bty + dy))
        for tx, ty in candidates:
            if 2 <= tx < gs.tilemap.width - size_tiles - 1 and \
               2 <= ty < gs.tilemap.height - size_tiles - 1:
                if gs.tilemap.is_buildable(tx, ty, size_tiles) and \
                        _footprint_free_of_buildings(gs, tx, ty, size_tiles):
                    return (tx, ty)
    return None


def _get_main_base(gs, player_id):
    """Главное здание игрока (первый живой HQ, иначе любое здание)."""
    hq = None
    fallback = None
    for b in gs.buildings:
        if b.player_id != player_id or not b.alive:
            continue
        if b.accepts_resources and hq is None:
            hq = b
        if fallback is None:
            fallback = b
    return hq or fallback


class EconomyManager:
    """Экономика ИИ: рабочие, supply, билд-ордер."""

    def __init__(self, brain):
        self.brain = brain
        self.order_index = 0

    # ---------- вспомогательные выборки ----------

    def my_buildings(self, gs, completed_only=False):
        res = []
        for b in gs.buildings:
            if b.player_id == self.brain.player_id and b.alive:
                if completed_only and not b.is_completed:
                    continue
                res.append(b)
        return res

    def my_workers(self, gs):
        return [u for u in gs.units
                if u.player_id == self.brain.player_id and u.alive
                and getattr(u, 'harvest_state', None) is not None]

    def count_building(self, gs, cls, include_uncompleted=True):
        n = 0
        for b in gs.buildings:
            if b.player_id == self.brain.player_id and b.alive:
                if isinstance(b, cls):
                    if include_uncompleted or b.is_completed:
                        n += 1
        return n

    # ---------- рабочие ----------

    def _nearest_resource(self, gs, wx, wy, tile_type):
        best = None
        best_d = float('inf')
        tiles = gs.tilemap.titan_deposits if tile_type == TILE_TITAN_ORE \
            else gs.tilemap.plasma_geysers
        for tx, ty in tiles:
            d = (tx * TILE_SIZE - wx) ** 2 + (ty * TILE_SIZE - wy) ** 2
            if d < best_d:
                best_d = d
                best = (tx, ty)
        return best

    def assign_idle_workers(self, gs):
        """Отправить простаивающих рабочих на ближайшие ресурсы."""
        base = _get_main_base(gs, self.brain.player_id)
        if not base:
            return
        workers = self.my_workers(gs)
        plasma_assigned = 0
        for w in workers:
            busy = (w.harvest_state != 'IDLE' or w.building_state != 'IDLE'
                    or w.state != 'IDLE')
            if busy:
                if w.carrying_resource == 'plasma' or \
                   (w.harvest_target and gs.tilemap.get_tile(*w.harvest_target)
                    == TILE_PLASMA_GEYSER):
                    plasma_assigned += 1
                continue

            # ~2 рабочих на плазму, остальные на титан
            if plasma_assigned < 2 and gs.tilemap.plasma_geysers:
                tile = self._nearest_resource(gs, w.x, w.y, TILE_PLASMA_GEYSER)
                if tile:
                    w.command_harvest(tile[0], tile[1])
                    plasma_assigned += 1
                    continue

            tile = self._nearest_resource(gs, base.x, base.y, TILE_TITAN_ORE)
            if tile:
                w.command_harvest(tile[0], tile[1])

    def manage_workers(self, gs):
        """Держать целевое число рабочих: ставить в очередь на HQ."""
        player = gs.players[self.brain.player_id]
        diff = self.brain.diff
        target = min(diff['max_workers'], self.brain.strategy_cfg['worker_target'])

        workers = self.my_workers(gs)
        if len(workers) >= target:
            return

        hqs = [b for b in self.my_buildings(gs, completed_only=True)
               if b.accepts_resources and b.can_produce]
        for hq in hqs:
            if len(hq.production_queue) == 0:
                from entities.worker import Worker
                hq.queue_unit(Worker, gs)
                return

    # ---------- supply ----------

    def manage_supply(self, gs):
        """Построить склад, если население упирается в лимит."""
        player = gs.players[self.brain.player_id]
        if player.max_supply >= MAX_SUPPLY:
            return True
        if player.current_supply + 3 <= player.max_supply:
            return True

        # Уже строится склад?
        for b in self.my_buildings(gs):
            if isinstance(b, SupplyDepot) and not b.is_completed:
                return True

        spot = find_build_spot(gs, self.brain.player_id, SupplyDepot(0, 0).size_tiles)
        if spot:
            return place_building_at(gs, self.brain.player_id,
                                     SupplyDepot, spot[0], spot[1]) is not None
        return False

    # ---------- билд-ордер ----------

    def manage_build_order(self, gs):
        """Выполнить следующий шаг билд-ордера стратегии."""
        cfg = self.brain.strategy_cfg
        order = cfg['build_order']
        limits = cfg.get('building_limits', {})
        player = gs.players[self.brain.player_id]

        # Уже что-то строится?
        under_construction = [b for b in self.my_buildings(gs)
                              if not b.is_completed]
        if under_construction:
            return False

        # Ищем следующий доступный шаг (с учётом лимитов и ошибок новичка)
        for _ in range(len(order)):
            if self.order_index >= len(order):
                self.order_index = 0  # порядок кончился — зацикливаемся
                return False

            cls = order[self.order_index]

            # Страховка: в билд-ордере могут быть только здания
            if not (isinstance(cls, type) and hasattr(cls, 'size_tiles')):
                self.order_index += 1
                continue

            limit = limits.get(cls)
            if limit is not None and self.count_building(gs, cls) >= limit:
                self.order_index += 1
                continue

            # Новобранец иногда «забывает» построить
            if self.brain.rng.random() < self.brain.diff['mistake_chance']:
                self.order_index += 1
                continue

            spot = find_build_spot(gs, self.brain.player_id, cls(0, 0).size_tiles)
            if spot and place_building_at(gs, self.brain.player_id,
                                          cls, spot[0], spot[1]):
                self.order_index += 1
                return True
            # Место/ресурсов нет — пробуем дальше в следующий тик
            return False

        return False

    # ---------- оборона базой ----------

    def manage_defense_buildings(self, gs):
        """Достроить целевое число турелей вокруг базы (вне билд-ордера).

        Работает только при «излишке» титана, чтобы не голодать билд-ордер.
        """
        cfg = self.brain.strategy_cfg
        target = cfg.get('turret_target', 0)
        if target <= 0:
            return
        current = self.count_building(gs, Turret) + self.count_building(gs, ArtilleryBunker)
        if current >= target:
            return
        player = gs.players[self.brain.player_id]
        # Буфер: турель не должна срывать следующий шаг билд-ордера
        if player.titan < 400:
            return
        spot = find_build_spot(gs, self.brain.player_id, 1)
        if spot:
            place_building_at(gs, self.brain.player_id, Turret, spot[0], spot[1])

    def update(self, gs):
        """Один тик мышления макро-менеджера."""
        self.assign_idle_workers(gs)
        self.manage_workers(gs)
        self.manage_supply(gs)
        self.manage_build_order(gs)
        self.manage_defense_buildings(gs)
