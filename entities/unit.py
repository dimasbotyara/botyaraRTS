"""
botyaraRTS - entities/unit.py
Базовый класс юнита с FSM (IDLE/MOVE/PURSUIT/ATTACK),
стансами и автобоем.
"""
import pygame
import math
import random
from entities.entity import Entity
from settings import *
from core.pathfinding import find_path, smooth_path


class Unit(Entity):
    """Базовый юнит с передвижением и боем."""

    def __init__(self, x, y, player_id=0):
        super().__init__(x, y, player_id)
        self.is_unit = True

        # Передвижение
        self.speed = 80.0  # пикселей в секунду
        self.move_target = None  # (world_x, world_y) или None
        self.path = []  # список тайлов [(tx, ty), ...]
        self.path_index = 0
        self.current_waypoint = None  # (world_x, world_y)

        # Бой
        self.attack_damage = 10
        self.attack_range = 128  # пикселей
        self.attack_cooldown = 1.0  # секунд
        self.attack_timer = 0
        self.attack_target = None  # Entity
        self.pursuit_range = 256  # макс. дистанция преследования
        self.origin_point = None  # откуда начал преследование

        # Типы урона/брони
        self.damage_type = 'normal'  # normal, explosive, energy, siege
        self.armor_type = 'light'    # light, medium, heavy, structure

        # Может ли атаковать воздух/землю
        self.can_attack_air = False
        self.can_attack_ground = True

        # FSM
        self.state = 'IDLE'
        self.stance = 'AGGRESSIVE'  # AGGRESSIVE, DEFENSIVE, HOLD_POSITION

        # Агро-радиус (в пикселях)
        self.aggro_range = 200

        # Точка возврата (для DEFENSIVE стойки)
        self.return_point = None

        # Лимит населения (сколько supply занимает)
        self.supply_cost = 1

        # Стоимость
        self.cost_titan = 50
        self.cost_plasma = 0
        self.build_time = 5.0  # секунд

        # Способности (список словарей)
        self.abilities = []

        # Для пассивки "Suppression" и т.п.
        self.attack_count = 0

        # Анимация движения
        self.facing_angle = 0  # градусы

        # Ранг юнита
        self.unit_type = 'infantry'  # infantry, vehicle, aircraft, special

    def update(self, dt, game_state):
        """Главный цикл обновления юнита."""
        super().update(dt, game_state)
        if not self.alive:
            return

        # Обновляем таймер атаки
        if self.attack_timer > 0:
            self.attack_timer -= dt

        # FSM
        if self.state == 'IDLE':
            self._state_idle(dt, game_state)
        elif self.state == 'MOVE':
            self._state_move(dt, game_state)
        elif self.state == 'PURSUIT':
            self._state_pursuit(dt, game_state)
        elif self.state == 'ATTACK':
            self._state_attack(dt, game_state)

        # Расталкивание юнитов
        self._apply_separation(dt, game_state)

    def _apply_separation(self, dt, game_state):
        """Простейшая физика избегания наложения юнитов друг на друга."""
        radius = 16.0  # Радиус столкновения
        neighbors = game_state.spatial_hash.query_radius(self.x, self.y, radius * 2.5)
        
        sep_x, sep_y = 0.0, 0.0
        count = 0
        
        import math
        for neighbor in neighbors:
            if neighbor is self or not neighbor.is_unit or not neighbor.alive or getattr(neighbor, 'is_flying', False) != getattr(self, 'is_flying', False):
                continue
                
            dx = self.x - neighbor.x
            dy = self.y - neighbor.y
            dist_sq = dx * dx + dy * dy
            
            # Если ровно в одной точке - случайно сдвигаем
            if dist_sq == 0:
                import random
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
                dist_sq = dx * dx + dy * dy

            if dist_sq < (radius * 2) ** 2:
                dist = math.sqrt(dist_sq)
                overlap = (radius * 2) - dist
                
                force = overlap / dist
                sep_x += dx * force
                sep_y += dy * force
                count += 1
                
        if count > 0:
            push_speed = 50.0  # Сила расталкивания
            self.x += (sep_x / count) * push_speed * dt
            self.y += (sep_y / count) * push_speed * dt

    def _state_idle(self, dt, game_state):
        """IDLE: Стоим, ищем врагов."""
        if self.stance == 'HOLD_POSITION':
            # Только атакуем тех кто подошел в радиус атаки
            enemy = self._find_enemy_in_range(game_state, self.attack_range)
            if enemy:
                self.attack_target = enemy
                self.state = 'ATTACK'
        elif self.stance in ('AGGRESSIVE', 'DEFENSIVE'):
            # Ищем врагов в агро-радиусе
            enemy = self._find_enemy_in_range(game_state, self.aggro_range)
            if enemy:
                self.origin_point = (self.x, self.y)
                self.attack_target = enemy
                self.state = 'PURSUIT'

    def _state_move(self, dt, game_state):
        """MOVE: Двигаемся к цели."""
        if not self.path or self.path_index >= len(self.path):
            self.path = []
            if not self._execute_next_queued_command():
                self.state = 'IDLE'
            return

        # Получаем текущий waypoint
        target_tx, target_ty = self.path[self.path_index]
        target_wx, target_wy = (
            target_tx * TILE_SIZE + TILE_SIZE // 2,
            target_ty * TILE_SIZE + TILE_SIZE // 2
        )

        # Двигаемся к нему
        arrived = self._move_towards(target_wx, target_wy, dt)

        if arrived:
            self.path_index += 1
            if self.path_index >= len(self.path):
                self.path = []
                if not self._execute_next_queued_command():
                    self.state = 'IDLE'

        # В агрессивном стансе или при Attack-Move — проверяем врагов по пути
        if getattr(self, 'is_attack_move', False):
            enemy = self._find_enemy_in_range(game_state, self.aggro_range)
            if enemy:
                self.origin_point = (self.x, self.y)
                self.attack_target = enemy
                self.state = 'PURSUIT'

    def _state_pursuit(self, dt, game_state):
        """PURSUIT: Преследуем врага."""
        target = self.attack_target

        # Цель мертва или исчезла
        if not target or not target.alive:
            self.attack_target = None
            self._return_or_idle()
            return

        dist = self.distance_to(target)

        # В радиусе атаки — атакуем
        if dist <= self.attack_range:
            self.state = 'ATTACK'
            return

        # Проверяем не ушли ли слишком далеко (для DEFENSIVE)
        if self.stance == 'DEFENSIVE' and self.origin_point:
            ox, oy = self.origin_point
            dist_from_origin = math.sqrt((self.x - ox)**2 + (self.y - oy)**2)
            if dist_from_origin > self.pursuit_range:
                self.attack_target = None
                self._return_or_idle()
                return

        # Двигаемся к цели напрямую
        self._move_towards(target.x, target.y, dt)

    def _state_attack(self, dt, game_state):
        """ATTACK: Атакуем цель."""
        target = self.attack_target

        # Цель мертва
        if not target or not target.alive:
            self.attack_target = None
            # Ищем нового врага
            enemy = self._find_enemy_in_range(game_state, self.aggro_range)
            if enemy:
                self.attack_target = enemy
                self.state = 'PURSUIT'
            else:
                self._return_or_idle()
            return

        dist = self.distance_to(target)

        # Цель вышла из радиуса — преследуем
        if dist > self.attack_range * 1.2:
            if self.stance == 'HOLD_POSITION':
                self.attack_target = None
                self.state = 'IDLE'
            else:
                self.state = 'PURSUIT'
            return

        # Поворачиваемся к цели
        self.facing_angle = math.degrees(
            math.atan2(target.y - self.y, target.x - self.x)
        )

        # Атакуем если кулдаун прошёл
        if self.attack_timer <= 0:
            self._perform_attack(target, game_state)
            self.attack_timer = self.attack_cooldown
            self.attack_count += 1

    def _perform_attack(self, target, game_state):
        """Выполнить одну атаку."""
        # Проверка: может ли атаковать эту цель?
        if target.is_flying and not self.can_attack_air:
            return
        if not target.is_flying and not self.can_attack_ground:
            return

        damage = self.attack_damage

        # Модификатор высоты
        my_height = game_state.tilemap.get_height(*self.get_tile_pos())
        target_height = game_state.tilemap.get_height(*target.get_tile_pos())
        if target_height > my_height and not self.is_flying:
            # Стреляем вверх — шанс промаха 25%
            if random.random() < 0.25:
                # Создаём эффект "MISS"
                if hasattr(game_state, 'add_floating_text'):
                    game_state.add_floating_text(target.x, target.y - 20, "MISS", (200, 200, 200))
                return

        # Модификатор типа урона vs типа брони
        damage = self._apply_damage_modifiers(damage, target)

        # Наносим урон
        target.take_damage(damage, self.damage_type, attacker=self)

        # Создаём снаряд/эффект
        if hasattr(game_state, 'add_projectile'):
            game_state.add_projectile(self.x, self.y, target.x, target.y, self.color)

    def _apply_damage_modifiers(self, damage, target):
        """Модификаторы урона по типу."""
        # Таблица эффективности
        modifiers = {
            ('normal', 'light'): 1.0,
            ('normal', 'medium'): 0.75,
            ('normal', 'heavy'): 0.5,
            ('normal', 'structure'): 0.5,
            ('explosive', 'light'): 0.5,
            ('explosive', 'medium'): 1.0,
            ('explosive', 'heavy'): 1.25,
            ('explosive', 'structure'): 1.5,
            ('energy', 'light'): 1.25,
            ('energy', 'medium'): 1.0,
            ('energy', 'heavy'): 0.75,
            ('energy', 'structure'): 0.75,
            ('siege', 'light'): 0.25,
            ('siege', 'medium'): 0.75,
            ('siege', 'heavy'): 1.0,
            ('siege', 'structure'): 2.0,
        }

        key = (self.damage_type, target.armor_type)
        modifier = modifiers.get(key, 1.0)
        return int(damage * modifier)

    def _find_enemy_in_range(self, game_state, range_px):
        """Найти врага в радиусе. ПРИОРИТЕТ: Вражеские юниты > Постройки."""
        if not hasattr(game_state, 'spatial_hash'):
            return None

        # Проверяем настройки авто-атаки
        try:
            from settings import game_settings
            auto_mode = game_settings.get('auto_attack_mode', 'all')
        except Exception:
            auto_mode = 'all'

        if auto_mode == 'never':
            return None

        def is_valid_target(e):
            if not e.alive or not e.is_enemy(self):
                return False
            if e.is_flying and not self.can_attack_air:
                return False
            if not e.is_flying and not self.can_attack_ground:
                return False
            if e.is_cloaked and not self.is_detector:
                return False
            return True

        def is_unit_target(e):
            return is_valid_target(e) and getattr(e, 'is_unit', False)

        def is_building_target(e):
            return is_valid_target(e) and getattr(e, 'is_building', False)

        # 1-й проход: ищем мобильных вражеских юнитов (высший приоритет)
        target_unit = game_state.spatial_hash.query_nearest(
            self.x, self.y, range_px, filter_fn=is_unit_target
        )
        if target_unit:
            return target_unit

        # 2-й проход: постройки (только если нет юнитов и режим позволяет)
        if auto_mode != 'units_only':
            target_building = game_state.spatial_hash.query_nearest(
                self.x, self.y, range_px, filter_fn=is_building_target
            )
            if target_building:
                return target_building

        return None

    def _move_towards(self, target_x, target_y, dt):
        """Двигаться к точке. Возвращает True если дошёл."""
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 4:  # Достаточно близко
            self.x = target_x
            self.y = target_y
            return True

        # Нормализуем и двигаемся
        move_dist = self.speed * dt
        if move_dist >= dist:
            self.x = target_x
            self.y = target_y
            return True

        self.x += (dx / dist) * move_dist
        self.y += (dy / dist) * move_dist
        self.facing_angle = math.degrees(math.atan2(dy, dx))
        return False

    def _execute_next_queued_command(self):
        """Выполнить следующий приказ из очереди Shift."""
        if not hasattr(self, 'command_queue') or not self.command_queue:
            return False

        cmd_type, args = self.command_queue.pop(0)
        if cmd_type == 'move':
            world_x, world_y, tilemap, attack_move = args
            self.move_to_point(world_x, world_y, tilemap, attack_move=attack_move, shift=False)
            return True
        elif cmd_type == 'attack':
            target = args[0]
            if target and getattr(target, 'alive', False):
                self.attack_target_entity(target, shift=False)
                return True
            else:
                return self._execute_next_queued_command()
        elif cmd_type == 'harvest' and hasattr(self, 'command_harvest'):
            tile_x, tile_y = args
            self.command_harvest(tile_x, tile_y, shift=False)
            return True
        elif cmd_type == 'build' and hasattr(self, 'command_build'):
            building_class, tile_x, tile_y = args
            self.command_build(building_class, tile_x, tile_y, shift=False)
            return True
        elif cmd_type == 'resume_build' and hasattr(self, 'command_resume_build'):
            building = args[0]
            self.command_resume_build(building, shift=False)
            return True
        return False

    def _return_or_idle(self):
        """Вернуться к исходной точке или выполнить следующий приказ из очереди Shift."""
        if self._execute_next_queued_command():
            return
        if self.stance == 'DEFENSIVE' and self.origin_point:
            ox, oy = self.origin_point
            dist = math.sqrt((self.x - ox)**2 + (self.y - oy)**2)
            if dist > TILE_SIZE:
                self.move_to_point(ox, oy, None)
                return
        self.state = 'IDLE'
        self.origin_point = None

    def move_to_point(self, world_x, world_y, tilemap, attack_move=False, shift=False):
        """Приказ двигаться к точке (находит путь A*). Поддерживает Shift-очередь."""
        if not hasattr(self, 'command_queue'):
            self.command_queue = []

        if shift and self.state != 'IDLE':
            self.command_queue.append(('move', (world_x, world_y, tilemap, attack_move)))
            return True

        self.command_queue.clear()
        self.is_attack_move = attack_move
        if tilemap:
            start_tx, start_ty = self.get_tile_pos()
            end_tx = int(world_x // TILE_SIZE)
            end_ty = int(world_y // TILE_SIZE)

            path = find_path(tilemap, start_tx, start_ty, end_tx, end_ty)
            if path:
                path = smooth_path(path, tilemap)
                # Пропускаем первый waypoint если юнит уже на этом тайле,
                # чтобы юнит не шёл назад к центру текущего тайла при быстром ПКМ
                skip = 0
                if len(path) > 1 and path[0] == (start_tx, start_ty):
                    skip = 1
                self.path = path
                self.path_index = skip
                self.state = 'MOVE'
                self.attack_target = None
                self.move_target = (world_x, world_y)
                return True
        # Если нет тайлмапа или путь не найден — идём напрямую
        self.path = [(int(world_x // TILE_SIZE), int(world_y // TILE_SIZE))]
        self.path_index = 0
        self.state = 'MOVE'
        self.attack_target = None
        self.move_target = (world_x, world_y)
        return True

    def attack_target_entity(self, target, shift=False):
        """Приказ атаковать конкретную цель. Поддерживает Shift-очередь."""
        if not hasattr(self, 'command_queue'):
            self.command_queue = []

        if shift and self.state != 'IDLE':
            self.command_queue.append(('attack', (target,)))
            return

        self.command_queue.clear()
        self.attack_target = target
        self.origin_point = (self.x, self.y)
        dist = self.distance_to(target)
        if dist <= self.attack_range:
            self.state = 'ATTACK'
        else:
            self.state = 'PURSUIT'

    def stop(self):
        """Приказ остановиться."""
        if hasattr(self, 'command_queue'):
            self.command_queue.clear()
        self.state = 'IDLE'
        self.path = []
        self.attack_target = None
        self.move_target = None

    def set_stance(self, stance):
        """Сменить стойку."""
        if stance in STANCES:
            self.stance = stance

    def render(self, surface, camera):
        """Отрисовка юнита."""
        if not self.visible and not self.alive:
            return

        if not self.alive:
            self.render_death(surface, camera)
            return

        screen_rect = self.get_screen_rect(camera)

        # За экраном — не рисуем
        if screen_rect.right < 0 or screen_rect.left > camera.screen_w or \
           screen_rect.bottom < 0 or screen_rect.top > camera.screen_h:
            return

        player_color = PLAYER_COLORS[self.player_id % len(PLAYER_COLORS)]

        # Тело юнита (круг для пехоты, квадрат для техники)
        center_x = screen_rect.centerx
        center_y = screen_rect.centery
        radius = max(4, screen_rect.width // 2)

        if self.unit_type == 'infantry':
            pygame.draw.circle(surface, player_color, (center_x, center_y), radius)
            pygame.draw.circle(surface, self.color, (center_x, center_y), radius - 2)
        elif self.unit_type == 'vehicle':
            pygame.draw.rect(surface, player_color, screen_rect)
            inner = screen_rect.inflate(-4, -4)
            pygame.draw.rect(surface, self.color, inner)
        elif self.unit_type == 'aircraft':
            # Треугольник
            angle_rad = math.radians(self.facing_angle)
            pts = []
            for i in range(3):
                a = angle_rad + (i * 2 * math.pi / 3) - math.pi / 2
                px = center_x + math.cos(a) * radius
                py = center_y + math.sin(a) * radius
                pts.append((px, py))
            pygame.draw.polygon(surface, player_color, pts)
            # Внутренний треугольник
            inner_r = radius - 3
            pts2 = []
            for i in range(3):
                a = angle_rad + (i * 2 * math.pi / 3) - math.pi / 2
                px = center_x + math.cos(a) * inner_r
                py = center_y + math.sin(a) * inner_r
                pts2.append((px, py))
            if inner_r > 2:
                pygame.draw.polygon(surface, self.color, pts2)
        else:
            # Ромб для спец-юнитов
            pts = [
                (center_x, center_y - radius),
                (center_x + radius, center_y),
                (center_x, center_y + radius),
                (center_x - radius, center_y),
            ]
            pygame.draw.polygon(surface, player_color, pts)
            inner_r = radius - 3
            if inner_r > 2:
                pts2 = [
                    (center_x, center_y - inner_r),
                    (center_x + inner_r, center_y),
                    (center_x, center_y + inner_r),
                    (center_x - inner_r, center_y),
                ]
                pygame.draw.polygon(surface, self.color, pts2)

        # Направление взгляда (маленькая линия)
        angle_rad = math.radians(self.facing_angle)
        lx = center_x + math.cos(angle_rad) * radius
        ly = center_y + math.sin(angle_rad) * radius
        pygame.draw.line(surface, (255, 255, 255), (center_x, center_y), (int(lx), int(ly)), 2)

        # Рамка выделения
        if self.selected:
            sel_rect = screen_rect.inflate(6, 6)
            pygame.draw.rect(surface, COLOR_SELECTION_BOX, sel_rect, 2)

            # Индикатор стойки
            stance_colors = {
                'AGGRESSIVE': (255, 50, 50),
                'DEFENSIVE': (50, 150, 255),
                'HOLD_POSITION': (255, 255, 50),
            }
            sc = stance_colors.get(self.stance, (150, 150, 150))
            pygame.draw.circle(surface, sc,
                               (screen_rect.right - 3, screen_rect.top - 3), 3)
