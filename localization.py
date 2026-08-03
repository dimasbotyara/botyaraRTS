"""
botyaraRTS - localization.py
Система локализации: Русский / English.
Все пользовательские строки собраны здесь.
"""
from settings import game_settings

# ===== ПЕРЕВОДЫ =====
TRANSLATIONS = {
    # ============================
    # MAIN MENU
    # ============================
    'menu.subtitle': {
        'en': 'A Sci-Fi Real-Time Strategy Game',
        'ru': 'Научно-фантастическая стратегия в реальном времени',
    },
    'menu.singleplayer': {
        'en': '▶  Singleplayer',
        'ru': '▶  Одиночная игра',
    },
    'menu.multiplayer': {
        'en': '🌐  Multiplayer',
        'ru': '🌐  Мультиплеер',
    },
    'menu.settings': {
        'en': '⚙  Settings',
        'ru': '⚙  Настройки',
    },
    'menu.quit': {
        'en': '✕  Quit',
        'ru': '✕  Выход',
    },

    # ============================
    # LOADING SCREEN
    # ============================
    'loading.quantum_core': {
        'en': 'Initializing Quantum Core...',
        'ru': 'Инициализация квантового ядра...',
    },
    'loading.terrain': {
        'en': 'Generating 320x320 Terrain Grid...',
        'ru': 'Генерация ландшафта 320x320...',
    },
    'loading.deploy_units': {
        'en': 'Deploying Player Headquarters & Field Units...',
        'ru': 'Развертывание штаба и полевых юнитов...',
    },
    'loading.enemy_outpost': {
        'en': 'Establishing Enemy Outpost...',
        'ru': 'Размещение вражеского форпоста...',
    },
    'loading.ready': {
        'en': 'Battle Operations Ready!',
        'ru': 'Боевые операции готовы!',
    },

    # ============================
    # COUNTDOWN
    # ============================
    'countdown.battle_start': {
        'en': 'BATTLE START!',
        'ru': 'БИТВА НАЧИНАЕТСЯ!',
    },

    # ============================
    # PAUSE MENU
    # ============================
    'pause.title': {
        'en': '⏸ PAUSED',
        'ru': '⏸ ПАУЗА',
    },
    'pause.continue': {
        'en': '▶ Continue',
        'ru': '▶ Продолжить',
    },
    'pause.settings': {
        'en': '⚙ Settings',
        'ru': '⚙ Настройки',
    },
    'pause.main_menu': {
        'en': '🏠 Main Menu',
        'ru': '🏠 Главное меню',
    },
    'pause.quit': {
        'en': '✕ Quit',
        'ru': '✕ Выход',
    },

    # ============================
    # GAME OVER
    # ============================
    'gameover.victory': {
        'en': '🏆 VICTORY!',
        'ru': '🏆 ПОБЕДА!',
    },
    'gameover.defeat': {
        'en': '💀 DEFEAT',
        'ru': '💀 ПОРАЖЕНИЕ',
    },
    'gameover.time': {
        'en': 'Time: {mins}m {secs}s',
        'ru': 'Время: {mins}м {secs}с',
    },
    'gameover.titan_plasma': {
        'en': 'Titan: {titan} | Plasma: {plasma}',
        'ru': 'Титан: {titan} | Плазма: {plasma}',
    },
    'gameover.units_stats': {
        'en': 'Units: {produced} built | {lost} lost',
        'ru': 'Юниты: {produced} создано | {lost} потеряно',
    },
    'gameover.buildings_stats': {
        'en': 'Buildings: {built} built | {lost} lost',
        'ru': 'Здания: {built} построено | {lost} потеряно',
    },
    'gameover.click_hint': {
        'en': 'Click anywhere to return to menu',
        'ru': 'Нажмите в любом месте, чтобы вернуться в меню',
    },

    # ============================
    # SETTINGS
    # ============================
    'settings.title': {
        'en': '⚙ Settings',
        'ru': '⚙ Настройки',
    },
    'settings.back': {
        'en': '← Back',
        'ru': '← Назад',
    },
    'settings.header_display': {
        'en': '─── Display ───',
        'ru': '─── Экран ───',
    },
    'settings.fullscreen': {
        'en': 'Fullscreen',
        'ru': 'Полный экран',
    },
    'settings.vsync': {
        'en': 'V-Sync',
        'ru': 'Верт. синхронизация',
    },
    'settings.fps_limit': {
        'en': 'FPS Limit',
        'ru': 'Лимит FPS',
    },
    'settings.header_camera': {
        'en': '─── Camera ───',
        'ru': '─── Камера ───',
    },
    'settings.edge_scrolling': {
        'en': 'Edge Scrolling',
        'ru': 'Скролл по краю экрана',
    },
    'settings.invert_zoom': {
        'en': 'Invert Zoom',
        'ru': 'Инвертировать зум',
    },
    'settings.lock_mouse': {
        'en': 'Lock Mouse',
        'ru': 'Захват мыши',
    },
    'settings.header_interface': {
        'en': '─── Interface ───',
        'ru': '─── Интерфейс ───',
    },
    'settings.hp_bars': {
        'en': 'HP Bars',
        'ru': 'Полоски здоровья',
    },
    'settings.hp_always': {
        'en': 'always',
        'ru': 'всегда',
    },
    'settings.hp_damaged': {
        'en': 'damaged',
        'ru': 'при уроне',
    },
    'settings.hp_selected': {
        'en': 'selected',
        'ru': 'выбраны',
    },
    'settings.hp_alt': {
        'en': 'alt',
        'ru': 'alt',
    },
    'settings.grid_overlay': {
        'en': 'Grid Overlay',
        'ru': 'Сетка',
    },
    'settings.grid_never': {
        'en': 'never',
        'ru': 'нет',
    },
    'settings.grid_building': {
        'en': 'building',
        'ru': 'строить',
    },
    'settings.grid_always': {
        'en': 'always',
        'ru': 'всегда',
    },
    'settings.header_gameplay': {
        'en': '─── Gameplay ───',
        'ru': '─── Геймплей ───',
    },
    'settings.rmb_auto_repeat': {
        'en': 'RMB Auto-Repeat (Dota 2 style)',
        'ru': 'Автоповтор ПКМ (как в Dota 2)',
    },
    'settings.header_audio': {
        'en': '─── Audio ───',
        'ru': '─── Звук ───',
    },
    'settings.minimize_sound': {
        'en': 'Sound When Minimized',
        'ru': 'Звук при свёрнутом окне',
    },
    'settings.header_network': {
        'en': '─── Network ───',
        'ru': '─── Сеть ───',
    },
    'settings.net_stats': {
        'en': 'Show Net Stats',
        'ru': 'Показать сетевую статистику',
    },
    'settings.auto_pause_desync': {
        'en': 'Auto Pause Desync',
        'ru': 'Авто-пауза при рассинхронизации',
    },
    'settings.header_language': {
        'en': '─── Language ───',
        'ru': '─── Язык ───',
    },
    'settings.language': {
        'en': 'Language',
        'ru': 'Язык',
    },

    # ============================
    # HUD
    # ============================
    'hud.selected': {
        'en': 'Selected: {count} units',
        'ru': 'Выбрано: {count} юнитов',
    },
    'hud.stance': {
        'en': 'Stance: {stance}',
        'ru': 'Стойка: {stance}',
    },
    'hud.build_tab_economy': {
        'en': '🏠 Economy',
        'ru': '🏠 Экономика',
    },
    'hud.build_tab_military': {
        'en': '⚔ Military',
        'ru': '⚔ Военные',
    },
    'hud.build_tab_research': {
        'en': '🔬 Research',
        'ru': '🔬 Исследования',
    },
    'hud.build_tab_defense': {
        'en': '🛡 Defense',
        'ru': '🛡 Оборона',
    },

    # ============================
    # STANCES
    # ============================
    'stance.AGGRESSIVE': {
        'en': 'Aggressive',
        'ru': 'Агрессивная',
    },
    'stance.DEFENSIVE': {
        'en': 'Defensive',
        'ru': 'Оборонительная',
    },
    'stance.HOLD_POSITION': {
        'en': 'Hold Position',
        'ru': 'Удержание позиции',
    },

    # ============================
    # UNIT NAMES
    # ============================
    'unit.Worker': {
        'en': 'Worker',
        'ru': 'Рабочий',
    },
    'unit.Trooper': {
        'en': 'Trooper',
        'ru': 'Боец',
    },
    'unit.Sniper': {
        'en': 'Sniper',
        'ru': 'Снайпер',
    },
    'unit.Medic': {
        'en': 'Medic',
        'ru': 'Медик',
    },
    'unit.Grenadier': {
        'en': 'Grenadier',
        'ru': 'Гренадер',
    },
    'unit.Tank': {
        'en': 'Tank',
        'ru': 'Танк',
    },
    'unit.Artillery': {
        'en': 'Artillery',
        'ru': 'Артиллерия',
    },
    'unit.APC': {
        'en': 'APC',
        'ru': 'БТР',
    },
    'unit.Buggy': {
        'en': 'Buggy',
        'ru': 'Багги',
    },
    'unit.Scout': {
        'en': 'Scout',
        'ru': 'Разведчик',
    },
    'unit.Bomber': {
        'en': 'Bomber',
        'ru': 'Бомбардировщик',
    },
    'unit.Fighter': {
        'en': 'Fighter',
        'ru': 'Истребитель',
    },
    'unit.Dropship': {
        'en': 'Dropship',
        'ru': 'Десантный корабль',
    },
    'unit.Ghost': {
        'en': 'Ghost',
        'ru': 'Призрак',
    },
    'unit.Saboteur': {
        'en': 'Saboteur',
        'ru': 'Диверсант',
    },
    'unit.Juggernaut': {
        'en': 'Juggernaut',
        'ru': 'Джаггернаут',
    },
    'unit.Commander': {
        'en': 'Commander',
        'ru': 'Командир',
    },

    # ============================
    # BUILDING NAMES
    # ============================
    'building.Headquarters': {
        'en': 'Headquarters',
        'ru': 'Штаб',
    },
    'building.SupplyDepot': {
        'en': 'Supply Depot',
        'ru': 'Склад снабжения',
    },
    'building.Barracks': {
        'en': 'Barracks',
        'ru': 'Казарма',
    },
    'building.Factory': {
        'en': 'Factory',
        'ru': 'Завод',
    },
    'building.Starport': {
        'en': 'Starport',
        'ru': 'Космопорт',
    },
    'building.ResearchLab': {
        'en': 'Research Lab',
        'ru': 'Лаборатория',
    },
    'building.Turret': {
        'en': 'Turret',
        'ru': 'Турель',
    },
    'building.Bunker': {
        'en': 'Bunker',
        'ru': 'Бункер',
    },
    'building.Refinery': {
        'en': 'Refinery',
        'ru': 'Нефтеперерабатывающий завод',
    },
    'building.AirDefense': {
        'en': 'Air Defense',
        'ru': 'ПВО',
    },
    'building.Reactor': {
        'en': 'Reactor',
        'ru': 'Реактор',
    },
    'building.Wall': {
        'en': 'Wall',
        'ru': 'Стена',
    },

    # ============================
    # RESOURCES
    # ============================
    'resource.titan': {
        'en': 'Titan',
        'ru': 'Титан',
    },
    'resource.plasma': {
        'en': 'Plasma',
        'ru': 'Плазма',
    },
    'resource.supply': {
        'en': 'Supply',
        'ru': 'Снабжение',
    },

    # ============================
    # LANGUAGE SELECTION SCREEN
    # ============================
    'langselect.title': {
        'en': 'Select Language / Выберите язык',
        'ru': 'Select Language / Выберите язык',
    },
    'langselect.english': {
        'en': 'English',
        'ru': 'English',
    },
    'langselect.russian': {
        'en': 'Русский',
        'ru': 'Русский',
    },

    # ============================
    # CHAT
    # ============================
    'chat.all': {
        'en': '[ALL]',
        'ru': '[ВСЕ]',
    },
    'chat.team': {
        'en': '[TEAM]',
        'ru': '[КОМАНДА]',
    },
    'chat.ally': {
        'en': '[ALLY]',
        'ru': '[СОЮЗНИК]',
    },
    'chat.hint': {
        'en': 'Tab to switch mode | Enter to send',
        'ru': 'Tab — переключить режим | Enter — отправить',
    },

    # ============================
    # MISSING UNIT NAMES
    # ============================
    'unit.Scout': {
        'en': 'Scout',
        'ru': 'Разведчик',
    },
    'unit.RocketSoldier': {
        'en': 'Rocket Soldier',
        'ru': 'Ракетчик',
    },
    'unit.ExoSoldier': {
        'en': 'Exo Soldier',
        'ru': 'Экзо-боец',
    },
    'unit.BattleTank': {
        'en': 'Battle Tank',
        'ru': 'Боевой танк',
    },
    'unit.Flamethrower': {
        'en': 'Flamethrower',
        'ru': 'Огнемётчик',
    },
    'unit.SiegeArtillery': {
        'en': 'Siege Artillery',
        'ru': 'Осадная артиллерия',
    },
    'unit.MobileAA': {
        'en': 'Mobile AA',
        'ru': 'Мобильная ПВО',
    },
    'unit.MechWalker': {
        'en': 'Mech Walker',
        'ru': 'Мех-шагатель',
    },
    'unit.ScoutDrone': {
        'en': 'Scout Drone',
        'ru': 'Разведывательный дрон',
    },
    'unit.AttackHelicopter': {
        'en': 'Attack Helicopter',
        'ru': 'Ударный вертолёт',
    },
    'unit.Transport': {
        'en': 'Transport',
        'ru': 'Транспорт',
    },
    'unit.PsiOperative': {
        'en': 'Psi Operative',
        'ru': 'Пси-оперативник',
    },
    'unit.MineLayer': {
        'en': 'Mine Layer',
        'ru': 'Минёр',
    },
    'unit.Punisher': {
        'en': 'Punisher',
        'ru': 'Каратель',
    },

    # ============================
    # MISSING BUILDING NAMES
    # ============================
    'building.PlasmaExtractor': {
        'en': 'Plasma Extractor',
        'ru': 'Экстрактор плазмы',
    },
    'building.TradingPost': {
        'en': 'Trading Post',
        'ru': 'Торговый пост',
    },
    'building.SpecOpsLab': {
        'en': 'Spec Ops Lab',
        'ru': 'Лаборатория спецопераций',
    },
    'building.SAMSite': {
        'en': 'SAM Site',
        'ru': 'Зенитный комплекс',
    },
    'building.ArtilleryBunker': {
        'en': 'Artillery Bunker',
        'ru': 'Артиллерийский бункер',
    },
    'building.ShieldGenerator': {
        'en': 'Shield Generator',
        'ru': 'Генератор щита',
    },
    'building.Armory': {
        'en': 'Armory',
        'ru': 'Оружейная',
    },
    'building.EngineeringBay': {
        'en': 'Engineering Bay',
        'ru': 'Инженерный отсек',
    },
    'building.AirDefense': {
        'en': 'Air Defense',
        'ru': 'ПВО',
    },

    # ============================
    # HUD LABELS
    # ============================
    'hud.titan': {
        'en': '⛏ Titan: {amount}',
        'ru': '⛏ Титан: {amount}',
    },
    'hud.plasma': {
        'en': '⚡ Plasma: {amount}',
        'ru': '⚡ Плазма: {amount}',
    },
    'hud.hp': {
        'en': 'HP: {current} / {max}',
        'ru': 'ОЗ: {current} / {max}',
    },
    'hud.shield': {
        'en': 'Shield: {current} / {max}',
        'ru': 'Щит: {current} / {max}',
    },
    'hud.dmg_rng_spd': {
        'en': 'DMG: {dmg}  RNG: {rng}  SPD: {spd}',
        'ru': 'УРОН: {dmg}  ДИСТ: {rng}  СКОР: {spd}',
    },
    'hud.fps': {
        'en': 'FPS: {fps}',
        'ru': 'FPS: {fps}',
    },

    # ============================
    # UPGRADE PICKER
    # ============================
    'upgrade.choose': {
        'en': 'Choose an Upgrade!',
        'ru': 'Выберите улучшение!',
    },
    'upgrade.replace_slot': {
        'en': 'Replace which slot?',
        'ru': 'Какой слот заменить?',
    },
    'upgrade.skip': {
        'en': 'Skip (+{amount} Titan)',
        'ru': 'Пропустить (+{amount} Титан)',
    },
    'upgrade.tier': {
        'en': 'Tier {tier}',
        'ru': 'Уровень {tier}',
    },
    'upgrade.click_replace': {
        'en': 'Click to replace',
        'ru': 'Нажмите для замены',
    },
    'upgrade.cancel': {
        'en': 'Cancel',
        'ru': 'Отмена',
    },

    # ============================
    # UPGRADE NAMES & DESCRIPTIONS
    # ============================
    'upgrade.Industrialization': {'en': 'Industrialization', 'ru': 'Индустриализация'},
    'upgrade.Industrialization.desc': {'en': 'Workers build 30% faster', 'ru': 'Рабочие строят на 30% быстрее'},
    'upgrade.ForcedMarch': {'en': 'Forced March', 'ru': 'Форсированный марш'},
    'upgrade.ForcedMarch.desc': {'en': 'Infantry moves 20% faster', 'ru': 'Пехота двигается на 20% быстрее'},
    'upgrade.EconomicBlueprints': {'en': 'Economic Blueprints', 'ru': 'Экономические чертежи'},
    'upgrade.EconomicBlueprints.desc': {'en': 'All buildings cost 15% less', 'ru': 'Все здания дешевле на 15%'},
    'upgrade.ReconData': {'en': 'Recon Data', 'ru': 'Данные разведки'},
    'upgrade.ReconData.desc': {'en': 'Vision range +50%', 'ru': 'Дальность обзора +50%'},
    'upgrade.SteelHelmets': {'en': 'Steel Helmets', 'ru': 'Стальные каски'},
    'upgrade.SteelHelmets.desc': {'en': 'Infantry HP +15%', 'ru': 'Здоровье пехоты +15%'},
    'upgrade.DeepDrilling': {'en': 'Deep Drilling', 'ru': 'Глубокое бурение'},
    'upgrade.DeepDrilling.desc': {'en': 'Workers bring +20% more plasma', 'ru': 'Рабочие приносят на 20% больше плазмы'},
    'upgrade.Mobilization': {'en': 'Mobilization', 'ru': 'Мобилизация'},
    'upgrade.Mobilization.desc': {'en': 'Barracks production +35% faster', 'ru': 'Производство в казармах на 35% быстрее'},
    'upgrade.Tempering': {'en': 'Tempering', 'ru': 'Закалка'},
    'upgrade.Tempering.desc': {'en': 'Buildings auto-repair 1% HP/sec out of combat', 'ru': 'Здания восстанавливают 1% ОЗ/сек вне боя'},
    'upgrade.CamoNets': {'en': 'Camo Nets', 'ru': 'Маскировочные сети'},
    'upgrade.CamoNets.desc': {'en': 'Turrets visible to enemy only at close range', 'ru': 'Турели видны врагу только вблизи'},
    'upgrade.BulkPurchase': {'en': 'Bulk Purchase', 'ru': 'Оптовая закупка'},
    'upgrade.BulkPurchase.desc': {'en': 'Supply from depots +50%', 'ru': 'Снабжение от складов +50%'},
    'upgrade.ReactiveAmmo': {'en': 'Reactive Ammo', 'ru': 'Реактивные боеприпасы'},
    'upgrade.ReactiveAmmo.desc': {'en': 'Vehicle attack range +25%', 'ru': 'Дальность атаки техники +25%'},
    'upgrade.FieldHospital': {'en': 'Field Hospital', 'ru': 'Полевой госпиталь'},
    'upgrade.FieldHospital.desc': {'en': 'Units regen 2% HP/sec after 5s out of combat', 'ru': 'Юниты восстанавливают 2% ОЗ/сек после 5 сек вне боя'},
    'upgrade.TitaniumAlloy': {'en': 'Titanium Alloy', 'ru': 'Титановый сплав'},
    'upgrade.TitaniumAlloy.desc': {'en': 'Heavy vehicles ignore first 10 damage', 'ru': 'Тяжёлая техника игнорирует первые 10 ед. урона'},
    'upgrade.BlackMarket': {'en': 'Black Market', 'ru': 'Чёрный рынок'},
    'upgrade.BlackMarket.desc': {'en': '+15 Titan every 10 seconds', 'ru': '+15 Титана каждые 10 секунд'},
    'upgrade.ExplosiveDeath': {'en': 'Explosive Death', 'ru': 'Взрывная смерть'},
    'upgrade.ExplosiveDeath.desc': {'en': 'Your units explode on death dealing AoE damage', 'ru': 'Ваши юниты взрываются при гибели, нанося урон по площади'},
    'upgrade.OneForAll': {'en': 'One For All', 'ru': 'Один за всех'},
    'upgrade.OneForAll.desc': {'en': '+2% armor per nearby allied unit', 'ru': '+2% брони за каждого союзника рядом'},
    'upgrade.LaserTargeting': {'en': 'Laser Targeting', 'ru': 'Лазерное наведение'},
    'upgrade.LaserTargeting.desc': {'en': '+30% damage vs High Ground units', 'ru': '+30% урона по юнитам на возвышенности'},
    'upgrade.CriticalOverheat': {'en': 'Critical Overheat', 'ru': 'Критический перегрев'},
    'upgrade.CriticalOverheat.desc': {'en': 'Every 4th attack deals 200% damage', 'ru': 'Каждая 4-я атака наносит 200% урона'},
    'upgrade.SpyNetwork': {'en': 'Spy Network', 'ru': 'Шпионская сеть'},
    'upgrade.SpyNetwork.desc': {'en': 'Minimap reveals fully every 2 minutes for 5 sec', 'ru': 'Миникарта раскрывается полностью каждые 2 мин на 5 сек'},
    'upgrade.ScrapCollection': {'en': 'Scrap Collection', 'ru': 'Сбор лома'},
    'upgrade.ScrapCollection.desc': {'en': 'Destroying enemies refunds 25% of their cost', 'ru': 'Уничтожение врагов возвращает 25% их стоимости'},
    'upgrade.NaniteVampirism': {'en': 'Nanite Vampirism', 'ru': 'Нанитный вампиризм'},
    'upgrade.NaniteVampirism.desc': {'en': '25% of damage dealt heals your units', 'ru': '25% нанесённого урона исцеляет ваших юнитов'},
    'upgrade.NuclearProtocol': {'en': 'Nuclear Protocol', 'ru': 'Ядерный протокол'},
    'upgrade.NuclearProtocol.desc': {'en': 'Every 10th siege attack creates mini-nuke', 'ru': 'Каждая 10-я осадная атака создаёт мини-ядерный взрыв'},
    'upgrade.AbsoluteShield': {'en': 'Absolute Shield', 'ru': 'Абсолютный щит'},
    'upgrade.AbsoluteShield.desc': {'en': 'HQ and turrets get 1000 shield (60s recharge)', 'ru': 'Штаб и турели получают 1000 ед. щита (перезарядка 60 сек)'},
    'upgrade.Overclocking': {'en': 'Overclocking', 'ru': 'Разгон'},
    'upgrade.Overclocking.desc': {'en': 'Attack speed +40%, but take +10% damage', 'ru': 'Скорость атаки +40%, но получаемый урон +10%'},
    'upgrade.AirSupremacy': {'en': 'Air Supremacy', 'ru': 'Воздушное превосходство'},
    'upgrade.AirSupremacy.desc': {'en': 'Aircraft 40% cheaper and 30% faster', 'ru': 'Авиация на 40% дешевле и на 30% быстрее'},
    'upgrade.Cloning': {'en': 'Cloning', 'ru': 'Клонирование'},
    'upgrade.Cloning.desc': {'en': '20% chance to produce 2 units for price of 1', 'ru': '20% шанс произвести 2 юнита по цене 1'},
    'upgrade.KamikazeDrones': {'en': 'Kamikaze Drones', 'ru': 'Дроны-камикадзе'},
    'upgrade.KamikazeDrones.desc': {'en': 'Destroyed buildings spawn 3 attack drones', 'ru': 'Уничтоженные здания порождают 3 атакующих дрона'},
    'upgrade.OrbitalStrike': {'en': 'Orbital Strike', 'ru': 'Орбитальный удар'},
    'upgrade.OrbitalStrike.desc': {'en': 'Call a laser strike anywhere every 3 minutes', 'ru': 'Вызвать лазерный удар в любую точку каждые 3 минуты'},
    'upgrade.EnergyDrain': {'en': 'Energy Drain', 'ru': 'Энергетический вампиризм'},
    'upgrade.EnergyDrain.desc': {'en': 'Your attacks drain enemy resources', 'ru': 'Ваши атаки отнимают ресурсы врага'},
    'upgrade.UnlimitedControl': {'en': 'Unlimited Control', 'ru': 'Безграничный контроль'},
    'upgrade.UnlimitedControl.desc': {'en': 'Max supply increased from 200 to 300', 'ru': 'Максимальное снабжение увеличено с 200 до 300'},

    # ============================
    # MISC
    # ============================
    'misc.completed': {
        'en': 'Completed',
        'ru': 'Завершено',
    },
    'misc.building': {
        'en': 'Building...',
        'ru': 'Строительство...',
    },
    'misc.training': {
        'en': 'Training...',
        'ru': 'Обучение...',
    },
    'misc.miss': {
        'en': 'MISS',
        'ru': 'ПРОМАХ',
    },
    'misc.player': {
        'en': 'Player {num}',
        'ru': 'Игрок {num}',
    },
    'menu.version_hint': {
        'en': 'v0.1.0 alpha  |  Press Enter for quick start',
        'ru': 'v0.1.0 альфа  |  Enter — быстрый старт',
    },
}

# Текущий язык
_current_lang = None


def get_lang():
    """Получить текущий язык."""
    global _current_lang
    if _current_lang:
        return _current_lang
    lang = game_settings.get('language')
    if lang in ('en', 'ru'):
        _current_lang = lang
        return lang
    return 'en'  # fallback


def set_lang(lang):
    """Установить текущий язык и сохранить."""
    global _current_lang
    _current_lang = lang
    game_settings.set('language', lang)
    game_settings.save()


def t(key, **kwargs):
    """Получить перевод по ключу. Поддерживает форматирование через kwargs."""
    lang = get_lang()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key  # fallback на сам ключ
    text = entry.get(lang, entry.get('en', key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def t_unit(name):
    """Перевести имя юнита."""
    return t(f'unit.{name}', ) if f'unit.{name}' in TRANSLATIONS else name


def t_building(name):
    """Перевести имя здания."""
    # Убираем пробелы для ключа
    key = f'building.{name.replace(" ", "")}'
    return t(key) if key in TRANSLATIONS else name


def needs_language_selection():
    """Нужно ли показать экран выбора языка (первый запуск)."""
    lang = game_settings.get('language')
    return not lang or lang not in ('en', 'ru')
