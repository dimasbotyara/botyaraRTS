"""
botyaraRTS - core/game.py
Главный класс игры. ПОЛНАЯ ВЕРСИЯ с интегрированным рендерингом.
"""
import pygame
import random
import math
import time
from settings import *
from core.camera import Camera
from core.tilemap import TileMap
from core.minimap import Minimap
from core.fog_of_war import FogOfWar
from core.spatial_hash import SpatialHash
from systems.selection import SelectionSystem
from systems.economy import PlayerState
from systems.upgrades import UpgradeSystem
from systems.commands import CommandSystem
from systems.stances import StanceSystem
from systems.combat import CombatSystem
from ui.hud import HUD
from ui.upgrade_picker import UpgradePicker
from ui.chat import ChatSystem
from ui.ping_system import PingSystem
from ui.widgets import Button, draw_chip_row, draw_spinner, draw_panel
from entities.building import Headquarters, SupplyDepot
from entities.worker import Worker
from rendering.render_manager import RenderManager
from localization import t, t_unit, t_building, needs_language_selection, set_lang
from ui.font_utils import SmartFont
from network.server import GameServer
from network.protocol import PKT_LOBBY_SET


# Состояния игры
STATE_MENU = 'menu'
STATE_CREATE_MATCH = 'create_match'
STATE_LOADING = 'loading'
STATE_PLAYING = 'playing'
STATE_PAUSED = 'paused'
STATE_SETTINGS = 'settings'
STATE_MP_MENU = 'mp_menu'
STATE_LOBBY = 'lobby'
STATE_GAME_OVER = 'game_over'


