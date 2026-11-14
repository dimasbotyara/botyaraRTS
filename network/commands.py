"""
botyaraRTS - network/commands.py
Сетевые игровые команды: применение и маршрутизация.

В одиночной игре команда применяется сразу (apply_command),
в сетевой — отправляется на сервер, ретранслируется всем и применяется
на границе тика симуляции в порядке seq сервера (мягкий локстеп).
"""
from settings import *
from systems.commands import place_building_at
from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER

from entities.building import (
    Headquarters, SupplyDepot, Refinery, PlasmaExtractor, TradingPost,
    Barracks, Factory, Starport, SpecOpsLab,
    Turret, SAMSite, Wall, ArtilleryBunker, ShieldGenerator,
    Armory, EngineeringBay,
)
from entities.worker import Worker
from entities.infantry import Scout, Trooper, Sniper, RocketSoldier, Medic, ExoSoldier
from entities.vehicles import Buggy, Tank, Flamethrower, SiegeTank, MobileAA, MechWalker
from entities.aircraft import ScoutDrone, AttackHelicopter, Fighter, Bomber, Transport
from entities.special_units import Saboteur, PsiUnit, MineDrone, SuperUnit

# Реестры имён для сериализации
BUILDING_BY_NAME = {cls.__name__: cls for cls in (
    Headquarters, SupplyDepot, Refinery, PlasmaExtractor, TradingPost,
    Barracks, Factory, Starport, SpecOpsLab,
    Turret, SAMSite, Wall, ArtilleryBunker, ShieldGenerator,
    Armory, EngineeringBay,
)}
UNIT_BY_NAME = {cls.__name__: cls for cls in (
    Worker, Scout, Trooper, Sniper, RocketSoldier, Medic, ExoSoldier,
    Buggy, Tank, Flamethrower, SiegeTank, MobileAA, MechWalker,
    ScoutDrone, AttackHelicopter, Fighter, Bomber, Transport,
    Saboteur, PsiUnit, MineDrone, SuperUnit,
)}


def _entity_index(gs):
    """Индекс id → сущность (юниты + здания)."""
    idx = {}
    for e in gs.units:
        idx[e.id] = e
    for b in gs.buildings:
        idx[b.id] = b
    return idx


def _own_entities(gs, player_id, ids, entity_filter=None):
    """Живые сущности игрока по списку id."""
    idx = _entity_index(gs)
    result = []
    for eid in ids:
        e = idx.get(eid)
        if e is None or not e.alive or e.player_id != player_id:
            continue
        if entity_filter and not entity_filter(e):
            continue
        result.append(e)
    return result


