"""
botyaraRTS - settings.py
Все константы, цвета и настройки по умолчанию.
"""
import pygame
import json
import os

# === DISPLAY ===
GAME_TITLE = "botyaraRTS"

# Тайлы: внутренний размер 8x8, отображаемый 32x32 (масштаб x4)
TILE_INTERNAL = 8
TILE_SIZE = 32
TILE_SCALE = TILE_SIZE // TILE_INTERNAL  # 4

# Карта: 320x320 тайлов = 10240x10240 пикселей мира
# При разрешении 1920x1080 это примерно 5x9 экранов — больше 10 экранов по площади
MAP_WIDTH_TILES = 320
MAP_HEIGHT_TILES = 320
MAP_WIDTH = MAP_WIDTH_TILES * TILE_SIZE   # 10240
MAP_HEIGHT = MAP_HEIGHT_TILES * TILE_SIZE  # 10240

# Высоты тайлов
HEIGHT_LOW = 0
HEIGHT_MID = 1
HEIGHT_HIGH = 2

# === CAMERA ===
CAMERA_SPEED = 15
CAMERA_EDGE_MARGIN = 20  # пикселей от края экрана для скролла
CAMERA_ZOOM_MIN = 0.5
CAMERA_ZOOM_MAX = 2.0
CAMERA_ZOOM_SPEED = 0.1
CAMERA_INERTIA = 0.85
CULLING_MARGIN = 2  # экрана запаса для culling

# === COLORS ===
# Ландшафт
COLOR_LOW_GROUND = (30, 42, 35)
COLOR_MID_GROUND = (45, 62, 50)
COLOR_HIGH_GROUND = (65, 85, 68)
COLOR_WATER = (25, 45, 75)
COLOR_WALL = (55, 50, 50)
COLOR_RAMP = (55, 72, 58)
COLOR_TITAN_ORE = (180, 170, 100)
COLOR_PLASMA_GEYSER = (80, 150, 220)

# UI
COLOR_BG = (10, 12, 15)
COLOR_UI_PANEL = (20, 25, 30)
COLOR_UI_PANEL_BORDER = (60, 70, 80)
COLOR_UI_TEXT = (200, 210, 220)
COLOR_UI_TEXT_DIM = (120, 130, 140)
COLOR_UI_ACCENT = (0, 180, 255)
COLOR_UI_WARNING = (255, 180, 0)
COLOR_UI_DANGER = (255, 60, 60)
COLOR_UI_SUCCESS = (60, 255, 120)
COLOR_SELECTION_BOX = (0, 255, 100)
COLOR_HP_BAR_BG = (40, 0, 0)
COLOR_HP_BAR_FULL = (0, 220, 0)
COLOR_HP_BAR_MED = (220, 220, 0)
COLOR_HP_BAR_LOW = (220, 0, 0)
COLOR_SHIELD_BAR = (0, 150, 255)

# Миникарта
COLOR_MINIMAP_BG = (15, 18, 22)
COLOR_MINIMAP_BORDER = (80, 90, 100)
COLOR_MINIMAP_VIEWPORT = (255, 255, 255)
COLOR_MINIMAP_FRIENDLY = (0, 200, 255)
COLOR_MINIMAP_ENEMY = (255, 50, 50)
COLOR_MINIMAP_RESOURCE = (255, 220, 50)

# Фракции
PLAYER_COLORS = [
    (0, 150, 255),    # Синий
    (255, 50, 50),     # Красный
    (50, 255, 50),     # Зеленый
    (255, 255, 50),    # Желтый
    (200, 50, 255),    # Фиолетовый
    (255, 150, 0),     # Оранжевый
    (0, 255, 200),     # Бирюзовый
    (255, 100, 150),   # Розовый
]

# Туман войны
FOG_UNEXPLORED = (0, 0, 0, 255)
FOG_EXPLORED = (0, 0, 0, 160)
FOG_VISIBLE = (0, 0, 0, 0)

# === RESOURCES ===
STARTING_TITAN = 500
STARTING_PLASMA = 100
STARTING_SUPPLY = 15
MAX_SUPPLY = 200

# === UNITS ===
UNIT_STATES = ['IDLE', 'MOVE', 'PURSUIT', 'ATTACK', 'HARVEST', 'BUILD', 'REPAIR']
STANCES = ['AGGRESSIVE', 'DEFENSIVE', 'HOLD_POSITION']

