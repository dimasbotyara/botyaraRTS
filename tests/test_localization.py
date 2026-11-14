"""
botyaraRTS - tests/test_localization.py
Полнота переводов: en+ru парность, форматы, фолбэки.
"""
import localization
from localization import TRANSLATIONS, t, t_unit, t_building


def test_every_key_has_both_languages():
    for key, entry in TRANSLATIONS.items():
        assert 'en' in entry, f"{key}: нет 'en'"
        assert 'ru' in entry, f"{key}: нет 'ru'"
        assert entry['en'].strip(), f"{key}: пустой 'en'"
        assert entry['ru'].strip(), f"{key}: пустой 'ru'"


def test_format_placeholders_match():
    import re
    pattern = re.compile(r'\{(\w+)\}')
    for key, entry in TRANSLATIONS.items():
        en = set(pattern.findall(entry['en']))
        ru = set(pattern.findall(entry['ru']))
        assert en == ru, f"{key}: плейсхолдеры en={en} != ru={ru}"


def test_t_fallback_to_key():
    assert t('definitely.not.a.key') == 'definitely.not.a.key'


def test_t_returns_both_languages():
    localization.set_lang('en')
    en = t('menu.singleplayer')
    localization.set_lang('ru')
    ru = t('menu.singleplayer')
    assert en and ru and en != ru


def test_unit_and_building_names_localized():
    from entities.infantry import Trooper
    from entities.building import Barracks
    localization.set_lang('en')
    en = t_unit('Trooper')
    localization.set_lang('ru')
    ru = t_unit('Trooper')
    assert en != ru
    # Название здания через класс
    en_b = t_building('Barracks')
    assert en_b


def test_new_feature_keys_present():
    required = [
        'create.title', 'create.start', 'create.difficulty', 'create.strategy',
        'ai.diff.novice', 'ai.diff.nightmare', 'ai.strat.rush',
        'ai.strat.air_only', 'ai.strat.harass',
        'surrender.title', 'surrender.accept', 'surrender.decline',
        'mp.title', 'mp.host', 'mp.join', 'lobby.title', 'lobby.start',
        'mp.desync', 'gameover.surrender',
        'loading.ramps', 'loading.resources', 'loading.minimap',
    ]
    for key in required:
        assert key in TRANSLATIONS, f"нет ключа {key}"


def test_ai_difficulty_names_russian():
    localization.set_lang('ru')
    assert t('ai.diff.novice') == 'Новобранец'
    assert t('ai.diff.nightmare') == 'Кошмар'
    assert t('ai.strat.air_only') == 'Только авиация'
    localization.set_lang('en')
