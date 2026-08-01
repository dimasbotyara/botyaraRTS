"""
botyaraRTS - systems/combat.py
Боевая система: снаряды, эффекты, мины, отложенные взрывы.
"""
import pygame
import math
from settings import *


class Projectile:
    """Визуальный снаряд (трассер)."""

    def __init__(self, x, y, target_x, target_y, color, speed=600):
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.color = color
        self.speed = speed
        self.alive = True

        dx = target_x - x
        dy = target_y - y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.vx = (dx / dist) * speed
            self.vy = (dy / dist) * speed
        else:
            self.vx = 0
            self.vy = 0
            self.alive = False

        self.trail = []
        self.max_trail = 5

    def update(self, dt):
        if not self.alive:
            return

        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Проверка — дошёл ли до цели
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 10:
            self.alive = False

    def render(self, surface, camera):
        if not self.alive:
            return

        # След
        for i, (tx, ty) in enumerate(self.trail):
            sx, sy = camera.world_to_screen(tx, ty)
            alpha = (i + 1) / (len(self.trail) + 1)
            size = max(1, int(2 * camera.zoom * alpha))
            dim_color = tuple(int(c * alpha * 0.5) for c in self.color)
            pygame.draw.circle(surface, dim_color, (int(sx), int(sy)), size)

        # Снаряд
        sx, sy = camera.world_to_screen(self.x, self.y)
        size = max(2, int(3 * camera.zoom))
        pygame.draw.circle(surface, self.color, (int(sx), int(sy)), size)


class Mine:
    """Скрытая мина."""

    def __init__(self, x, y, damage, owner_id):
        self.x = x
        self.y = y
        self.damage = damage
        self.owner_id = owner_id
        self.alive = True
        self.trigger_radius = 32
        self.explosion_radius = 64
        self.arm_time = 1.0
        self.arm_timer = 0

    def update(self, dt, game_state):
        if not self.alive:
            return

        self.arm_timer += dt
        if self.arm_timer < self.arm_time:
            return

        # Проверяем триггер
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                self.x, self.y, self.trigger_radius
            )
            for entity in nearby:
                if entity.alive and entity.player_id != self.owner_id and entity.is_unit:
                    self.explode(game_state)
                    return

    def explode(self, game_state):
        """Взрыв мины."""
        self.alive = False
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(
                self.x, self.y, self.explosion_radius
            )
            for entity in nearby:
                if entity.alive and entity.player_id != self.owner_id:
                    entity.take_damage(self.damage, 'explosive')

        if hasattr(game_state, 'camera'):
            game_state.camera.shake(6, 0.3)


class FloatingText:
    """Всплывающий текст (MISS, урон и т.д.)."""

    def __init__(self, x, y, text, color, duration=1.0):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.duration = duration
        self.timer = 0
        self.alive = True

    def update(self, dt):
        self.timer += dt
        self.y -= 30 * dt  # Поднимается вверх
        if self.timer >= self.duration:
            self.alive = False

    def render(self, surface, camera):
        if not self.alive:
            return
        sx, sy = camera.world_to_screen(self.x, self.y)
        alpha = 1.0 - (self.timer / self.duration)
        font = pygame.font.Font(None, 20)
        text_surf = font.render(self.text, True, self.color)
        text_surf.set_alpha(int(255 * alpha))
        surface.blit(text_surf, (int(sx), int(sy)))


class DelayedEffect:
    """Отложенный эффект (бомба и т.д.)."""

    def __init__(self, delay, x, y, radius, damage, damage_type, owner_id):
        self.delay = delay
        self.x = x
        self.y = y
        self.radius = radius
        self.damage = damage
        self.damage_type = damage_type
        self.owner_id = owner_id
        self.timer = 0
        self.alive = True

    def update(self, dt, game_state):
        self.timer += dt
        if self.timer >= self.delay:
            self.explode(game_state)

    def explode(self, game_state):
        self.alive = False
        if hasattr(game_state, 'spatial_hash'):
            nearby = game_state.spatial_hash.query_radius(self.x, self.y, self.radius)
            for entity in nearby:
                if entity.alive and entity.player_id != self.owner_id:
                    entity.take_damage(self.damage, self.damage_type)

        if hasattr(game_state, 'camera'):
            game_state.camera.shake(10, 0.5)


class CombatSystem:
    """Управление боевыми эффектами."""

    def __init__(self):
        self.projectiles = []
        self.mines = []
        self.floating_texts = []
        self.delayed_effects = []

    def add_projectile(self, x, y, target_x, target_y, color):
        self.projectiles.append(Projectile(x, y, target_x, target_y, color))

    def add_mine(self, x, y, damage, owner_id):
        self.mines.append(Mine(x, y, damage, owner_id))

    def add_floating_text(self, x, y, text, color):
        self.floating_texts.append(FloatingText(x, y, text, color))

    def add_delayed_effect(self, delay, x, y, radius, damage, damage_type, owner_id):
        self.delayed_effects.append(
            DelayedEffect(delay, x, y, radius, damage, damage_type, owner_id)
        )

    def update(self, dt, game_state):
        # Снаряды
        for p in self.projectiles:
            p.update(dt)
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Мины
        for m in self.mines:
            m.update(dt, game_state)
        self.mines = [m for m in self.mines if m.alive]

        # Тексты
        for t in self.floating_texts:
            t.update(dt)
        self.floating_texts = [t for t in self.floating_texts if t.alive]

        # Отложенные эффекты
        for e in self.delayed_effects:
            e.update(dt, game_state)
        self.delayed_effects = [e for e in self.delayed_effects if e.alive]

    def render(self, surface, camera):
        for p in self.projectiles:
            p.render(surface, camera)
        for t in self.floating_texts:
            t.render(surface, camera)
