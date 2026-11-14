"""
botyaraRTS - ai/brain.py
Мозг ИИ-игрока: связывает макро-экономику, армейского командира
и оценщик сдачи. Один экземпляр на каждого ИИ-игрока в матче.

Детерминизм: таймеры копят dt симуляции, случайность — только gs.rng.
"""
from ai.config import get_difficulty
from ai.strategies import resolve_strategy, get_strategy
from ai.macro import EconomyManager
from ai.commander import ArmyManager
from ai.surrender import SurrenderEvaluator


class AIBrain:
    def __init__(self, player_id, difficulty='standard', strategy='random'):
        self.player_id = player_id
        self.diff_id = difficulty if difficulty in (
            'novice', 'standard', 'veteran', 'nightmare') else 'standard'
        self.diff = get_difficulty(self.diff_id)

        # Стратегия 'random' резолвится при первом апдейте через gs.rng
        self.strategy_id = strategy
        self.strategy_cfg = None

        self.rng = None
        self.macro = EconomyManager(self)
        self.commander = ArmyManager(self)
        self.surrender = SurrenderEvaluator(self)

        self.think_timer = 0.0
        self.desperate = False   # True после отказа игрока принять сдачу
        self._initialized = False

    def _init_from_game_state(self, gs):
        """Привязка к конкретному матчу (один раз)."""
        self.rng = gs.rng
        self.strategy_id = resolve_strategy(self.strategy_id, gs.rng)
        self.strategy_cfg = get_strategy(self.strategy_id)
        # Множитель дохода сложности ИИ
        player = gs.players.get(self.player_id)
        if player:
            player.income_mult = self.diff['income_mult']
        self._initialized = True

    def update(self, dt, gs):
        """Тик мозга (вызывается из симуляции каждый кадр/тик)."""
        player = gs.players.get(self.player_id)
        if not player or player.is_defeated:
            return

        if not self._initialized:
            self._init_from_game_state(gs)

        self.think_timer += dt
        if self.think_timer >= self.diff['think_interval']:
            self.think_timer = 0.0
            self.macro.update(gs)
            self.commander.update(gs)
            self.surrender.update(gs)

    # ---------- отладка/интерфейс ----------

    def describe(self):
        """Короткое описание для дебаг-панели."""
        return f"AI{self.player_id}[{self.diff_id}/{self.strategy_id}" \
               f"{'/ALL-IN' if self.desperate else ''}]"
