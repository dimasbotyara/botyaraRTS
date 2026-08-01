"""
botyaraRTS - core/camera.py
Камера с плавным скроллом, зумом, инерцией и edge scrolling.
"""
import pygame
from settings import *


class Camera:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Позиция камеры в мировых координатах (левый верхний угол)
        self.x = 0.0
        self.y = 0.0

        # Зум
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Инерция (скорость скролла)
        self.vel_x = 0.0
        self.vel_y = 0.0

        # Настройки
        self.speed = game_settings.get('camera_speed')
        self.edge_scrolling = game_settings.get('edge_scrolling')
        self.edge_margin = CAMERA_EDGE_MARGIN
        self.inertia = game_settings.get('camera_inertia')
        self.zoom_speed = game_settings.get('zoom_sensitivity')
        self.invert_zoom = game_settings.get('invert_zoom')

        # Для плавного перехода (при клике на миникарту)
        self.target_x = None
        self.target_y = None
        self.snap_speed = 0.15

    def update(self, dt, keys_pressed, mouse_pos):
        """Обновить камеру каждый кадр."""
        dx, dy = 0.0, 0.0
        speed = self.speed / self.zoom  # Скорость зависит от зума

        # Клавиатурный скролл
        bindings = game_settings.get('keybindings')
        if keys_pressed[bindings.get('camera_up', pygame.K_UP)] or \
           keys_pressed[bindings.get('camera_up_alt', pygame.K_w)]:
            dy -= speed
        if keys_pressed[bindings.get('camera_down', pygame.K_DOWN)] or \
           keys_pressed[bindings.get('camera_down_alt', pygame.K_s)]:
            dy += speed
        if keys_pressed[bindings.get('camera_left', pygame.K_LEFT)] or \
           keys_pressed[bindings.get('camera_left_alt', pygame.K_a)]:
            dx -= speed
        if keys_pressed[bindings.get('camera_right', pygame.K_RIGHT)] or \
           keys_pressed[bindings.get('camera_right_alt', pygame.K_d)]:
            dx += speed

        # Edge scrolling
        if self.edge_scrolling and mouse_pos:
            mx, my = mouse_pos
            if mx <= self.edge_margin:
                dx -= speed * (1 - mx / self.edge_margin)
            elif mx >= self.screen_w - self.edge_margin:
                dx += speed * (1 - (self.screen_w - mx) / self.edge_margin)
            if my <= self.edge_margin:
                dy -= speed * (1 - my / self.edge_margin)
            elif my >= self.screen_h - self.edge_margin:
                dy += speed * (1 - (self.screen_h - my) / self.edge_margin)

        # Применяем инерцию
        if dx != 0 or dy != 0:
            self.vel_x = dx
            self.vel_y = dy
            self.target_x = None
            self.target_y = None
        else:
            self.vel_x *= self.inertia
            self.vel_y *= self.inertia
            if abs(self.vel_x) < 0.1:
                self.vel_x = 0
            if abs(self.vel_y) < 0.1:
                self.vel_y = 0

        # Плавный переход к целевой точке (клик на миникарте)
        if self.target_x is not None:
            diff_x = self.target_x - self.x
            diff_y = self.target_y - self.y
            self.x += diff_x * self.snap_speed
            self.y += diff_y * self.snap_speed
            if abs(diff_x) < 1 and abs(diff_y) < 1:
                self.x = self.target_x
                self.y = self.target_y
                self.target_x = None
                self.target_y = None
        else:
            self.x += self.vel_x
            self.y += self.vel_y

        # Плавный зум
        if abs(self.zoom - self.target_zoom) > 0.001:
            self.zoom += (self.target_zoom - self.zoom) * 0.15
        else:
            self.zoom = self.target_zoom

        # Ограничение границ карты
        self.clamp()

    def handle_zoom(self, direction, mouse_pos):
        """Зум колесиком мыши. direction: +1 приближение, -1 отдаление."""
        if self.invert_zoom:
            direction = -direction

        old_zoom = self.target_zoom
        self.target_zoom += direction * self.zoom_speed
        self.target_zoom = max(CAMERA_ZOOM_MIN, min(CAMERA_ZOOM_MAX, self.target_zoom))

        # Зумим в точку под мышкой
        if mouse_pos and old_zoom != self.target_zoom:
            mx, my = mouse_pos
            # Мировые координаты под мышью до зума
            world_x = self.x + mx / old_zoom
            world_y = self.y + my / old_zoom
            # Новая позиция камеры чтобы мировая точка осталась под мышью
            self.x = world_x - mx / self.target_zoom
            self.y = world_y - my / self.target_zoom

    def clamp(self):
        """Не дать камере выйти за границы карты."""
        view_w = self.screen_w / self.zoom
        view_h = self.screen_h / self.zoom

        max_x = MAP_WIDTH - view_w
        max_y = MAP_HEIGHT - view_h

        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))

    def center_on(self, world_x, world_y, instant=False):
        """Центрировать камеру на мировых координатах."""
        target_x = world_x - self.screen_w / (2 * self.zoom)
        target_y = world_y - self.screen_h / (2 * self.zoom)

        if instant:
            self.x = target_x
            self.y = target_y
            self.clamp()
        else:
            self.target_x = target_x
            self.target_y = target_y

    def world_to_screen(self, wx, wy):
        """Мировые координаты → экранные координаты."""
        sx = (wx - self.x) * self.zoom
        sy = (wy - self.y) * self.zoom
        return sx, sy

    def screen_to_world(self, sx, sy):
        """Экранные координаты → мировые координаты."""
        wx = sx / self.zoom + self.x
        wy = sy / self.zoom + self.y
        return wx, wy

    def get_visible_rect(self):
        """Получить прямоугольник видимой области в мировых координатах."""
        view_w = self.screen_w / self.zoom
        view_h = self.screen_h / self.zoom
        return pygame.Rect(self.x, self.y, view_w, view_h)

    def get_culling_rect(self):
        """Расширенный прямоугольник для culling (с запасом 2 экрана)."""
        view_w = self.screen_w / self.zoom
        view_h = self.screen_h / self.zoom
        margin_w = view_w * CULLING_MARGIN
        margin_h = view_h * CULLING_MARGIN
        return pygame.Rect(
            self.x - margin_w,
            self.y - margin_h,
            view_w + margin_w * 2,
            view_h + margin_h * 2
        )

    def get_visible_tiles(self):
        """Получить диапазон видимых тайлов (с запасом)."""
        cull = self.get_culling_rect()
        start_x = max(0, int(cull.x // TILE_SIZE))
        start_y = max(0, int(cull.y // TILE_SIZE))
        end_x = min(MAP_WIDTH_TILES, int((cull.x + cull.width) // TILE_SIZE) + 1)
        end_y = min(MAP_HEIGHT_TILES, int((cull.y + cull.height) // TILE_SIZE) + 1)
        return start_x, start_y, end_x, end_y

    def resize(self, new_w, new_h):
        """При изменении размера окна."""
        self.screen_w = new_w
        self.screen_h = new_h
        self.clamp()

    # Тряска камеры
    _shake_intensity = 0
    _shake_duration = 0
    _shake_timer = 0

    def shake(self, intensity=5, duration=0.3):
        """Запуск тряски камеры."""
        shake_mult = game_settings.get('screen_shake')
        self._shake_intensity = intensity * shake_mult
        self._shake_duration = duration
        self._shake_timer = duration

    def get_shake_offset(self, dt):
        """Получить смещение тряски для текущего кадра."""
        if self._shake_timer <= 0:
            return 0, 0
        self._shake_timer -= dt
        import random
        factor = self._shake_timer / self._shake_duration
        ox = random.uniform(-1, 1) * self._shake_intensity * factor
        oy = random.uniform(-1, 1) * self._shake_intensity * factor
        return ox, oy
