# ĐẠI TRÙNG TỬ UI UPGRADE PLAN
> Revolutionary UI overhaul — from login to dashboard. Cinematic, holographic, liquid-glass. Siêu đẹp siêu ngầu.

---

## 0. CURRENT STATE ANALYSIS

### File Inventory
| Path | Status | Action |
|------|--------|--------|
| `ui.py` | Refactored ✅ | Use `ui/` package modules |
| `astra_ui/core/theme.py` | Ready ✅ | Glass QSS + color tokens |
| `astra_ui/widgets/orb.py` | Ready ✅ | OrbVisualizer + CoreOrb alias |
| `astra_ui/widgets/panels.py` | Ready ✅ | Card, MetricCard, HealthRow |
| `astra_ui/widgets/icons.py` | Ready ✅ | SVG icon loader |
| `astra_ui/assets.py` | Ready ✅ | Font/textures loader |
| `Security/login_ui.py` | Exists ⚠️ | Basic SPA login, needs upgrade |
| `public/index.html` | Exists ⚠️ | Imports `orb.js` which is MISSING |
| `public/planner.js` | Exists ✅ | Durable execution planner |
| `public/workspace.js` | Exists ✅ | Google Workspace mock |
| `public/orb.js` | **MISSING ❌** | Needs full WebGL implementation |
| `metrics/charts.py` | Exists ✅ | Chart.js specs for data |
| `metrics/collector.py` | Exists ✅ | Data aggregation |
| `Automation/Automation_Brain.py` | Exists ✅ | Automation logic |

### Integration Flow
```
[Login Window] → authentication → [Main AstraWindow]
                                     ↓
              ┌─────────────────┬──────────────────┬────────────────┐
              │ OrbVisualizer   │ Sidebar Nav     │ Workspace      │
              │ (PyQt5 paint)   │ (glass cards)   │ (glass panels) │
              └─────────────────┴─────────────────┴────────────────┘
                          ↘                    ↘
              [WebGL Orb Bridge]        [Metrics / Charts]
              (public/orb.js)          (metrics/charts.py)
```

---

## 1. LOGIN UI UPGRADE (Security/login_ui.py)

### 1.1 Current Issues
- Basic SPA with simple fade
- No holographic effects
- Emoji icons (📷, 👆, 🔐) should be custom SVGs
- No parallax/motion on auth steps
- No biometric scanner visualization

### 1.2 Upgrade Plan

#### 1.2.1 Visual Design
- **Background**: Deep space gradient `#05070f → #07111d` with subtle starfield (canvas-drawn twinkling dots)
- **Container**: Frosted glass card (same glass system as main UI)
- **Accent**: Cyan-teal pulse on active state
- **Particles**: 30–50 floating micro-particles behind card, slow drift
- **Orb**: Mini holographic orb in top-right corner, pulses with auth state

#### 1.2.2 Animation Sequence (Entrance)
1. **0ms**: Window fade-in + scale from 0.8 (400ms, OutBack)
2. **200ms**: Orb pulses once (cyan)
3. **400ms**: Logo slides down + fades (300ms, OutCubic)
4. **600ms**: Container card rises up (350ms, OutElastic)
5. **700ms**: Form elements stagger-fade (each 100ms offset)
6. **1000ms**: First auth option pulses (idle loop)

#### 1.2.3 Auth Step Transitions
| From → To | Transition | Duration |
|-----------|------------|----------|
| Welcome → Users | Slide left + fade | 300ms |
| Users → Register | Slide left + fade | 300ms |
| Users → Options | Slide left + fade | 300ms |
| Options → PIN | Slide left + fade | 300ms |
| Any → Error | Shake + red flash | 500ms |

#### 1.2.4 Biometric Scanner UI
- **Face Recognition**: Live camera feed with holographic circle overlay
  - `QCamera` + `QVideoProbe` for frame capture
  - Overlay: concentric rings (cyan) + "scanning" sweep line
  - Progress: ring fill animation → green check on success
- **Fingerprint**: Animated fingerprint sensor
  - SVG of fingerprint with scan line animation
  - Dot-matrix pattern fills gradually
  - Success: particles burst from sensor

#### 1.3 PIN Entry (Enhanced)
- Custom PIN pad (4×3 grid of circular buttons)
- Buttons: glass effect, ripple on click
- PIN dots: filled circles with subtle pulse
- Keypad: backspace button with icon
- Progress: each digit lights up the Orb incrementally

---

## 2. WEBGL ORB (public/orb.js) — REVOLUTIONARY 3D

