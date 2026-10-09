# ASTRA NEBULA UI — DESIGN PLAN

> **Goal**: Siêu đẹp, siêu ngầu, cinematic. Orb trung tâm là linh hồn.
> Mọi interaction (hover, mic, typing) đều có feedback visual mượt, sống động.

---

## 1. CONCEPT DIRECTION

| Attribute | Value |
|-----------|-------|
| Tên | **Astra Nebula UI** |
| Vibe | Cyberpunk minimal + Holographic + Liquid Glass/Mica |
| Tone | Sleek, mysterious, high-tech |
| Focus | OrbVisualizer trung tâm, glow mạnh, mượt |
| Rule | Ít màu nhưng đúng lúc: cyan/violet/amber glow. Dark dominant. |

### 1.1 Tham chiếu ảnh
- **IMG1** (`Screenshot 2026-10-07 232446.png`) — Quả cầu đơn, core trắng-cyan, outer glow mềm teal-cyan, ring structure nhẹ, volumetric bloom. Vibe: "core alive".
- **IMG2** (`Screenshot 2026-10-07 232503.png`) — Energy flow ngang, light sweep, nhiều ring layer + streaks, cyan-violet interplay. Vibe: "energy field + visualizer".

**Kết hợp**: IMG1 → core/glow, IMG2 → energy rings + sweep + visualizer bands.

---

## 2. COLOR SYSTEM

### 2.1 Base Surfaces
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-deep` | `#05070f` | Window gradient start |
| `--bg-base` | `#07111d` | Window gradient mid |
| `--bg-elevated` | `#0a1624` | Elevated surfaces |
| `--bg-glass` | `rgba(10, 22, 36, 0.72)` | Panel/frosted glass |
| `--bg-glass-hover` | `rgba(14, 32, 52, 0.88)` | Hover lift |

### 2.2 Borders
| Token | Value | Usage |
|-------|-------|-------|
| `--border-subtle` | `rgba(70, 130, 160, 0.18)` | Default borders |
| `--border-glass` | `rgba(95, 235, 255, 0.22)` | Glass borders |
| `--border-glow` | `rgba(95, 235, 255, 0.45)` | Focus/hover glow |
| `--border-strong` | `rgba(95, 235, 255, 0.65)` | Active focus |

### 2.3 Text
| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#e8f7ff` | Main text |
| `--text-secondary` | `#9dc3da` | Muted text |
| `--text-tertiary` | `#6f93b3` | Secondary muted |
| `--text-muted` | `#4a6b85` | Very muted |

### 2.4 Accent Palette
| Token | Value | Usage |
|-------|-------|-------|
| `--cyan` | `#4df4ff` | Primary glow |
| `--cyan-soft` | `#7afffb` | Inner highlight |
| `--cyan-deep` | `#00b4cc` | Depth |
| `--teal` | `#3df5d9` | Listening/success |
| `--violet` | `#9d7bff` | Exotic accent |
| `--magenta` | `#ff4dff` | Rare accent |
| `--amber` | `#f5b63b` | Tool/executing |
| `--orange` | `#ff9a4d` | Executing strong |
| `--red` | `#ff6b66` | Error |
| `--green` | `#6ef2ab` | Success |

### 2.5 Semantic Mode Colors
| Mode | Color | Usage |
|------|-------|-------|
| idle | `#29d3f1` | Standby cyan |
| listening | `#4cf4de` | Teal-cyan |
| processing | `#4bc0ff` | Blue |
| thinking | `#5cadff` | Light blue |
| tool_selection | `#f1c26e` | Gold |
| executing | `#ffaa5e` | Orange |
| observing | `#68dcff` | Light cyan |
| responding | `#5de8de` | Aqua |
| speaking | `#69efff` | Bright cyan |
| success | `#6df2ab` | Green |
| error | `#ff7571` | Red |
| interrupted | `#ffd183` | Amber |
| clarification | `#f5c36e` | Gold |
| booting | `#63cdff` | Light blue |

---

## 3. TYPOGRAPHY

### 3.1 Font Families
| Font | Weights | Use Case |
|------|---------|----------|
| **Exo 2** | 300–900 | Brand, PageTitle, Metrics, Eyebrow |
| **Outfit** | 300–900 | UI headings, CardTitle, Buttons |
| **Oxanium** | 200–800 | Eyebrow, status badges |
| **Inter** | 400–700 | Body text |
| **JetBrains Mono** | 400–600 | Logs, timestamps |

### 3.2 Scale (4pt base)
| Role | Size | Weight | Font |
|------|------|--------|------|
| PageTitle | 28px | 600 | Exo 2 |
| BrandName | 20px | 700 | Exo 2 |
| CardTitle | 15px | 600 | Outfit |
| MetricValue | 18px | 600 | Exo 2 |
| Body | 12px | 400 | Inter |
| Muted | 11px | 400 | Inter |
| Eyebrow | 10px | 700 | Oxanium |
| StatusValue | 10px | 700 | Oxanium |
| Mono | 12px | 400 | JetBrains Mono |

