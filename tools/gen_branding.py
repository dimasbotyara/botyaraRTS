#!/usr/bin/env python3
"""Генератор брендинга botyaraRTS: баннеры EN/RU + альтернативный RU (SVG).

Запуск из корня репозитория:
    python3 tools/gen_branding.py
    rsvg-convert -w 1280 -h 400 assets/branding/banner_en.svg -o assets/branding/banner_en.png
    rsvg-convert -w 1280 -h 400 assets/branding/banner_ru.svg -o assets/branding/banner_ru.png
    rsvg-convert -w 1280 -h 400 assets/branding/banner_ru_alt.svg -o assets/branding/banner_ru_alt.png
    rsvg-convert -w 512 -h 512 assets/branding/icon.svg -o assets/branding/icon_512.png
    rsvg-convert -w 64  -h 64  assets/branding/icon.svg -o assets/branding/icon_64.png
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'assets', 'branding')
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 400
FRAME_RX = 16  # радиус скругления рамки баннера


def stars(n=90):
    import random
    rng = random.Random(42)
    out = []
    for _ in range(n):
        x = rng.uniform(0, W)
        y = rng.uniform(0, H)
        r = rng.choice([0.8, 1.0, 1.2, 1.6, 2.2])
        o = rng.uniform(0.25, 0.95)
        c = rng.choice(['#cfe8ff', '#ffffff', '#a8d4ff', '#ffe9c4'])
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{c}" opacity="{o:.2f}"/>')
    return '\n  '.join(out)


def frame_open(id_suffix, defs):
    """Открывает кадр: defs + clip по скруглённому прямоугольнику,
    чтобы фон не выходил за скруглённые углы."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
{defs}
    <clipPath id="frame-{id_suffix}">
      <rect x="0" y="0" width="{W}" height="{H}" rx="{FRAME_RX}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#frame-{id_suffix})">
'''


def frame_close():
    return f'''  </g>
  <rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="{FRAME_RX}" fill="none" stroke="#1d3350" stroke-width="3"/>
