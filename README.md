# 🚀 botyaraRTS

> **A feature-rich Sci-Fi Real-Time Strategy game built in Python + Pygame.** Fog of war, A* pathfinding, roguelike upgrades, 3 factions' worth of units, and full RU/EN localization — all in pure Python, no engine.

A modern RTS with the depth of the classics and the polish of a modern indie — built from scratch on Pygame. No Unity, no Godot, no shortcuts. Just 10,000 lines of Python, a spatial hash, and a dream.

---

## ✨ Features

### ⚔️ RTS Core & Tactical Gameplay
- **Match Countdown** — animated `3... 2... 1... BATTLE START!` overlay kicks off every match
- **Auto-Worker Economy** — starting workers auto-harvest the nearest Titan ore and Plasma geysers on match start
- **Contextual Worker Build Menu** — command workers to construct Headquarters, Barracks, Factories, Defense Turrets, and Energy Reactors right from their UI card
- **Shift Command Queuing** — chain movement and attack orders by holding `Shift`
- **Multi-Selection System** — box drag select, `Shift + Click` to add/toggle, double-click to grab every nearby unit of the same type
- **Stance Control** — toggle each unit between **Aggressive**, **Defensive**, and **Hold Position**
- **Auto-Repeat RMB (Dota-2 style)** — toggle continuous right-click pathing in settings for effortless micro

### 🛠️ Roguelike Upgrade System
Every **3 minutes**, a modal presents **3 random tech cards** to pick from. **30 unique upgrades** across 3 tiers:

- 🏭 Industrialization, ⚙️ Titanium Alloy, 🩸 Nanite Vampirism, ☢️ Nuclear Protocol, and 26 more
- Equip up to **3 active cards** at once
- **Recycle** unwanted cards for bonus Titan resources
- Cards stack, synergize, and completely change your strategy mid-match

### 🌫️ Fog of War & Vision
- Full **vision grid** with explored vs. currently visible tiles
- Enemy units hidden in the fog
- Perfect for scout-heavy playstyles

### 🌐 Full Localization & Cross-Platform UI
- **Dual language support** — complete EN/RU translation for all UI, unit names, building descriptions, settings, and upgrade cards
- **First-run language selector** with persistent settings
- **Cross-platform glyph compatibility** — the unicode symbol set is tuned for both Windows and Linux (no more ☐ missing-glyph boxes)

### 🎮 Camera & Controls
- **WASD / Arrow keys** — smooth camera pan
- **Mouse Edge Scrolling** — pan by pushing the cursor to the screen edge
- **Middle-Mouse Drag** — grab-and-pull camera
- **Mouse Wheel Zoom** — from tactical close-up to strategic overview
- **Independent sensitivity sliders** for edge scroll, MMB drag, and keyboard speed

### 🗺️ Terrain, Pathfinding & Performance
- **320×320 tile map** — huge battlespace
- **A\* pathfinding** with proper unit navigation
- **Spatial hash** for collision lookups — thousands of entities without an O(n²) death spiral
- **Interactive minimap** in the bottom-left, click-to-jump and shows fog state

### 🎯 Tactical UI & Comms
- **In-game chat** — All / Team / Allies channels
- **Ping system** — Attention and Retreat pings on the tactical map
- **Adjustable HUD** — top resource bar, bottom unit control panel, HP-bar toggle (`Left Alt`), grid toggle (`G`)

### 🔫 Combat & Units
Multiple unit classes across air, land, and support:
- **Infantry** — Scouts, Troopers, Snipers, Medics
- **Vehicles** — Battle Tanks, Buggies, Siege Artillery
- **Aircraft** — Scout Drones, Fighters, Attack Helicopters
- **Special units** — the exotic stuff
- Projectiles, delayed explosions, floating damage text, hit sounds per weapon type

### 🎨 Rendering Pipeline
A dedicated `rendering/` package with per-category renderers:
- `terrain_renderer`, `unit_renderer`, `vehicle_renderer`, `aircraft_renderer`, `building_renderer`, `projectile_renderer`, `special_renderer`
- Centralized `render_manager` and `colors` palette
- All the juice — unit animations, muzzle flashes, explosions, ambient effects

### 🔊 Audio
- Bundled SFX library: weapons (rifle, sniper, minigun, plasma, laser, rocket, artillery, cannon, flame, AA, turret), UI (click, hover, error, alert, chat, ping, upgrade, select), impacts (metal, shield), explosions (small/medium/large/nuke/mine), economy (harvest, drop, build start/complete), unit ready
- Victory / defeat music (`music_victory.ogg`, `music_defeat.ogg`)
- Licensed sources listed in `assets/sounds/LICENSES.md`

### 🌐 Network Layer (WIP)
A `network/` module with `client.py`, `server.py`, and `protocol.py` — foundation laid for multiplayer.

---

## 🎮 Controls & Shortcuts

| Action | Control |
| :--- | :--- |
| **Move / Attack Target** | `Right Click` |
| **Select Unit / Box Drag** | `Left Click` |
| **Multi-Select Add / Toggle** | `Shift + Left Click` |
| **Queue Commands** | `Shift + Right Click` |
| **Attack-Move** | `A + Left Click` |
| **Stop Current Order** | `S` |
| **Hold Position** | `H` |
| **Cycle Unit Stance** | `T` |
| **Control Groups** | `Ctrl + 1..9` (assign), `1..9` (select) |
| **Camera Movement** | `WASD` / Arrows / Edge Scroll / MMB Drag |
| **Zoom** | Mouse Wheel |
| **Toggle Grid** | `G` |
| **Toggle HP Bars** | `Left Alt` |
| **Pause** | `ESC` |