def apply_command(gs, cmd):
    """Применить команду к состоянию игры (детерминированно)."""
    kind = cmd.get('cmd')
    player_id = cmd.get('player_id', gs.local_player_id)

    if kind == 'move':
        units = _own_entities(gs, player_id, cmd.get('unit_ids', []),
                              lambda e: e.is_unit)
        x = float(cmd.get('x', 0))
        y = float(cmd.get('y', 0))
        am = bool(cmd.get('attack_move'))
        shift = bool(cmd.get('shift'))
        for u in units:
            u.move_to_point(x, y, gs.tilemap, attack_move=am, shift=shift)

    elif kind == 'attack':
        idx = _entity_index(gs)
        target = idx.get(cmd.get('target_id'))
        if target is not None and target.alive:
            units = _own_entities(gs, player_id, cmd.get('unit_ids', []),
                                  lambda e: e.is_unit)
            shift = bool(cmd.get('shift'))
            for u in units:
                u.attack_target_entity(target, shift=shift)

    elif kind == 'stop':
        for u in _own_entities(gs, player_id, cmd.get('unit_ids', []),
                               lambda e: e.is_unit):
            if hasattr(u, 'stop'):
                u.stop()

    elif kind == 'stance':
        from systems.stances import StanceSystem
        units = _own_entities(gs, player_id, cmd.get('unit_ids', []),
                              lambda e: e.is_unit)
        StanceSystem.set_stance(units, cmd.get('stance', 'AGGRESSIVE'))

    elif kind == 'siege':
        for u in _own_entities(gs, player_id, cmd.get('unit_ids', []),
                               lambda e: e.is_unit):
            if hasattr(u, 'toggle_siege'):
                u.toggle_siege()

    elif kind == 'harvest':
        tx, ty = int(cmd.get('tx', 0)), int(cmd.get('ty', 0))
        shift = bool(cmd.get('shift'))
        for u in _own_entities(gs, player_id, cmd.get('unit_ids', []),
                               lambda e: e.is_unit):
            if isinstance(u, Worker):
                u.command_harvest(tx, ty, shift=shift)

    elif kind == 'resume_build':
        idx = _entity_index(gs)
        target = idx.get(cmd.get('target_id'))
        if target is not None and target.alive:
            shift = bool(cmd.get('shift'))
            for u in _own_entities(gs, player_id, cmd.get('unit_ids', []),
                                   lambda e: e.is_unit):
                if isinstance(u, Worker):
                    u.command_resume_build(target, shift=shift)

    elif kind == 'rally':
        x, y = float(cmd.get('x', 0)), float(cmd.get('y', 0))
        for b in _own_entities(gs, player_id, cmd.get('unit_ids', []),
                               lambda e: e.is_building):
            if b.can_produce:
                b.set_rally_point(x, y)

    elif kind == 'build':
        cls = BUILDING_BY_NAME.get(cmd.get('building'))
        if cls is not None:
            place_building_at(gs, player_id, cls,
                              int(cmd.get('tx', 0)), int(cmd.get('ty', 0)))

    elif kind == 'produce':
        idx = _entity_index(gs)
        building = idx.get(cmd.get('building_id'))
        cls = UNIT_BY_NAME.get(cmd.get('unit'))
        if building is not None and cls is not None and building.alive \
                and building.player_id == player_id:
            building.queue_unit(cls, gs)

    elif kind == 'cancel_produce':
        idx = _entity_index(gs)
        building = idx.get(cmd.get('building_id'))
        if building is not None and building.player_id == player_id:
            building.cancel_production(cmd.get('index'), game_state=gs)

    elif kind == 'upgrade_pick':
        if player_id == gs.local_player_id and gs.upgrade_system.is_choosing:
            replace_index = cmd.get('replace_index')
            gs.upgrade_system.select_upgrade(
                int(cmd.get('index', 0)), gs,
                replace_index=replace_index if replace_index is None
                else int(replace_index))

    elif kind == 'upgrade_skip':
        if player_id == gs.local_player_id and gs.upgrade_system.is_choosing:
            gs.upgrade_system.skip_upgrade(gs)

    elif kind == 'ping':
        gs.ping_system.add_ping(float(cmd.get('x', 0)), float(cmd.get('y', 0)),
                                cmd.get('type', 'attention'))

    elif kind == 'chat':
        gs.chat.add_message({
            'text': str(cmd.get('text', ''))[:200],
            'sender': gs.players.get(player_id).name
            if gs.players.get(player_id) else f"Player {player_id}",
            'mode': cmd.get('mode', 'all'),
        })

    else:
        # Неизвестная команда — игнорируем (совместимость версий)
        pass


def issue_command(gs, cmd):
    """Точка входа для игровой логики: локально или через сеть."""
    session = getattr(gs, 'net_session', None)
    import os
    if session is not None and session.connected and session.in_game:
        session.queue_local_command(cmd)
    else:
        if os.environ.get('BOTYARA_NET_DEBUG') and cmd.get('cmd') not in ('chat', 'ping'):
            import sys
            print(f"[NET-DEBUG] fallback: session={session} connected="
                  f"{getattr(session, 'connected', None)} in_game="
                  f"{getattr(session, 'in_game', None)} cmd={cmd.get('cmd')}",
                  file=sys.stderr, flush=True)
        apply_command(gs, cmd)


def compute_state_hash(gs):
    """Лёгкий хэш состояния для детекта рассинхрона."""
    try:
        units = sorted(gs.units, key=lambda e: e.id)
        buildings = sorted(gs.buildings, key=lambda e: e.id)
        h = 2166136261
        for e in units:
            h = ((h ^ e.id) * 16777619) & 0xFFFFFFFF
            h = ((h ^ int(e.hp)) * 16777619) & 0xFFFFFFFF
            h = ((h ^ int(e.x)) * 16777619) & 0xFFFFFFFF
            h = ((h ^ int(e.y)) * 16777619) & 0xFFFFFFFF
        for b in buildings:
            h = ((h ^ b.id) * 16777619) & 0xFFFFFFFF
            h = ((h ^ int(b.hp)) * 16777619) & 0xFFFFFFFF
        for pid, p in gs.players.items():
            h = ((h ^ int(p.titan)) * 16777619) & 0xFFFFFFFF
        return f"{h:08x}"
    except Exception:
        return "error"