</svg>'''


def mech(x, y, s, accent='#00d4ff', team='#1e90ff'):
    """Стилизованный мех-ходун: геометрический силуэт с неоновыми стыками."""
    return f'''
  <g transform="translate({x},{y}) scale({s})" >
    <!-- ноги -->
    <path d="M -46,-10 L -66,60 L -50,66 L -30,6 Z" fill="#1b2432" stroke="#2e3d54" stroke-width="2"/>
    <path d="M 46,-10 L 66,60 L 50,66 L 30,6 Z" fill="#1b2432" stroke="#2e3d54" stroke-width="2"/>
    <path d="M -70,58 L -46,58 L -44,72 L -72,72 Z" fill="#141c28"/>
    <path d="M 70,58 L 46,58 L 44,72 L 72,72 Z" fill="#141c28"/>
    <rect x="-72" y="70" width="30" height="5" rx="2" fill="{accent}" opacity="0.8"/>
    <rect x="42" y="70" width="30" height="5" rx="2" fill="{accent}" opacity="0.8"/>
    <circle cx="-48" cy="26" r="7" fill="#0e1520" stroke="{accent}" stroke-width="2.5"/>
    <circle cx="48" cy="26" r="7" fill="#0e1520" stroke="{accent}" stroke-width="2.5"/>
    <!-- шея -->
    <rect x="-16" y="-84" width="32" height="24" fill="#1b2432"/>
    <!-- корпус -->
    <path d="M -52,-64 L 52,-64 L 62,-30 L 44,2 L -44,2 L -62,-30 Z"
          fill="#232f42" stroke="#3a4c68" stroke-width="2.5"/>
    <path d="M -52,-64 L 0,-64 L 0,2 L -44,2 L -62,-30 Z" fill="#283650"/>
    <path d="M -44,-58 L 44,-58 L 48,-46 L -48,-46 Z" fill="{team}" opacity="0.85"/>
    <!-- кабина -->
    <path d="M -20,-108 L 20,-108 L 30,-78 L -30,-78 Z"
          fill="#182230" stroke="#3a4c68" stroke-width="2.5"/>
    <path d="M -16,-96 L 16,-96 L 20,-86 L -20,-86 Z" fill="{accent}">
      <animate attributeName="opacity" values="1;0.55;1" dur="2.4s" repeatCount="indefinite"/>
    </path>
    <!-- плечевые блоки -->
    <rect x="-84" y="-60" width="26" height="34" rx="4" fill="#1b2432" stroke="#3a4c68" stroke-width="2"/>
    <rect x="58" y="-60" width="26" height="34" rx="4" fill="#1b2432" stroke="#3a4c68" stroke-width="2"/>
    <!-- пушка справа -->
    <rect x="80" y="-56" width="74" height="12" rx="3" fill="#222c3e" stroke="#3a4c68" stroke-width="2"/>
    <rect x="150" y="-59" width="12" height="18" rx="2" fill="#141c28"/>
    <circle cx="158" cy="-50" r="4" fill="{accent}" opacity="0.9">
      <animate attributeName="opacity" values="0.2;1;0.2" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <!-- ракетный блок слева -->
    <rect x="-92" y="-58" width="20" height="26" rx="3" fill="#222c3e" stroke="#3a4c68" stroke-width="2"/>
    <circle cx="-87" cy="-52" r="2.4" fill="{accent}"/><circle cx="-79" cy="-52" r="2.4" fill="{accent}"/>
    <circle cx="-87" cy="-44" r="2.4" fill="{accent}"/><circle cx="-79" cy="-44" r="2.4" fill="{accent}"/>
    <!-- центральное ядро -->
    <circle cx="0" cy="-32" r="10" fill="#0e1520" stroke="{accent}" stroke-width="3"/>
    <circle cx="0" cy="-32" r="4.5" fill="{accent}">
      <animate attributeName="r" values="4.5;6;4.5" dur="2s" repeatCount="indefinite"/>
    </circle>
    <line x1="24" y1="-108" x2="34" y2="-140" stroke="#3a4c68" stroke-width="3"/>
    <circle cx="35" cy="-142" r="4" fill="{accent}">
      <animate attributeName="opacity" values="1;0.3;1" dur="1.8s" repeatCount="indefinite"/>
    </circle>
  </g>'''


# ========================================
# Баннер 1: мех и планета (EN / RU)
# ========================================

def banner_main(lang):
    if lang == 'en':
        title = 'BOTYARA RTS'
        subtitle = 'SCI-FI REAL-TIME STRATEGY'
        tips = ['LAN battles up to 4 commanders', '9 AI doctrines · 4 difficulty tiers',
                'Fog of war · roguelike upgrades']
    else:
        title = 'БОТЯРА RTS'
        subtitle = 'СТРАТЕГИЯ В РЕАЛЬНОМ ВРЕМЕНИ'
        tips = ['Сетевые битвы до 4 командиров', '9 доктрин ИИ · 4 уровня сложности',
                'Туман войны · рогалик-улучшения']
    defs = '''    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#070a10"/>
      <stop offset="0.55" stop-color="#0c1320"/>
      <stop offset="1" stop-color="#122036"/>
    </linearGradient>
    <radialGradient id="neb1" cx="0.22" cy="0.3" r="0.55">
      <stop offset="0" stop-color="#123a66" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#123a66" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="neb2" cx="0.8" cy="0.75" r="0.6">
      <stop offset="0" stop-color="#3a1466" stop-opacity="0.4"/>
      <stop offset="1" stop-color="#3a1466" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00d4ff"/>
      <stop offset="1" stop-color="#0066ff"/>
    </linearGradient>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>'''
    body = f'''
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#neb1)"/>
    <rect width="{W}" height="{H}" fill="url(#neb2)"/>

    <g>
    {stars()}
    </g>

    <g stroke="#1d3350" stroke-width="1" opacity="0.5">
      {''.join(f'<line x1="{x}" y1="400" x2="{320 + (x - 640) * 0.35:.0f}" y2="268"/>' for x in range(0, 1281, 160))}
      <line x1="0" y1="304" x2="1280" y2="304"/>
      <line x1="0" y1="336" x2="1280" y2="336"/>
      <line x1="0" y1="372" x2="1280" y2="372"/>
    </g>

    <circle cx="1130" cy="86" r="46" fill="#16283f" stroke="#2a4a72" stroke-width="2"/>
    <ellipse cx="1130" cy="86" rx="64" ry="12" fill="none" stroke="#3a6ea8" stroke-width="2" opacity="0.7" transform="rotate(-14 1130 86)"/>

    {mech(1055, 330, 1.35)}

    <g filter="url(#glow)">
      <text x="64" y="170" font-family="DejaVu Sans, Arial, sans-serif" font-weight="bold"
            font-size="84" letter-spacing="6" fill="url(#accent)">{title}</text>
    </g>
    <text x="66" y="170" font-family="DejaVu Sans, Arial, sans-serif" font-weight="bold"
          font-size="84" letter-spacing="6" fill="#eaf6ff" opacity="0.92">{title}</text>

    <rect x="68" y="196" width="430" height="4" rx="2" fill="url(#accent)"/>
    <text x="66" y="240" font-family="DejaVu Sans, Arial, sans-serif" font-weight="bold"
          font-size="26" letter-spacing="7" fill="#7fc4e8">{subtitle}</text>

    <g font-family="DejaVu Sans, Arial, sans-serif" font-size="19" fill="#9fb8d0">
      <text x="68" y="296">▸ {tips[0]}</text>
      <text x="68" y="326">▸ {tips[1]}</text>
      <text x="68" y="356">▸ {tips[2]}</text>
    </g>