class GameState:
    """Контейнер всех данных игрового мира."""

    def __init__(self, screen_w, screen_h, seed=None, local_player_id=0,
                 tilemap=None, player_count=2, start_titan=STARTING_TITAN,
                 start_plasma=STARTING_PLASMA, defer_pregen=False,
                 match_settings=None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.local_player_id = local_player_id

        # Настройки матча
        self.match_settings = dict(match_settings) if match_settings else {}

        # Детерминированный RNG симуляции (важно для сетевой игры)
        base_seed = seed if seed is not None else random.randint(0, 999999)
        self.seed = base_seed
        self.rng = random.Random(base_seed ^ 0x5EEDC0DE)

        # Карта
        self.tilemap = tilemap if tilemap is not None else TileMap(seed=seed)

        # Камера
        self.camera = Camera(screen_w, screen_h)
        self.camera.set_map_bounds(
            self.tilemap.width * TILE_SIZE, self.tilemap.height * TILE_SIZE,
            self.tilemap.width, self.tilemap.height
        )

        # Центрируем камеру на спавне игрока
        if self.tilemap.spawn_points:
            sp = self.tilemap.spawn_points[local_player_id % len(self.tilemap.spawn_points)]
            wx, wy = self.tilemap.tile_to_world(sp[0], sp[1])
            self.camera.center_on(wx, wy, instant=True)

        # Пространственный хеш
        self.spatial_hash = SpatialHash(cell_size=128)

        # Туман войны
        self.fog_of_war = FogOfWar(self.tilemap.width, self.tilemap.height)

        # Миникарта
        self.minimap = Minimap(self.tilemap, screen_w, screen_h)

        # Рендер-менеджер
        self.render_manager = RenderManager(self.tilemap)

        # Тяжёлая предгенерация: сразу или отложенно (при инкрементальной загрузке)
        if defer_pregen:
            self._pregen_done = False
        else:
            self.minimap.pregen()
            self.render_manager.terrain.pregen()
            self._pregen_done = True

        # Игроки
        self.players = {}
        for pid in range(max(2, player_count)):
            self.players[pid] = PlayerState(pid, start_titan=start_titan,
                                            start_plasma=start_plasma)

        # Сущности
        self.units = []
        self.buildings = []
        self.dead_entities = []

        # Сетевая сессия (HostSession/RemoteSession) или None в одиночке
        self.net_session = None

        # ИИ-мозги (наполняются при загрузке матча)
        self.ai_brains = {}
        # Запрос ИИ о сдаче (pid) — обрабатывает Game один раз за матч
        self.ai_surrender_request = None

        # Системы
        self.selection = SelectionSystem()
        self.upgrade_system = UpgradeSystem()
        self.command_system = CommandSystem()
        self.combat = CombatSystem()
        self.ping_system = PingSystem()

        # UI
        self.hud = HUD(screen_w, screen_h)
        self.upgrade_picker = UpgradePicker(screen_w, screen_h)
        self.chat = ChatSystem(screen_w, screen_h)

        # Время
        self.game_time = 0
        self.clock = pygame.time.Clock()

        # Пассивный доход таймер
        self.passive_income_timer = 0

        # Spy network
        self.spy_reveal_timer = 0
        self.spy_reveal_active = False
        self.spy_reveal_duration = 0

        # Сетка
        self.show_grid = False

        # Дебаг
        self.debug_mode = False
        self.debug_fog = True

    def finish_pregen(self):
        """Догенерировать отложенную предгенерацию синхронно."""
        if not self._pregen_done:
            self.minimap.pregen()
            self.render_manager.terrain.pregen()
            self._pregen_done = True

    def issue_command(self, cmd):
        """Маршрут игровых команд: локально или через сеть."""
        from network.commands import issue_command
        issue_command(self, cmd)

    def add_entity(self, entity):
        if entity.is_building:
            self.buildings.append(entity)
        elif entity.is_unit:
            self.units.append(entity)
        self.spatial_hash.insert(entity)

    def remove_entity(self, entity):
        self.spatial_hash.remove(entity)
        if entity.is_building and entity in self.buildings:
            self.buildings.remove(entity)
        elif entity.is_unit and entity in self.units:
            self.units.remove(entity)

    def get_all_entities(self):
        return self.units + self.buildings

    def add_projectile(self, x, y, target_x, target_y, color):
        self.combat.add_projectile(x, y, target_x, target_y, color)

    def add_floating_text(self, x, y, text, color):
        self.combat.add_floating_text(x, y, text, color)

    def add_mine(self, x, y, damage, owner_id):
        self.combat.add_mine(x, y, damage, owner_id)

    def add_delayed_effect(self, delay, x, y, radius, damage, damage_type, owner_id):
        self.combat.add_delayed_effect(delay, x, y, radius, damage, damage_type, owner_id)


class Game:
    """Главный класс игры."""

    def __init__(self, screen, screen_w, screen_h):
        self.screen = screen
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.running = True
        self.state = STATE_MENU
        self.game_state = None

        # Экран выбора языка (первый запуск)
        self._show_lang_select = needs_language_selection()
        self.clock = pygame.time.Clock()

        # Шрифты
        self.menu_font_large = SmartFont(52, bold=True)
        self.menu_font_medium = SmartFont(28, bold=True)
        self.menu_font_small = SmartFont(18)
        self.menu_font_title = SmartFont(64, bold=True)

        # Пауза
        self.pause_votes = set()
        self.total_players = 1

        # Настройки
        self.settings_scroll = 0

        # Экран создания матча
        self.cm_cfg = None
        self._cm_chips = {}
        self._cm_spinners = {}
        self._cm_buttons = []

        # Анимация меню
        self.menu_time = 0

        # Сеть
        self.network = None
        self.is_host = False
        self._mp_name = game_settings.get('player_name') or 'Player'
        self._mp_color = game_settings.get('player_color')
        self._mp_input_rects = {}
        self._mp_color_rects = []
        self._mp_focus = None
        self._mp_status = ''
        self._lobby_buttons = {}
        self._lobby_actions = {}
        self.server = None            # GameServer (хост)
        self.net_session = None       # HostSession / RemoteSession
        self._lobby_state = None      # последний снапшот лобби
        self._lobby_status = ''       # текст статуса подключения
        self._mp_join_ip = ''
        self._mp_ready = False
        self._sim_accumulator = 0.0
        self._sim_tick_counter = 0
        self._net_cmd_buckets = {}     # tick -> [(seq, cmd), ...]
        self._net_server_tick = 0
        self._net_last_sync_wall = 0.0
        self._sync_hash_timer = 0.0
        self._last_state_hash = ''
        self._desync_detected = False
        self._net_paused = False
        self._mp_disconnect_msg = None

    def run(self):
        while self.running:
            dt = self.clock.tick(game_settings.get('fps_limit')) / 1000.0
            dt = min(dt, 0.05)

            events = pygame.event.get()

            if self._show_lang_select:
                self.menu_time += dt
                self._update_lang_select(events)
                self._render_lang_select()
                pygame.display.flip()
                continue

            # Сетевые события обрабатываются в любом состоянии
            self._poll_network()

            if self.state == STATE_MENU:
                self.menu_time += dt
                self._update_menu(events)
                self._render_menu()
            elif self.state == STATE_CREATE_MATCH:
                self.menu_time += dt
                self._update_create_match(events)
                self._render_create_match()
            elif self.state == STATE_LOADING:
                self.menu_time += dt
                self._update_loading(events)
                self._advance_loading()
                self._render_loading()
            elif self.state == STATE_PLAYING:
                self._update_game(dt, events)
                self._render_game()
            elif self.state == STATE_PAUSED:
                self._update_pause(events)
                self._render_pause()
            elif self.state == STATE_SETTINGS:
                self._update_settings(events)
                self._render_settings()
            elif self.state == STATE_MP_MENU:
                self.menu_time += dt
                self._update_mp_menu(events)
                self._render_mp_menu()
            elif self.state == STATE_LOBBY:
                self.menu_time += dt
                self._update_lobby(events)
                self._render_lobby()
            elif self.state == STATE_GAME_OVER:
                self._update_game_over(events)
                self._render_game_over()

            pygame.display.flip()

    # ========================================
    # MENU
    # ========================================

    def _update_menu(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_RETURN:
                    self._start_singleplayer()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_menu_click(event.pos)

    def _handle_menu_click(self, pos):
        x, y = pos
        cx = self.screen_w // 2
        btn_w = 320
        btn_h = 55
        start_y = self.screen_h // 2 - 40

        actions = [
            self._open_create_match,
            self._start_lobby,
            self._open_settings,
            self._quit,
        ]

        for i, action in enumerate(actions):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 70, btn_w, btn_h)
            if rect.collidepoint(x, y):
                action()
                break

    def _render_menu(self):
        self.screen.fill(COLOR_BG)

        # Анимированный фон — звёздное поле
        self._render_starfield()

        # Сообщение о разрыве сетевого матча
        if self._mp_disconnect_msg:
            msg = self.menu_font_medium.render(self._mp_disconnect_msg, True,
                                               COLOR_UI_WARNING)
            self.screen.blit(msg, (self.screen_w // 2 - msg.get_width() // 2, 170))
            self._mp_disconnect_msg = None

        # Заголовок с неоновым свечением
        title_text = "botyaraRTS"
        title_surf = self.menu_font_title.render(title_text, True, (0, 200, 255))

        # Свечение заголовка
        glow_intensity = int((math.sin(self.menu_time * 2) + 1) * 20 + 10)
        glow_surf = self.menu_font_title.render(title_text, True,
                                                 (0, 150 + glow_intensity, 255))
        glow_rect = glow_surf.get_rect(center=(self.screen_w // 2, 90))

        # Тень
        shadow = self.menu_font_title.render(title_text, True, (0, 40, 80))
        self.screen.blit(shadow, (glow_rect.x + 3, glow_rect.y + 3))
        self.screen.blit(glow_surf, glow_rect)

        # Подзаголовок
        sub = self.menu_font_small.render(
            t('menu.subtitle'), True, COLOR_UI_TEXT_DIM
        )
        self.screen.blit(sub, (self.screen_w // 2 - sub.get_width() // 2, 140))

        # Линия-разделитель
        line_w = 300
        line_y = 170
        pygame.draw.line(self.screen, (0, 100, 150),
                         (self.screen_w // 2 - line_w // 2, line_y),
                         (self.screen_w // 2 + line_w // 2, line_y), 1)

        # Кнопки
        cx = self.screen_w // 2
        btn_w = 320
        btn_h = 55
        start_y = self.screen_h // 2 - 40
        mouse_pos = pygame.mouse.get_pos()

        labels = [t('menu.singleplayer'), t('menu.multiplayer'), t('menu.settings'), t('menu.quit')]
        btn_colors = [
            (0, 120, 200),
            (0, 100, 160),
            (80, 80, 100),
            (120, 40, 40),
        ]

        for i, (label, btn_color) in enumerate(zip(labels, btn_colors)):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 70, btn_w, btn_h)
            hovered = rect.collidepoint(mouse_pos)

            # Фон кнопки
            bg_color = brighten_color(btn_color, 30) if hovered else btn_color
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=8)

            # Обводка
            border_color = brighten_color(btn_color, 80) if hovered else brighten_color(btn_color, 40)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=8)

            # Свечение при hover
            if hovered:
                glow = pygame.Surface((btn_w + 20, btn_h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*brighten_color(btn_color, 60), 25),
                                 (0, 0, btn_w + 20, btn_h + 20), border_radius=12)
                self.screen.blit(glow, (rect.x - 10, rect.y - 10))

            text = self.menu_font_medium.render(label, True, COLOR_UI_TEXT)
            self.screen.blit(text, (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2
            ))

        # Версия и подсказки
        ver = self.menu_font_small.render(t('menu.version_hint'),
                                          True, COLOR_UI_TEXT_DIM)
        self.screen.blit(ver, (self.screen_w // 2 - ver.get_width() // 2,
                               self.screen_h - 40))

    def _render_starfield(self):
        """Анимированное звёздное поле в фоне меню."""
        random.seed(42)  # Фиксированный сид для стабильных звёзд
        num_stars = 150
        for i in range(num_stars):
            sx = random.randint(0, self.screen_w)
            sy = random.randint(0, self.screen_h)
            layer = random.randint(1, 3)

            # Параллакс
            offset_y = (self.menu_time * layer * 5) % self.screen_h
            star_y = (sy + offset_y) % self.screen_h

            brightness = random.randint(40, 120)
            twinkle = int(math.sin(self.menu_time * random.uniform(1, 4) + i) * 30)
            b = max(20, min(255, brightness + twinkle))

            color = (b, b, int(b * 1.1)) if layer == 1 else \
                    (b, int(b * 0.9), b) if layer == 2 else \
                    (int(b * 0.9), b, int(b * 1.2))

            size = layer
            pygame.draw.circle(self.screen, color, (int(sx), int(star_y)), size)

        random.seed()  # Сбрасываем сид

    # ========================================
    # CREATE MATCH (настройки матча)
    # ========================================

    def _open_create_match(self):
        self.cm_cfg = self._default_match_settings()
        self.state = STATE_CREATE_MATCH

    def _cm_row_y(self, i):
        return 130 + i * 58

    def _update_create_match(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_MENU
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_create_match_click(event.pos)

    def _handle_create_match_click(self, pos):
        cfg = self.cm_cfg

        # Кнопка Back
        back_rect = pygame.Rect(20, 20, 120, 40)
        if back_rect.collidepoint(pos):
            self.state = STATE_MENU
            return

        # Кнопки (Back/Start уже учтены, здесь — виджеты ряда)
        for widget in self._cm_buttons:
            if widget.handle_click(pos):
                return

        # Чипсы
        for key, rects in self._cm_chips.items():
            for idx, rect in enumerate(rects):
                if rect.collidepoint(pos):
                    if key == 'players':
                        cfg['players'] = idx + 2          # 1 человек + N ИИ
                    elif key == 'ai_difficulty':
                        cfg['ai_difficulty'] = AI_DIFFICULTY_IDS[idx]
                    elif key == 'map_size':
                        cfg['map_size'] = ['small', 'medium', 'large'][idx]
                    elif key == 'start_resources':
                        cfg['start_resources'] = ['poor', 'normal', 'rich', 'mad'][idx]
                    elif key == 'resource_density':
                        cfg['resource_density'] = ['sparse', 'normal', 'rich'][idx]
                    elif key == 'seed_random':
                        cfg['seed'] = 0
                    return

        # Спиннеры
        for key, (left, right, _value) in self._cm_spinners.items():
            if left.collidepoint(pos):
                if key == 'ai_strategy':
                    idx = AI_STRATEGY_IDS.index(cfg['ai_strategy'])
                    cfg['ai_strategy'] = AI_STRATEGY_IDS[(idx - 1) % len(AI_STRATEGY_IDS)]
                elif key == 'seed':
                    cfg['seed'] = max(0, int(cfg.get('seed') or 0) - 1)
                return
            if right.collidepoint(pos):
                if key == 'ai_strategy':
                    idx = AI_STRATEGY_IDS.index(cfg['ai_strategy'])
                    cfg['ai_strategy'] = AI_STRATEGY_IDS[(idx + 1) % len(AI_STRATEGY_IDS)]
                elif key == 'seed':
                    cfg['seed'] = int(cfg.get('seed') or 0) + 1
                return

    def _render_create_match(self):
        self.screen.fill(COLOR_BG)
        self._render_starfield()
        cfg = self.cm_cfg
        self._cm_chips = {}
        self._cm_spinners = {}
        self._cm_buttons = []
        mouse_pos = pygame.mouse.get_pos()

        cx = self.screen_w // 2

        # Заголовок
        title = self.menu_font_large.render(t('create.title'), True, (0, 200, 255))
        self.screen.blit(title, (cx - title.get_width() // 2, 22))

        # Кнопка Back
        back_rect = pygame.Rect(20, 20, 120, 40)
        back = Button(back_rect, t('settings.back'), self.menu_font_small,
                      kind='neutral', border_radius=6)
        back.draw(self.screen, mouse_pos)
        self._cm_buttons.append(back)

        label_x = 70
        chips_x = label_x + 250
        row = 0

        def chips(key, labels, current_idx):
            rects, _ = draw_chip_row(self.screen, self.menu_font_small,
                                     chips_x, self._cm_row_y(row) + 4,
                                     labels, current_idx, mouse_pos)
            self._cm_chips[key] = rects

        def spinner(key, label_text):
            l, r, _v = draw_spinner(self.screen, self.menu_font_small,
                                    chips_x, self._cm_row_y(row) + 4,
                                    label_text, width=170)
            self._cm_spinners[key] = (l, r, _v)

        # 1. Противники
        text = self.menu_font_medium.render(t('create.opponents'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        chips('players', ['1', '2', '3'], cfg['players'] - 2)
        row += 1

        # 2. Сложность ИИ
        text = self.menu_font_medium.render(t('create.difficulty'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        chips('ai_difficulty',
              [t('ai.diff.' + d) for d in AI_DIFFICULTY_IDS],
              AI_DIFFICULTY_IDS.index(cfg['ai_difficulty'])
              if cfg['ai_difficulty'] in AI_DIFFICULTY_IDS else 1)
        row += 1

        # 3. Стратегия ИИ (спиннер — вариантов много)
        text = self.menu_font_medium.render(t('create.strategy'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        strat_label = t('ai.strat.' + cfg.get('ai_strategy', 'random'))
        spinner('ai_strategy', strat_label)
        row += 1

        # 4. Размер карты
        text = self.menu_font_medium.render(t('create.map_size'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        chips('map_size',
              [t('mapsize.' + s) for s in ('small', 'medium', 'large')],
              ['small', 'medium', 'large'].index(cfg['map_size']))
        row += 1

        # 5. Стартовые ресурсы
        text = self.menu_font_medium.render(t('create.start_resources'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        chips('start_resources',
              [t('res.' + r) for r in ('poor', 'normal', 'rich', 'mad')],
              ['poor', 'normal', 'rich', 'mad'].index(cfg['start_resources']))
        row += 1

        # 6. Плотность ресурсов
        text = self.menu_font_medium.render(t('create.resource_density'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        chips('resource_density',
              [t('density.' + d) for d in ('sparse', 'normal', 'rich')],
              ['sparse', 'normal', 'rich'].index(cfg['resource_density']))
        row += 1

        # 7. Seed
        text = self.menu_font_medium.render(t('create.seed'), True, COLOR_UI_TEXT)
        self.screen.blit(text, (label_x, self._cm_row_y(row)))
        seed_val = int(cfg.get('seed') or 0)
        spinner('seed', t('create.seed_random') if seed_val == 0 else str(seed_val))
        # Чипс «Случайно» рядом
        rects, _ = draw_chip_row(self.screen, self.menu_font_small,
                                 chips_x + 200, self._cm_row_y(row) + 4,
                                 [t('create.seed_random')], -1, mouse_pos)
        self._cm_chips['seed_random'] = rects
        row += 1

        # Кнопка старт
        btn_w, btn_h = 380, 64
        start_rect = pygame.Rect(cx - btn_w // 2, self.screen_h - 110, btn_w, btn_h)
        start = Button(start_rect, t('create.start'), self.menu_font_medium,
                       kind='accent', border_radius=10,
                       callback=lambda: self._start_singleplayer(self.cm_cfg))
        start.draw(self.screen, mouse_pos)
        self._cm_buttons.append(start)
        if start.rect.collidepoint(mouse_pos):
            glow = pygame.Surface((btn_w + 20, btn_h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow, (0, 150, 255, 30), (0, 0, btn_w + 20, btn_h + 20),
                             border_radius=14)
            self.screen.blit(glow, (start_rect.x - 10, start_rect.y - 10))

        # Подсказка про цвет игрока
        hint = self.menu_font_small.render(
            t('create.opponents') + f": {cfg['players'] - 1} AI", True, COLOR_UI_TEXT_DIM)
        self.screen.blit(hint, (cx - hint.get_width() // 2, self.screen_h - 130 - 26))

    def _show_loading_step(self, progress, status_text):
        """Отрисовка экрана загрузки с прогрессбаром (один кадр, без flip —
        оставлено для совместимости; основной путь — STATE_LOADING)."""
        self.screen.fill((10, 12, 18))
        self._render_starfield()

        cx = self.screen_w // 2
        cy = self.screen_h // 2

        # Заголовок
        title = self.menu_font_large.render(GAME_TITLE, True, COLOR_UI_TEXT)
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))

        # Описание этапа
        status = self.menu_font_medium.render(status_text, True, COLOR_UI_ACCENT)
        self.screen.blit(status, (cx - status.get_width() // 2, cy - 30))

        # Прогрессбар
        bar_w = 480
        bar_h = 24
        bar_x = cx - bar_w // 2
        bar_y = cy + 20

        # Фон полосы
        pygame.draw.rect(self.screen, (20, 25, 35), (bar_x, bar_y, bar_w, bar_h), border_radius=12)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=12)

        # Заполнение
        fill_w = int((bar_w - 6) * max(0.0, min(1.0, progress)))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x + 3, bar_y + 3, fill_w, bar_h - 6)
            pygame.draw.rect(self.screen, COLOR_UI_ACCENT, fill_rect, border_radius=8)

        # Процент
        pct_text = self.menu_font_small.render(f"{int(progress * 100)}%", True, COLOR_UI_TEXT)
        self.screen.blit(pct_text, (cx - pct_text.get_width() // 2, bar_y + bar_h + 8))

    # ========================================
    # ЗАГРУЗКА МАТЧА (инкрементальная)
    # ========================================

    def _default_match_settings(self):
        """Настройки матча по умолчанию (сохранённые или базовые)."""
        cfg = DEFAULT_MATCH_SETTINGS.copy()
        for key in cfg:
            saved = game_settings.get('last_match_' + key)
            if saved is not None:
                cfg[key] = saved
        cfg['players'] = max(2, min(4, int(cfg['players'])))
        return cfg

    def _save_match_settings(self, cfg):
        for key, value in cfg.items():
            game_settings.set('last_match_' + key, value)

    def _start_singleplayer(self, match_settings=None):
        """Запуск одиночной игры: переключаемся в состояние загрузки.

        Тяжёлая работа выполняется по шагам в _match_load_iter(),
        чтобы экран загрузки оставался живым и анимированным.
        """
        cfg = match_settings if match_settings is not None else self._default_match_settings()
        cfg['players'] = max(2, min(4, int(cfg['players'])))
        self._save_match_settings(cfg)
        self._match_cfg = cfg
        self.total_players = 1
        # Сброс состояния сдачи бота на новый матч
        self._surrender_used = False
        self._surrender_pending_pid = None
        self._bot_surrendered = False
        # Сброс локстепа
        self._sim_accumulator = 0.0
        self._sim_tick_counter = 0
        self._net_cmd_buckets = {}
        self._net_paused = False
        self._load_gen = self._match_load_iter(cfg)
        self._load_progress = 0.0
        self._load_label = t('loading.quantum_core')
        self.state = STATE_LOADING

    def _start_lobby(self):
        """Открыть сетевое меню (хост/подключение)."""
        self._open_mp_menu()

    def _start_network_match(self, data):
        """Запуск сетевого матча по данным PKT_GAME_START."""
        if self.net_session is None:
            return
        players = data.get('players', [])
        settings = data.get('settings', {})
        self.net_session.in_game = True

        cfg = {
            'map_size': settings.get('map_size', 'medium'),
            'players': max(2, len(players)),
            'ai_difficulty': settings.get('ai_difficulty', 'standard'),
            'ai_strategy': settings.get('ai_strategy', 'random'),
            'start_resources': settings.get('start_resources', 'normal'),
            'resource_density': settings.get('resource_density', 'normal'),
            'seed': data.get('seed', 1),
            'local_player_id': self.net_session.player_id,
            'ai_slot_ids': [p['id'] for p in players if p.get('is_ai')],
            'mp_names': {p['id']: p.get('name', f"P{p['id']}") for p in players},
            'mp': True,
        }
        self.total_players = max(1, sum(1 for p in players if not p.get('is_ai')))
        self._net_paused = False
        self._desync_detected = False
        self._start_singleplayer(cfg)

    # ========================================
    # СЕТЬ: МЕНЮ И ЛОББИ
    # ========================================

    def _open_mp_menu(self):
        self._mp_focus = None
        self._mp_status = ''
        self.state = STATE_MP_MENU

    def _cleanup_network(self):
        if self.net_session is not None:
            try:
                self.net_session.shutdown()
            except Exception:
                pass
            self.net_session = None
        if self.server is not None:
            try:
                self.server.stop()
            except Exception:
                pass
            self.server = None
        self._lobby_state = None
        self._mp_ready = False
        self._net_paused = False
        self._desync_detected = False

    def _host_game(self):
        """Поднять сервер и открыть лобби хоста."""
        self._cleanup_network()
        game_settings.set('player_name', self._mp_name or 'Host')
        cfg = self._default_match_settings()
        self.server = GameServer(match_settings=cfg)
        try:
            self.server.start()
        except OSError as e:
            self._mp_status = f"Port error: {e}"
            self.server = None
            return
        from network.session import HostSession
        self.net_session = HostSession(self.server)
        self._lobby_status = ''
        self.state = STATE_LOBBY

    def _join_game(self, ip, port):
        """Подключиться к лобби."""
        self._cleanup_network()
        from network.client import GameClient
        from network.session import RemoteSession
        client = GameClient()
        name = (self._mp_name or game_settings.get('player_name') or 'Player')
        color = int(self._mp_color)
        if not client.connect(ip, port, name=name, color_index=color):
            self._mp_status = t('mp.conn_failed')
            return
        self.net_session = RemoteSession(client)
        self._lobby_status = t('mp.connecting')
        self.state = STATE_LOBBY

    def _poll_network(self):
        """Обработка сетевых событий (вызывается каждый кадр)."""
        if self.net_session is None:
            return
        gs = self.game_state

        for kind, data in self.net_session.poll():
            if kind == 'lobby':
                self._lobby_state = data
                self._lobby_status = ''

            elif kind == 'join_ack':
                self._lobby_state = data.get('lobby')
                self._lobby_status = ''

            elif kind == 'join_reject':
                reason = data.get('reason', '')
                self._mp_status = t('mp.reject_full') if 'full' in reason \
                    else t('mp.reject')
                self._cleanup_network()
                self.state = STATE_MP_MENU

            elif kind == 'game_start':
                if data.get('action') == 'unpause':
                    # Все проголосовали за продолжение
                    self._net_paused = False
                    self.pause_votes.clear()
                    if self.state == STATE_PAUSED:
                        self.state = STATE_PLAYING
                elif data.get('action') == 'begin':
                    # Все загрузились — синхронный старт матча
                    self._net_paused = False
                    self.match_start_countdown = 1.2
                    self._sim_accumulator = 0.0
                    self._net_server_tick = 0
                    self._net_last_sync_wall = time.monotonic()
                elif self.state in (STATE_LOBBY, STATE_LOADING, STATE_PLAYING,
                                    STATE_PAUSED):
                    self._start_network_match(data)

            elif kind == 'tick':
                tick = int(data.get('tick', 0))
                if tick > self._net_server_tick:
                    self._net_server_tick = tick
                self._net_last_sync_wall = time.monotonic()

            elif kind == 'cmd':
                if gs is not None:
                    tick = int(data.get('tick', self._sim_tick_counter + 1))
                    self._net_cmd_buckets.setdefault(tick, []).append(
                        (data.get('seq', 0), data))

            elif kind == 'sync':
                their = data.get('hash')
                if their and self._last_state_hash and \
                        their != self._last_state_hash:
                    self._desync_detected = True

            elif kind == 'pause':
                # Кто-то приостановил матч
                pid = data.get('player_id')
                if self.state == STATE_PLAYING:
                    self.state = STATE_PAUSED
                self._net_paused = True
                self.pause_votes.clear()
                name = gs.players[pid].name if gs and gs.players.get(pid) \
                    else f"Player {pid}"
                if gs:
                    gs.chat.add_message({'text': t('mp.paused_by'),
                                         'sender': name, 'mode': 'all'})

            elif kind == 'unpause':
                votes = data.get('votes', 0)
                needed = data.get('needed', 1)
                self.pause_votes = set(range(votes))

            elif kind in ('disconnect', 'connection_lost'):
                name = data.get('name', '') if kind == 'disconnect' else ''
                self._mp_disconnect_msg = (t('mp.peer_left').format(name=name)
                                           if name else t('mp.conn_lost'))
                self._cleanup_network()
                if self.state in (STATE_PLAYING, STATE_PAUSED, STATE_LOADING):
                    self.state = STATE_MENU

    # ========================================
    # СЕТЬ: ЭКРАНЫ
    # ========================================

    def _update_mp_menu(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_MENU
                elif self._mp_focus is not None:
                    if event.key == pygame.K_BACKSPACE:
                        if self._mp_focus == 'name':
                            self._mp_name = self._mp_name[:-1]
                        else:
                            self._mp_join_ip = self._mp_join_ip[:-1]
                    elif event.key == pygame.K_RETURN:
                        self._mp_focus = None
                    elif event.unicode and event.unicode.isprintable():
                        if self._mp_focus == 'name':
                            self._mp_name = (self._mp_name + event.unicode)[:20]
                        else:
                            self._mp_join_ip = (self._mp_join_ip + event.unicode)[:39]
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mp_menu_click(event.pos)

    def _handle_mp_menu_click(self, pos):
        x, y = pos
        cx = self.screen_w // 2

        back_rect = pygame.Rect(20, 20, 120, 40)
        if back_rect.collidepoint(pos):
            self.state = STATE_MENU
            return

        for key, rect in self._mp_input_rects.items():
            if rect.collidepoint(pos):
                self._mp_focus = key
                return
        self._mp_focus = None

        # Цвета
        for idx, rect in enumerate(self._mp_color_rects):
            if rect.collidepoint(pos):
                self._mp_color = idx
                return

        # Host / Join
        host_rect = pygame.Rect(cx - 260, self.screen_h - 170, 240, 52)
        join_rect = pygame.Rect(cx + 20, self.screen_h - 170, 240, 52)
        if host_rect.collidepoint(pos):
            game_settings.set('player_name', self._mp_name)
            game_settings.set('player_color', int(self._mp_color))
            self._host_game()
            return
        if join_rect.collidepoint(pos):
            game_settings.set('player_name', self._mp_name)
            game_settings.set('player_color', int(self._mp_color))
            port = game_settings.get('server_port')
            ip = self._mp_join_ip.strip() or '127.0.0.1'
            if ':' in ip:
                ip, _, port_s = ip.partition(':')
                try:
                    port = int(port_s)
                except ValueError:
                    pass
            self._join_game(ip, port)
            return

    def _render_mp_menu(self):
        self.screen.fill(COLOR_BG)
        self._render_starfield()

        cx = self.screen_w // 2
        mouse_pos = pygame.mouse.get_pos()
        self._mp_input_rects = {}
        self._mp_color_rects = []

        title = self.menu_font_large.render(t('mp.title'), True, (0, 200, 255))
        self.screen.blit(title, (cx - title.get_width() // 2, 40))

        back_rect = pygame.Rect(20, 20, 120, 40)
        back = Button(back_rect, t('settings.back'), self.menu_font_small,
                      kind='neutral', border_radius=6)
        back.draw(self.screen, mouse_pos)

        col_w = 460
        # --- Левая колонка: имя + цвет ---
        name_label = self.menu_font_small.render(t('mp.name'), True, COLOR_UI_TEXT)
        self.screen.blit(name_label, (cx - col_w - 40, 150))
        name_rect = pygame.Rect(cx - col_w - 40, 175, col_w, 40)
        self._draw_input_box(name_rect, self._mp_name,
                             self._mp_focus == 'name')

        color_label = self.menu_font_small.render(t('mp.color'), True, COLOR_UI_TEXT)
        self.screen.blit(color_label, (cx - col_w - 40, 235))
        crect = pygame.Rect(cx - col_w - 40, 260, 36, 36)
        for idx in range(8):
            r = crect.copy()
            r.x = cx - col_w - 40 + idx * 44
            self._mp_color_rects.append(r)
            selected = (idx == int(self._mp_color))
            pygame.draw.rect(self.screen, PLAYER_COLORS[idx], r,
                             border_radius=6)
            pygame.draw.rect(self.screen,
                             (255, 255, 255) if selected else (60, 80, 100),
                             r, 3 if selected else 1, border_radius=6)

        # --- Правая колонка: IP ---
        ip_label = self.menu_font_small.render(t('mp.address'), True, COLOR_UI_TEXT)
        self.screen.blit(ip_label, (cx + 40, 150))
        ip_rect = pygame.Rect(cx + 40, 175, col_w, 40)
        self._draw_input_box(ip_rect, self._mp_join_ip or '127.0.0.1',
                             self._mp_focus == 'ip')
        self._mp_input_rects['ip'] = ip_rect

        hint = self.menu_font_small.render(t('mp.hint'), True, COLOR_UI_TEXT_DIM)
        self.screen.blit(hint, (cx + 40, 222))

        # Кнопки
        host_rect = pygame.Rect(cx - 260, self.screen_h - 170, 240, 52)
        join_rect = pygame.Rect(cx + 20, self.screen_h - 170, 240, 52)
        host = Button(host_rect, t('mp.host'), self.menu_font_medium,
                      kind='accent', callback=self._host_game)
        join = Button(join_rect, t('mp.join'), self.menu_font_medium,
                      kind='success', callback=lambda: self._handle_mp_menu_click(join_rect.center))
        host.draw(self.screen, mouse_pos)
        join.draw(self.screen, mouse_pos)

        if self._mp_status:
            err = self.menu_font_small.render(self._mp_status, True,
                                              COLOR_UI_DANGER)
            self.screen.blit(err, (cx - err.get_width() // 2,
                                   self.screen_h - 100))

        # Имя — рисуем после кнопок, чтобы сфокусированный бокс был сверху
        self._mp_input_rects['name'] = name_rect

    def _draw_input_box(self, rect, text, focused):
        pygame.draw.rect(self.screen, (18, 22, 30), rect, border_radius=6)
        pygame.draw.rect(self.screen,
                         (0, 180, 255) if focused else (60, 80, 100),
                         rect, 2, border_radius=6)
        shown = text + ('│' if focused and int(self.menu_time * 2) % 2 == 0 else '')
        surf = self.menu_font_small.render(shown or ' ', True, COLOR_UI_TEXT)
        self.screen.blit(surf, (rect.x + 10, rect.centery - surf.get_height() // 2))

    def _update_lobby(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._leave_lobby()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_lobby_click(event.pos)

    def _leave_lobby(self):
        self._cleanup_network()
        self.state = STATE_MENU

    def _handle_lobby_click(self, pos):
        if self._lobby_state is None:
            self._leave_lobby()
            return
        my_id = self.net_session.player_id
        is_host = my_id == self._lobby_state.get('host_id', 0)
        settings = self._lobby_state.get('settings', {})

        for key, fn in self._lobby_buttons.items():
            if key.startswith('chip:'):
                _, chip_key, idx = key.split(':')
                if not is_host:
                    continue
                idx = int(idx)
                value = {'map_size': ['small', 'medium', 'large'],
                         'start_resources': ['poor', 'normal', 'rich', 'mad'],
                         'resource_density': ['sparse', 'normal', 'rich'],
                         'ai_difficulty': AI_DIFFICULTY_IDS}[chip_key][idx]
                self.server.set_settings({chip_key: value})
                return
            if key.startswith('kick:'):
                pid = int(key.split(':')[1])
                if is_host and pid != my_id:
                    self.server.remove_player(pid)
                return

        for rect, fn in self._lobby_actions.items():
            if rect.collidepoint(pos):
                fn()
                return

    def _render_lobby(self):
        self.screen.fill(COLOR_BG)
        self._render_starfield()
        mouse_pos = pygame.mouse.get_pos()
        cx = self.screen_w // 2
        self._lobby_buttons = {}
        self._lobby_actions = {}

        title = self.menu_font_large.render(t('lobby.title'), True, (0, 200, 255))
        self.screen.blit(title, (cx - title.get_width() // 2, 28))

        back_rect = pygame.Rect(20, 20, 120, 40)
        back = Button(back_rect, t('lobby.leave'), self.menu_font_small,
                      kind='danger', border_radius=6,
                      callback=self._leave_lobby)
        back.draw(self.screen, mouse_pos)
        self._lobby_actions[back_rect] = self._leave_lobby

        if self._lobby_status:
            st = self.menu_font_medium.render(self._lobby_status, True,
                                              COLOR_UI_ACCENT)
            self.screen.blit(st, (cx - st.get_width() // 2, self.screen_h // 2))
            return

        if self._lobby_state is None:
            return

        my_id = self.net_session.player_id if self.net_session else 0
        host_id = self._lobby_state.get('host_id', 0)
        is_host = my_id == host_id
        settings = self._lobby_state.get('settings', {})
        players = self._lobby_state.get('players', [])

        # === Игроки ===
        panel_rect = pygame.Rect(cx - 330, 90, 660, 60 + len(players) * 46 + 16)
        draw_panel(self.screen, panel_rect)
        hdr = self.menu_font_small.render(t('lobby.players'), True, COLOR_UI_TEXT_DIM)
        self.screen.blit(hdr, (panel_rect.x + 16, panel_rect.y + 10))

        y = panel_rect.y + 44
        for p in players:
            pid = p['id']
            color_rect = pygame.Rect(panel_rect.x + 16, y + 6, 28, 28)
            pygame.draw.rect(self.screen, PLAYER_COLORS[p['color'] % 8],
                             color_rect, border_radius=6)
            name = p['name']
            if pid == host_id:
                name = '♛ ' + name
            if p['is_ai']:
                name = '🤖 ' + name
            if pid == my_id:
                name += '  ←'
            ntext = self.menu_font_medium.render(name, True, COLOR_UI_TEXT)
            self.screen.blit(ntext, (panel_rect.x + 58, y + 6))

            if p['is_ai']:
                rtxt = self.menu_font_small.render('CPU', True, COLOR_UI_TEXT_DIM)
                self.screen.blit(rtxt, (panel_rect.right - 110, y + 12))
            else:
                ready = p['ready'] or pid == host_id
                rtxt = self.menu_font_small.render(
                    '✔ ' + t('lobby.ready') if ready else t('lobby.not_ready'),
                    True, (60, 255, 120) if ready else COLOR_UI_TEXT_DIM)
                self.screen.blit(rtxt, (panel_rect.right - 150, y + 12))

            if is_host and pid != my_id:
                kick_rect = pygame.Rect(panel_rect.right - 52, y + 8, 26, 24)
                pygame.draw.rect(self.screen, (90, 40, 40), kick_rect,
                                 border_radius=4)
                xt = self.menu_font_small.render('✕', True, COLOR_UI_TEXT)
                self.screen.blit(xt, (kick_rect.centerx - xt.get_width() // 2,
                                      kick_rect.centery - xt.get_height() // 2))
                self._lobby_buttons[f'kick:{pid}'] = True

            y += 46

        # === Настройки (хост) ===
        y += 18
        settings_rect = pygame.Rect(cx - 330, y, 660, 190)
        draw_panel(self.screen, settings_rect)
        sy = settings_rect.y + 12

        def chips(label, chip_key, options, labels, current):
            nonlocal sy
            ltext = self.menu_font_small.render(t(label), True, COLOR_UI_TEXT)
            self.screen.blit(ltext, (settings_rect.x + 16, sy + 4))
            rects, _ = draw_chip_row(self.screen, self.menu_font_small,
                                     settings_rect.x + 240, sy,
                                     labels, current, mouse_pos)
            for i, r in enumerate(rects):
                self._lobby_buttons[f'chip:{chip_key}:{i}'] = True
            sy += 36

        chips('create.map_size', 'map_size', 3,
              [t('mapsize.' + s) for s in ('small', 'medium', 'large')],
              ['small', 'medium', 'large'].index(settings.get('map_size', 'medium')))
        chips('create.start_resources', 'start_resources', 4,
              [t('res.' + r) for r in ('poor', 'normal', 'rich', 'mad')],
              ['poor', 'normal', 'rich', 'mad'].index(settings.get('start_resources', 'normal')))
        chips('create.resource_density', 'resource_density', 3,
              [t('density.' + d) for d in ('sparse', 'normal', 'rich')],
              ['sparse', 'normal', 'rich'].index(settings.get('resource_density', 'normal')))
        chips('create.difficulty', 'ai_difficulty', 4,
              [t('ai.diff.' + d) for d in AI_DIFFICULTY_IDS],
              AI_DIFFICULTY_IDS.index(settings.get('ai_difficulty', 'standard'))
              if settings.get('ai_difficulty') in AI_DIFFICULTY_IDS else 1)

        if not is_host:
            note = self.menu_font_small.render(t('lobby.host_sets'), True,
                                               COLOR_UI_TEXT_DIM)
            self.screen.blit(note, (settings_rect.x + 16, sy + 2))

        # === Кнопки ===
        btn_y = self.screen_h - 120
        humans = [p for p in players if not p['is_ai']]
        all_ready = all(p['ready'] for p in humans if p['id'] != host_id)

        if is_host:
            add_rect = pygame.Rect(cx - 500, btn_y, 200, 48)
            can_add = len(players) < 4
            add = Button(add_rect, t('lobby.add_ai'), self.menu_font_small,
                         kind='neutral' if can_add else 'neutral')
            add.draw(self.screen, mouse_pos, enabled=can_add)
            if can_add:
                self._lobby_actions[add_rect] = lambda: self.server.add_ai_slot()

            start_rect = pygame.Rect(cx - 120, btn_y, 240, 48)
            can_start = all_ready and len(players) >= 2
            start = Button(start_rect, t('lobby.start'), self.menu_font_medium,
                           kind='accent')
            start.draw(self.screen, mouse_pos, enabled=can_start)
            if can_start:
                self._lobby_actions[start_rect] = lambda: self.server.try_start_game(host_id)
        else:
            ready_rect = pygame.Rect(cx - 120, btn_y, 240, 48)
            ready = Button(ready_rect,
                           t('lobby.iam_ready') if self._mp_ready
                           else t('lobby.iam_not_ready'),
                           self.menu_font_medium, kind='success')
            ready.draw(self.screen, mouse_pos, selected=self._mp_ready)
            self._lobby_actions[ready_rect] = self._toggle_ready

        # Порт хоста — подсказка
        if is_host and self.server:
            ptext = self.menu_font_small.render(
                t('lobby.port_hint').format(port=self.server.port),
                True, COLOR_UI_TEXT_DIM)
            self.screen.blit(ptext, (cx - ptext.get_width() // 2, btn_y + 60))

    def _toggle_ready(self):
        self._mp_ready = not self._mp_ready
        # Отправляем готовность серверу (только удалённые клиенты)
        if self.net_session is not None and hasattr(self.net_session, 'client'):
            self.net_session.client.send(PKT_LOBBY_SET, {'ready': self._mp_ready})

    def _match_load_iter(self, cfg):
        """Генератор загрузки матча: yield (progress, localization_key)."""
        yield 0.02, 'loading.quantum_core'

        seed = cfg.get('seed') or random.randint(0, 999999)
        self._match_seed = seed
        size = MATCH_SIZES.get(cfg.get('map_size', 'medium'), 256)
        local_id = int(cfg.get('local_player_id', 0))

        # 1) Генерация ландшафта (чанками)
        tm = TileMap(size, size, seed=seed, spawn_count=cfg['players'],
                     resource_density=MATCH_DENSITY.get(cfg.get('resource_density', 'normal'), 1.0))
        for p, label in tm.generate_iter():
            yield 0.05 + p * 0.40, label

        # 2) Скелет игрового мира (без тяжёлой предгенерации)
        start_titan, start_plasma = MATCH_START_RESOURCES.get(
            cfg.get('start_resources', 'normal'), (STARTING_TITAN, STARTING_PLASMA))
        gs = GameState(self.screen_w, self.screen_h, seed=seed, local_player_id=local_id,
                       tilemap=tm, player_count=cfg['players'],
                       start_titan=start_titan, start_plasma=start_plasma,
                       defer_pregen=True, match_settings=cfg)
        self.game_state = gs
        gs.clock = self.clock
        # Сетевая сессия и имена игроков
        if cfg.get('mp'):
            gs.net_session = self.net_session
            for pid, name in (cfg.get('mp_names') or {}).items():
                if pid in gs.players:
                    gs.players[pid].name = str(name)[:20]
        yield 0.46, 'loading.quantum_core'

        # 3) Предгенерация миникарты (чанками)
        for p, _ in gs.minimap.pregen_iter():
            yield 0.46 + p * 0.22, 'loading.minimap'

        # 4) Предгенерация деталей тайлов (чанками)
        for p, _ in gs.render_manager.terrain.pregen_iter():
            yield 0.68 + p * 0.17, 'loading.tile_details'

        # 5) Юниты игроков
        for pid in range(cfg['players']):
            self._spawn_starting_units(pid)
        yield 0.88, 'loading.deploy_units'

        # 6) ИИ-противники
        self._setup_ai_brains(cfg)
        yield 0.97, 'loading.ready'

    def _setup_ai_brains(self, cfg):
        """Создать ИИ-мозги для слотов, помеченных как ИИ.

        В одиночной игре человек — player 0, остальные — ИИ;
        в сетевой игре список ИИ-слотов приходит из лобби.
        """
        from ai.brain import AIBrain

        difficulty = cfg.get('ai_difficulty', 'standard')
        strategy = cfg.get('ai_strategy', 'random')

        slot_ids = cfg.get('ai_slot_ids')
        if slot_ids is None:
            slot_ids = list(range(1, len(self.game_state.players)))

        for pid in slot_ids:
            if pid in self.game_state.players:
                brain = AIBrain(pid, difficulty=difficulty, strategy=strategy)
                self.game_state.ai_brains[pid] = brain

    def _update_loading(self, events):
        """Обработка событий на экране загрузки."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

    def _advance_loading(self, time_budget=0.024):
        """Продвинуть загрузку на ограниченный бюджет времени."""
        if self._load_gen is None:
            return
        deadline = time.perf_counter() + time_budget
        try:
            while time.perf_counter() < deadline:
                progress, label = next(self._load_gen)
                self._load_progress = progress
                if label:
                    self._load_label = t(label)
        except StopIteration:
            self._load_gen = None
            self._finish_loading()

    def _finish_loading(self):
        self.match_start_countdown = 3.5  # 3... 2... 1... BATTLE START!
        # В сетевой игре ждём всех: докладываем о готовности и держим симуляцию
        if self.game_state is not None and self.game_state.net_session is not None:
            self.match_start_countdown = 0
            self._net_paused = True
            self._sim_tick_counter = 0
            self._net_cmd_buckets.clear()
            self._send_loaded()
        self.state = STATE_PLAYING

    def _send_loaded(self):
        if self.net_session is None:
            return
        if hasattr(self.net_session, 'client'):
            self.net_session.client.send(PKT_LOBBY_SET, {'loaded': True})
        else:
            # Хост: напрямую на сервер
            self.server._handle_packet(self.server.players[self.net_session.player_id],
                                       PKT_LOBBY_SET, {'loaded': True})

    def _render_loading(self):
        """Анимированный экран загрузки."""
        self.screen.fill((10, 12, 18))
        self._render_starfield()

        cx = self.screen_w // 2
        cy = self.screen_h // 2
        progress = max(0.0, min(1.0, self._load_progress))

        # Заголовок
        title = self.menu_font_large.render(GAME_TITLE, True, COLOR_UI_TEXT)
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 110))

        # Анимированное описание этапа
        dots = '.' * (1 + int(self.menu_time * 2) % 3)
        status = self.menu_font_medium.render(self._load_label + dots, True, COLOR_UI_ACCENT)
        self.screen.blit(status, (cx - status.get_width() // 2, cy - 34))

        # Прогрессбар
        bar_w = 480
        bar_h = 24
        bar_x = cx - bar_w // 2
        bar_y = cy + 20

        pygame.draw.rect(self.screen, (20, 25, 35), (bar_x, bar_y, bar_w, bar_h), border_radius=12)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=12)

        fill_w = int((bar_w - 6) * progress)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x + 3, bar_y + 3, fill_w, bar_h - 6)
            pygame.draw.rect(self.screen, COLOR_UI_ACCENT, fill_rect, border_radius=8)

            # Бегущий блик по заполненной части
            shine_x = bar_x + 3 + int((fill_w + bar_w) * ((self.menu_time * 0.4) % 1.0)) - bar_w
            shine_rect = pygame.Rect(shine_x, bar_y + 3, 26, bar_h - 6)
            if shine_rect.right > bar_x + 3 and shine_rect.left < bar_x + 3 + fill_w:
                shine = pygame.Surface((26, bar_h - 6), pygame.SRCALPHA)
                shine.fill((255, 255, 255, 40))
                self.screen.blit(shine, (max(shine_rect.x, bar_x + 3), shine_rect.y))

        # Процент
        pct_text = self.menu_font_small.render(f"{int(progress * 100)}%", True, COLOR_UI_TEXT)
        self.screen.blit(pct_text, (cx - pct_text.get_width() // 2, bar_y + bar_h + 8))

    def _open_settings(self):
        self._previous_state = STATE_MENU
        self.state = STATE_SETTINGS

    def _quit(self):
        self.running = False

    def _spawn_starting_units(self, player_id):
        gs = self.game_state
        spawn_idx = player_id % len(gs.tilemap.spawn_points)
        sx, sy = gs.tilemap.spawn_points[spawn_idx]
        wx, wy = gs.tilemap.tile_to_world(sx, sy)

        hq = Headquarters(wx, wy, player_id)
        hq.is_completed = True
        hq.construction_progress = hq.build_time
        gs.add_entity(hq)

        depot = SupplyDepot(wx + TILE_SIZE * 4, wy + TILE_SIZE * 2, player_id)
        depot.is_completed = True
        depot.construction_progress = depot.build_time
        gs.add_entity(depot)

        # Поиск ближайших ресурсов для авто-добычи
        from core.tilemap import TILE_TITAN_ORE, TILE_PLASMA_GEYSER
        titan_tiles = []
        plasma_tiles = []

        for ty in range(max(0, sy - 25), min(gs.tilemap.height, sy + 25)):
            for tx in range(max(0, sx - 25), min(gs.tilemap.width, sx + 25)):
                t = gs.tilemap.get_tile(tx, ty)
                if t == TILE_TITAN_ORE:
                    dist = (tx - sx) ** 2 + (ty - sy) ** 2
                    titan_tiles.append((dist, tx, ty))
                elif t == TILE_PLASMA_GEYSER:
                    dist = (tx - sx) ** 2 + (ty - sy) ** 2
                    plasma_tiles.append((dist, tx, ty))

        titan_tiles.sort()
        plasma_tiles.sort()

        # Авто-установка Rally Point HQ на ближайший титан
        if titan_tiles:
            hq.set_rally_point(titan_tiles[0][1] * TILE_SIZE + 16, titan_tiles[0][2] * TILE_SIZE + 16)

        # Спавним 6 рабочих
        workers = []
        for i in range(6):
            angle = (i / 6) * math.pi * 2
            ux = wx + math.cos(angle) * TILE_SIZE * 3
            uy = wy + math.sin(angle) * TILE_SIZE * 3
            worker = Worker(ux, uy, player_id)
            gs.add_entity(worker)
            workers.append(worker)

        # Авто-назначение на добычу: 1 рабочий на плазму, остальные 5 на титан
        if plasma_tiles and len(workers) > 0:
            workers[0].command_harvest(plasma_tiles[0][1], plasma_tiles[0][2])

        if titan_tiles:
            for idx, w in enumerate(workers[1:]):
                tile_info = titan_tiles[idx % len(titan_tiles)]
                w.command_harvest(tile_info[1], tile_info[2])

        gs.players[player_id].recalculate_supply(gs.buildings)
        gs.players[player_id].recalculate_current_supply(gs.units)

    # ========================================
    # GAMEPLAY UPDATE
    # ========================================

    def _update_game(self, dt, events):
        gs = self.game_state

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                self._handle_game_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_game_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_game_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_game_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                gs.camera.handle_zoom(event.y, pygame.mouse.get_pos())
            elif event.type == pygame.VIDEORESIZE:
                self.screen_w = event.w
                self.screen_h = event.h
                gs.camera.resize(event.w, event.h)
                gs.minimap.resize(event.w, event.h)
                gs.hud.resize(event.w, event.h)
                gs.upgrade_picker.resize(event.w, event.h)

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        gs.camera.update(dt, keys, mouse_pos)

        # === Авто-повтор ПКМ (как в Dota 2) ===
        if game_settings.get('rmb_auto_repeat') and pygame.mouse.get_pressed()[2]:
            if not hasattr(self, '_rmb_repeat_timer'):
                self._rmb_repeat_timer = 0
            self._rmb_repeat_timer += dt
            if self._rmb_repeat_timer >= 0.1:  # каждые 100мс
                self._rmb_repeat_timer = 0
                if not gs.command_system.build_mode and \
                   not gs.upgrade_system.is_choosing and \
                   not gs.minimap.is_point_on_minimap(*mouse_pos) and \
                   not gs.hud.is_point_on_panel(*mouse_pos):
                    gs.selection._handle_right_click(
                        mouse_pos, gs.camera, gs, keys
                    )
        else:
            self._rmb_repeat_timer = 0

        if hasattr(self, 'match_start_countdown') and self.match_start_countdown > 0:
            self.match_start_countdown -= dt
            if self.match_start_countdown < 0:
                self.match_start_countdown = 0

        # Обновляем рендер-менеджер (анимации воды и т.д.)
        gs.render_manager.update(dt)

        # === Фиксированный тик симуляции (детерминированный локстеп) ===
        if not hasattr(self, 'match_start_countdown') or self.match_start_countdown <= 0:
            if not self._net_paused:
                # В сетевой игре не убегаем вперёд от тика сервера
                if gs.net_session is not None:
                    now = time.monotonic()
                    extrapolated = self._net_server_tick + \
                        max(0.0, now - self._net_last_sync_wall) * SIM_RATE
                    if self._sim_tick_counter >= extrapolated - 2:
                        self._sim_accumulator = min(self._sim_accumulator, SIM_DT)
                self._sim_accumulator += dt
                ticks = 0
                while self._sim_accumulator >= SIM_DT and ticks < 6:
                    self._sim_accumulator -= SIM_DT
                    self._sim_tick()
                    ticks += 1
                if ticks >= 6:
                    # Не догоняем бесконечно после лагов
                    self._sim_accumulator = 0.0
        else:
            # Даже во время паузы нужно обновлять spatial_hash для выделения юнитов рамкой
            gs.spatial_hash.clear()
            for entity in gs.get_all_entities():
                if entity.alive:
                    gs.spatial_hash.insert(entity)

        # === Визуальные обновления (клиентская часть) ===

        # Туман войны
        self._update_fog_of_war(dt)

        # Миникарта
        gs.minimap.update(dt)

        # Пинги
        gs.ping_system.update(dt)

        # Выделение
        gs.selection.update()

        # Строительство
        if gs.command_system.build_mode:
            gs.command_system.update_build_preview(mouse_pos, gs.camera, gs.tilemap)

    def _sim_tick(self):
        """Один детерминированный тик симуляции (SIM_DT).

        Выполняется одинаково на всех клиентах: сетевые команды
        применяются на границе тика в порядке seq сервера.
        """
        gs = self.game_state
        dt = SIM_DT
        gs.game_time += dt

        # 1. Сетевые команды этого тика (в порядке seq сервера)
        current = self._sim_tick_counter
        due = self._net_cmd_buckets.pop(current, [])
        # Опоздавшие команды (тик уже прошёл) — применяем сейчас
        for tick in [t for t in self._net_cmd_buckets if t < current]:
            due.extend(self._net_cmd_buckets.pop(tick))
        if due:
            from network.commands import apply_command
            gs._dbg_tick = current
            for _seq, cmd in sorted(due, key=lambda item: item[0]):
                apply_command(gs, cmd)

        self._sim_tick_counter += 1

        # 2. Пространственный хеш
        gs.spatial_hash.clear()
        for entity in gs.get_all_entities():
            if entity.alive:
                gs.spatial_hash.insert(entity)

        # 3. Юниты
        for unit in gs.units[:]:
            if unit.alive:
                unit.update(dt, gs)
            else:
                unit.death_timer += dt
                if unit.death_timer > unit.death_duration:
                    gs.units.remove(unit)

        # 4. Здания
        for building in gs.buildings[:]:
            if building.alive:
                building.update(dt, gs)
            else:
                building.death_timer += dt
                if building.death_timer > building.death_duration:
                    gs.buildings.remove(building)

        # 5. Supply
        for pid, player in gs.players.items():
            player.recalculate_supply(gs.buildings)
            player.recalculate_current_supply(gs.units)

        # 6. Боевая система
        gs.combat.update(dt, gs)

        # 7. Улучшения
        gs.upgrade_system.update(dt, gs.game_time, gs)

        # 8. Пассивные эффекты
        self._update_upgrade_effects(dt)

        # 9. ИИ (мозги на каждого бота)
        for brain in gs.ai_brains.values():
            brain.update(dt, gs)

        # 10. Предложение бота о сдаче (одно за матч)
        self._poll_surrender_request()

        # 11. Хэш состояния (детект рассинхрона)
        self._sync_hash_tick()

        # 12. Победа
        self._check_victory()

    def _sync_hash_tick(self):
        """Раз в SYNC_HASH_INTERVAL секунд — обмен хэшами состояния."""
        gs = self.game_state
        self._sync_hash_timer += SIM_DT
        if self._sync_hash_timer < SYNC_HASH_INTERVAL:
            return
        self._sync_hash_timer = 0.0

        from network.commands import compute_state_hash
        self._last_state_hash = compute_state_hash(gs)
        if gs.net_session is not None and gs.net_session.connected:
            gs.net_session.send_sync_hash(int(gs.game_time * 30),
                                          self._last_state_hash)

    def _update_fog_of_war(self, dt):
        gs = self.game_state
        if not gs.debug_fog:
            gs.fog_of_war.reveal_all()
            return

        vision_sources = []
        local_id = gs.local_player_id
        for entity in gs.get_all_entities():
            if entity.alive and entity.player_id == local_id:
                tx, ty = entity.get_tile_pos()
                vision_r = entity.vision_range
                player = gs.players.get(local_id)
                if player:
                    mult = player.get_upgrade_bonus('vision_range', 1.0)
                    vision_r = int(vision_r * mult)
                vision_sources.append((tx, ty, vision_r))

        gs.fog_of_war.update(dt, vision_sources)

        for entity in gs.get_all_entities():
            if entity.player_id != local_id:
                entity.visible = gs.fog_of_war.is_visible_world(entity.x, entity.y)
            else:
                entity.visible = True

    def _update_upgrade_effects(self, dt):
        gs = self.game_state
        for pid, player in gs.players.items():
            income = player.get_upgrade_bonus('passive_income', 0)
            if income > 0:
                gs.passive_income_timer += dt
                if gs.passive_income_timer >= 10.0:
                    gs.passive_income_timer = 0
                    player.titan += income

            if player.upgrade_bonuses.get('building_regen', False):
                for b in gs.buildings:
                    if b.player_id == pid and b.alive and b.is_completed:
                        if b.hp < b.max_hp:
                            b.heal(b.max_hp * 0.01 * dt)

            if player.upgrade_bonuses.get('spy_reveal', False) and pid == gs.local_player_id:
                gs.spy_reveal_timer += dt
                if gs.spy_reveal_timer >= 120:
                    gs.spy_reveal_timer = 0
                    gs.spy_reveal_active = True
                    gs.spy_reveal_duration = 5.0

        if gs.spy_reveal_active:
            gs.spy_reveal_duration -= dt
            gs.fog_of_war.reveal_all()
            if gs.spy_reveal_duration <= 0:
                gs.spy_reveal_active = False

    # ========================================
    # СДАЧА БОТА
    # ========================================

    def _poll_surrender_request(self):
        """Одно предложение сдачи за матч: бот просит пощады — решает игрок."""
        gs = self.game_state
        pid = gs.ai_surrender_request
        if pid is None or getattr(self, '_surrender_used', False):
            return
        if pid not in gs.ai_brains:
            gs.ai_surrender_request = None
            return
        self._surrender_used = True
        self._surrender_pending_pid = pid

    def _handle_surrender_click(self, pos):
        """Клик по панели сдачи. True — клик поглощён."""
        gs = self.game_state
        pid = self._surrender_pending_pid
        rects = getattr(self, '_surrender_rects', None)
        if not rects:
            return False

        if rects['accept'].collidepoint(pos):
            player = gs.players.get(pid)
            if player:
                player.is_defeated = True
            self._bot_surrendered = True
            self._surrender_pending_pid = None
            gs.ai_surrender_request = None
            # Игрок принял капитуляцию — немедленная победа
            self.state = STATE_GAME_OVER
            self._game_over_result = 'victory'
            return True

        if rects['decline'].collidepoint(pos):
            brain = gs.ai_brains.get(pid)
            if brain:
                brain.desperate = True  # бот дерётся до конца (all-in)
            self._surrender_pending_pid = None
            gs.ai_surrender_request = None
            return True

        return False

    def _render_surrender_panel(self):
        """Панель «принять победу / заставить драться» сверху по центру."""
        pid = getattr(self, '_surrender_pending_pid', None)
        if pid is None or self.game_state is None:
            return

        panel_w, panel_h = 560, 148
        panel_x = (self.screen_w - panel_w) // 2
        panel_y = 18
        panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        # Фон
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        bg.fill((24, 14, 10, 235))
        self.screen.blit(bg, panel.topleft)
        pygame.draw.rect(self.screen, (255, 170, 40), panel, 2, border_radius=10)

        cx = panel.centerx
        title = self.menu_font_medium.render(t('surrender.title'), True, (255, 200, 60))
        self.screen.blit(title, (cx - title.get_width() // 2, panel_y + 12))

        hint = self.menu_font_small.render(t('surrender.hint'), True, COLOR_UI_TEXT_DIM)
        self.screen.blit(hint, (cx - hint.get_width() // 2, panel_y + 42))

        mouse_pos = pygame.mouse.get_pos()
        btn_w, btn_h = 250, 44
        btn_y = panel_y + 78
        acc_rect = pygame.Rect(panel_x + 26, btn_y, btn_w, btn_h)
        dec_rect = pygame.Rect(panel_x + panel_w - btn_w - 26, btn_y, btn_w, btn_h)
        self._surrender_rects = {'accept': acc_rect, 'decline': dec_rect}

        for rect, label, base_color in (
                (acc_rect, t('surrender.accept'), (30, 110, 60)),
                (dec_rect, t('surrender.decline'), (140, 45, 40))):
            color = brighten_color(base_color, 30) if rect.collidepoint(mouse_pos) else base_color
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, brighten_color(base_color, 60), rect, 2, border_radius=8)
            text = self.menu_font_small.render(label, True, COLOR_UI_TEXT)
            self.screen.blit(text, (rect.centerx - text.get_width() // 2,
                                    rect.centery - text.get_height() // 2))

    def _check_victory(self):
        gs = self.game_state
        for pid, player in gs.players.items():
            if player.is_defeated:
                continue
            has_anything = any(b for b in gs.buildings if b.player_id == pid and b.alive) or \
                           any(u for u in gs.units if u.player_id == pid and u.alive)
            if not has_anything:
                player.is_defeated = True
                if pid == gs.local_player_id:
                    self.state = STATE_GAME_OVER
                    self._game_over_result = 'defeat'
                elif all(p.is_defeated for p_id, p in gs.players.items()
                         if p_id != gs.local_player_id):
                    self.state = STATE_GAME_OVER
                    self._game_over_result = 'victory'

    # ========================================
    # INPUT
    # ========================================

    def _handle_game_keydown(self, event):
        gs = self.game_state

        if gs.chat.is_open:
            if event.key == pygame.K_RETURN:
                msg = gs.chat.send(gs.players[gs.local_player_id].name)
                # В сетевой игре отправляем сообщение остальным
                if msg and gs.net_session is not None:
                    gs.net_session.send_chat(msg['text'], msg['mode'])
            elif event.key == pygame.K_ESCAPE:
                gs.chat.is_open = False
            elif event.key == pygame.K_TAB:
                gs.chat.toggle_mode()
            elif event.key == pygame.K_BACKSPACE:
                gs.chat.backspace()
            elif event.unicode and event.unicode.isprintable():
                gs.chat.add_char(event.unicode)
            return

        if event.key == pygame.K_ESCAPE:
            if gs.command_system.build_mode:
                gs.command_system.cancel_build_mode()
            elif gs.upgrade_system.is_choosing:
                pass
            else:
                self.state = STATE_PAUSED
                self.pause_votes.clear()
                # В сетевой игре пауза требует согласия остальных
                if gs.net_session is not None:
                    gs.net_session.send_pause()
                    self._net_paused = True
        elif event.key == pygame.K_RETURN:
            gs.chat.toggle()
        elif event.key == pygame.K_g:
            gs.show_grid = not gs.show_grid
        elif event.key == pygame.K_F1:
            gs.debug_mode = not gs.debug_mode
        elif event.key == pygame.K_F2:
            gs.debug_fog = not gs.debug_fog
        elif pygame.K_1 <= event.key <= pygame.K_9:
            number = event.key - pygame.K_0
            keys = pygame.key.get_pressed()
            center = gs.selection.handle_group_key(number, keys)
            if center:
                gs.camera.center_on(center[0], center[1])
        elif event.key == pygame.K_a:
            gs.selection.attack_move_mode = not gs.selection.attack_move_mode
        elif event.key == pygame.K_h:
            unit_ids = [e.id for e in gs.selection.selected_entities
                        if e.is_unit and e.player_id == gs.local_player_id]
            if unit_ids:
                gs.issue_command({'cmd': 'stance', 'unit_ids': unit_ids,
                                  'stance': 'HOLD_POSITION'})
        elif event.key == pygame.K_t:
            units = [e for e in gs.selection.selected_entities
                     if e.is_unit and e.player_id == gs.local_player_id]
            if units:
                from systems.stances import StanceSystem
                StanceSystem.cycle_stance(units)
                new_stance = units[0].stance
                gs.issue_command({'cmd': 'stance',
                                  'unit_ids': [u.id for u in units],
                                  'stance': new_stance})
        elif event.key == pygame.K_s and not pygame.key.get_pressed()[pygame.K_LCTRL]:
            unit_ids = [e.id for e in gs.selection.selected_entities
                        if e.is_unit and e.player_id == gs.local_player_id]
            if unit_ids:
                gs.issue_command({'cmd': 'stop', 'unit_ids': unit_ids})
        elif event.key == pygame.K_e:
            unit_ids = [e.id for e in gs.selection.selected_entities
                        if e.is_unit and e.player_id == gs.local_player_id]
            if unit_ids:
                gs.issue_command({'cmd': 'siege', 'unit_ids': unit_ids})

    def _handle_game_mouse_down(self, event):
        gs = self.game_state
        keys = pygame.key.get_pressed()

        # Панель сдачи бота — модальный приоритет
        if getattr(self, '_surrender_pending_pid', None) is not None:
            if self._handle_surrender_click(event.pos):
                return

        if gs.upgrade_system.is_choosing:
            if event.button == 1:
                gs.upgrade_picker.handle_click(event.pos, gs.upgrade_system, gs)
            return

        # Зажатие колесика мыши (MMB Drag)
        if gs.camera.handle_mouse_down(event.pos, event.button):
            return

        if event.button == 1 and keys[pygame.K_LALT]:
            world_x, world_y = gs.camera.screen_to_world(*event.pos)
            ping_type = 'retreat' if keys[pygame.K_LCTRL] else 'attention'
            gs.ping_system.add_ping(world_x, world_y, ping_type)
            if gs.net_session is not None:
                gs.net_session.send_ping(world_x, world_y, ping_type)
            return

        if event.button == 1 and gs.minimap.is_point_on_minimap(*event.pos):
            gs.minimap.handle_click(*event.pos, gs.camera, button='left')
            return

        if event.button == 3 and gs.minimap.is_point_on_minimap(*event.pos):
            world_x, world_y = gs.minimap.minimap_to_world(*event.pos)
            world_x = max(0, min(world_x, gs.tilemap.width * TILE_SIZE))
            world_y = max(0, min(world_y, gs.tilemap.height * TILE_SIZE))
            unit_ids = [u.id for u in gs.selection.selected_entities
                        if u.is_unit and u.player_id == gs.local_player_id]
            if unit_ids:
                gs.issue_command({'cmd': 'move', 'unit_ids': unit_ids,
                                  'x': world_x, 'y': world_y})
            return

        if event.button == 1 and gs.hud.is_point_on_panel(*event.pos):
            gs.hud.handle_click(event.pos, gs, gs.command_system)
            return

        if event.button == 1 and gs.command_system.build_mode:
            gs.command_system.try_place_building(gs, gs.local_player_id)
            return

        if event.button == 3 and gs.command_system.build_mode:
            gs.command_system.cancel_build_mode()
            return

        gs.selection.handle_mouse_down(event.pos, event.button, gs.camera, gs)

    def _handle_game_mouse_up(self, event):
        gs = self.game_state
        keys = pygame.key.get_pressed()
        gs.camera.handle_mouse_up(event.button)
        if event.button == 1:
            gs.minimap.handle_release()
        gs.selection.handle_mouse_up(event.pos, event.button, gs.camera, gs, keys)

    def _handle_game_mouse_motion(self, event):
        gs = self.game_state
        if gs.camera.handle_mouse_motion(event.pos):
            return
        if gs.minimap.dragging:
            gs.minimap.handle_drag(*event.pos, gs.camera)
            return
        gs.selection.handle_mouse_move(event.pos)

    # ========================================
    # RENDER — ОСНОВНОЙ МЕТОД С RENDER MANAGER
    # ========================================

    def _render_game(self):
        gs = self.game_state
        camera = gs.camera
        rm = gs.render_manager

        self.screen.fill(COLOR_BG)

        # Тряска камеры
        shake_x, shake_y = camera.get_shake_offset(
            1.0 / max(1, self.clock.get_fps())
        )

        # ===== ЛАНДШАФТ =====
        rm.render_terrain(self.screen, camera)

        # Сетка
        grid_mode = game_settings.get('show_grid')
        if gs.show_grid or grid_mode == 'always' or \
           (grid_mode == 'building' and gs.command_system.build_mode):
            rm.render_grid(self.screen, camera)

        # ===== СУЩНОСТИ (сортировка по Y для правильного перекрытия) =====
        all_entities = gs.get_all_entities()

        # Разделяем на наземных и воздушных
        ground_entities = []
        air_entities = []
        dead_entities = []

        for entity in all_entities:
            if not entity.alive:
                dead_entities.append(entity)
                continue
            if not entity.visible and entity.player_id != gs.local_player_id:
                continue
            if entity.is_flying if hasattr(entity, 'is_flying') else False:
                air_entities.append(entity)
            else:
                ground_entities.append(entity)

        # Сортируем по Y
        ground_entities.sort(key=lambda e: e.y)
        air_entities.sort(key=lambda e: e.y)

        # Culling rect
        cull_rect = camera.get_culling_rect()

        # Рисуем трупы (под всеми)
        for entity in dead_entities:
            if cull_rect.collidepoint(entity.x, entity.y):
                rm.render_death(self.screen, camera, entity)

        # Наземные сущности
        for entity in ground_entities:
            if not cull_rect.collidepoint(entity.x, entity.y):
                continue
            rm.render_entity(self.screen, camera, entity)

        # Воздушные сущности (поверх наземных)
        for entity in air_entities:
            if not cull_rect.collidepoint(entity.x, entity.y):
                continue
            rm.render_entity(self.screen, camera, entity)

        # ===== ТУМАН ВОЙНЫ =====
        if gs.debug_fog:
            gs.fog_of_war.render(self.screen, camera)

        # ===== БОЕВЫЕ ЭФФЕКТЫ =====
        rm.render_combat_effects(self.screen, camera, gs.combat, gs.local_player_id)

        # ===== ПИНГИ В МИРЕ =====
        gs.ping_system.render(self.screen, camera)

        # ===== ПРЕВЬЮ СТРОИТЕЛЬСТВА =====
        gs.command_system.render_build_preview(self.screen, camera, gs.tilemap)

        # ===== ВЕЙПОИНТЫ И ОЧЕРЕДЬ ПРИКАЗОВ =====
        self._render_waypoints(camera)

        # ===== РАМКА ВЫДЕЛЕНИЯ =====
        gs.selection.render_selection_box(self.screen)

        # ===== UI =====
        gs.hud.render(self.screen, gs, gs.selection.selected_entities)

        # ===== МИНИКАРТА =====
        gs.minimap.render(self.screen, camera,
                          entities=gs.get_all_entities(),
                          fog_of_war=gs.fog_of_war if gs.debug_fog else None)

        # ===== ЧАТ =====
        gs.chat.render(self.screen)

        # ===== КУРСОР АТАКИ (A-клик) =====
        if gs.selection.attack_move_mode:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(self.screen, (255, 50, 50), (mx, my), 10, 2)
            pygame.draw.line(self.screen, (255, 50, 50), (mx - 15, my), (mx + 15, my), 2)
            pygame.draw.line(self.screen, (255, 50, 50), (mx, my - 15), (mx, my + 15), 2)

        # ===== ОБРАТНЫЙ ОТСЧЕТ (3, 2, 1, BATTLE START!) =====
        self._render_match_countdown()

        # ===== ОВЕРЛЕЙ УЛУЧШЕНИЙ =====
        if gs.upgrade_system.is_choosing and (not hasattr(self, 'match_start_countdown') or self.match_start_countdown <= 0):
            gs.upgrade_picker.render(self.screen, gs.upgrade_system, gs)

        # ===== ПАНЕЛЬ СДАЧИ БОТА =====
        self._render_surrender_panel()

        # ===== ПРЕДУПРЕЖДЕНИЕ О РАССИНХРОНЕ =====
        if self._desync_detected:
            warn = self.menu_font_medium.render(t('mp.desync'), True,
                                                COLOR_UI_DANGER)
            bw = warn.get_width() + 30
            bx = (self.screen_w - bw) // 2
            bar = pygame.Surface((bw, 34), pygame.SRCALPHA)
            bar.fill((60, 10, 10, 200))
            self.screen.blit(bar, (bx, 66))
            self.screen.blit(warn, (bx + 15, 70))

        # ===== ДЕБАГ =====
        if gs.debug_mode:
            self._render_debug()

    def _render_match_countdown(self):
        """Отрисовка обратного отсчета 3... 2... 1... BATTLE START!"""
        if not hasattr(self, 'match_start_countdown') or self.match_start_countdown <= 0:
            return

        cx = self.screen_w // 2
        cy = self.screen_h // 2 - 40
        ct = self.match_start_countdown

        if ct > 0.6:
            num = int(ct)
            num_str = str(num)
            scale_pulse = 1.0 + (ct - math.floor(ct)) * 0.25
            font_size = int(110 * scale_pulse)
            font = SmartFont(font_size, bold=True)

            shadow = font.render(num_str, True, (0, 0, 0))
            self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 4, cy - shadow.get_height() // 2 + 4))

            txt_color = (0, 220, 255) if num == 3 else ((255, 200, 0) if num == 2 else (255, 60, 60))
            txt = font.render(num_str, True, txt_color)
            self.screen.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

            r = int(70 * scale_pulse)
            pygame.draw.circle(self.screen, txt_color, (cx, cy), r, 3)

        else:
            scale_pulse = 1.0 + (0.6 - ct) * 0.4
            font_size = int(72 * scale_pulse)
            font = SmartFont(font_size, bold=True)

            text_str = t('countdown.battle_start')
            shadow = font.render(text_str, True, (0, 0, 0))
            self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 3, cy - shadow.get_height() // 2 + 3))

            txt = font.render(text_str, True, (50, 255, 100))
            self.screen.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

    def _render_waypoints(self, camera):
        gs = self.game_state
        for entity in gs.selection.selected_entities:
            if entity.player_id != gs.local_player_id:
                continue

            # Рисуем rally point для зданий
            if entity.is_building and hasattr(entity, 'rally_point') and entity.rally_point:
                rx, ry = entity.rally_point
                sx1, sy1 = camera.world_to_screen(entity.x, entity.y)
                sx2, sy2 = camera.world_to_screen(rx, ry)
                pygame.draw.line(self.screen, (200, 200, 200), (sx1, sy1), (sx2, sy2), 1)
                pygame.draw.circle(self.screen, (200, 200, 200), (sx2, sy2), 3)

            # Рисуем путь для юнитов
            if entity.is_unit:
                points = []
                points.append((entity.x, entity.y))
                
                # Добавляем текущую конечную точку пути
                if getattr(entity, 'path', None):
                    last_tx, last_ty = entity.path[-1]
                    px = last_tx * 32 + 16 # TILE_SIZE = 32
                    py = last_ty * 32 + 16
                    points.append((px, py))
                elif getattr(entity, 'target_x', None) is not None:
                    points.append((entity.target_x, entity.target_y))
                
                # Добавляем точки из очереди команд
                if hasattr(entity, 'command_queue'):
                    for cmd_type, args in entity.command_queue:
                        if cmd_type == 'move':
                            points.append((args[0], args[1]))
                        elif cmd_type in ('harvest', 'build'):
                            if cmd_type == 'harvest':
                                tx, ty = args[0], args[1]
                            else: # build
                                _, tx, ty = args[0], args[1], args[2]
                            px = tx * 32 + 16
                            py = ty * 32 + 16
                            points.append((px, py))
                        elif cmd_type == 'resume_build' or cmd_type == 'attack':
                            target = args[0]
                            if hasattr(target, 'x'):
                                points.append((target.x, target.y))

                if len(points) > 1:
                    screen_points = [camera.world_to_screen(px, py) for px, py in points]
                    pygame.draw.lines(self.screen, (50, 255, 50), False, screen_points, 1)
                    for sp in screen_points[1:]:
                        pygame.draw.circle(self.screen, (50, 255, 50), sp, 3)

    def _render_debug(self):
        gs = self.game_state
        font = SmartFont(18)
        y = 45
        lines = [
            f"Game Time: {gs.game_time:.1f}s",
            f"Units: {len(gs.units)} | Buildings: {len(gs.buildings)}",
            f"Camera: ({gs.camera.x:.0f}, {gs.camera.y:.0f}) zoom={gs.camera.zoom:.2f}",
            f"Selected: {len(gs.selection.selected_entities)}",
            f"Projectiles: {len(gs.combat.projectiles)} | Mines: {len(gs.combat.mines)}",
            f"Build Mode: {gs.command_system.build_mode}",
            f"Fog: {'ON' if gs.debug_fog else 'OFF'}",
            f"FPS: {int(self.clock.get_fps())}",
        ]

        bg = pygame.Surface((250, len(lines) * 16 + 10), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (5, y - 5))

        for line in lines:
            text = font.render(line, True, (255, 255, 0))
            self.screen.blit(text, (10, y))
            y += 16

    # ========================================
    # PAUSE
    # ========================================

    def _update_pause(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_PLAYING
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_pause_click(event.pos)

    def _handle_pause_click(self, pos):
        cx = self.screen_w // 2
        btn_w = 280
        btn_h = 50
        start_y = self.screen_h // 2 - 80

        actions = [
            self._try_continue,
            lambda: (setattr(self, '_previous_state', STATE_PAUSED),
                     setattr(self, 'state', STATE_SETTINGS)),
            lambda: setattr(self, 'state', STATE_MENU),
            self._quit,
        ]

        for i, action in enumerate(actions):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 65, btn_w, btn_h)
            if rect.collidepoint(pos):
                action()
                break

    def _try_continue(self):
        gs = self.game_state
        if gs is not None and gs.net_session is not None:
            # Решение за всеми: сервер рассылает голоса и снимает паузу
            gs.net_session.send_unpause_vote()
            return
        self.pause_votes.add(gs.local_player_id if gs else 0)
        if len(self.pause_votes) >= self.total_players:
            self.state = STATE_PLAYING
            self.pause_votes.clear()

    def _render_pause(self):
        self._render_game()

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        title = self.menu_font_large.render(t('pause.title'), True, COLOR_UI_TEXT)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 80))

        cx = self.screen_w // 2
        btn_w = 280
        btn_h = 50
        start_y = self.screen_h // 2 - 80
        mouse_pos = pygame.mouse.get_pos()

        votes = len(self.pause_votes)
        needed = self.total_players

        labels = [
            f"{t('pause.continue')} ({votes}/{needed})",
            t('pause.settings'),
            t('pause.main_menu'),
            t('pause.quit')
        ]

        for i, label in enumerate(labels):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 65, btn_w, btn_h)
            hovered = rect.collidepoint(mouse_pos)
            color = (0, 100, 180) if hovered else (30, 40, 55)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, (60, 80, 100), rect, 2, border_radius=8)

            text = self.menu_font_medium.render(label, True, COLOR_UI_TEXT)
            self.screen.blit(text, (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2
            ))

    # ========================================
    # SETTINGS
    # ========================================

    def _update_settings(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_settings.save()
                    self.state = getattr(self, '_previous_state', STATE_MENU)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_settings_click(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                self.settings_scroll -= event.y * 30
                self.settings_scroll = max(0, self.settings_scroll)

    def _handle_settings_click(self, pos):
        x, y = pos

        back_rect = pygame.Rect(20, 20, 120, 40)
        if back_rect.collidepoint(x, y):
            game_settings.save()
            self.state = getattr(self, '_previous_state', STATE_MENU)
            return

        settings_y = 110 - self.settings_scroll
        item_height = 45
        items = self._get_settings_items()

        for i, item in enumerate(items):
            iy = settings_y + i * item_height
            if item['type'] == 'toggle':
                toggle_rect = pygame.Rect(450, iy + 5, 60, 28)
                if toggle_rect.collidepoint(x, y):
                    current = game_settings.get(item['key'])
                    game_settings.set(item['key'], not current)
            elif item['type'] == 'choice':
                for j, option in enumerate(item['options']):
                    opt_rect = pygame.Rect(450 + j * 85, iy + 5, 75, 28)
                    if opt_rect.collidepoint(x, y):
                        game_settings.set(item['key'], option)
                        if item['key'] == 'language' and option in ('en', 'ru'):
                            set_lang(option)

    def _get_settings_items(self):
        return [
            {'label': t('settings.header_display'), 'type': 'header'},
            {'label': t('settings.fullscreen'), 'key': 'fullscreen', 'type': 'toggle'},
            {'label': t('settings.vsync'), 'key': 'vsync', 'type': 'toggle'},
            {'label': t('settings.fps_limit'), 'key': 'fps_limit', 'type': 'choice',
             'options': [30, 60, 120, 0]},
            {'label': t('settings.header_camera'), 'type': 'header'},
            {'label': t('settings.edge_scrolling'), 'key': 'edge_scrolling', 'type': 'toggle'},
            {'label': t('settings.invert_zoom'), 'key': 'invert_zoom', 'type': 'toggle'},
            {'label': t('settings.lock_mouse'), 'key': 'lock_mouse', 'type': 'toggle'},
            {'label': t('settings.header_interface'), 'type': 'header'},
            {'label': t('settings.hp_bars'), 'key': 'hp_bar_mode', 'type': 'choice',
             'options': ['always', 'damaged', 'selected', 'alt']},
            {'label': t('settings.grid_overlay'), 'key': 'show_grid', 'type': 'choice',
             'options': ['never', 'building', 'always']},
            {'label': t('settings.header_gameplay'), 'type': 'header'},
            {'label': t('settings.rmb_auto_repeat'), 'key': 'rmb_auto_repeat', 'type': 'toggle'},
            {'label': t('settings.header_audio'), 'type': 'header'},
            {'label': t('settings.minimize_sound'), 'key': 'minimize_sound', 'type': 'toggle'},
            {'label': t('settings.header_network'), 'type': 'header'},
            {'label': t('settings.net_stats'), 'key': 'show_net_graph', 'type': 'toggle'},
            {'label': t('settings.auto_pause_desync'), 'key': 'auto_pause_desync', 'type': 'toggle'},
            {'label': t('settings.header_language'), 'type': 'header'},
            {'label': t('settings.language'), 'key': 'language', 'type': 'choice',
             'options': ['en', 'ru']},
        ]

    def _render_settings(self):
        self.screen.fill(COLOR_BG)

        title = self.menu_font_large.render(t('settings.title'), True, (0, 180, 255))
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 25))

        # Кнопка Back
        back_rect = pygame.Rect(20, 20, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        back_hover = back_rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, (0, 100, 160) if back_hover else (30, 40, 55),
                         back_rect, border_radius=6)
        pygame.draw.rect(self.screen, (60, 80, 100), back_rect, 1, border_radius=6)
        back_text = self.menu_font_small.render(t('settings.back'), True, COLOR_UI_TEXT)
        self.screen.blit(back_text, (back_rect.x + 15, back_rect.y + 10))

        # Настройки
        settings_y = 110 - self.settings_scroll
        item_height = 45
        items = self._get_settings_items()
        font = self.menu_font_small

        for i, item in enumerate(items):
            iy = settings_y + i * item_height
            if iy < 70 or iy > self.screen_h - 30:
                continue

            if item['type'] == 'header':
                text = self.menu_font_medium.render(item['label'], True, (0, 150, 220))
                self.screen.blit(text, (30, iy + 5))

            elif item['type'] == 'toggle':
                text = font.render(item['label'], True, COLOR_UI_TEXT)
                self.screen.blit(text, (60, iy + 10))

                value = game_settings.get(item['key'])
                toggle_rect = pygame.Rect(450, iy + 5, 60, 28)
                bg_color = (0, 160, 80) if value else (60, 60, 70)
                pygame.draw.rect(self.screen, bg_color, toggle_rect, border_radius=14)
                knob_x = toggle_rect.x + 38 if value else toggle_rect.x + 22
                pygame.draw.circle(self.screen, (255, 255, 255), (knob_x, iy + 19), 9)

            elif item['type'] == 'choice':
                text = font.render(item['label'], True, COLOR_UI_TEXT)
                self.screen.blit(text, (60, iy + 10))

                current = game_settings.get(item['key'])
                for j, option in enumerate(item['options']):
                    opt_rect = pygame.Rect(450 + j * 85, iy + 5, 75, 28)
                    is_selected = (str(current) == str(option))
                    color = (0, 120, 200) if is_selected else (40, 45, 55)
                    pygame.draw.rect(self.screen, color, opt_rect, border_radius=4)
                    pygame.draw.rect(self.screen, (60, 80, 100), opt_rect, 1, border_radius=4)

                    label = str(option) if option != 0 else "∞"
                    opt_text = font.render(label, True, COLOR_UI_TEXT)
                    self.screen.blit(opt_text, (
                        opt_rect.centerx - opt_text.get_width() // 2,
                        opt_rect.centery - opt_text.get_height() // 2
                    ))

    # ========================================
    # GAME OVER
    # ========================================

    def _update_game_over(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                self.state = STATE_MENU

    def _render_game_over(self):
        self.screen.fill(COLOR_BG)
        self._render_starfield()

        result = getattr(self, '_game_over_result', 'defeat')

        if result == 'victory':
            color = (0, 255, 120)
            text = t('gameover.victory')
        else:
            color = (255, 60, 60)
            text = t('gameover.defeat')

        title = self.menu_font_large.render(text, True, color)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2,
                                 self.screen_h // 2 - 80))

        if self.game_state:
            gs = self.game_state
            player = gs.players.get(gs.local_player_id)
            if player:
                mins = int(gs.game_time // 60)
                secs = int(gs.game_time % 60)
                stats = [
                    t('gameover.time', mins=mins, secs=secs),
                    t('gameover.titan_plasma', titan=player.total_titan_mined, plasma=player.total_plasma_mined),
                    t('gameover.units_stats', produced=player.units_produced, lost=player.units_lost),
                    t('gameover.buildings_stats', built=player.buildings_built, lost=player.buildings_lost),
                ]
                if getattr(self, '_bot_surrendered', False) and result == 'victory':
                    stats.insert(1, t('gameover.surrender'))
                for i, stat in enumerate(stats):
                    text = self.menu_font_small.render(stat, True, COLOR_UI_TEXT_DIM)
                    self.screen.blit(text, (self.screen_w // 2 - text.get_width() // 2,
                                           self.screen_h // 2 + i * 28))

        hint = self.menu_font_small.render(
            t('gameover.click_hint'), True, COLOR_UI_TEXT_DIM
        )
        self.screen.blit(hint, (self.screen_w // 2 - hint.get_width() // 2,
                                self.screen_h - 60))

    # ========================================
    # LANGUAGE SELECTION
    # ========================================

    def _update_lang_select(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cx = self.screen_w // 2
                btn_w = 300
                btn_h = 70
                start_y = self.screen_h // 2 - 30
                # English
                rect_en = pygame.Rect(cx - btn_w // 2, start_y, btn_w, btn_h)
                if rect_en.collidepoint(event.pos):
                    set_lang('en')
                    self._show_lang_select = False
                # Russian
                rect_ru = pygame.Rect(cx - btn_w // 2, start_y + 90, btn_w, btn_h)
                if rect_ru.collidepoint(event.pos):
                    set_lang('ru')
                    self._show_lang_select = False

    def _render_lang_select(self):
        self.screen.fill(COLOR_BG)
        self._render_starfield()

        cx = self.screen_w // 2

        # Title
        title = self.menu_font_large.render(
            "Select Language / Выберите язык", True, (0, 200, 255)
        )
        self.screen.blit(title, (cx - title.get_width() // 2, self.screen_h // 2 - 140))

        btn_w = 300
        btn_h = 70
        start_y = self.screen_h // 2 - 30
        mouse_pos = pygame.mouse.get_pos()

        langs = [
            ('[EN]  English', 'en'),
            ('[RU]  Русский', 'ru'),
        ]
        for i, (label, _) in enumerate(langs):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 90, btn_w, btn_h)
            hovered = rect.collidepoint(mouse_pos)
            color = (0, 120, 200) if hovered else (30, 45, 60)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, (0, 150, 220), rect, 2, border_radius=12)

            text = self.menu_font_medium.render(label, True, COLOR_UI_TEXT)
            self.screen.blit(text, (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2
            ))

# ========================================
# Утилита для цветов (используется в меню)
# ========================================
def brighten_color(color, amount=30):
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )
