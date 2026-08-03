# 🚀 botyaraRTS

A modern, high-performance Sci-Fi Real-Time Strategy (RTS) game built in Python using Pygame. Feature-rich, highly optimized, and designed with full English & Russian localization.

---

## 🌟 Key Features

### ⚔️ RTS Core & Tactical Gameplay
- **Match Countdown**: Animated 3... 2... 1... BATTLE START! overlay at game start.
- **Auto-Worker Economy**: Starting workers automatically begin harvesting nearby Titan ore and Plasma geysers upon match start.
- **Worker Build Menu**: Command workers directly from their contextual UI card to construct Headquarters, Barracks, Factories, Defense Turrets, and Energy Reactors.
- **Shift Command Queuing**: Chain multiple movement and attack orders by holding `Shift`.
- **Multi-Selection System**: Box selection drag, `Shift + Click` to add/toggle units, and double-click to select all nearby units of the same type.
- **Stance Control**: Toggle unit behavior between **Aggressive**, **Defensive**, and **Hold Position**.
- **Auto-Repeat RMB (Dota 2 style)**: Toggle continuous right-click pathing in settings to effortlessly micro-manage units.

### 🌐 Full Localization & Cross-Platform UI
- **Dual Language Support**: Complete English and Russian localization for all UI, unit names, building descriptions, settings, and upgrade cards.
- **First-Run Language Selector**: Select your language on first launch with persistent settings save.
- **Cross-Platform Glyph Compatibility**: Optimized unicode symbol set ensuring crisp visual rendering on both **Windows** and **Linux** without square missing-glyph boxes.

### 🛠️ Upgrades & Tech Trees
- **Dynamic Roguelike Upgrades**: Every 3 minutes, select from 3 randomized tech upgrade cards across 3 Tiers (30 unique cards in total: Industrialization, Titanium Alloy, Nanite Vampirism, Nuclear Protocol, etc.).
- **Slot Management & Recycling**: Equip up to 3 active upgrade cards or recycle unwanted cards for bonus Titan resources.

### 🎮 Camera & Controls
- **Flexible Navigation**: Smooth camera controls via **WASD / Arrow keys**, **Mouse Edge Scrolling**, **Middle-Mouse Drag (MMB)**, and **Mouse Wheel Zooming**.
- **Adjustable Sensitivities**: Independent mouse edge, middle-click drag, and keyboard camera speed settings.

---

## 🎮 Controls & Shortcuts

| Action | Control / Keybinding |
| :--- | :--- |
| **Move / Attack Target** | `Right Click (RMB)` |
| **Select Unit / Box Drag** | `Left Click (LMB)` |
| **Multi-Select Add/Toggle** | `Shift + Left Click` |
| **Queue Commands** | `Shift + Right Click` |
| **Attack-Move** | `A + Left Click` |
| **Stop Current Order** | `S` |
| **Hold Position** | `H` |
| **Cycle Unit Stance** | `T` |
| **Control Groups** | `Ctrl + 1..9` (Assign), `1..9` (Select/Focus) |
| **Camera Movement** | `WASD` / `Arrow Keys` / `Edge Scroll` / `MMB Drag` |
| **Zoom In / Out** | `Mouse Wheel` |
| **Toggle Grid** | `G` |
| **Toggle HP Bars** | `Left Alt` |
| **Pause Game** | `ESC` |

---

## 📦 Installation & Running

### Requirements
- **Python 3.9+**
- **Pygame 2.1+**

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/botyaraRTS.git
   cd botyaraRTS
   ```

2. **Install dependencies:**
   ```bash
   pip install pygame
   ```

3. **Launch the game:**
   ```bash
   python main.py
   ```

---

## 🏗️ Architecture & Codebase Structure

```text
botyaraRTS/
├── main.py              # Application entry point & Pygame display initialization
├── settings.py          # Global constants, colors, keybindings & JSON settings manager
├── localization.py      # Translation dictionary (EN/RU) & string lookup helpers
├── core/
│   ├── game.py          # Core game loop, state management, loading, menu & countdown
│   ├── camera.py        # Camera viewport, zoom, pan, inertia & edge scrolling
│   ├── tilemap.py       # 320x320 terrain grid & A* pathfinding
│   ├── fog_of_war.py    # Vision grid & exploration visibility mask
│   ├── minimap.py       # Interactive bottom-left minimap viewport
│   └── spatial_hash.py   # Spatial partitioning for fast entity collision lookups
├── ui/
│   ├── hud.py           # Top resource bar & bottom unit selection control panel
│   ├── upgrade_picker.py# Card picker modal for 3-minute tech upgrades
│   ├── chat.py          # In-game chat system (All / Team / Allies)
│   └── ping_system.py   # Tactical map pings (Attention / Retreat)
├── entities/
│   ├── unit.py          # Unit base class, movement state machine & Shift queue
│   ├── worker.py        # Worker unit logic, resource mining & building placement
│   ├── building.py      # Base building class & production queues
│   ├── infantry.py      # Scouts, Troopers, Snipers, Medics
│   ├── vehicles.py      # Battle Tanks, Buggies, Siege Artillery
│   └── aircraft.py      # Scout Drones, Fighters, Attack Helicopters
└── systems/
    ├── selection.py     # Unit selection logic (box drag, Shift multi-select)
    ├── commands.py      # Building placement & build mode state machine
    ├── economy.py       # Player resource tracking (Titan, Plasma, Supply)
    ├── combat.py        # Projectiles, delayed explosions & float damage text
    └── upgrades.py      # 30 Tech upgrades database & bonus appliers
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
