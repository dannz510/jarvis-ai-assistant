"""
Icon helper for ASTRA Nebula UI.
Provides SVG-based icon loading with accent color recoloring.
"""

import os
from typing import Optional

from PyQt5.QtCore import QSize, Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPixmap, QIcon
from PyQt5.QtSvg import QSvgRenderer

ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "assets",
    "icons",
)


def load_icon(name: str, color: Optional[str] = None,
              size: int = 24) -> QIcon:
    """
    Load an SVG icon from assets/icons/.
    If color is given, recolor the SVG's fills with that color.
    """
    path = os.path.join(ICONS_DIR, f"{name}.svg")
    if not os.path.isfile(path):
        # Fallback: return empty
        return QIcon()

    if color:
        return _recolor_svg_icon(path, color, size)

    return QIcon(path)


def _recolor_svg_icon(svg_path: str, color: str, size: int) -> QIcon:
    """Render SVG to pixmap with recolored strokes."""
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Render with desired color by adjusting fills
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    # Tint
    tint = QPixmap(pixmap)
    tp = QPainter(tint)
    tp.setCompositionMode(QPainter.CompositionMode_SourceIn)
    tp.fillRect(tint.rect(), QColor(color))
    tp.end()

    return QIcon(tint)


def icon_pixmap(name: str, color: str = "#4df4ff", size: int = 24) -> QPixmap:
    """Get a recolored QPixmap for the given icon name."""
    icon = load_icon(name, color, size)
    return icon.pixmap(QSize(size, size))


# Common icon map (for documentation / autocomplete)
ICON_MAP = {
    "mic": "mic.svg",
    "mic-off": "mic-off.svg",
    "send": "send.svg",
    "brain": "brain.svg",
    "visualizer": "visualizer.svg",
    "settings": "settings.svg",
    "terminal": "terminal.svg",
    "shield": "shield.svg",
    "spark": "spark.svg",
    "audio": "audio.svg",
    "model": "model.svg",
    "agent": "agent.svg",
    "memory": "memory.svg",
    "tool": "tool.svg",
    "folder": "folder.svg",
    "file": "file.svg",
    "refresh": "refresh.svg",
    "delete": "delete.svg",
    "save": "save.svg",
    "eye": "eye.svg",
    "eye-off": "eye-off.svg",
    "plus": "plus.svg",
    "minus": "minus.svg",
    "check": "check.svg",
    "close": "close.svg",
    "warning": "warning.svg",
    "error": "error.svg",
    "success": "success.svg",
    "info": "info.svg",
    "chevron-down": "chevron-down.svg",
    "chevron-up": "chevron-up.svg",
    "chevron-left": "chevron-left.svg",
    "chevron-right": "chevron-right.svg",
}


__all__ = ["load_icon", "icon_pixmap", "ICON_MAP"]