---

## 4. SPACING / RADIUS / LAYOUT GRID

### 4.1 Spacing (4pt scale)
| Token | Value |
|-------|-------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |

### 4.2 Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Buttons, inputs |
| `--radius-md` | 10px | Cards (was 7px) |
| `--radius-lg` | 12px | Large panels |
| `--radius-xl` | 14px | Card containers |
| `--radius-orb` | 20px | Orb container |

### 4.3 Layout
| Element | Size |
|---------|------|
| Sidebar | 220px fixed |
| Card padding | 18px 16px |
| Page margins | 14px |
| Card gap | 12px |
| Orb min | 260×260px |
| Orb ideal | 320×320px |

---

## 5. VISUAL EFFECTS

### 5.1 Frosted Glass
```css
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 rgba(12, 26, 40, 0.85), stop:1 rgba(8, 18, 28, 0.72));
border: 1px solid rgba(95, 235, 255, 0.16);
border-radius: 12px;
```
- Hover: border → `rgba(95, 235, 255, 0.32)`, bg lifts
- Accent borders per card type

### 5.2 Mica-like Noise
- 4×4 grayscale noise PNG at `assets/textures/noise-4x4.png`
- Opacity: 0.015–0.025 (applied in paintEvent)
- Adds material depth without distraction

### 5.3 Hover Glow
```css
QFrame#Card:hover { border-color: rgba(95, 235, 255, 0.32); }
QPushButton:hover { border-color: rgba(95, 235, 255, 0.4); }
```

### 5.4 Neon Scrollbar
- 6px track, cyan handle
- Hover: alpha 0.55
- Vertical and horizontal variants

---

## 6. ORB VISUALIZER ARCHITECTURE

File: `astra_ui/widgets/orb.py`

### 6.1 Layer Stack (paint order)
```
1. Far Bloom         — outermost, huge radial, very low alpha
2. Energy Rings      — 3 rotating ellipses, alpha by intensity
3. Holographic Sweep — conic arc 75°, follows phase
4. Mid Glow          — soft radial, medium alpha
5. Core Sphere       — layered radial gradient, rim light
6. Node Field        — 78 3D-projected nodes + links
7. Mic Ripples       — expanding rings, audio-reactive
8. Particle Orbit    — 16 particles, slow orbit
9. FFT Visualizer    — 3 concentric arcs (low/mid/high bands)
10. Tool Text        — overlay when executing
11. Progress Ring    — if progress is set
```

### 6.2 Energy Rings (3 rings)
| Ring | Radius | Alpha | Rotation | Width |
|------|--------|-------|----------|-------|
| 1 | 1.18× | 0.25× | +rot_speed | 1.0 × |
| 2 | 1.42× | 0.32× | -rot_speed | 1.15 × |
| 3 | 1.68× | 0.45× | +rot_speed | 1.3 × |

### 6.3 Holographic Sweep
- Arc: 75°, gradient transparent→cyan→transparent
- Speed: `phase * 0.9`
- Brightness: scales with `intensity + 0.3 * audio_level`

### 6.4 Mic Ripples
- Trigger: `audio_level > 0.18` (35% chance/frame)
- Count: max 2 concurrent
- Life: 600ms, radius 0.85→2.2×, alpha 200→0

### 6.5 Particle Field
- 16 particles, random orbit radius/phase
- Speed: 0.012–0.024 rad/tick
- Size: 1.2–2.8px
- Alpha: 120 × intensity × (1 + high_band × 0.8)

### 6.6 FFT Visualizer
- 3 concentric rings: inner=low (teal), mid=cyan, outer=violet
- 24 segments per ring
- Height = `band_value * radius * 0.09 * intensity`
- Rotation: phase-synced, alternating direction

### 6.7 Node Field (3D sphere projection)
- 78 nodes via golden spiral
- Links: edges where distance < 0.26
- Projected with perspective (3D rotation + tilt)
- Mouse parallax: tilt_x/tilt_y from pointer_offset

### 6.8 Breathing + Parallax
- Breathing: `1 + 0.012 * sin(phase * 2.4)`
- Audio pulse: `+ 0.035 * audio_level`
- Low band pump: `+ 0.028 * frequency_bands["low"]`
- Parallax: ±4% radius shift + ±12% tilt

### 6.9 Core Layers
1. **Hotspot**: white-cyan, alpha 235, radius 18%
2. **Core gradient**: white(245) → accent(200) → deep_blue(140) → transparent
3. **Rim light**: 1.3px stroke, cyan, alpha 180
4. **Progress ring**: if active, 2.5px arc, 360° × progress

