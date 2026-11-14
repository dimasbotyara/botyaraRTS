"""
botyaraRTS - ai/config.py
Профили сложности ИИ. Все значения подобраны так, чтобы сложность
меняла скорость мышления, качество макро-решений и дисциплину,
а не только «читерский» доход.

Все таймеры копят dt симуляции, случайность берётся из gs.rng —
мозг полностью детерминирован (важно для сетевой игры с ИИ-слотами).
"""

DIFFICULTY_IDS = ['novice', 'standard', 'veteran', 'nightmare']

DIFFICULTIES = {
    # Новобранец: медленно думает, часто «забывает» строить, слабо контролирует армию
    'novice': {
        'think_interval': 2.5,     # сек между решениями макро/микро
        'reaction_time': 4.0,      # задержка реакции на вторжение
        'mistake_chance': 0.30,    # шанс пропустить шаг билд-ордера
        'income_mult': 0.75,       # handicap добычи
        'max_attack_squad': 5,     # максимум юнитов в атакующей группе
        'retreat_hp_frac': 0.20,   # отступать при HP < 20% (почти никогда)
        'aggression': 0.55,
        'squad_retreat_frac': 0.0, # группа не отступает (бьётся до конца)
        'scout': False,
        'max_workers': 10,
    },
    # Солдат: базовый уровень — примерно как опытный игрок-новичок
    'standard': {
        'think_interval': 1.5,
        'reaction_time': 2.2,
        'mistake_chance': 0.12,
        'income_mult': 1.0,
        'max_attack_squad': 10,
        'retreat_hp_frac': 0.35,
        'aggression': 0.8,
        'squad_retreat_frac': 0.45,
        'scout': True,
        'max_workers': 14,
    },
    # Ветеран: быстро реагирует, держит состав армии, отступает и перегруппировывается
    'veteran': {
        'think_interval': 1.0,
        'reaction_time': 1.2,
        'mistake_chance': 0.04,
        'income_mult': 1.1,
        'max_attack_squad': 14,
        'retreat_hp_frac': 0.45,
        'aggression': 1.0,
        'squad_retreat_frac': 0.55,
        'scout': True,
        'max_workers': 16,
    },
    # Кошмар: почти без ошибок, мгновенная реакция, усиленная экономика
    'nightmare': {
        'think_interval': 0.6,
        'reaction_time': 0.6,
        'mistake_chance': 0.0,
        'income_mult': 1.3,
        'max_attack_squad': 18,
        'retreat_hp_frac': 0.50,
        'aggression': 1.2,
        'squad_retreat_frac': 0.65,
        'scout': True,
        'max_workers': 18,
    },
}


def get_difficulty(name):
    """Профиль сложности по id (с безопасным фолбэком)."""
    return DIFFICULTIES.get(name, DIFFICULTIES['standard'])
