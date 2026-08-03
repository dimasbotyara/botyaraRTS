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
from entities.building import Headquarters, SupplyDepot
from entities.worker import Worker
from rendering.render_manager import RenderManager
from localization import t, t_unit, t_building, needs_language_selection, set_lang
from ui.font_utils import SmartFont


# Состояния игры
STATE_MENU = 'menu'
STATE_PLAYING = 'playing'
STATE_PAUSED = 'paused'
STATE_SETTINGS = 'settings'
STATE_LOBBY = 'lobby'
STATE_GAME_OVER = 'game_over'


class GameState:
    """Контейнер всех данных игрового мира."""

    def __init__(self, screen_w, screen_h, seed=None, local_player_id=0):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.local_player_id = local_player_id

        # Карта
        self.tilemap = TileMap(seed=seed)

        # Камера
        self.camera = Camera(screen_w, screen_h)

        # Центрируем камеру на спавне игрока
        if self.tilemap.spawn_points:
            sp = self.tilemap.spawn_points[local_player_id % len(self.tilemap.spawn_points)]
            wx, wy = self.tilemap.tile_to_world(sp[0], sp[1])
            self.camera.center_on(wx, wy, instant=True)

        # Пространственный хеш
        self.spatial_hash = SpatialHash(cell_size=128)

        # Туман войны
        self.fog_of_war = FogOfWar(MAP_WIDTH_TILES, MAP_HEIGHT_TILES)

        # Миникарта
        self.minimap = Minimap(self.tilemap, screen_w, screen_h)

        # Рендер-менеджер
        self.render_manager = RenderManager(self.tilemap)

        # Игроки
        self.players = {}
        self.players[0] = PlayerState(0)
        self.players[1] = PlayerState(1)

        # Сущности
        self.units = []
        self.buildings = []
        self.dead_entities = []

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

        # Анимация меню
        self.menu_time = 0

        # Сеть
        self.network = None
        self.is_host = False

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

            if self.state == STATE_MENU:
                self.menu_time += dt
                self._update_menu(events)
                self._render_menu()
            elif self.state == STATE_PLAYING:
                self._update_game(dt, events)
                self._render_game()
            elif self.state == STATE_PAUSED:
                self._update_pause(events)
                self._render_pause()
            elif self.state == STATE_SETTINGS:
                self._update_settings(events)
                self._render_settings()
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
            self._start_singleplayer,
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

    def _show_loading_step(self, progress, status_text):
        """Отрисовка экрана загрузки с прогрессбаром."""
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

        pygame.display.flip()
        pygame.event.pump()

    def _start_singleplayer(self):
        self._show_loading_step(0.05, t('loading.quantum_core'))
        seed = random.randint(0, 999999)

        self._show_loading_step(0.20, t('loading.terrain'))
        self.game_state = GameState(self.screen_w, self.screen_h, seed=seed, local_player_id=0)
        self.game_state.clock = self.clock

        self._show_loading_step(0.65, t('loading.deploy_units'))
        self._spawn_starting_units(0)

        self._show_loading_step(0.85, t('loading.enemy_outpost'))
        self._spawn_ai_units(1)
        self.total_players = 1

        self._show_loading_step(1.00, t('loading.ready'))
        time.sleep(0.2)
        self.match_start_countdown = 3.5  # 3... 2... 1... BATTLE START!
        self.state = STATE_PLAYING

    def _start_lobby(self):
        self._start_singleplayer()
        self.total_players = 2

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

    def _spawn_ai_units(self, player_id):
        self._spawn_starting_units(player_id)

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

        if not hasattr(self, 'match_start_countdown') or self.match_start_countdown <= 0:
            gs.game_time += dt

            # Пространственный хеш
            gs.spatial_hash.clear()
            for entity in gs.get_all_entities():
                if entity.alive:
                    gs.spatial_hash.insert(entity)

            # Юниты
            for unit in gs.units[:]:
                if unit.alive:
                    unit.update(dt, gs)
                else:
                    unit.death_timer += dt
                    if unit.death_timer > unit.death_duration:
                        gs.units.remove(unit)

            # Здания
            for building in gs.buildings[:]:
                if building.alive:
                    building.update(dt, gs)
                else:
                    building.death_timer += dt
                    if building.death_timer > building.death_duration:
                        gs.buildings.remove(building)

            # Supply
            for pid, player in gs.players.items():
                player.recalculate_supply(gs.buildings)
                player.recalculate_current_supply(gs.units)

            # Боевая система
            gs.combat.update(dt, gs)

            # Туман войны
            self._update_fog_of_war(dt)

            # Улучшения
            gs.upgrade_system.update(dt, gs.game_time, gs)

            # Пассивные эффекты
            self._update_upgrade_effects(dt)
        else:
            # Даже во время паузы нужно обновлять spatial_hash для выделения юнитов рамкой
            gs.spatial_hash.clear()
            for entity in gs.get_all_entities():
                if entity.alive:
                    gs.spatial_hash.insert(entity)

        # Миникарта
        gs.minimap.update(dt)

        # Пинги
        gs.ping_system.update(dt)

        # Выделение
        gs.selection.update()

        # Строительство
        if gs.command_system.build_mode:
            gs.command_system.update_build_preview(mouse_pos, gs.camera, gs.tilemap)

        # ИИ
        self._update_simple_ai(dt)

        # Победа
        self._check_victory()

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

    def _update_simple_ai(self, dt):
        gs = self.game_state
        ai_id = 1
        player = gs.players.get(ai_id)
        if not player or player.is_defeated:
            return

        if not hasattr(self, '_ai_timer'):
            self._ai_timer = 0
            self._ai_attack_interval = 30.0

        self._ai_timer += dt
        if self._ai_timer >= self._ai_attack_interval:
            self._ai_timer = 0

            ai_units = [u for u in gs.units if u.player_id == ai_id and u.alive
                        and u.state == 'IDLE']

            if ai_units:
                targets = [b for b in gs.buildings
                           if b.player_id == gs.local_player_id and b.alive]
                targets += [u for u in gs.units
                            if u.player_id == gs.local_player_id and u.alive]

                if targets:
                    target = random.choice(targets)
                    for unit in ai_units[:5]:
                        unit.attack_target_entity(target)

            ai_barracks = [b for b in gs.buildings
                           if b.player_id == ai_id and b.alive and b.is_completed
                           and b.can_produce and hasattr(b, 'get_producible_units')]
            for barracks in ai_barracks:
                if len(barracks.production_queue) < 2:
                    units = barracks.get_producible_units()
                    if units:
                        unit_class = random.choice(units)
                        barracks.queue_unit(unit_class, gs)

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
                gs.chat.send(gs.players[gs.local_player_id].name)
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
            StanceSystem.set_stance(gs.selection.selected_entities, 'HOLD_POSITION')
        elif event.key == pygame.K_t:
            StanceSystem.cycle_stance(gs.selection.selected_entities)
        elif event.key == pygame.K_s and not pygame.key.get_pressed()[pygame.K_LCTRL]:
            for e in gs.selection.selected_entities:
                if hasattr(e, 'stop'):
                    e.stop()
        elif event.key == pygame.K_e:
            for e in gs.selection.selected_entities:
                if hasattr(e, 'toggle_siege'):
                    e.toggle_siege()

    def _handle_game_mouse_down(self, event):
        gs = self.game_state
        keys = pygame.key.get_pressed()

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
            return

        if event.button == 1 and gs.minimap.is_point_on_minimap(*event.pos):
            gs.minimap.handle_click(*event.pos, gs.camera, button='left')
            return

        if event.button == 3 and gs.minimap.is_point_on_minimap(*event.pos):
            world_x, world_y = gs.minimap.minimap_to_world(*event.pos)
            world_x = max(0, min(world_x, MAP_WIDTH))
            world_y = max(0, min(world_y, MAP_HEIGHT))
            for unit in gs.selection.selected_entities:
                if unit.is_unit and unit.player_id == gs.local_player_id:
                    unit.move_to_point(world_x, world_y, gs.tilemap)
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
        self.pause_votes.add(self.game_state.local_player_id)
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