---

## 7. PANEL / CARD SYSTEM

### 7.1 Card Variants
| Class | Accent | Usage |
|-------|--------|-------|
| `Card(accent="cyan")` | cyan | Orb container, Conversation |
| `Card(accent="teal")` | teal | Voice interface |
| `Card(accent="violet")` | violet | Agent loop, Activity feed |
| `Card(accent="orange")` | orange | Tools & Skills |
| `Card(accent="amber")` | amber | Quick prompts |
| `Card(accent="magenta")` | magenta | Memory |

### 7.2 Hover States
- Background: bg_glass_hover
- Border: border_glow (0.32 alpha)
- No shadow (Qt5 limitation)

### 7.3 GlassMixin
- Applies `accent` property for dynamic styling
- Used by: `Card`, `MetricCard`, `HealthRow`

---

## 8. INTERACTION EFFECTS

### 8.1 Mouse Hover
- **Cards**: border glow + bg lift (180ms)
- **Buttons**: bg shift + border glow (180ms)
- **Nav items**: bg bg + text color shift (180ms)
- **Orb**: parallax tilt + breathing accent (40ms)

### 8.2 Mic Interaction
| State | Orb Behavior |
|-------|-------------|
| idle | Slow rings, subtle sweep, faint particles |
| listening | Rings fast, strong sweep, particle orbit, FFT active |
| speaking | Breathing sync, cyan-white core pulse |
| error | Red pulse, scattered particles, error ring |

### 8.3 Keyboard
- `Ctrl+Return`: Send message
- `Enter` in input: Send message
- `Tab`: Navigate inputs

---

## 9. Icons / Symbols

### 9.1 Icon Set (SVG, 24×24, stroke 1.5px)
| Name | Purpose |
|------|---------|
| mic | Voice input start |
| mic-off | Voice input off |
| send | Send message |
| brain | Neural core |
| visualizer | Visualizer toggle |
| settings | Settings |
| terminal | Terminal/log |
| shield | Security |
| spark | Energy/activate |
| audio | Audio level |
| model | Local model |
| agent | Agent loop |
| memory | Persistent memory |
| tool | Tool/skill |
| folder | Folder/browser |
| file | File/document |
| refresh | Reload/refresh |
| delete | Remove |
| save | Save |
| eye | Toggle visibility |
| eye-off | Hide |
| plus | Add |
| minus | Remove/collapse |
| check | Success |
| close | Close |
| warning | Warning |
| error | Error |
| success | Success |
| info | Info/help |
| chevron-* | Direction |

