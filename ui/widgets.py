"""
botyaraRTS - ui/widgets.py
Лёгкие переиспользуемые UI-виджеты для меню и экранов настройки
(кнопки, ряды «чипсов» выбора, спиннеры). Стиль — как у кнопок главного меню.
"""
import pygame
from settings import *


def brighten(color, amount=30):
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )


def darken(color, amount=30):
    return (
        max(0, color[0] - amount),
        max(0, color[1] - amount),
        max(0, color[2] - amount),
    )


class Button:
    """Простая кнопка в стиле главного меню."""

    ACCENT = (0, 120, 200)
    NEUTRAL = (30, 40, 55)
    DANGER = (120, 40, 40)
    SUCCESS = (30, 100, 60)

    def __init__(self, rect, label, font, kind='neutral', callback=None,
                 border_radius=8, data=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.kind = kind
        self.callback = callback
        self.border_radius = border_radius
        self.data = data  # произвольные данные (например, значение опции)

    @property
    def base_color(self):
        return {
            'accent': self.ACCENT,
            'neutral': self.NEUTRAL,
            'danger': self.DANGER,
            'success': self.SUCCESS,
        }.get(self.kind, self.NEUTRAL)

    def draw(self, surface, mouse_pos, enabled=True, selected=False):
        base = self.base_color if enabled else darken(self.NEUTRAL, 10)
        bg = brighten(base, 30) if self.rect.collidepoint(mouse_pos) and enabled else base
        if selected:
            bg = brighten(base, 45)
        pygame.draw.rect(surface, bg, self.rect, border_radius=self.border_radius)
        border = brighten(base, 80) if self.rect.collidepoint(mouse_pos) else brighten(base, 40)
        if selected:
            border = (0, 200, 255)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=self.border_radius)

        text = self.font.render(self.label, True, COLOR_UI_TEXT if enabled else COLOR_UI_TEXT_DIM)
        surface.blit(text, (
            self.rect.centerx - text.get_width() // 2,
            self.rect.centery - text.get_height() // 2
        ))

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.callback:
                self.callback()
            return True
        return False


def draw_chip_row(surface, font, x, y, labels, current_idx, mouse_pos,
                  height=28, min_width=60, pad=8, gap=8):
    """Ряд выбираемых «чипсов». Возвращает (rects, clicked_idx_or_None).

    rects — список pygame.Rect для hit-теста кликом позже.
    """
    rects = []
    clicked = None
    cx = x
    for i, label in enumerate(labels):
        text = font.render(label, True, COLOR_UI_TEXT)
        w = max(min_width, text.get_width() + pad * 2)
        rect = pygame.Rect(cx, y, w, height)
        rects.append(rect)

        selected = (i == current_idx)
        hovered = rect.collidepoint(mouse_pos)
        if selected:
            bg = (0, 120, 200)
        elif hovered:
            bg = (55, 65, 85)
        else:
            bg = (40, 45, 55)
        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, (0, 150, 220) if selected else (60, 80, 100),
                         rect, 1, border_radius=4)
        surface.blit(text, (rect.centerx - text.get_width() // 2,
                            rect.centery - text.get_height() // 2))
        cx += w + gap

    return rects, clicked


def draw_spinner(surface, font, x, y, label_text, height=28, width=150):
    """Спиннер «‹ значение ›». Возвращает (left_rect, right_rect, value_rect)."""
    left_rect = pygame.Rect(x, y, height, height)
    right_rect = pygame.Rect(x + width + 4, y, height, height)
    value_rect = pygame.Rect(x + height + 4, y, width - height, height)

    mouse_pos = pygame.mouse.get_pos()
    for rect, arrow in ((left_rect, '‹'), (right_rect, '›')):
        bg = (0, 120, 200) if rect.collidepoint(mouse_pos) else (40, 45, 55)
        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, (60, 80, 100), rect, 1, border_radius=4)
        a = font.render(arrow, True, COLOR_UI_TEXT)
        surface.blit(a, (rect.centerx - a.get_width() // 2,
                         rect.centery - a.get_height() // 2))

    pygame.draw.rect(surface, (30, 35, 45), value_rect, border_radius=4)
    pygame.draw.rect(surface, (60, 80, 100), value_rect, 1, border_radius=4)
    text = font.render(label_text, True, COLOR_UI_TEXT)
    surface.blit(text, (value_rect.centerx - text.get_width() // 2,
                        value_rect.centery - text.get_height() // 2))
    return left_rect, right_rect, value_rect


def draw_panel(surface, rect, opacity=200):
    """Полупрозрачная панель с рамкой."""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((16, 20, 28, opacity))
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, (60, 80, 100), rect, 2, border_radius=10)


def draw_header(surface, font, text, x, y, color=(0, 150, 220)):
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, (x, y))