### 2.1 Core Concept
**Three.js** holographic neural orb with:
- GPU-accelerated volumetric glow (additive blending)
- 3D node network with dynamic linking
- Audio-reactive FFT bars (Web Audio API)
- Mouse parallax (subtle 3D tilt)
- Touch controls (pinch to zoom, drag to rotate)
- WebGL post-processing: bloom + chromatic aberration

### 2.2 Architecture
```
orb.js (main module)
├── OrbVisualizer (class)
│   ├── initScene()      → Renderer, Scene, Camera, Lights
│   ├── createOrbMesh()  → Sphere + Node field (InstancedMesh)
│   ├── createGlow()     → ShaderMaterial volumetric glow
│   ├── createRings()    → TorusKnot + rotation groups
│   ├── createSweep()    → Conical gradient arc (shader)
│   └── animate()        → Ticker loop
├── NodeField (subclass)
│   ├── buildSphericalLayout() → Golden spiral points
│   ├── buildLinks()           → Delaunay triangulation
│   └── updateLinks()          → Dynamic based on proximity
├── EnergyRings (3 rings)
│   ├── rotationSpeed (per ring, opposing directions)
│   └── visualParams (thickness, opacity, color)
├── LightSweep (conic shader)
│   ├── angle (driven by time)
│   ├── width (75°)
│   └── intensity (mode-dependent)
├── ParticleSystem (16 particles)
│   ├── orbit paths (elliptical)
│   ├── texture-based sprites (soft glow)
│   └── audio reactivity
├── AudioAnalyzer (Web Audio API)
│   ├── FFT data → frequency bands
│   ├── smooth decay
│   └── event dispatch
└── StateMachine (mode transitions)
    ├── idle → listening (ring speedup + sweep brighten)
    ├── listening → thinking (core color shift)
    ├── thinking → executing (node field intensifies)
    ├── executing → speaking (breathing + audio sync)
    ├── speaking → idle (smooth decay)
    └── error/success (special transitions)
```

### 2.3 Visual Features

#### 2.3.1 Volumetric Glow (Shader)
```glsl
// Fragment shader: additive glow with exponential falloff
vec3 glow = glowColor * exp(-distance(gl_PointCoord, vec2(0.5)) * glowSharpness);
gl_FragColor = vec4(glow, glowAlpha);
```
- Layers: 3 glow spheres at different scales (0.5x, 1x, 2x radius)
- Color: mode-dependent (cyan → teal → violet → white)
- Intensity: `0.3 + 0.7 * audioLevel + 0.4 * modeIntensity`

#### 2.3.2 Node Field (InstancedMesh)
- 78 nodes rendered as instanced spheres (for perf)
- Custom shader: depth-based fade + node highlight
- Links: dynamic line segments, depth-sorted
- Interaction: hover highlights nearest node + links

#### 2.3.3 Energy Rings (3 rings)
- Ring 1 (inner): thin, fast rotation, cyan
- Ring 2 (middle): medium, opposite rotation, teal
- Ring 3 (outer): thick, slow, violet
- All scale with `audioLevel` and mode intensity

#### 2.3.4 Holographic Sweep
- 75° arc with gradient: transparent → cyan → transparent
- Rotates continuously, speeds up on activity
- Mode-specific color shifts
- Subtle distortion (sinusoidal wobble)

#### 2.3.5 Particle Orbit
- 16 particles as PointCloud
- Elliptical orbit paths (3 different planes)
- Size varies by audio band (high band = bigger)
- Color: white core, cyan edge, alpha fades by depth

#### 2.3.6 Audio Reactivity
- Web Audio API: `AnalyserNode` → FFT
- `frequencyBands = {low: 0.2-150Hz, mid: 150-4000Hz, high: 4000-20000Hz}`
- Smooth decay: `alpha *= 0.88` per frame
- FFT rings: 24 segments per band, height = bandValue × maxHeight
- Mic level → pulse intensity + color saturation

### 2.4 Post-Processing Effects
| Effect | Params | Usage |
|--------|--------|-------|
| Bloom | strength=1.5, radius=0.7, threshold=0.3 | Always on, subtle |
| FXAA | normal material | Anti-aliasing |
| Chromatic Aberration | offset=0.002 | Active modes only |
| Vignette | offset=0.7, darkness=0.4 | Always on |
| Film Grain | intensity=0.02 | Mica texture |

