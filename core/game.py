"""
botyaraRTS - core/game.py
Главный класс игры. Связывает все системы воедино.
"""
import pygame
import random
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

        # Игроки
        self.players = {}
        self.players[0] = PlayerState(0)
        self.players[1] = PlayerState(1)

        # Сущности
        self.units = []
        self.buildings = []
        self.dead_entities = []  # для отрисовки трупов

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

        # Spy network таймер
        self.spy_reveal_timer = 0
        self.spy_reveal_active = False
        self.spy_reveal_duration = 0

        # Сетка
        self.show_grid = False

        # Дебаг
        self.debug_mode = False
        self.debug_fog = True

    def add_entity(self, entity):
        """Добавить сущность в мир."""
        if entity.is_building:
            self.buildings.append(entity)
        elif entity.is_unit:
            self.units.append(entity)
        self.spatial_hash.insert(entity)

    def remove_entity(self, entity):
        """Удалить сущность из мира."""
        self.spatial_hash.remove(entity)
        if entity.is_building and entity in self.buildings:
            self.buildings.remove(entity)
        elif entity.is_unit and entity in self.units:
            self.units.remove(entity)

    def get_all_entities(self):
        """Все живые сущности."""
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
        self.clock = pygame.time.Clock()

        # Меню
        self.menu_font_large = pygame.font.Font(None, 64)
        self.menu_font_medium = pygame.font.Font(None, 36)
        self.menu_font_small = pygame.font.Font(None, 24)

        # Пауза
        self.pause_votes = set()
        self.total_players = 1

        # Настройки (меню настроек)
        self.settings_scroll = 0
        self.settings_items = []

        # Сеть
        self.network = None
        self.is_host = False

    def run(self):
        """Главный цикл."""
        while self.running:
            dt = self.clock.tick(game_settings.get('fps_limit')) / 1000.0
            dt = min(dt, 0.05)  # Ограничиваем dt для стабильности

            events = pygame.event.get()

            if self.state == STATE_MENU:
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

    # ========================
    # MENU
    # ========================

    def _update_menu(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_menu_click(event.pos)

    def _handle_menu_click(self, pos):
        x, y = pos
        cx = self.screen_w // 2
        btn_w = 300
        btn_h = 50
        start_y = self.screen_h // 2 - 60

        buttons = [
            ('Singleplayer', self._start_singleplayer),
            ('Multiplayer', self._start_lobby),
            ('Settings', self._open_settings),
            ('Quit', self._quit),
        ]

        for i, (text, action) in enumerate(buttons):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 65, btn_w, btn_h)
            if rect.collidepoint(x, y):
                action()
                break

    def _render_menu(self):
        self.screen.fill(COLOR_BG)

        # Заголовок
        title = self.menu_font_large.render("botyaraRTS", True, COLOR_UI_ACCENT)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 80))

        subtitle = self.menu_font_small.render(
            "A Sci-Fi Real-Time Strategy Game", True, COLOR_UI_TEXT_DIM
        )
        self.screen.blit(subtitle, (self.screen_w // 2 - subtitle.get_width() // 2, 145))

        # Кнопки
        cx = self.screen_w // 2
        btn_w = 300
        btn_h = 50
        start_y = self.screen_h // 2 - 60

        buttons = ['Singleplayer', 'Multiplayer', 'Settings', 'Quit']
        mouse_pos = pygame.mouse.get_pos()

        for i, text in enumerate(buttons):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 65, btn_w, btn_h)
            hovered = rect.collidepoint(mouse_pos)
            color = COLOR_UI_ACCENT if hovered else COLOR_UI_PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, rect, 2, border_radius=8)

            text_surf = self.menu_font_medium.render(text, True, COLOR_UI_TEXT)
            self.screen.blit(text_surf, (
                rect.centerx - text_surf.get_width() // 2,
                rect.centery - text_surf.get_height() // 2
            ))

        # Версия
        ver = self.menu_font_small.render("v0.1.0 alpha", True, COLOR_UI_TEXT_DIM)
        self.screen.blit(ver, (10, self.screen_h - 30))

    def _start_singleplayer(self):
        seed = random.randint(0, 999999)
        self.game_state = GameState(self.screen_w, self.screen_h, seed=seed, local_player_id=0)
        self.game_state.clock = self.clock
        self._spawn_starting_units(0)
        self._spawn_ai_units(1)
        self.total_players = 1
        self.state = STATE_PLAYING

    def _start_lobby(self):
        # Для простоты — запускаем как сингл с 2 игроками
        self._start_singleplayer()
        self.total_players = 2

    def _open_settings(self):
        self.state = STATE_SETTINGS
        self._previous_state = STATE_MENU

    def _quit(self):
        self.running = False

    def _spawn_starting_units(self, player_id):
        """Заспавнить стартовые юниты для игрока."""
        gs = self.game_state
        spawn_idx = player_id % len(gs.tilemap.spawn_points)
        sx, sy = gs.tilemap.spawn_points[spawn_idx]
        wx, wy = gs.tilemap.tile_to_world(sx, sy)

        # HQ
        hq = Headquarters(wx, wy, player_id)
        hq.is_completed = True
        hq.construction_progress = hq.build_time
        gs.add_entity(hq)

        # Supply Depot
        depot = SupplyDepot(wx + TILE_SIZE * 4, wy + TILE_SIZE * 2, player_id)
        depot.is_completed = True
        depot.construction_progress = depot.build_time
        gs.add_entity(depot)

        # 6 рабочих
        for i in range(6):
            angle = (i / 6) * 3.14159 * 2
            import math
            ux = wx + math.cos(angle) * TILE_SIZE * 3
            uy = wy + math.sin(angle) * TILE_SIZE * 3
            worker = Worker(ux, uy, player_id)
            gs.add_entity(worker)

        # Пересчитываем supply
        gs.players[player_id].recalculate_supply(gs.buildings)
        gs.players[player_id].recalculate_current_supply(gs.units)

    def _spawn_ai_units(self, player_id):
        """Заспавнить ИИ-противника (пока просто юниты)."""
        self._spawn_starting_units(player_id)

    # ========================
    # GAMEPLAY
    # ========================

    def _update_game(self, dt, events):
        gs = self.game_state

        # Обработка событий
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                self._handle_game_keydown(event)
            elif event.type == pygame.KEYUP:
                pass
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

        # Обновляем камеру
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        gs.camera.update(dt, keys, mouse_pos)

        # Игровое время
        gs.game_time += dt

        # Обновляем пространственный хеш
        gs.spatial_hash.clear()
        for entity in gs.get_all_entities():
            if entity.alive:
                gs.spatial_hash.insert(entity)

        # Обновляем юнитов
        for unit in gs.units[:]:
            if unit.alive:
                unit.update(dt, gs)
            else:
                unit.death_timer += dt
                if unit.death_timer > unit.death_duration:
                    gs.units.remove(unit)

        # Обновляем здания
        for building in gs.buildings[:]:
            if building.alive:
                building.update(dt, gs)
            else:
                building.death_timer += dt
                if building.death_timer > building.death_duration:
                    gs.buildings.remove(building)

        # Обновляем supply
        for pid, player in gs.players.items():
            player.recalculate_supply(gs.buildings)
            player.recalculate_current_supply(gs.units)

        # Обновляем боевую систему
        gs.combat.update(dt, gs)

        # Обновляем туман войны
        self._update_fog_of_war(dt)

        # Обновляем улучшения
        gs.upgrade_system.update(dt, gs.game_time, gs)

        # Пассивные эффекты улучшений
        self._update_upgrade_effects(dt)

        # Обновляем миникарту
        gs.minimap.update(dt)

        # Обновляем пинги
        gs.ping_system.update(dt)

        # Обновляем выделение
        gs.selection.update()

        # Обновляем режим строительства
        if gs.command_system.build_mode:
            gs.command_system.update_build_preview(mouse_pos, gs.camera, gs.tilemap)

        # Проверяем простой ИИ
        self._update_simple_ai(dt)

        # Проверяем условия победы
        self._check_victory()

    def _update_fog_of_war(self, dt):
        gs = self.game_state
        if not gs.debug_fog:
            gs.fog_of_war.reveal_all()
            return

        # Собираем источники обзора
        vision_sources = []
        local_id = gs.local_player_id
        for entity in gs.get_all_entities():
            if entity.alive and entity.player_id == local_id:
                tx, ty = entity.get_tile_pos()
                vision_r = entity.vision_range
                # Бонус от улучшения
                player = gs.players.get(local_id)
                if player:
                    mult = player.get_upgrade_bonus('vision_range', 1.0)
                    vision_r = int(vision_r * mult)
                vision_sources.append((tx, ty, vision_r))

        gs.fog_of_war.update(dt, vision_sources)

        # Обновляем видимость вражеских юнитов
        for entity in gs.get_all_entities():
            if entity.player_id != local_id:
                entity.visible = gs.fog_of_war.is_visible_world(entity.x, entity.y)
            else:
                entity.visible = True

    def _update_upgrade_effects(self, dt):
        """Пассивные эффекты от улучшений."""
        gs = self.game_state
        for pid, player in gs.players.items():
            # Пассивный доход (Black Market)
            income = player.get_upgrade_bonus('passive_income', 0)
            if income > 0:
                gs.passive_income_timer += dt
                if gs.passive_income_timer >= 10.0:
                    gs.passive_income_timer = 0
                    player.titan += income

            # Авто-ремонт зданий (Tempering)
            if player.upgrade_bonuses.get('building_regen', False):
                for b in gs.buildings:
                    if b.player_id == pid and b.alive and b.is_completed:
                        if b.hp < b.max_hp:
                            b.heal(b.max_hp * 0.01 * dt)

            # Spy Network
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
        """Очень простой ИИ для синглплеера."""
        gs = self.game_state
        ai_id = 1
        player = gs.players.get(ai_id)
        if not player or player.is_defeated:
            return

        # ИИ просто периодически отправляет юнитов атаковать
        if not hasattr(self, '_ai_timer'):
            self._ai_timer = 0
            self._ai_attack_interval = 30.0  # атака каждые 30 сек

        self._ai_timer += dt
        if self._ai_timer >= self._ai_attack_interval:
            self._ai_timer = 0

            # Ищем вражеские юниты ИИ
            ai_units = [u for u in gs.units if u.player_id == ai_id and u.alive
                        and u.state == 'IDLE']

            if ai_units:
                # Ищем ближайшего врага
                player_buildings = [b for b in gs.buildings
                                    if b.player_id == gs.local_player_id and b.alive]
                player_units = [u for u in gs.units
                                if u.player_id == gs.local_player_id and u.alive]
                targets = player_buildings + player_units

                if targets:
                    import random as rng
                    target = rng.choice(targets)
                    for unit in ai_units[:5]:
                        unit.attack_target_entity(target)

            # ИИ строит юнитов
            ai_barracks = [b for b in gs.buildings
                           if b.player_id == ai_id and b.alive and b.is_completed
                           and b.can_produce and hasattr(b, 'get_producible_units')]
            for barracks in ai_barracks:
                if len(barracks.production_queue) < 2:
                    units = barracks.get_producible_units()
                    if units:
                        import random as rng
                        unit_class = rng.choice(units)
                        barracks.queue_unit(unit_class, gs)

    def _check_victory(self):
        """Проверка условий победы."""
        gs = self.game_state
        for pid, player in gs.players.items():
            if player.is_defeated:
                continue
            has_buildings = any(b for b in gs.buildings
                                if b.player_id == pid and b.alive)
            has_units = any(u for u in gs.units
                           if u.player_id == pid and u.alive)
            if not has_buildings and not has_units:
                player.is_defeated = True
                if pid == gs.local_player_id:
                    self.state = STATE_GAME_OVER
                    self._game_over_result = 'defeat'
                elif all(p.is_defeated for p_id, p in gs.players.items()
                         if p_id != gs.local_player_id):
                    self.state = STATE_GAME_OVER
                    self._game_over_result = 'victory'

    # ========================
    # INPUT HANDLING
    # ========================

    def _handle_game_keydown(self, event):
        gs = self.game_state

        # Чат
        if gs.chat.is_open:
            if event.key == pygame.K_RETURN:
                msg = gs.chat.send(gs.players[gs.local_player_id].name)
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
                pass  # Нельзя закрыть ESC
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

        # Группы (1-9)
        elif pygame.K_1 <= event.key <= pygame.K_9:
            number = event.key - pygame.K_0
            keys = pygame.key.get_pressed()
            center = gs.selection.handle_group_key(number, keys)
            if center:
                gs.camera.center_on(center[0], center[1])

        # Стансы
        elif event.key == pygame.K_h:
            StanceSystem.set_stance(gs.selection.selected_entities, 'HOLD_POSITION')
        elif event.key == pygame.K_t:
            StanceSystem.cycle_stance(gs.selection.selected_entities)

        # Стоп
        elif event.key == pygame.K_s and not (pygame.key.get_pressed()[pygame.K_LCTRL]):
            for e in gs.selection.selected_entities:
                if hasattr(e, 'stop'):
                    e.stop()

        # Осадный режим (для Siege Tank)
        elif event.key == pygame.K_e:
            for e in gs.selection.selected_entities:
                if hasattr(e, 'toggle_siege'):
                    e.toggle_siege()

    def _handle_game_mouse_down(self, event):
        gs = self.game_state
        keys = pygame.key.get_pressed()

        # Проверяем оверлей улучшений
        if gs.upgrade_system.is_choosing:
            if event.button == 1:
                gs.upgrade_picker.handle_click(event.pos, gs.upgrade_system, gs)
            return

        # Alt+ЛКМ — пинг
        if event.button == 1 and keys[pygame.K_LALT]:
            world_x, world_y = gs.camera.screen_to_world(*event.pos)
            if keys[pygame.K_LCTRL]:
                gs.ping_system.add_ping(world_x, world_y, 'retreat')
            else:
                gs.ping_system.add_ping(world_x, world_y, 'attention')
            return

        # Миникарта
        if event.button == 1 and gs.minimap.is_point_on_minimap(*event.pos):
            gs.minimap.handle_click(*event.pos, gs.camera, button='left')
            return

        if event.button == 3 and gs.minimap.is_point_on_minimap(*event.pos):
            # ПКМ по миникарте — отправить юнитов
            world_x, world_y = gs.minimap.minimap_to_world(*event.pos)
            world_x = max(0, min(world_x, MAP_WIDTH))
            world_y = max(0, min(world_y, MAP_HEIGHT))
            for unit in gs.selection.selected_entities:
                if unit.is_unit and unit.player_id == gs.local_player_id:
                    unit.move_to_point(world_x, world_y, gs.tilemap)
            return

        # HUD
        if event.button == 1 and gs.hud.is_point_on_panel(*event.pos):
            gs.hud.handle_click(event.pos, gs, gs.command_system)
            return

        # Строительство
        if event.button == 1 and gs.command_system.build_mode:
            gs.command_system.try_place_building(gs, gs.local_player_id)
            return

        if event.button == 3 and gs.command_system.build_mode:
            gs.command_system.cancel_build_mode()
            return

        # Выделение
        gs.selection.handle_mouse_down(event.pos, event.button, gs.camera, gs)

    def _handle_game_mouse_up(self, event):
        gs = self.game_state
        keys = pygame.key.get_pressed()

        # Миникарта
        if event.button == 1:
            gs.minimap.handle_release()

        gs.selection.handle_mouse_up(event.pos, event.button, gs.camera, gs, keys)

    def _handle_game_mouse_motion(self, event):
        gs = self.game_state

        # Миникарта перетаскивание
        if gs.minimap.dragging:
            gs.minimap.handle_drag(*event.pos, gs.camera)
            return

        gs.selection.handle_mouse_move(event.pos)

    # ========================
    # RENDERING
    # ========================

    def _render_game(self):
        gs = self.game_state
        self.screen.fill(COLOR_BG)

        # Тряска камеры
        shake_x, shake_y = gs.camera.get_shake_offset(1 / max(1, self.clock.get_fps()))

        # Тайловая карта
        gs.tilemap.render(self.screen, gs.camera)

        # Сетка
        grid_mode = game_settings.get('show_grid')
        if gs.show_grid or grid_mode == 'always' or \
           (grid_mode == 'building' and gs.command_system.build_mode):
            gs.tilemap.render_grid(self.screen, gs.camera)

        # Сущности (сортируем по Y для правильного перекрытия)
        all_entities = gs.get_all_entities()
        all_entities.sort(key=lambda e: e.y)

        # Culling
        cull_rect = gs.camera.get_culling_rect()

        for entity in all_entities:
            if not entity.visible and entity.player_id != gs.local_player_id:
                continue
            if not cull_rect.collidepoint(entity.x, entity.y):
                continue

            entity.render(self.screen, gs.camera)

            # HP bars
            hp_mode = game_settings.get('hp_bar_mode')
            keys = pygame.key.get_pressed()
            if hp_mode == 'alt' and keys[pygame.K_LALT]:
                entity.render_hp_bar(self.screen, gs.camera, mode='alt')
            else:
                entity.render_hp_bar(self.screen, gs.camera, mode=hp_mode)

            # Полоска производства для зданий
            if entity.is_building:
                entity.render_production_bar(self.screen, gs.camera)

        # Туман войны
        if gs.debug_fog:
            gs.fog_of_war.render(self.screen, gs.camera)

        # Снаряды и эффекты
        gs.combat.render(self.screen, gs.camera)

        # Пинги в мире
        gs.ping_system.render(self.screen, gs.camera)

        # Превью строительства
        gs.command_system.render_build_preview(self.screen, gs.camera, gs.tilemap)

        # Рамка выделения
        gs.selection.render_selection_box(self.screen)

        # UI
        gs.hud.render(self.screen, gs, gs.selection.selected_entities)

        # Миникарта
        gs.minimap.render(self.screen, gs.camera,
                          entities=gs.get_all_entities(),
                          fog_of_war=gs.fog_of_war if gs.debug_fog else None)

        # Чат
        gs.chat.render(self.screen)

        # Оверлей улучшений
        if gs.upgrade_system.is_choosing:
            gs.upgrade_picker.render(self.screen, gs.upgrade_system, gs)

        # Дебаг
        if gs.debug_mode:
            self._render_debug()

    def _render_debug(self):
        gs = self.game_state
        font = pygame.font.Font(None, 18)
        y = 40
        lines = [
            f"Game Time: {gs.game_time:.1f}s",
            f"Entities: {len(gs.units)} units, {len(gs.buildings)} buildings",
            f"Camera: ({gs.camera.x:.0f}, {gs.camera.y:.0f}) zoom={gs.camera.zoom:.2f}",
            f"Selected: {len(gs.selection.selected_entities)}",
            f"Projectiles: {len(gs.combat.projectiles)}",
            f"Build Mode: {gs.command_system.build_mode}",
            f"Fog: {'ON' if gs.debug_fog else 'OFF'}",
        ]
        for line in lines:
            text = font.render(line, True, (255, 255, 0))
            self.screen.blit(text, (10, y))
            y += 16

    # ========================
    # PAUSE
    # ========================

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
        btn_w = 250
        btn_h = 45
        start_y = self.screen_h // 2 - 80

        buttons = [
            ('continue', self._try_continue),
            ('settings', lambda: setattr(self, 'state', STATE_SETTINGS) or
                setattr(self, '_previous_state', STATE_PAUSED)),
            ('main_menu', lambda: setattr(self, 'state', STATE_MENU)),
            ('quit', self._quit),
        ]

        for i, (key, action) in enumerate(buttons):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 60, btn_w, btn_h)
            if rect.collidepoint(pos):
                action()
                break

    def _try_continue(self):
        self.pause_votes.add(self.game_state.local_player_id)
        if len(self.pause_votes) >= self.total_players:
            self.state = STATE_PLAYING
            self.pause_votes.clear()

    def _render_pause(self):
        # Рисуем игру затемнённой
        self._render_game()

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Заголовок
        title = self.menu_font_large.render("PAUSED", True, COLOR_UI_TEXT)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 100))

        # Кнопки
        cx = self.screen_w // 2
        btn_w = 250
        btn_h = 45
        start_y = self.screen_h // 2 - 80
        mouse_pos = pygame.mouse.get_pos()

        votes_needed = self.total_players
        current_votes = len(self.pause_votes)

        labels = [
            f"Continue ({current_votes}/{votes_needed})",
            "Settings",
            "Main Menu",
            "Quit"
        ]

        for i, label in enumerate(labels):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * 60, btn_w, btn_h)
            hovered = rect.collidepoint(mouse_pos)
            color = COLOR_UI_ACCENT if hovered else COLOR_UI_PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, rect, 2, border_radius=6)

            text = self.menu_font_medium.render(label, True, COLOR_UI_TEXT)
            self.screen.blit(text, (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2
            ))

    # ========================
    # SETTINGS
    # ========================

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

    def _handle_settings_click(self, pos):
        x, y = pos
        # Кнопка "Back"
        back_rect = pygame.Rect(20, 20, 100, 35)
        if back_rect.collidepoint(x, y):
            game_settings.save()
            self.state = getattr(self, '_previous_state', STATE_MENU)
            return

        # Настройки — кликабельные элементы
        settings_y = 100 - self.settings_scroll
        item_height = 40
        items = self._get_settings_items()

        for i, item in enumerate(items):
            iy = settings_y + i * item_height
            if item['type'] == 'toggle':
                toggle_rect = pygame.Rect(400, iy, 60, 28)
                if toggle_rect.collidepoint(x, y):
                    current = game_settings.get(item['key'])
                    game_settings.set(item['key'], not current)
            elif item['type'] == 'choice':
                for j, option in enumerate(item['options']):
                    opt_rect = pygame.Rect(400 + j * 80, iy, 70, 28)
                    if opt_rect.collidepoint(x, y):
                        game_settings.set(item['key'], option)

    def _get_settings_items(self):
        return [
            {'label': '--- Display ---', 'type': 'header'},
            {'label': 'Fullscreen', 'key': 'fullscreen', 'type': 'toggle'},
            {'label': 'V-Sync', 'key': 'vsync', 'type': 'toggle'},
            {'label': 'FPS Limit', 'key': 'fps_limit', 'type': 'choice',
             'options': [30, 60, 120, 0]},
            {'label': '--- Camera ---', 'type': 'header'},
            {'label': 'Edge Scrolling', 'key': 'edge_scrolling', 'type': 'toggle'},
            {'label': 'Invert Zoom', 'key': 'invert_zoom', 'type': 'toggle'},
            {'label': 'Lock Mouse', 'key': 'lock_mouse', 'type': 'toggle'},
            {'label': '--- UI ---', 'type': 'header'},
            {'label': 'HP Bars', 'key': 'hp_bar_mode', 'type': 'choice',
             'options': ['always', 'damaged', 'selected', 'alt']},
            {'label': 'Grid', 'key': 'show_grid', 'type': 'choice',
             'options': ['never', 'building', 'always']},
            {'label': '--- Audio ---', 'type': 'header'},
            {'label': 'Minimize Sound', 'key': 'minimize_sound', 'type': 'toggle'},
            {'label': '--- Network ---', 'type': 'header'},
            {'label': 'Show Net Graph', 'key': 'show_net_graph', 'type': 'toggle'},
            {'label': 'Auto Pause Desync', 'key': 'auto_pause_desync', 'type': 'toggle'},
        ]

    def _render_settings(self):
        self.screen.fill(COLOR_BG)

        # Заголовок
        title = self.menu_font_large.render("Settings", True, COLOR_UI_ACCENT)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2, 30))

        # Кнопка Back
        back_rect = pygame.Rect(20, 20, 100, 35)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, back_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, back_rect, 1, border_radius=6)
        back_text = self.menu_font_small.render("< Back", True, COLOR_UI_TEXT)
        self.screen.blit(back_text, (35, 27))

        # Список настроек
        settings_y = 100 - self.settings_scroll
        item_height = 40
        items = self._get_settings_items()
        font = self.menu_font_small

        for i, item in enumerate(items):
            iy = settings_y + i * item_height

            if iy < 70 or iy > self.screen_h - 20:
                continue

            if item['type'] == 'header':
                text = font.render(item['label'], True, COLOR_UI_ACCENT)
                self.screen.blit(text, (30, iy + 5))
            elif item['type'] == 'toggle':
                # Label
                text = font.render(item['label'], True, COLOR_UI_TEXT)
                self.screen.blit(text, (50, iy + 5))

                # Toggle
                value = game_settings.get(item['key'])
                toggle_rect = pygame.Rect(400, iy, 60, 28)
                color = COLOR_UI_SUCCESS if value else (80, 80, 80)
                pygame.draw.rect(self.screen, color, toggle_rect, border_radius=14)
                circle_x = toggle_rect.x + 40 if value else toggle_rect.x + 20
                pygame.draw.circle(self.screen, COLOR_UI_TEXT, (circle_x, iy + 14), 10)

                val_text = font.render("ON" if value else "OFF", True, COLOR_UI_TEXT_DIM)
                self.screen.blit(val_text, (470, iy + 5))

            elif item['type'] == 'choice':
                text = font.render(item['label'], True, COLOR_UI_TEXT)
                self.screen.blit(text, (50, iy + 5))

                current = game_settings.get(item['key'])
                for j, option in enumerate(item['options']):
                    opt_rect = pygame.Rect(400 + j * 80, iy, 70, 28)
                    is_selected = (str(current) == str(option))
                    color = COLOR_UI_ACCENT if is_selected else COLOR_UI_PANEL
                    pygame.draw.rect(self.screen, color, opt_rect, border_radius=4)
                    pygame.draw.rect(self.screen, COLOR_UI_PANEL_BORDER, opt_rect, 1, border_radius=4)

                    label = str(option) if option != 0 else "∞"
                    opt_text = font.render(label, True, COLOR_UI_TEXT)
                    self.screen.blit(opt_text, (
                        opt_rect.centerx - opt_text.get_width() // 2,
                        opt_rect.centery - opt_text.get_height() // 2
                    ))

    # ========================
    # GAME OVER
    # ========================

    def _update_game_over(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    self.state = STATE_MENU
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.state = STATE_MENU

    def _render_game_over(self):
        self.screen.fill(COLOR_BG)

        result = getattr(self, '_game_over_result', 'defeat')

        if result == 'victory':
            color = COLOR_UI_SUCCESS
            text = "VICTORY!"
        else:
            color = COLOR_UI_DANGER
            text = "DEFEAT"

        title = self.menu_font_large.render(text, True, color)
        self.screen.blit(title, (self.screen_w // 2 - title.get_width() // 2,
                                 self.screen_h // 2 - 60))

        # Статистика
        if self.game_state:
            gs = self.game_state
            player = gs.players.get(gs.local_player_id)
            if player:
                stats = [
                    f"Game Time: {int(gs.game_time // 60)}m {int(gs.game_time % 60)}s",
                    f"Titan Mined: {player.total_titan_mined}",
                    f"Plasma Mined: {player.total_plasma_mined}",
                    f"Units Produced: {player.units_produced}",
                    f"Buildings Built: {player.buildings_built}",
                ]
                for i, stat in enumerate(stats):
                    text = self.menu_font_small.render(stat, True, COLOR_UI_TEXT_DIM)
                    self.screen.blit(text, (self.screen_w // 2 - text.get_width() // 2,
                                           self.screen_h // 2 + 20 + i * 25))

        hint = self.menu_font_small.render(
            "Click or press Enter to return to menu", True, COLOR_UI_TEXT_DIM
        )
        self.screen.blit(hint, (self.screen_w // 2 - hint.get_width() // 2,
                                self.screen_h - 80))