'''
    return frame_open('main', defs) + body + frame_close()


# ========================================
# Баннер 2 (альтернативный, RU): танковая колонна и авиация
# ========================================

def tank(x, y, s, accent='#00d4ff'):
    """Танк side-view, едет влево."""
    return f'''
  <g transform="translate({x},{y}) scale({s})">
    <path d="M -52,-18 L 46,-18 L 58,-4 L 50,6 L -50,6 L -60,-6 Z"
          fill="#232f42" stroke="#3a4c68" stroke-width="2"/>
    <path d="M -34,-34 L 22,-34 L 30,-18 L -40,-18 Z" fill="#1b2432" stroke="#3a4c68" stroke-width="2"/>
    <rect x="-6" y="-30" width="86" height="8" rx="3" fill="#222c3e" stroke="#3a4c68" stroke-width="1.5"/>
    <circle cx="-34" cy="-30" r="3" fill="{accent}"/>
    <path d="M -58,4 Q 0,16 52,4 L 48,18 Q 0,28 -54,18 Z" fill="#141c28" stroke="#2e3d54" stroke-width="2"/>
    <g fill="#0e1520" stroke="{accent}" stroke-width="1.6">
      <circle cx="-40" cy="12" r="6"/><circle cx="-14" cy="13" r="6"/>
      <circle cx="12" cy="13" r="6"/><circle cx="38" cy="12" r="6"/>
    </g>
    <rect x="-58" y="20" width="104" height="3" rx="1.5" fill="{accent}" opacity="0.55"/>
  </g>'''


def jet(x, y, s, accent='#ff5f8a', contrail_w=170):
    """Истребитель-бесхвостка, летит влево, с инверсионным следом."""
    return f'''
  <g transform="translate({x},{y}) scale({s})">
    <line x1="14" y1="0" x2="{14 + contrail_w}" y2="0" stroke="{accent}" stroke-width="2.5" opacity="0.35" stroke-dasharray="14 10"/>
    <path d="M -44,0 L 10,-9 L 26,0 L 10,9 Z" fill="#26344a" stroke="#3f567a" stroke-width="2"/>
    <path d="M -2,-9 L 12,-24 L 20,-10 Z" fill="#1b2432" stroke="#3a4c68" stroke-width="1.5"/>
    <circle cx="-36" cy="0" r="2.6" fill="{accent}">
      <animate attributeName="opacity" values="1;0.3;1" dur="1.4s" repeatCount="indefinite"/>
    </circle>
  </g>'''


def banner_ru_alt():
    title = 'БОТЯРА RTS'
    subtitle = 'КОМАНДУЙ · СТРОЙ · ПОБЕЖДАЙ'
    tips = 'Армия против армии: пехота, танки, авиация и спецназ'
    defs = '''    <linearGradient id="bg2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0b0714"/>
      <stop offset="0.5" stop-color="#150d26"/>
      <stop offset="1" stop-color="#241338"/>
    </linearGradient>
    <radialGradient id="nebA" cx="0.78" cy="0.25" r="0.6">
      <stop offset="0" stop-color="#5a1440" stop-opacity="0.5"/>
      <stop offset="1" stop-color="#5a1440" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="nebB" cx="0.15" cy="0.7" r="0.55">
      <stop offset="0" stop-color="#0e3a5c" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#0e3a5c" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="acc2" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#ff5f8a"/>
      <stop offset="1" stop-color="#ff9a3d"/>
    </linearGradient>
    <filter id="glow2" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="7" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>'''
    body = f'''
    <rect width="{W}" height="{H}" fill="url(#bg2)"/>
    <rect width="{W}" height="{H}" fill="url(#nebA)"/>
    <rect width="{W}" height="{H}" fill="url(#nebB)"/>

    <g>
    {stars()}
    </g>

    <!-- луна -->
    <circle cx="150" cy="80" r="40" fill="#241b33" stroke="#4a3a63" stroke-width="2"/>
    <circle cx="138" cy="70" r="7" fill="#312547"/>
    <circle cx="160" cy="92" r="5" fill="#312547"/>
    <circle cx="146" cy="96" r="4" fill="#312547"/>

    <!-- авиация -->
    {jet(520, 84, 1.25, accent='#00d4ff', contrail_w=200)}
    {jet(760, 150, 0.95, accent='#00d4ff', contrail_w=150)}
    {jet(400, 190, 0.75, accent='#ff5f8a', contrail_w=110)}

    <!-- земля -->
    <rect x="0" y="318" width="{W}" height="82" fill="#0e0a18"/>
    <rect x="0" y="316" width="{W}" height="3" fill="#4a2050"/>
    <g stroke="#241a38" stroke-width="1.5" opacity="0.8">
      <line x1="0" y1="344" x2="1280" y2="344"/>
      <line x1="0" y1="370" x2="1280" y2="370"/>
      {''.join(f'<line x1="{x}" y1="318" x2="{x - 60}" y2="400"/>' for x in range(60, 1281, 140))}
    </g>

    <!-- танковая колонна -->
    {tank(1090, 332, 1.3)}
    {tank(950, 340, 1.0, accent='#1e90ff')}
    {tank(835, 346, 0.8, accent='#1e90ff')}
    {tank(120, 338, 1.15, accent='#ff5f8a')}

    <!-- заголовок по центру -->
    <g filter="url(#glow2)">
      <text x="{W // 2}" y="232" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif"
            font-weight="bold" font-size="96" letter-spacing="8" fill="url(#acc2)">{title}</text>
    </g>
    <text x="{W // 2 - 4}" y="228" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif"
          font-weight="bold" font-size="96" letter-spacing="8" fill="#f4ecff" opacity="0.95">{title}</text>

    <text x="{W // 2}" y="272" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif"
          font-weight="bold" font-size="24" letter-spacing="9" fill="#c9a8e8">{subtitle}</text>

    <text x="{W // 2}" y="298" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif"
          font-size="17" fill="#8f7fae">{tips}</text>
