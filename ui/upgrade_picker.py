"""
botyaraRTS - ui/upgrade_picker.py
Экран выбора карточки улучшения (оверлей).
"""
import pygame
from settings import *


class UpgradePicker:
    """Оверлей выбора улучшения."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.card_width = 220
        self.card_height = 300
        self.card_spacing = 30
        self.card_rects = []

        # Замена
        self.replacing = False
        self.replace_card_index = -1
        self.slot_rects = []

        # Кнопка "Пропустить"
        self.skip_rect = pygame.Rect(0, 0, 200, 40)

        try:
            self.font_title = pygame.font.Font(None, 32)
            self.font_name = pygame.font.Font(None, 26)
            self.font_desc = pygame.font.Font(None, 20)
            self.font_tier = pygame.font.Font(None, 22)
            self.font_btn = pygame.font.Font(None, 24)
        except Exception:
            self.font_title = pygame.font.SysFont('arial', 24)
            self.font_name = pygame.font.SysFont('arial', 18)
            self.font_desc = pygame.font.SysFont('arial', 14)
            self.font_tier = pygame.font.SysFont('arial', 16)
            self.font_btn = pygame.font.SysFont('arial', 18)

    def render(self, surface, upgrade_system, game_state):
        """Отрисовка оверлея."""
        if not upgrade_system.is_choosing:
            return

        player = game_state.players.get(upgrade_system.choosing_player_id)
        if not player:
            return

        # Полупрозрачный фон
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        # Заголовок
        if not self.replacing:
            title = self.font_title.render("Choose an Upgrade!", True, COLOR_UI_ACCENT)
        else:
            title = self.font_title.render("Replace which slot?", True, COLOR_UI_WARNING)
        surface.blit(title, (self.screen_w // 2 - title.get_width() // 2, 50))

        if not self.replacing:
            # Показываем 3 карточки
            self._render_cards(surface, upgrade_system.current_choices)

            # Кнопка "Пропустить"
            self.skip_rect.centerx = self.screen_w // 2
            self.skip_rect.y = self.screen_h - 80
            pygame.draw.rect(surface, (80, 60, 30), self.skip_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_UI_WARNING, self.skip_rect, 2, border_radius=6)
            skip_text = self.font_btn.render(
                f"Skip (+{UPGRADE_COMPENSATION} Titan)", True, COLOR_UI_WARNING
            )
            surface.blit(skip_text, (
                self.skip_rect.centerx - skip_text.get_width() // 2,
                self.skip_rect.centery - skip_text.get_height() // 2
            ))
        else:
            # Показываем текущие слоты для замены
            self._render_replace_slots(surface, player, upgrade_system)

    def _render_cards(self, surface, choices):
        """Отрисовка карточек."""
        self.card_rects = []
        total_width = len(choices) * self.card_width + (len(choices) - 1) * self.card_spacing
        start_x = (self.screen_w - total_width) // 2
        card_y = (self.screen_h - self.card_height) // 2 - 20

        for i, upgrade in enumerate(choices):
            x = start_x + i * (self.card_width + self.card_spacing)
            rect = pygame.Rect(x, card_y, self.card_width, self.card_height)
            self.card_rects.append(rect)

            # Фон карточки
            pygame.draw.rect(surface, (25, 30, 40), rect, border_radius=10)

            # Обводка по тиру
            tier_colors = {1: (100, 200, 100), 2: (220, 200, 50), 3: (220, 50, 50)}
            border_color = tier_colors.get(upgrade.tier, COLOR_UI_PANEL_BORDER)
            pygame.draw.rect(surface, border_color, rect, 3, border_radius=10)

            # Цветная полоса сверху
            top_bar = pygame.Rect(x + 3, card_y + 3, self.card_width - 6, 50)
            pygame.draw.rect(surface, upgrade.icon_color, top_bar, border_radius=8)

            # Тир
            tier_text = self.font_tier.render(f"Tier {upgrade.tier}", True, (0, 0, 0))
            surface.blit(tier_text, (x + 10, card_y + 10))

            # Название
            name_text = self.font_name.render(upgrade.name, True, COLOR_UI_TEXT)
            surface.blit(name_text, (x + 10, card_y + 65))

            # Описание (с переносом строк)
            self._render_wrapped_text(
                surface, upgrade.description,
                x + 10, card_y + 95,
                self.card_width - 20,
                self.font_desc, COLOR_UI_TEXT_DIM
            )

            # Hover эффект
            mouse_pos = pygame.mouse.get_pos()
            if rect.collidepoint(mouse_pos):
                hover = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                hover.fill((255, 255, 255, 20))
                surface.blit(hover, rect.topleft)

    def _render_replace_slots(self, surface, player, upgrade_system):
        """Слоты для замены."""
        self.slot_rects = []
        slot_width = 180
        slot_height = 80
        total_width = len(player.active_upgrades) * (slot_width + 20)
        start_x = (self.screen_w - total_width) // 2
        slot_y = self.screen_h // 2 - 40

        for i, upgrade in enumerate(player.active_upgrades):
            x = start_x + i * (slot_width + 20)
            rect = pygame.Rect(x, slot_y, slot_width, slot_height)
            self.slot_rects.append(rect)

            pygame.draw.rect(surface, (40, 30, 30), rect, border_radius=6)
            pygame.draw.rect(surface, (200, 50, 50), rect, 2, border_radius=6)

            name_text = self.font_name.render(upgrade.name, True, COLOR_UI_TEXT)
            surface.blit(name_text, (x + 10, slot_y + 10))

            replace_text = self.font_desc.render("Click to replace", True, COLOR_UI_DANGER)
            surface.blit(replace_text, (x + 10, slot_y + 40))

            mouse_pos = pygame.mouse.get_pos()
            if rect.collidepoint(mouse_pos):
                hover = pygame.Surface((slot_width, slot_height), pygame.SRCALPHA)
                hover.fill((255, 100, 100, 30))
                surface.blit(hover, rect.topleft)

        # Кнопка "Отмена"
        cancel_rect = pygame.Rect(self.screen_w // 2 - 60, slot_y + 120, 120, 35)
        pygame.draw.rect(surface, (60, 60, 60), cancel_rect, border_radius=6)
        cancel_text = self.font_btn.render("Cancel", True, COLOR_UI_TEXT)
        surface.blit(cancel_text, (
            cancel_rect.centerx - cancel_text.get_width() // 2,
            cancel_rect.centery - cancel_text.get_height() // 2
        ))
        self.cancel_rect = cancel_rect

    def _render_wrapped_text(self, surface, text, x, y, max_width, font, color):
        """Текст с переносом строк."""
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i, line in enumerate(lines):
            text_surf = font.render(line, True, color)
            surface.blit(text_surf, (x, y + i * (font.get_height() + 2)))

    def handle_click(self, pos, upgrade_system, game_state):
        """Обработка клика по оверлею."""
        if not upgrade_system.is_choosing:
            return False

        player = game_state.players.get(upgrade_system.choosing_player_id)
        if not player:
            return False

        if not self.replacing:
            # Клик по карточке
            for i, rect in enumerate(self.card_rects):
                if rect.collidepoint(pos):
                    if len(player.active_upgrades) < UPGRADE_SLOTS:
                        upgrade_system.select_upgrade(i, game_state)
                    else:
                        # Нужно заменить — переходим в режим замены
                        self.replacing = True
                        self.replace_card_index = i
                    return True

            # Кнопка "Пропустить"
            if self.skip_rect.collidepoint(pos):
                upgrade_system.skip_upgrade(game_state)
                return True
        else:
            # Режим замены — клик по слоту
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(pos):
                    upgrade_system.select_upgrade(
                        self.replace_card_index, game_state, replace_index=i
                    )
                    self.replacing = False
                    return True

            # Кнопка "Отмена"
            if hasattr(self, 'cancel_rect') and self.cancel_rect.collidepoint(pos):
                self.replacing = False
                return True

        return False

    def resize(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