---

## 📦 Installation & Running

### Requirements
- **Python 3.9+**
- **Pygame 2.1+**

### Quick Start

```bash
git clone https://github.com/dimasbotyara/botyaraRTS.git
cd botyaraRTS

python -m venv .venv
source .venv/bin/activate     # Linux/macOS
# .venv\Scripts\activate      # Windows

pip install pygame
python main.py
```

---

## 🏗️ Architecture

```
botyaraRTS/
├── main.py                 # Entry point & display init
├── settings.py             # Constants, colors, keybindings, JSON settings
├── localization.py         # EN/RU translation dictionary
│
├── core/                   # Engine-level systems
│   ├── game.py             # Main loop, state machine, countdown, menus
│   ├── camera.py           # Viewport, zoom, pan, inertia, edge scroll
│   ├── tilemap.py          # 320×320 terrain grid
│   ├── pathfinding.py      # A* navigation
│   ├── fog_of_war.py       # Vision & exploration mask
│   ├── minimap.py          # Interactive minimap
│   └── spatial_hash.py     # Entity lookup acceleration
│
├── ui/                     # HUD & overlays
│   ├── hud.py              # Resource bar + unit panel
│   ├── upgrade_picker.py   # Roguelike card modal
│   ├── chat.py             # In-game chat
│   └── ping_system.py      # Tactical pings
│
├── entities/               # Game objects
│   ├── entity.py / unit.py # Base classes
│   ├── worker.py           # Mining & building
│   ├── building.py         # Production queues
│   ├── infantry.py         # Scouts, Troopers, Snipers, Medics
│   ├── vehicles.py         # Tanks, Buggies, Artillery
│   ├── aircraft.py         # Drones, Fighters, Choppers
│   └── special_units.py    # Exotic units
│
├── systems/                # Game logic
│   ├── selection.py        # Box drag, shift multi-select
│   ├── commands.py         # Build mode & placement
│   ├── economy.py          # Titan / Plasma / Supply
│   ├── combat.py           # Projectiles & damage
│   ├── stances.py          # Aggressive / Defensive / Hold
│   └── upgrades.py         # 30 tech cards
│
├── rendering/              # Drawing pipeline
│   ├── render_manager.py   # Central renderer
│   ├── *_renderer.py       # Terrain / units / vehicles / air / buildings / projectiles / specials
│   ├── colors.py
│   └── utils.py
│
├── network/                # Multiplayer (foundation)
│   ├── server.py
│   ├── client.py
│   └── protocol.py
│
├── assets/
│   ├── fonts/              # Roboto
│   └── sounds/             # Full SFX + victory/defeat music
│
├── data/settings.json      # Persisted user config
├── BUILDINGS_EN.md         # Building reference (EN)
├── BUILDINGS_RU.md         # Building reference (RU)
├── screenshots/            # (add your own!)
└── LICENSE
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.9+ |
| **Engine** | Pygame 2.1+ |
| **Pathfinding** | Custom A* |
| **Vision** | Custom fog-of-war grid |
| **Perf** | Spatial hashing |
| **Localization** | Built-in dict (EN/RU) |
| **UI** | Hand-rolled Pygame widgets |

Zero external Python dependencies beyond `pygame`. No numpy, no PIL, no engine — pure Python.

---

## 🔧 Customization

### Adding a new upgrade card
Edit `systems/upgrades.py` — the upgrade database is a plain list of dicts, so you can add Industrialization-tier cards in a few lines.

### Adding a new unit type
Subclass `entities/unit.py` (or `infantry`/`vehicles`/`aircraft`) with its stats and draw logic, then register a renderer in `rendering/`.

### Tweaking balance
All global tuning lives in `settings.py` — unit costs, build times, damage values, camera speeds, keybindings.

### Adding a new language
Add a new dict to `localization.py` and hook it into the first-run language selector.

---

## 🐛 Troubleshooting

**Missing glyph boxes (☐) for unicode icons**
- Install a broad unicode font on your system (e.g., `ttf-dejavu`, `noto-fonts` on Arch). The game's own glyph set is tuned for cross-platform rendering, but very minimal Linux installs can still miss some symbols.

**Low FPS with huge armies**
- Lower the map fog resolution or disable HP bars (`Left Alt`).
- The spatial hash helps a lot, but 1000+ simultaneously visible units is still Pygame's territory, not yours.

**No sound**
- Check `assets/sounds/` is intact — the game expects the bundled SFX.
- Audio license info lives in `assets/sounds/LICENSES.md`.

**Text looks blurry on HiDPI**
- Launch with `SDL_VIDEO_X11_SCALING=1 python main.py` (X11), or adjust font rendering in `ui/font_utils.py`.

---

## 🚧 Roadmap

- ✅ Roguelike upgrade system (done!)
- ✅ Fog of war
- ✅ A* pathfinding
- ✅ 30 tech cards
- 🚧 Multiplayer (foundation laid in `network/`)
- ⬜ Campaign mode
- ⬜ AI opponents with strategy tiers
- ⬜ Replays

---

## ⚠️ Disclaimer

This is a hobby project. It's not trying to compete with StarCraft — it's trying to prove that you can build a real RTS in Python with Pygame. And it kind of does.

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**dimasbotyara** — [@dimasbotyara](https://github.com/dimasbotyara)

Made with 🚀, ☕, and ~10,000 lines of `pygame.draw.*`.

---

<div align="center">

**If you like it, drop a ⭐ — it fuels the next 10,000 lines**

</div>
