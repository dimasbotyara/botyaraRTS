"""
botyaraRTS - ui/chat.py
Система чата и пингов.
"""
import pygame
import time
from settings import *
from ui.font_utils import SmartFont


class ChatSystem:
    """Внутриигровой чат."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_open = False
        self.input_text = ""
        self.chat_mode = 'allies'  # 'allies' или 'all'
        self.messages = []  # [{'text': ..., 'sender': ..., 'time': ..., 'mode': ...}, ...]
        self.max_messages = 50
        self.display_duration = 10.0

        self.font = SmartFont(20)

    def toggle(self):
        self.is_open = not self.is_open
        if not self.is_open:
            self.input_text = ""

    def toggle_mode(self):
        if self.chat_mode == 'allies':
            self.chat_mode = 'all'
        else:
            self.chat_mode = 'allies'

    def add_char(self, char):
        if self.is_open:
            self.input_text += char

    def backspace(self):
        if self.is_open and self.input_text:
            self.input_text = self.input_text[:-1]

    def send(self, sender_name):
        if self.is_open and self.input_text.strip():
            self.messages.append({
                'text': self.input_text.strip(),
                'sender': sender_name,
                'time': time.time(),
                'mode': self.chat_mode,
            })
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)
            self.input_text = ""
            self.is_open = False
            return self.messages[-1]
        self.is_open = False
        return None

    def add_message(self, msg):
        """Добавить входящее сообщение."""
        msg['time'] = time.time()
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def render(self, surface):
        """Отрисовка чата."""
        x = 10
        y = self.screen_h - 220

        # Показываем последние сообщения
        current_time = time.time()
        recent = [m for m in self.messages
                  if current_time - m['time'] < self.display_duration or self.is_open]
        recent = recent[-8:]

        for msg in recent:
            alpha = 1.0
            age = current_time - msg['time']
            if age > self.display_duration - 2 and not self.is_open:
                alpha = max(0, (self.display_duration - age) / 2)

            mode_color = (100, 200, 255) if msg['mode'] == 'allies' else (255, 255, 100)
            prefix = "[ALLY] " if msg['mode'] == 'allies' else "[ALL] "
            text = self.font.render(
                f"{prefix}{msg['sender']}: {msg['text']}", True, mode_color
            )
            if alpha < 1.0:
                text.set_alpha(int(255 * alpha))
            surface.blit(text, (x, y))
            y += 18

        # Поле ввода
        if self.is_open:
            input_y = self.screen_h - 205
            bar_rect = pygame.Rect(x, input_y, 400, 24)
            pygame.draw.rect(surface, (0, 0, 0, 180), bar_rect)
            pygame.draw.rect(surface, COLOR_UI_ACCENT, bar_rect, 1)

            mode_str = "[ALLY]" if self.chat_mode == 'allies' else "[ALL]"
            mode_color = (100, 200, 255) if self.chat_mode == 'allies' else (255, 255, 100)
            mode_text = self.font.render(mode_str, True, mode_color)
            surface.blit(mode_text, (x + 4, input_y + 3))

            cursor = "│" if int(time.time() * 2) % 2 == 0 else ""
            input_surf = self.font.render(self.input_text + cursor, True, COLOR_UI_TEXT)
            surface.blit(input_surf, (x + mode_text.get_width() + 8, input_y + 3))

            hint = self.font.render("Tab to switch mode | Enter to send", True, COLOR_UI_TEXT_DIM)
            surface.blit(hint, (x, input_y - 16))
