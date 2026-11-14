"""
botyaraRTS - ai/surrender.py
Оценщик безнадёжности: бот признаёт, что матч проигран, и просит о сдаче.

Игрок получает одно предложение за матч (панель сверху): принять победу
или заставить бота драться дальше. При отказе бот переходит в отчаянный
режим (all-in) и больше не предлагает сдачу.
"""
from entities.worker import Worker


class SurrenderEvaluator:
    """Периодически считает «безнадёжность» положения бота (0..1)."""

    def __init__(self, brain):
        self.brain = brain
        self.check_interval = 5.0   # сек симуляции между проверками
        self.timer = 0.0
        self.min_game_time = 150.0  # не сдаёмся в первые 2.5 минуты

    # ---------- выборки ----------

    def _army_value(self, units):
        return sum(u.cost_titan + u.cost_plasma for u in units)

    def _my_units(self, gs):
        return [u for u in gs.units
                if u.player_id == self.brain.player_id and u.alive]

    def _my_buildings(self, gs):
        return [b for b in gs.buildings
                if b.player_id == self.brain.player_id and b.alive]

    # ---------- оценка ----------

    def compute_hopelessness(self, gs):
        """0 — всё прекрасно, 1 — абсолютно безнадёжно."""
        my_units = self._my_units(gs)
        my_buildings = self._my_buildings(gs)
        workers = [u for u in my_units if isinstance(u, Worker)]
        combat = [u for u in my_units if not isinstance(u, Worker)]

        enemy_units = [u for u in gs.units
                       if u.alive and u.player_id != self.brain.player_id
                       and not isinstance(u, Worker)]

        score = 0.0

        # 1. Штаб потерян — некуда сдавать ресурсы и производить рабочих
        hq_alive = any(b.accepts_resources for b in my_buildings)
        if not hq_alive:
            score += 0.45

        # 2. Производственных зданий не осталось (или все недостроены)
        production = [b for b in my_buildings
                      if b.can_produce and b.is_completed]
        if not production:
            score += 0.30

        # 3. Почти нечего оборонять
        if len(my_buildings) <= 2:
            score += 0.15

        # 4. Соотношение сил
        my_value = self._army_value(combat)
        enemy_value = self._army_value(enemy_units)
        if enemy_value > 0:
            if my_value == 0:
                score += 0.35
            elif enemy_value > my_value * 3:
                score += 0.30
            elif enemy_value > my_value * 2:
                score += 0.15

        # 5. Экономика мертва: рабочих нет и денег не хватает
        player = gs.players[self.brain.player_id]
        if len(workers) == 0 and player.titan < 150:
            score += 0.30
        elif len(workers) <= 2 and player.titan < 150:
            score += 0.20

        # 6. Огромные потери за матч
        lost = player.units_lost + player.buildings_lost
        produced = player.units_produced + player.buildings_built + 1
        if lost > 25 and lost > produced * 0.9:
            score += 0.10

        return min(1.0, score)

    def update(self, gs):
        """Тик проверки; при безнадёжности — запрос сдачи в GameState."""
        if self.brain.desperate:
            return
        self.timer += self.check_interval  # вызывается раз в тик мышления
        if gs.game_time < self.min_game_time:
            return
        if gs.ai_surrender_request is not None:
            return

        hopelessness = self.compute_hopelessness(gs)
        # Слабые боты сдаются легче, кошмар — держится до конца
        threshold = {'novice': 0.60, 'standard': 0.70,
                     'veteran': 0.80, 'nightmare': 0.90}.get(
            self.brain.diff_id, 0.70)
        if hopelessness >= threshold:
            gs.ai_surrender_request = self.brain.player_id
