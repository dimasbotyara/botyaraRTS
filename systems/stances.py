"""
botyaraRTS - systems/stances.py
Управление режимами поведения юнитов.
"""
from settings import STANCES


class StanceSystem:
    """Управление стойками юнитов."""

    @staticmethod
    def set_stance(entities, stance):
        """Установить стойку для группы юнитов."""
        if stance not in STANCES:
            return
        for entity in entities:
            if hasattr(entity, 'set_stance') and entity.is_unit:
                entity.set_stance(stance)

    @staticmethod
    def cycle_stance(entities):
        """Переключить стойку циклически."""
        if not entities:
            return
        current = entities[0].stance if hasattr(entities[0], 'stance') else 'AGGRESSIVE'
        idx = STANCES.index(current)
        next_stance = STANCES[(idx + 1) % len(STANCES)]
        StanceSystem.set_stance(entities, next_stance)
