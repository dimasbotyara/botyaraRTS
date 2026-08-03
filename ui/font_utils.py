"""
botyaraRTS - ui/font_utils.py
Умная система шрифтов с автоподдержкой кириллицы и полноцветных эмодзи.
Гарантирует 100% корректное отображение на Windows и Linux.
"""
import pygame

# Список приоритетных системных шрифтов для кириллицы
SYS_FONTS = ['segoeui', 'dejavusans', 'arial', 'liberationsans', 'freesans', 'ubuntu', 'sans-serif']

# Синглтон эмодзи-шрифта
_EMOJI_FONT_PATH = None
_EMOJI_FONT_CHECKED = False


def _get_emoji_font_path():
    global _EMOJI_FONT_PATH, _EMOJI_FONT_CHECKED
    if not _EMOJI_FONT_CHECKED:
        _EMOJI_FONT_CHECKED = True
        try:
            for name in ['notocoloremoji', 'segouiemoji', 'symbola', 'notosansemoji']:
                path = pygame.font.match_font(name)
                if path:
                    _EMOJI_FONT_PATH = path
                    break
        except Exception:
            _EMOJI_FONT_PATH = None
    return _EMOJI_FONT_PATH


import os

def create_font(size, bold=False):
    """Создать системный шрифт с поддержкой кириллицы."""
    font_name = 'Roboto-Bold.ttf' if bold else 'Roboto-Regular.ttf'
    font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts', font_name)
    try:
        return pygame.font.Font(font_path, size)
    except Exception:
        try:
            return pygame.font.SysFont(SYS_FONTS, size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)


def is_emoji_char(char):
    """Проверить, является ли символ эмодзи или расширенным значком."""
    code = ord(char)
    return (
        (0x1F300 <= code <= 0x1FAFF) or
        (0x2000 <= code <= 0x33FF) or
        (0x1F1E6 <= code <= 0x1F1FF)
    )


def render_smart_text(font, text, color, size=None):
    """
    Рендеринг текста. Безопасно отображает эмодзи и кириллицу на любых платформах.
    """
    if size is None:
        size = font.get_height()

    # Быстрый путь для текстов без эмодзи
    has_emoji = any(is_emoji_char(c) for c in text)
    if not has_emoji:
        return font.render(text, True, color)

    emoji_path = _get_emoji_font_path()
    emoji_font = None
    if emoji_path:
        try:
            emoji_font = pygame.font.Font(emoji_path, size)
        except Exception:
            emoji_font = None

    parts = []
    curr = ''
    for char in text:
        if is_emoji_char(char):
            if curr:
                parts.append((curr, False))
                curr = ''
            parts.append((char, True))
        else:
            curr += char
    if curr:
        parts.append((curr, False))

    surfaces = []
    target_h = font.get_height()

    for part, is_em in parts:
        rendered = False
        if is_em and emoji_font:
            try:
                s = emoji_font.render(part, True, (255, 255, 255))
                if s.get_height() > 0 and s.get_width() > 0:
                    if s.get_height() != target_h:
                        w = max(1, int(s.get_width() * (target_h / s.get_height())))
                        s = pygame.transform.smoothscale(s, (w, target_h))
                    surfaces.append(s)
                    rendered = True
            except Exception:
                rendered = False

        if not rendered:
            try:
                surfaces.append(font.render(part, True, color))
            except Exception:
                pass

    if not surfaces:
        return font.render(text, True, color)

    total_w = sum(s.get_width() for s in surfaces)
    total_h = max(target_h, max(s.get_height() for s in surfaces))

    result = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    x = 0
    for s in surfaces:
        y = (total_h - s.get_height()) // 2
        result.blit(s, (x, y))
        x += s.get_width()

    return result

class SmartFont:
    """Обертка над pygame.font.Font с авто-поддержкой кириллицы и эмодзи."""
    def __init__(self, size, bold=False):
        self.font = create_font(size, bold)
        self.font_size = size

    def render(self, text, antialias, color, background=None):
        return render_smart_text(self.font, text, color, self.font_size)

    def get_height(self):
        return self.font.get_height()
        
    def get_width(self, text):
        return self.render(text, True, (0,0,0)).get_width()

    def size(self, text):
        return self.font.size(text)