### 2.5 Event System
```javascript
// Listen to Python OrbBridge events
window.addEventListener('message', (event) => {
    const data = event.data;
    if (data.type === 'orb-state') {
        visualizer.setContextState(data.state);
    } else if (data.type === 'orb-audio') {
        visualizer.setAudioLevel(data.level, data.bands);
    } else if (data.type === 'orb-pulse') {
        visualizer.triggerPulse();
    }
});
```

### 2.6 Control Panel Upgrade
Current HTML panel gets a full redesign:
- **Glass morphism panel** (frosted glass, cyan border)
- **Animated tabs** (mode select, audio, controls)
- **Real-time FFT visualization** (bar chart, audio-reactive)
- **State indicator** with color-coded status badge
- **Model selector** with dropdown animation
- **API key field** with eye toggle (show/hide)
- **Microphone button** with ripple effect + recording indicator

---

## 3. WELCOME SCREEN (New File: astra_ui/widgets/welcome.py)

### 3.1 Concept
Full-screen holographic welcome after login:
- 3D rotating ASTRA logo (extruded geometry)
- Particle stream forming "WELCOME" text
- Progress bar with micro-interactions
- Quick stats overlay (model count, memory size)

### 3.2 Animation Sequence
1. **0-500ms**: Black fade-in, starfield appears
2. **500-1200ms**: Particle stream forms "ASTRA" (typewriter + physics)
3. **1200-2000ms**: 3D logo rises from center, orb orbits around it
4. **2000-3000ms**: Quick stats slide in from edges
5. **3000ms**: Click to continue (pulsing button)

### 3.3 Components
```python
class WelcomeScreen(QWidget):
    def __init__(self):
        self.logo_3d      # Custom paint: extruded text
        self.particle_stream # QTimer + QPainter
        self.orbit_orb    # Small OrbVisualizer
        self.stats_cards  # Quick stats (model, memory, version)
        self.progress_bar # Animated with QProgress
```

---

## 4. DASHBOARD / WORKSPACE UPGRADE

### 4.1 New Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
  ┌───────────────────────────────────────────────────────────┐
  │ [Orb]  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
  │        │  Metric 1   │  │  Metric 2   │  │  Metric 3   │ │
  │        │  (Model)    │  │  (Tokens)   │  │  (Uptime)   │ │
  │        └─────────────┘  └─────────────┘  └─────────────┘ │
  └───────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ ┌─────────────────┐ ┌─────────────────────────────────────┐ │
│ │ Activity Feed   │ │ Usage Over Time Chart               │ │
│ │ (live log)      │ │ (Chart.js in QWebEngine)            │ │
│ │                 │ │                                     │ │
│ └─────────────────┘ └─────────────────────────────────────┘ │
│ ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│ │ Quick Prompts   │ │ Memory       │ │ System Health    │ │
│ │ (glass buttons) │ │ Management   │ │ (CPU, RAM, Disk) │ │
│ └─────────────────┘ └──────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
  Footer: Local Agent / Ollama / Voice / Clock
```

### 4.2 New UI Components

#### 4.2.1 Floating Action Button (FAB)
```python
class FAB(QWidget):
    # Circular floating button with glow ripple effect
    # Position: bottom-right, 24px margin
    # Animations: pulse when action available, scale on hover
```

#### 4.2.2 Animated Toggle Switch
```python
class AnimatedToggle(QCheckBox):
    # Custom paint: sliding knob with glow trail
    # States: off (gray), on (cyan)
    # Transition: 200ms, OutCubic
```

#### 4.2.3 Circular Progress Indicator
```python
class CircularProgress(QWidget):
    # Orbital ring with trailing segments
    # Animated sweep + numeric percentage
    # Used for model loading, voice warmup
```

#### 4.2.4 Data Grid (Memory Table)
```python
class MemoryGrid(QTableWidget):
    # Glass header, row hover glow
    # Pin/star column with icon
    # Inline edit with fade-in editor
    # Delete with row collapse animation
