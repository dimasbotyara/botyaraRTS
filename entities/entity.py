"""
botyaraRTS - entities/entity.py
Базовый класс для всех игровых объектов (юниты, здания, снаряды).
"""
import pygame
import math
from settings import *


class Entity:
    """Базовый объект в мире игры."""

    _next_id = 0

    @classmethod
    def _get_next_id(cls):
        cls._next_id += 1
        return cls._next_id

    def __init__(self, x, y, player_id=0):
        self.id = Entity._get_next_id()
        self.x = float(x)
        self.y = float(y)
        self.player_id = player_id

        # Размеры для коллизий и отрисовки
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.radius = TILE_SIZE // 2

        # HP
        self.max_hp = 100
        self.hp = 100
        self.shield = 0
        self.max_shield = 0
        self.shield_regen = 0  # в секунду

        # Состояние
        self.alive = True
        self.selected = False
        self.visible = True  # виден ли для текущего игрока

        # Визуал
        self.color = (150, 150, 150)
        self.name = "Entity"

        # Флаги
        self.is_building = False
        self.is_unit = False
        self.is_flying = False
        self.is_cloaked = False
        self.is_detector = False  # видит невидимых

        # Обзор
        self.vision_range = 6  # в тайлах

        # Эффекты при смерти
        self.death_timer = 0
        self.death_duration = 2.0  # секунды до исчезновения трупа

        # Пассивные способности (заполняются в подклассах)
        self.passives = []
        self.abilities = []

    def update(self, dt, game_state):
        """Обновление каждый кадр."""
        if not self.alive:
            self.death_timer += dt
            return

        # Регенерация щита
        if self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + self.shield_regen * dt)

    def take_damage(self, damage, damage_type='normal', attacker=None):
        """Получить урон."""
        if not self.alive:
            return 0

        actual_damage = damage

        # Щит поглощает урон первым
        if self.shield > 0:
            if self.shield >= actual_damage:
                self.shield -= actual_damage
                return actual_damage
            else:
                actual_damage -= self.shield
                self.shield = 0

        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.die(attacker)

        return actual_damage

    def heal(self, amount):
        """Восстановить HP."""
        if not self.alive:
            return
        self.hp = min(self.max_hp, self.hp + amount)

    def die(self, killer=None):
        """Смерть объекта."""
        self.alive = False
        self.death_timer = 0

    def get_tile_pos(self):
        """Позиция в тайловых координатах."""
        return int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)

    def get_rect(self):
        """Прямоугольник для коллизий."""
        return pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )

    def get_screen_rect(self, camera):
        """Прямоугольник на экране."""
        sx, sy = camera.world_to_screen(
            self.x - self.width // 2,
            self.y - self.height // 2
        )
        w = int(self.width * camera.zoom)
        h = int(self.height * camera.zoom)
        return pygame.Rect(int(sx), int(sy), w, h)

    def distance_to(self, other):
        """Расстояние до другого объекта."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def distance_to_point(self, x, y):
        """Расстояние до точки."""
        dx = self.x - x
        dy = self.y - y
        return math.sqrt(dx * dx + dy * dy)

    def is_enemy(self, other):
        """Является ли другой объект врагом?"""
        return other.player_id != self.player_id

    def is_ally(self, other):
        """Является ли другой объект союзником?"""
        return other.player_id == self.player_id and other.id != self.id

    def render(self, surface, camera):
        """Базовая отрисовка."""
        if not self.visible:
            return

        screen_rect = self.get_screen_rect(camera)

        # Не рисуем если за экраном
        if screen_rect.right < 0 or screen_rect.left > camera.screen_w or \
           screen_rect.bottom < 0 or screen_rect.top > camera.screen_h:
            return

        # Тело
        player_color = PLAYER_COLORS[self.player_id % len(PLAYER_COLORS)]
        pygame.draw.rect(surface, player_color, screen_rect)

        # Рамка если выделен
        if self.selected:
            sel_rect = screen_rect.inflate(4, 4)
            pygame.draw.rect(surface, COLOR_SELECTION_BOX, sel_rect, 2)

    def render_hp_bar(self, surface, camera, mode='damaged'):
        """Отрисовка полоски HP."""
        if not self.alive:
            return

        show = False
        if mode == 'always':
            show = True
        elif mode == 'damaged' and self.hp < self.max_hp:
            show = True
        elif mode == 'selected' and self.selected:
            show = True
        elif mode == 'alt':
            show = True  # Вызывается только при зажатом Alt

        if not show:
            return

        screen_rect = self.get_screen_rect(camera)
        bar_width = screen_rect.width
        bar_height = max(3, int(4 * camera.zoom))
        bar_x = screen_rect.x
        bar_y = screen_rect.y - bar_height - 2

        # Фон
        pygame.draw.rect(surface, COLOR_HP_BAR_BG,
                         (bar_x, bar_y, bar_width, bar_height))

        # HP
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0
        if hp_ratio > 0.6:
            hp_color = COLOR_HP_BAR_FULL
        elif hp_ratio > 0.3:
            hp_color = COLOR_HP_BAR_MED
        else:
            hp_color = COLOR_HP_BAR_LOW

        hp_width = int(bar_width * hp_ratio)
        if hp_width > 0:
            pygame.draw.rect(surface, hp_color,
                             (bar_x, bar_y, hp_width, bar_height))

        # Щит поверх HP
        if self.max_shield > 0 and self.shield > 0:
            shield_ratio = self.shield / self.max_shield
            shield_width = int(bar_width * shield_ratio)
            shield_y = bar_y - bar_height - 1
            pygame.draw.rect(surface, COLOR_HP_BAR_BG,
                             (bar_x, shield_y, bar_width, bar_height))
            pygame.draw.rect(surface, COLOR_SHIELD_BAR,
                             (bar_x, shield_y, shield_width, bar_height))

    def render_death(self, surface, camera):
        """Отрисовка трупа/обломков."""
        if self.alive or self.death_timer > self.death_duration:
            return False  # Удалить

        alpha = 1.0 - (self.death_timer / self.death_duration)
        screen_rect = self.get_screen_rect(camera)

        # Затухающий серый прямоугольник
        gray = int(80 * alpha)
        if gray > 0:
            color = (gray, gray // 2, gray // 3)
            pygame.draw.rect(surface, color, screen_rect)
        return True  # Ещё показывать

    def serialize(self):
        """Сериализация для сохранения/сети."""
        return {
            'id': self.id,
            'type': self.__class__.__name__,
            'x': self.x,
            'y': self.y,
            'hp': self.hp,
            'shield': self.shield,
            'player_id': self.player_id,
            'alive': self.alive,
        }
