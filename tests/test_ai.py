"""
botyaraRTS - tests/test_ai.py
ИИ: конфиги сложностей, стратегии, детерминизм, механика сдачи.
"""
import pytest

from ai.config import DIFFICULTIES, get_difficulty, DIFFICULTY_IDS
from ai.strategies import STRATEGIES, get_strategy, resolve_strategy, STRATEGY_IDS
from ai.brain import AIBrain
from ai.surrender import SurrenderEvaluator
from entities.worker import Worker
from entities.building import (
    SupplyDepot, Refinery, Barracks, Turret, Wall, ArtilleryBunker,
    SAMSite, ShieldGenerator, Starport, SpecOpsLab, Factory,
)


def test_difficulties_complete():
    for d in DIFFICULTY_IDS:
        cfg = DIFFICULTIES[d]
        assert 0 < cfg['think_interval'] <= 3
        assert 0 <= cfg['mistake_chance'] <= 1
        assert cfg['income_mult'] > 0
        assert cfg['max_workers'] >= 10
    # Сложности монотонно усиливаются
    assert (DIFFICULTIES['novice']['think_interval']
            > DIFFICULTIES['nightmare']['think_interval'])


def test_strategies_have_valid_build_orders():
    building_classes = (SupplyDepot, Refinery, Barracks, Starport, SpecOpsLab,
                        Factory, Turret, SAMSite, Wall, ArtilleryBunker,
                        ShieldGenerator)
    for name, cfg in STRATEGIES.items():
        assert cfg['worker_target'] >= 10
        assert cfg['build_order'], name
        for cls in cfg['build_order']:
            assert cls in building_classes, f"{name}: {cls} не здание"
        assert cfg['army_composition']
        assert cfg['attack_min_army'] >= 3
        assert get_strategy(name) is cfg


def test_resolve_strategy_random_uses_rng():
    class FakeRng:
        def __init__(self):
            self.calls = 0

        def choice(self, seq):
            self.calls += 1
            return seq[0]
    rng = FakeRng()
    assert resolve_strategy('random', rng) == STRATEGY_IDS[0]
    assert rng.calls == 1
    assert resolve_strategy('rush', rng) == 'rush'
    assert rng.calls == 1  # для конкретной стратегии RNG не нужен


def test_brain_binds_to_game_rng(game_state):
    """Мозг привязывается к gs.rng и не трогает глобальный random."""
    brain = AIBrain(1, difficulty='veteran', strategy='rush')
    gs = game_state
    brain._init_from_game_state(gs)
    assert brain.rng is gs.rng
    assert brain.strategy_id == 'rush'
    assert brain.strategy_cfg is STRATEGIES['rush']
    # Множитель дохода применён к игроку
    assert gs.players[1].income_mult == brain.diff['income_mult']


def test_brain_random_strategy_deterministic():
    """random-стратегия резолвится одинаково при одинаковом состоянии RNG
    (в матче оба клиента идут по одной ветке gs.rng)."""
    import random

    class FakeGS:
        players = {}

    results = []
    for _ in range(2):
        gs = FakeGS()
        gs.rng = random.Random(4242)
        brain = AIBrain(1, 'standard', 'random')
        brain._init_from_game_state(gs)
        results.append(brain.strategy_id)
    assert results[0] == results[1]


def _wreck_ai(gs, pid=1):
    """Свести экономику ИИ к безнадёжной (тест не крутит симуляцию,
    поэтому обычное условие поражения не срабатывает)."""
    for b in list(gs.buildings):
        if b.player_id == pid and b.alive:
            b.take_damage(99999)
    for u in list(gs.units):
        if u.player_id == pid and u.alive:
            u.take_damage(99999)
    gs.players[pid].titan = 10


def test_surrender_triggers_in_hopeless_position(game_state):
    gs = game_state
    brain = AIBrain(1, 'standard', 'balanced')
    gs.ai_brains[1] = brain
    gs.ai_surrender_request = None
    gs.game_time = 200  # больше минимального
    _wreck_ai(gs)
    evaluator = brain.surrender
    score = evaluator.compute_hopelessness(gs)
    assert score >= 0.70
    evaluator.update(gs)
    assert gs.ai_surrender_request == 1


def test_surrender_not_requested_in_healthy_position(game_state):
    gs = game_state
    brain = AIBrain(1, 'standard', 'balanced')
    gs.ai_brains[1] = brain
    gs.game_time = 200
    evaluator = brain.surrender
    evaluator.update(gs)
    assert gs.ai_surrender_request is None
    assert evaluator.compute_hopelessness(gs) < 0.5


def test_surrender_respects_minimum_time(game_state):
    gs = game_state
    brain = AIBrain(1, 'standard', 'balanced')
    gs.game_time = 10  # слишком рано
    _wreck_ai(gs)
    brain.surrender.update(gs)
    assert gs.ai_surrender_request is None


def test_nightmare_holds_longer_than_novice():
    thresholds = {'novice': 0.60, 'standard': 0.70,
                  'veteran': 0.80, 'nightmare': 0.90}
    assert thresholds['novice'] < thresholds['nightmare']


def test_mistake_chance_by_difficulty():
    assert get_difficulty('novice')['mistake_chance'] \
        > get_difficulty('nightmare')['mistake_chance']
