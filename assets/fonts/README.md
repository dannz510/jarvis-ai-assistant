# ASTRA Fonts

Download and place the following font files here:

## UI Fonts (Essential)
- **Exo 2** — Headings, brand, metrics
  - Exo2-Regular.ttf, Exo2-Bold.ttf, Exo2-SemiBold.ttf
  - Download: https://fonts.google.com/specimen/Exo+2
- **Outfit** — General UI text, buttons, labels
  - Outfit-Regular.ttf, Outfit-Medium.ttf, Outfit-SemiBold.ttf
  - Download: https://fonts.google.com/specimen/Outfit
- **Oxanium** — Eyebrow text, status badges, tiny labels
  - Oxanium-Regular.ttf, Oxanium-Bold.ttf
  - Download: https://fonts.google.com/specimen/Oxanium
- **JetBrains Mono** — Logs, timestamps, monospace content
  - JetBrainsMono-Regular.ttf, JetBrainsMono-Medium.ttf
  - Download: https://www.jetbrains.com/lp/mono/
- **Inter** (optional) — Body text fallback
  - Inter-Regular.ttf, Inter-Medium.ttf
  - Download: https://rsms.me/inter/

## Installation
Place all .ttf/.otf files in this directory. They will be auto-loaded
by `ui/assets.py` via `QFontDatabase.addApplicationFont` when the app starts.

The QSS references fonts in this order:
- Headings: "Exo 2", "Outfit", "Segoe UI"
- UI text: "Outfit", "Segoe UI"
- Monospace: "JetBrains Mono", "Consolas"
- Eyebrow/Badge: "Oxanium", "Outfit", "Segoe UI"

## Auto-detection
On Windows, system fonts (Segoe UI) are auto-registered.
On macOS/Linux, system fonts are used as fallbacks automatically.