```

---

## 5. CHARTS & METRICS UI (Upgrade metrics integration)

### 5.1 Chart Types (using embedded QWebEngine + Chart.js)

| Chart | Data Source | Update Interval | Visual Style |
|-------|-------------|-----------------|--------------|
| Usage Over Time | `metrics.collector` events | Real-time (1s) | Line, cyan gradient fill |
| Token Consumption | `metrics.collector` tokens | Per request | Area, teal |
| Session Duration | `metrics.collector` duration | Per session end | Bar, amber |
| Cache Hit Ratio | `metrics.collector` cache | Per request | Doughnut, violet/green |
| Storage Growth | `storage.manager` | On change | Doughnut, cyan/amber |
| Ops Distribution | Live tally | Real-time | Pie, multi-color |

### 5.2 Chart.js Config (Glass Style)
```javascript
{
    type: 'line',
    data: {
        datasets: [{
            borderColor: 'rgba(95, 235, 255, 0.9)',
            backgroundColor: 'rgba(95, 235, 255, 0.08)',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.4,
            fill: true,
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.03)' } },
            y: { grid: { color: 'rgba(255,255,255,0.03)' } },
        },
        plugins: {
            legend: { labels: { color: '#9dc3da' } },
        }
    }
}
```

### 5.3 Embedded WebView Container
```python
class ChartContainer(QFrame):
    """
    Glass-framed web view for Chart.js rendering.
    """
    def __init__(self):
        self.web_view = QWebEngineView()
        self.web_view.setContextMenuPolicy(Qt.NoContextMenu)
        # Load chart HTML template
        # Transparent background
        # Inject CSS for glass theme
```

---

## 6. MEMORY MANAGEMENT UI (Brain/memory_store.py integration)

### 6.1 Current State
- `AstraWindow._build_memory_page` exists with tabs
- Has: profile editor, records list, pin/delete/clear
- Needs visual upgrade

### 6.2 Upgrade Plan

#### 6.2.1 Profile Tab
- **Memory path display**: glass chip with copy button (copied → pulse green)
- **Editor**: enhanced Transcript with syntax highlighting (categories)
  - `◆ semantic` — blue tags
  - `◆ episodic` — green tags
  - `◆ preference` — purple tags
  - `◆ instruction` — amber tags
- **Actions**: Reload + Save buttons with hover glow
- **Stats bar**: Word count, category breakdown (mini pie chart)

#### 6.2.2 Records Tab
- **Filter bar**: search + category filter dropdowns (glass inputs)
- **Records grid**: 
  - Pinned records float to top with ★
  - Importance slider (0–10, interactive)
  - Timestamp column (human-readable)
  - Category badge (colored chips)
  - Action buttons per row: Pin, Edit, Delete (with confirmation modal)
- **Empty state**: animated "No memories yet" with floating particles

#### 6.2.3 Memory Visualization (NEW)
- **Knowledge graph view**: Force-directed graph of memory connections
  - Nodes = memories, edges = connections
  - Interactive: hover → highlight connected
  - Click → detail panel
  - Physics simulation (d3.js in webview or custom QPainter)
- **Timeline view**: Horizontal timeline of memory creation
  - Scrollable, zoomable
  - Click events on timeline points

#### 6.2.4 Memory Actions Panel
```
┌─────────────────────────────────────┐
│  Memory Overview                    │
├─────────────────────────────────────┤
│  Total Records:  24                │
│  Pinned:          4                 │
│  Semantic:        18                │
│  Episodic:        6                 │
├─────────────────────────────────────┤
│  [Pin Selected] [Delete] [Export]   │
└─────────────────────────────────────┘
```

---

## 7. USAGE STATS & TIME UI

### 7.1 Time Operations Widget (Time_Operations/brain.py)

#### 7.1.1 Pomodoro Timer
```python
class PomodoroTimer(QWidget):
    # Circular progress visualization
    # States: Ready → Work → Break → Work → ...
    # Sound on transition
    # Auto-start toggle
    # Customizable durations (25/5/15 default)
```

#### 7.1.2 Clock Face (Circular)
```python
class CircularClock(QWidget):
    # Analog-style with digital overlay
    # Second hand with smooth sweep
    # Hour markers as glowing dots
    # Date in center (day + date)
    # Timezone support (click to cycle)
```

#### 7.1.3 Usage Stats Dashboard
```python
class UsageStatsWidget(QWidget):
    # Daily/weekly/monthly usage
    # Heatmap calendar (clickable days)
    # Top tools used (bar chart)
    # Average response time (gauge)
    # CPU/memory usage trends
```

### 7.2 Data Integration Points
```python
class MetricsDashboard(AstraWindow mixin):
    # Integrates with:
    # 1. metrics/collector.py → real-time events
    # 2. metrics/charts.py → chart specs
    # 3. jarvis_runtime.py → runtime stats
    # 4. Brain/memory_store.py → memory stats