# === UPGRADES ===
UPGRADE_INTERVAL = 180  # секунд (3 минуты)
UPGRADE_SLOTS = 3
UPGRADE_CHOICES = 3
UPGRADE_COMPENSATION = 300  # титан за отказ

# Тиры улучшений по времени
UPGRADE_TIER_THRESHOLDS = {
    1: 0,     # 0-3 мин
    2: 360,   # 6+ мин
    3: 720,   # 12+ мин
}

# === NETWORK ===
DEFAULT_PORT = 5555
TICK_RATE = 20  # серверных тиков в секунду
NET_BUFFER_SIZE = 4096

# === GAMEPLAY ===
WORKER_HARVEST_AMOUNT = 8
WORKER_HARVEST_TIME = 2.0  # секунды
WORKER_BUILD_SPEED = 1.0
VISION_UPDATE_INTERVAL = 0.2  # секунды между обновлениями тумана

# === PATHS ===
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
SAVE_DIR = os.path.join(os.path.dirname(__file__), 'saves')

# === DEFAULT KEYBINDINGS ===
DEFAULT_KEYBINDINGS = {
    'camera_up': pygame.K_UP,
    'camera_down': pygame.K_DOWN,
    'camera_left': pygame.K_LEFT,
    'camera_right': pygame.K_RIGHT,
    'camera_up_alt': pygame.K_w,
    'camera_down_alt': pygame.K_s,
    'camera_left_alt': pygame.K_a,
    'camera_right_alt': pygame.K_d,
    'select_all_same': pygame.K_q,
    'ability_1': pygame.K_q,
    'ability_2': pygame.K_w,
    'ability_3': pygame.K_e,
    'ability_4': pygame.K_r,
    'stop': pygame.K_s,
    'hold_position': pygame.K_h,
    'attack_move': pygame.K_a,
    'patrol': pygame.K_p,
    'chat': pygame.K_RETURN,
    'pause': pygame.K_ESCAPE,
    'grid_toggle': pygame.K_g,
    'hp_bars_toggle': pygame.K_LALT,
}

# === SETTINGS MANAGER ===
class Settings:
    """Менеджер настроек с сохранением в JSON."""

    def __init__(self):
        self.settings_file = os.path.join(DATA_DIR, 'settings.json')
        self.defaults = {
            # Display
            'fullscreen': True,
            'screen_width': 1920,
            'screen_height': 1080,
            'fps_limit': 60,
            'vsync': False,

            # Camera
            'edge_scrolling': True,
            'camera_speed': CAMERA_SPEED,
            'camera_inertia': CAMERA_INERTIA,
            'zoom_sensitivity': CAMERA_ZOOM_SPEED,
            'invert_zoom': False,
            'lock_mouse': True,

            # UI
            'hp_bar_mode': 'damaged',  # always/damaged/selected/alt
            'minimap_size': 250,
            'minimap_position': 'bottom_left',
            'ui_opacity': 0.9,
            'show_grid': 'building',  # never/building/always
            'colorblind_mode': 'none',
            'screen_shake': 0.7,

            # Audio
            'master_volume': 0.8,
            'music_volume': 0.5,
            'sfx_volume': 0.7,
            'voice_volume': 0.6,
            'voice_frequency': 'normal',
            'minimize_sound': True,

            # Network
            'player_name': 'Player',
            'player_color': 0,
            'server_port': DEFAULT_PORT,
            'auto_pause_desync': True,
            'show_net_graph': False,

            # Keybindings
            'keybindings': DEFAULT_KEYBINDINGS.copy(),

            # Graphics quality
            'particle_quality': 'medium',
            'decal_lifetime': 30,
            'double_click_speed': 0.3,
        }
        self.values = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    saved = json.load(f)
                    for key, val in saved.items():
                        if key in self.defaults:
                            self.values[key] = val
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        serializable = {}
        for key, val in self.values.items():
            if key == 'keybindings':
                serializable[key] = {k: v for k, v in val.items()}
            else:
                serializable[key] = val
        with open(self.settings_file, 'w') as f:
            json.dump(serializable, f, indent=2)

    def get(self, key):
        return self.values.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.values[key] = value

    def reset(self):
        self.values = self.defaults.copy()


# Глобальный экземпляр
game_settings = Settings()