### 9.2 Visual Symbols
- **Status dot**: `●` 8px, colored by mode
- **Brand mark**: `◉` stylized
- **Accent slashes**: `/`, `\` subtle, tertiary color

---

## 10. Animation Specs

| Effect | Duration | Easing |
|--------|----------|--------|
| Page transition | 260ms | OutCubic |
| Card hover lift | 180ms | OutQuad |
| Border glow | 200ms | OutQuad |
| Button press | 80ms | OutQuad |
| Orb mode switch | 400ms | OutCubic |
| Ripple expand | 600ms | OutCubic |
| Sweep rotation | Continuous | Linear |
| Ring rotation | Continuous | Linear |
| Particle orbit | Continuous | Linear |
| FFT decay | 40ms/frame | 0.88× |

### Reduced Motion
- Respect `prefersReducedMotion`
- Disable continuous animations
- Keep state transitions only

---

## 11. Layout Wireframe (Command Center)

```
┌─────────────────────────────────────────────────────────┐
│  ◉ ASTRA    LOCAL COMMAND CENTER    ● SYSTEM STANDBY   │  ← Top bar
├─┬───────────────────────────────────────────────────────┤
│ │  ◆ Command Center                                      │ Sidebar (220px)
│ │  ○ Conversations                                       │
│ │  ○ Agent Loop                                          │
│ │  ○ Voice Interface  ┌─● Listening────────────────┐      │
│ │  ○ Tools & Skills  │  Voice link card (teal)    │      │
│ │  ○ Memory          │  ● Standby                 │      │
│ │                    │  Say a request...          │      │
│ │                    └─────────────────────────────┘      │
│ │                    ┌─────────────────────────────┐      │
│ │   ┌────────────┐    │  ○ Ollama · 8 models       │      │
│ │   │  [ ORBITAL]│    └─────────────────────────────┘      │
│ │   │  CORE     │    ┌─────────────────────────────┐      │
│ │   │  ○○○○○○○ │    │  ○ Model: phi3-mini        │      │
│ │   │  READY    │    │  ○ Agent: native_react     │      │
│ │   └─────────┘  │    └─────────────────────────────┘      │
│ │   ┌────────────┐                                       │  │
│ │   │ Conversation │ ◇ Live session                      │  │
│ │   ├────────────┤ ◇ [Message input] [Send] [🎤]       │  │
│ │   └────────────┘                                       │  │
│ └──┘──────────────────────────────────────────────────────┤
│                                                          │  │ Main content area
│ ┌─────────────────────────────┐ ┌──────────────────────┐ │  ├── Body (flex 7+3)
│ │  Runtime health (teal)     │ │  Activity feed        │ │  │
│ │  ○ Ollama · online         │ │  Waiting...            │ │
│ │  ○ Speech · Vosk           │ │                        │ │
│ │  ○ Voice · SAPI            │ │  Quick prompts        │ │
│ └─────────────────────────────┘ │  ○ What can you do?   │ │
│                                 │  ○ Tell me about...   │ │
│                                 │  ○ Summarize last     │ │
│                                 └──────────────────────┘ │  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  LOCAL AGENT / OLLAMA / VOICE   Sat, 04 Oct 2025 · 14:30 │ Footer
└─────────────────────────────────────────────────────────┘
```

---

## 12. Architecture Refactor

### 12.1 File Structure
```
jarvis-ai-assistant/
├── ui/
│   ├── __init__.py              # Exports
│   ├── core/
│   │   ├── __init__.py
│   │   └── theme.py             # COLORS, MODE_COLORS, STYLESHEET, mode_stylesheet()
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── orb.py               # OrbVisualizer, CoreOrb
│   │   ├── panels.py            # Card, MetricCard, HealthRow, GlassMixin
│   │   └── icons.py             # load_icon, icon_pixmap
│   ├── assets.py                # load_assets() — fonts + textures
│   └── views/                   # (reserved for future)
├── assets/
│   ├── fonts/                   # Exo2, Outfit, Oxanium, JetBrains Mono
│   ├── textures/
│   │   ├── noise-4x4.png        # Mica noise
│   │   └── generate_noise.py    # Regen script
│   └── icons/                   # 28 SVG icons
├── DESIGN_PLAN.md               # This file
├── ui.py                        # Main window (refactored)
└── ...
```

### 12.2 Module Dependencies
```
ui.py
├── ui/__init__.py  (exports public API)
│   ├── astra_ui/core/theme.py
│   ├── astra_ui/widgets/orb.py
│   ├── astra_ui/widgets/panels.py
│   └── astra_ui/assets.py
└── astra_ui/widgets/icons.py
```

### 12.3 Backward Compatibility
- `CoreOrb = OrbVisualizer` alias maintained
- All `PROFILES` keys preserved
- All method signatures unchanged

---

## 13. Implementation Summary

### ✅ Hoàn thành
1. Phân tích ảnh tham chiếu (colors, structure)
2. Đọc UI hiện tại (ui.py, CoreOrb, layouts)
3. Viết DESIGN_PLAN.md (hoàn chỉnh)
4. Viết `astra_ui/core/theme.py` — COLORS, MODE_COLORS, STYLESHEET (263 lines)
5. Viết `astra_ui/widgets/orb.py` — OrbVisualizer (full upgrade)
6. Viết `astra_ui/widgets/panels.py` — Card, MetricCard, HealthRow
7. Viết `astra_ui/widgets/icons.py` — icon loader
8. Viết `astra_ui/assets.py` — font/textures loader
9. Viết `ui/__init__.py` — exports
10. Viết `assets/textures/noise-4x4.png` + gen script
11. Viết 10 SVG icons (mic, brain, spark, etc.)
12. Viết `assets/fonts/README.md`
13. Refactor `ui.py` — dùng module mới, giữ logic cũ

### 🔄 Testing
```bash
python -c "import ast; ast.parse(open('ui.py').read()); print('ui.py syntax OK')"
python -c "import ast; ast.parse(open('astra_ui/widgets/orb.py').read()); print('orb.py syntax OK')"
python -c "import ast; ast.parse(open('astra_ui/core/theme.py').read()); print('theme.py syntax OK')"
python -c "import ast; ast.parse(open('astra_ui/widgets/panels.py').read()); print('panels.py syntax OK')"
python -c "import ast; ast.parse(open('astra_ui/assets.py').read()); print('assets.py syntax OK')"
```

---

## 14. Quick Start

```bash
# 1. Install fonts (optional but recommended)
#    Download Exo2, Outfit, Oxanium, JetBrainsMono → assets/fonts/

# 2. Run the app (backward compatible import)
python ui.py

# 3. Or import the UI package directly
python -c "from ui import AstraWindow; print('OK')"
```

---

*Design Plan v1.0 — Ready for implementation. Siêu đẹp • Siêu ngầu • Mượt như ý.*