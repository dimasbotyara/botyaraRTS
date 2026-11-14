"""
botyaraRTS - tests/test_economy.py
Экономика: расходы, supply, множитель дохода, отмена производства.
"""
from systems.economy import PlayerState
from entities.worker import Worker
from entities.building import Barracks, SupplyDepot


def test_spend_and_afford():
    p = PlayerState(0, start_titan=500, start_plasma=100)
    assert p.can_afford(500, 100)
    assert not p.can_afford(501, 0)
    assert p.spend(200, 50)
    assert p.titan == 300 and p.plasma == 50
    assert not p.spend(1000, 0)


def test_income_mult_applies_to_mined():
    p = PlayerState(0)
    p.income_mult = 1.5
    p.add_titan(8)
    p.add_plasma(8)
    assert p.titan == 500 + 12
    assert p.total_titan_mined == 12
    assert p.total_plasma_mined == 12
    p2 = PlayerState(1)
    p2.income_mult = 0.5
    p2.add_titan(8)
    assert p2.titan == 500 + 4


def test_supply_recalculation(game_state):
    gs = game_state
    player = gs.players[0]
    player.recalculate_supply(gs.buildings)
    player.recalculate_current_supply(gs.units)
    assert player.max_supply == 15 + 10  # HQ + склад
    assert player.current_supply == 6    # 6 рабочих


def test_queue_unit_checks_resources(game_state):
    gs = game_state
    player = gs.players[0]
    player.titan = 0
    hq = next(b for b in gs.buildings if b.accepts_resources)
    from entities.worker import Worker
    assert not hq.queue_unit(Worker, gs)  # нет денег
    player.titan = 1000
    assert hq.queue_unit(Worker, gs)
    assert len(hq.production_queue) == 1


def test_cancel_production_refunds(game_state):
    gs = game_state
    player = gs.players[0]
    player.titan = 1000
    player.plasma = 200
    barracks = Barracks(500, 500, 0)
    barracks.is_completed = True
    gs.add_entity(barracks)
    from entities.infantry import Trooper
    assert barracks.queue_unit(Trooper, gs)
    titan_before, plasma_before = player.titan, player.plasma
    barracks.cancel_production(0, game_state=gs)
    assert player.titan > titan_before      # возврат
    assert player.plasma >= plasma_before
    assert barracks.production_queue == []


def test_supply_block(game_state):
    gs = game_state
    player = gs.players[0]
    # Заполняем supply до лимита
    player.current_supply = player.max_supply
    barracks = next((b for b in gs.buildings if isinstance(b, SupplyDepot)), None)
    assert barracks is not None
    from entities.infantry import Trooper
    assert not barracks.queue_unit(Trooper, gs)  # нет места
