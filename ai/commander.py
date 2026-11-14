"""
botyaraRTS - ai/commander.py
Армейский командир ИИ: производство, отряды, атаки, оборона, диверсии.
"""
import math
from settings import *
from entities.worker import Worker


def army_value(units):
    """Сила группы в «титане» (стоимость юнитов)."""
    return sum(u.cost_titan + u.cost_plasma for u in units)


class ArmyManager:
    """Управление армией: очередь производства, атаки, оборона."""

    def __init__(self, brain):
        self.brain = brain
        self.attack_state = 'idle'      # idle | attacking | retreating
        self.squad_ids = set()          # id юнитов атакующей группы
        self.squad_start_value = 0
        self.harass_timer = 0
        self.retarget_timer = 0

    # ---------- выборки ----------

    def my_combat_units(self, gs):
        return [u for u in gs.units
                if u.player_id == self.brain.player_id and u.alive
                and not isinstance(u, Worker)]

    def my_workers(self, gs):
        return [u for u in gs.units
                if u.player_id == self.brain.player_id and u.alive
                and isinstance(u, Worker)]

    def enemy_entities(self, gs):
        pid = self.brain.player_id
        return ([b for b in gs.buildings if b.alive and b.player_id != pid] +
                [u for u in gs.units if u.alive and u.player_id != pid])

    def _main_base(self, gs):
        from ai.macro import _get_main_base
        return _get_main_base(gs, self.brain.player_id)

    def _nearest_enemy_building(self, gs, wx, wy):
        best, best_d = None, float('inf')
        for b in gs.buildings:
            if b.alive and b.player_id != self.brain.player_id:
                d = (b.x - wx) ** 2 + (b.y - wy) ** 2
                if d < best_d:
                    best_d, best = d, b
        return best

    def _nearest_enemy_worker(self, gs, wx, wy):
        best, best_d = None, float('inf')
        for u in gs.units:
            if u.alive and u.player_id != self.brain.player_id \
                    and isinstance(u, Worker):
                d = (u.x - wx) ** 2 + (u.y - wy) ** 2
                if d < best_d:
                    best_d, best = d, u
        return best

    # ---------- производство ----------

    def manage_production(self, gs):
        """Заполнять очереди производства по целевому составу армии."""
        cfg = self.brain.strategy_cfg
        composition = cfg['army_composition']
        buildings = [b for b in gs.buildings
                     if b.player_id == self.brain.player_id and b.alive
                     and b.is_completed and b.can_produce
                     and len(b.production_queue) < 2]
        if not buildings:
            return

        counts = {}
        for u in self.my_combat_units(gs):
            counts[type(u)] = counts.get(type(u), 0) + 1

        producible = {}
        for b in buildings:
            for cls in b.get_producible_units():
                producible.setdefault(cls, []).append(b)

        # Очередь на здание: выбираем тип с наибольшим дефицитом
        for b in buildings:
            if len(b.production_queue) >= 2:
                continue
            best_cls, best_deficit = None, 0.0
            for cls, weight in composition:
                if cls not in producible:
                    continue
                have = counts.get(cls, 0)
                deficit = (weight - have) / max(1.0, weight)
                if deficit > best_deficit:
                    best_deficit = deficit
                    best_cls = cls
            if best_cls is not None:
                if b.queue_unit(best_cls, gs):
                    counts[best_cls] = counts.get(best_cls, 0) + 1

    # ---------- угрозы и оборона ----------

    def find_threat(self, gs):
        """Вражеские юниты рядом с нашими зданиями."""
        radius = self.brain.strategy_cfg['defend_radius']
        my_buildings = [b for b in gs.buildings
                        if b.player_id == self.brain.player_id and b.alive]
        if not my_buildings:
            return None
        for b in my_buildings:
            threat = gs.spatial_hash.query_nearest(
                b.x, b.y, radius,
                filter_fn=lambda e: e.alive and e.is_enemy(b) and not e.is_building
            )
            if threat:
                return threat
        return None

    def handle_defense(self, gs, threat):
        """Отбить вторжение: свободные юниты + отозванная группа."""
        units = self.my_combat_units(gs)

        # Если групповая атака идёт — отзываем её только при серьёзной угрозе
        nearby = gs.spatial_hash.query_radius(threat.x, threat.y, 300)
        enemy_nearby = [e for e in nearby
                        if e.alive and e.is_enemy(threat) and not e.is_building]
        if self.attack_state == 'attacking' and len(enemy_nearby) < 3:
            return  # атака важнее пары разведчиков

        self.attack_state = 'idle'
        self.squad_ids.clear()
        for u in units:
            u.attack_target_entity(threat) if u.distance_to(threat) < 600 \
                else u.move_to_point(threat.x, threat.y, gs.tilemap, attack_move=True)

    # ---------- атаки ----------

    def _squad_units(self, gs):
        alive = [u for u in gs.units if u.id in self.squad_ids and u.alive]
        return alive

    def _start_attack(self, gs, units):
        cfg = self.brain.strategy_cfg
        diff = self.brain.diff
        max_squad = diff['max_attack_squad']
        squad = units[:max_squad]
        if not squad:
            return

        cx = sum(u.x for u in squad) / len(squad)
        cy = sum(u.y for u in squad) / len(squad)
        target = self._nearest_enemy_building(gs, cx, cy)
        if target is None:
            # Зданий нет — атакуем юнитов
            enemies = self.enemy_entities(gs)
            if not enemies:
                return
            target = enemies[0]

        for u in squad:
            u.move_to_point(target.x, target.y, gs.tilemap, attack_move=True)
            self.squad_ids.add(u.id)

        self.squad_start_value = army_value(squad)
        self.attack_state = 'attacking'

    def _retreat(self, gs, squad):
        base = self._main_base(gs)
        self.attack_state = 'retreating'
        if base:
            for u in squad:
                u.move_to_point(base.x + self.brain.rng.randint(-96, 96),
                                base.y + self.brain.rng.randint(-96, 96),
                                gs.tilemap)
        self.squad_ids.clear()
        self.attack_state = 'idle'

    def manage_attack(self, gs):
        cfg = self.brain.strategy_cfg
        diff = self.brain.diff
        units = self.my_combat_units(gs)
        value = army_value(units)

        if self.attack_state == 'attacking':
            squad = self._squad_units(gs)
            if not squad:
                self.attack_state = 'idle'
                return

            # Отступление при тяжёлых потерях (дисциплина по сложности)
            frac = army_value(squad) / max(1, self.squad_start_value)
            if frac < (1.0 - diff['squad_retreat_frac']) and diff['squad_retreat_frac'] > 0:
                self._retreat(gs, squad)
                return

            # Дотягиваем подкрепления
            for u in units:
                if u.id not in self.squad_ids and len(self.squad_ids) < diff['max_attack_squad'] \
                        and u.state == 'IDLE':
                    target = self._nearest_enemy_building(gs, u.x, u.y)
                    if target:
                        u.move_to_point(target.x, target.y, gs.tilemap, attack_move=True)
                        self.squad_ids.add(u.id)

            # Переназначение цели простаивающим и осадный режим танков
            self.retarget_timer -= 1
            for u in squad:
                if u.state == 'IDLE':
                    target = self._nearest_enemy_building(gs, u.x, u.y)
                    if target:
                        u.move_to_point(target.x, target.y, gs.tilemap,
                                        attack_move=True)
                self._auto_siege(gs, u)

        else:
            # Триггер атаки: сила армии или поздний тайминг
            threshold_cost = cfg['attack_min_army'] * 120
            time_ok = gs.game_time > cfg['attack_time']
            if value >= threshold_cost or (time_ok and value >= threshold_cost * 0.5):
                idle_units = [u for u in units if u.state == 'IDLE'] or units
                self._start_attack(gs, idle_units)

    def _auto_siege(self, gs, unit):
        """Осадные танки разворачиваются у вражеских зданий."""
        if not hasattr(unit, 'siege_mode'):
            return
        target = self._nearest_enemy_building(gs, unit.x, unit.y)
        if target is None:
            return
        dist = unit.distance_to(target)
        if dist < unit.siege_range * 0.8 and not unit.siege_mode:
            unit.toggle_siege()
        elif dist > unit.siege_range * 1.2 and unit.siege_mode:
            unit.toggle_siege()

    # ---------- диверсии ----------

    def manage_harass(self, gs):
        """Рейды по экономике противника (снайперы, диверсанты, мины)."""
        self.harass_timer -= 1
        if self.harass_timer > 0:
            return
        self.harass_timer = 25  # тиков мышления (~30 сек)

        from entities.infantry import Sniper
        from entities.special_units import Saboteur, MineDrone

        harassers = [u for u in self.my_combat_units(gs)
                     if u.state == 'IDLE' and
                     isinstance(u, (Sniper, Saboteur, MineDrone))]
        if not harassers:
            return

        # Цель — вражеский рабочий возле его базы
        enemies = [b for b in gs.buildings
                   if b.alive and b.player_id != self.brain.player_id]
        if not enemies:
            return
        enemy_base = enemies[0]
        worker = self._nearest_enemy_worker(gs, enemy_base.x, enemy_base.y)
        target_pos = worker if worker else enemy_base

        for u in harassers[:2]:
            u.attack_target_entity(target_pos)

    # ---------- отчаяние ----------

    def all_in(self, gs):
        """Отчаянный режим: в атаку идёт всё, отступлений нет."""
        units = self.my_combat_units(gs)
        if not units:
            return
        target = self._nearest_enemy_building(gs, units[0].x, units[0].y)
        if target is None:
            enemies = self.enemy_entities(gs)
            if not enemies:
                return
            target = enemies[0]
        for u in units:
            if u.state == 'IDLE':
                u.move_to_point(target.x, target.y, gs.tilemap, attack_move=True)
            self._auto_siege(gs, u)

    # ---------- тик ----------

    def update(self, gs):
        self.manage_production(gs)

        threat = self.find_threat(gs)
        if threat is not None:
            self.handle_defense(gs, threat)
            return

        if self.brain.desperate:
            self.all_in(gs)
        else:
            self.manage_attack(gs)

        if self.brain.strategy_cfg.get('harass') and not self.brain.desperate:
            self.manage_harass(gs)