```

---

## 8. INTERACTION ANIMATION SYSTEM

### 8.1 Animation Engine
```python
class AnimationEngine:
    """
    Centralized animation orchestrator.
    All UI animations go through here for consistency.
    """
    timings = {
        "micro":    80,    # Button press, toggle
        "fast":    180,    # Card hover, input focus
        "medium":  260,    # Page transition, panel open
        "slow":    400,    # Mode transition, orb state change
        "entrance": 800,    # Window open, welcome
    }
    easings = {
        "standard": QEasingCurve.OutCubic,
        "emphasized": QEasingCurve.OutQuart,
        "standard_decel": QEasingCurve.OutCubic,
        "standard_accel": QEasingCurve.OutCubicD
    }
```

### 8.2 Hover Effects Catalog
| Element | Hover Effect | Intensity |
|---------|-------------|-----------|
| Card | Border glow + bg lift | 0.32 → 0.65 |
| Button | Gradient shift + lift | 0 → 4px |
| Nav item | Text glow + bg tint | 0.22 → 0.4 |
| Orb | Parallax tilt + breath | ±3% scale |
| Input | Border glow + pulse | 0.22 → 0.6 |
| Toggle | Knob slide + glow trail | 0 → 12px |
| FAB | Pulse + scale | +8%, glow |

### 8.3 State Transitions
| State | Enter Effect | Exist Effect |
|-------|-------------|-------------|
| Listening | Orb: rings fast + sweep bright | Orb: rings slow + sweep dim |
| Thinking | Node field intensifies | Node field calms |
| Executing | Tool activity overlay + color shift | Tool activity fades |
| Speaking | Breathing sync + core pulse | Breathing calm |
| Error | Red flash + shake | Red fade |
| Success | Green pulse ring + particles burst | Calm green |
| Booting | Gradual intensity ramp | Sharp settle |

### 8.4 Micro-interactions
- **Input focus**: Border glow expands (0 → 2px)
- **Button click**: Scale to 0.95 + ripple (QGraphicsEffect)
- **Toggle**: Knob slides + color transition
- **Card open**: Staggered element fade (120ms delay each)
- **List item hover**: Row bg lift + accent border
- **Progress**: Animated fill with easing
- **Status dot**: Pulse (scale + opacity)

---

## 9. REVOLUTIONARY UI ELEMENTS (Never-seen-before)

### 9.1 Holographic Depth Parallax
- Mouse movement causes **multi-layer parallax** on ALL panels
- Front panel moves 100%, mid 70%, back 40%
- Creates 3D "floating layers" effect
- **Performance**: throttled to 20ms (50fps) via requestAnimationFrame

### 9.2 Neural Path Visualization
- Between orb and chat: subtle animated lines (like neurons firing)
- Trigger: on tool execution, message send
- Color: cyan → teal (data flow effect)

### 9.3 Audio Waveform Background
- Subtle waveform of room audio in background canvas
- Behind sidebar, very low opacity (0.03)
- Peaks on voice input

### 9.4 Context-Aware Orb Reflection
- Orb reflects the active panel's content
- Render active panel to offscreen, blur, apply to orb's base
- Very low performance impact (static image cache)

### 9.5 Dynamic Theme Shift
- Theme subtly shifts based on time of day
  - 06:00-12:00: Morning cyan (brighter)
  - 12:00-18:00: Midday (neutral)
  - 18:00-24:00: Evening violet (warmer)
  - 00:00-06:00: Night dim (lowest intensity)
- **Transition**: 2000ms crossfade between palettes

### 9.6 Voice Activity Heatmap
- In the Voice Interface page
- Shows audio level over last 60 seconds
- Color: green → yellow → red
- Click to see detailed waveform

### 9.7 Command Palette (Ctrl+K)
```python
class CommandPalette(QDialog):
    # Spotlight-style search
    # Categories: Actions, Tools, Navigation, Settings
    # Recent commands at top
    # Keyboard navigation (Ctrl+K to open)
    # Glass morphism background