'''
    return frame_open('alt', defs) + body + frame_close()


# ========================================
# Иконка
# ========================================

def icon_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0c1320"/>
      <stop offset="1" stop-color="#13233c"/>
    </linearGradient>
    <linearGradient id="ac" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#00e5ff"/>
      <stop offset="1" stop-color="#0077ff"/>
    </linearGradient>
    <filter id="g" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="8" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="512" height="512" rx="96" fill="url(#bg)"/>
  <circle cx="96" cy="92" r="4" fill="#cfe8ff" opacity="0.9"/>
  <circle cx="420" cy="70" r="3" fill="#ffffff" opacity="0.7"/>
  <circle cx="440" cy="180" r="5" fill="#a8d4ff" opacity="0.8"/>
  <circle cx="70" cy="240" r="3" fill="#ffffff" opacity="0.6"/>
  <circle cx="392" cy="330" r="3.5" fill="#cfe8ff" opacity="0.7"/>
  <g filter="url(#g)">
    <path d="M 136,300 L 376,300 L 340,180 Q 256,120 172,180 Z"
          fill="#26344a" stroke="#3f567a" stroke-width="10"/>
  </g>
  <path d="M 200,236 Q 256,196 312,236 L 300,268 L 212,268 Z" fill="#141d2c"/>
  <rect x="196" y="222" width="120" height="26" rx="8" fill="url(#ac)">
    <animate attributeName="opacity" values="1;0.6;1" dur="2.2s" repeatCount="indefinite"/>
  </rect>
  <rect x="360" y="220" width="120" height="34" rx="8" fill="#1c2838" stroke="#3f567a" stroke-width="8"/>
  <rect x="466" y="212" width="22" height="50" rx="6" fill="#141d2c"/>
  <path d="M 152,296 L 360,296 L 352,322 L 160,322 Z" fill="#1e90ff" opacity="0.9"/>
  <path d="M 168,330 L 344,330 L 322,402 L 190,402 Z" fill="#1c2838" stroke="#3f567a" stroke-width="8"/>
  <circle cx="256" cy="366" r="20" fill="#0e1520" stroke="url(#ac)" stroke-width="7">
    <animate attributeName="r" values="20;23;20" dur="2s" repeatCount="indefinite"/>
  </circle>
  <rect x="150" y="398" width="212" height="34" rx="14" fill="#141d2c" stroke="#2c3d58" stroke-width="6"/>
  <g fill="#2c3d58">
    <circle cx="182" cy="415" r="9"/><circle cx="222" cy="415" r="9"/>
    <circle cx="262" cy="415" r="9"/><circle cx="302" cy="415" r="9"/>
    <circle cx="336" cy="415" r="9"/>
  </g>
  <rect x="4" y="4" width="504" height="504" rx="92" fill="none" stroke="#1d3350" stroke-width="6"/>
</svg>'''


for lang in ('en', 'ru'):
    path = os.path.join(OUT, f'banner_{lang}.svg')
    with open(path, 'w') as f:
        f.write(banner_main(lang))
    print('wrote', path)

with open(os.path.join(OUT, 'banner_ru_alt.svg'), 'w') as f:
    f.write(banner_ru_alt())
print('wrote banner_ru_alt.svg')

with open(os.path.join(OUT, 'icon.svg'), 'w') as f:
    f.write(icon_svg())
print('wrote icon.svg')