```

### 9.8 Interactive Tutorial Overlay
- First-time user walkthrough
- Highlights key UI elements
- Interactive: click to proceed
- "Don't show again" option

---

## 10. IMPLEMENTATION PRIORITIES

### Phase 1: Foundation (Critical)
| Task | File | Est. Time |
|------|------|-----------|
| Create `public/orb.js` | New file | 2h |
| Create `astra_ui/widgets/welcome.py` | New file | 1h |
| Create `astra_ui/widgets/animations.py` | New file | 1h |
| Create `astra_ui/widgets/charts.py` | New file | 1.5h |
| Create `astra_ui/widgets/fab.py` | New file | 0.5h |
| Create `astra_ui/widgets/toggle.py` | New file | 0.5h |
| Update `Security/login_ui.py` | Edit | 1.5h |
| Update `ui.py` to include new components | Edit | 1h |

### Phase 2: Visual Enhancements (High)
| Task | File | Est. Time |
|------|------|-----------|
| Add 15 more SVG icons | assets/icons/ | 1h |
| Create noise textures (4x4, 8x8) | assets/textures/ | 0.5h |
| Add starfield background | astra_ui/widgets/background.py | 1h |
| Add parallax layers | astra_ui/widgets/parallax.py | 1h |

### Phase 3: Charts & Metrics (Medium)
| Task | File | Est. Time |
|------|------|-----------|
| Embed Chart.js in QML | astra_ui/widgets/charts.py | 1.5h |
| Create heatmap calendar | astra_ui/widgets/heatmap.py | 1h |
| Create circular progress | astra_ui/widgets/circular_progress.py | 1h |

### Phase 4: Revolutionary Elements (Bonus)
| Task | File | Est. Time |
|------|------|-----------|
| Neural path visualization | astra_ui/widgets/neural_path.py | 1.5h |
| Context-aware reflection | astra_ui/widgets/reflection.py | 1h |
| Command palette | astra_ui/widgets/command_palette.py | 1.5h |
| Dynamic theme shift | astra_ui/core/theme.py | 0.5h |

---

## 11. Technical Stack Decisions

| Feature | Technology | Reason |
|---------|-----------|--------|
| Orb visualizer | Three.js r158+ | Best WebGL performance |
| Charts | Chart.js 4.x | Lightweight, glass-compatible |
| 3D models | Three.js + custom shaders | No external assets needed |
| Icons | Inline SVG with QSvgRenderer | Sharp at any size |
| Animations | QPropertyAnimation + QEasingCurve | Qt5 native, smooth |
| Parallax | mouseMoveEvent + QTimer | Low overhead |
| Noise texture | 4×4 PNG canvas blend | Cheap, effective |
| State machine | Custom Python class | Full control |
| Audio analysis | Web Audio API (Web) + Vosk (Python) | Both supported |

---

## 12. Performance Budget
| Target | Metric |
|--------|--------|
| FPS | 60fps (desktop), 30fps (web orb) |
| Memory | <200MB baseline |
| GPU | Moderate (WebGL orb only) |
| CPU | <5% idle (orb animation, QTimer 40ms) |
| Paint ops | <3ms per frame (orb), <0.5ms (UI) |
| Animations | Disable on <50% battery |

---

## 13. Deliverables Checklist

### Files to Create
- [ ] `public/orb.js` — Full WebGL OrbVisualizer
- [ ] `astra_ui/widgets/welcome.py` — Welcome screen
- [ ] `astra_ui/widgets/animations.py` — Animation engine
- [ ] `astra_ui/widgets/charts.py` — Chart containers (QWebEngine)
- [ ] `astra_ui/widgets/fab.py` — Floating Action Button
- [ ] `astra_ui/widgets/toggle.py` — Animated toggle switch
- [ ] `astra_ui/widgets/circular_progress.py` — Circular progress
- [ ] `astra_ui/widgets/background.py` — Starfield background
- [ ] `astra_ui/widgets/parallax.py` — Multi-layer parallax
- [ ] `astra_ui/widgets/neural_path.py` — Neural network visualization
- [ ] `astra_ui/widgets/command_palette.py` — Cmd+K palette
- [ ] `assets/icons/*.svg` — 15+ additional icons
- [ ] `assets/textures/noise-8x8.png` — Higher-res noise

### Files to Modify
- [ ] `Security/login_ui.py` — Add holographic effects
- [ ] `ui.py` — Integrate new components
- [ ] `public/index.html` — Connect to upgraded orb.js
- [ ] `metrics/charts.py` — Add glass-themed chart specs
- [ ] `astra_ui/core/theme.py` — Add time-based theme shifts

### Files Already Done
- [x] `ui/` package structure
- [x] `astra_ui/core/theme.py` — Glass QSS + colors
- [x] `astra_ui/widgets/orb.py` — OrbVisualizer (PyQt5)
- [x] `astra_ui/widgets/panels.py` — Card, MetricCard, HealthRow
- [x] `astra_ui/widgets/icons.py` — SVG icon loader
- [x] `astra_ui/assets.py` — Font/textures loader
- [x] `DESIGN_PLAN.md` — Original design plan

---

*Plan v1.0 — Cinematic. Revolutionary. Đẹp như mơ.*