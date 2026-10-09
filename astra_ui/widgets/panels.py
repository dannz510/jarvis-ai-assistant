"""
Glass-style card and panel components for ASTRA Nebula UI.
"""

from typing import Optional
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget,
    QStyle,
)
from PyQt5.QtGui import QFont, QFontDatabase, QPainter

from ..core.theme import COLORS


class GlassMixin:
    """Mixin that adds frosted-glass styling helpers to widgets."""

    def apply_glass(self, accent: str = "cyan", hover: bool = True):
        self.setProperty("accent", accent)
        self.setProperty("class", "glass-card")
        if hover:
            self.setProperty("hover", "true")


class Card(QFrame):
    """Glass-style container card with optional eyebrow title."""

    def __init__(self, title: str = "", eyebrow: Optional[str] = None,
                 parent: Optional[QWidget] = None, accent: str = "cyan"):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("accent", accent)
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(18, 16, 18, 16)
        self.content.setSpacing(10)

        if eyebrow:
            sub = QLabel(eyebrow.upper())
            sub.setObjectName("Eyebrow")
            self.content.addWidget(sub)

        if title:
            heading = QLabel(title)
            heading.setObjectName("CardTitle")
            self.content.addWidget(heading)

    def set_accent(self, accent: str):
        self.setProperty("accent", accent)
        self.style().unpolish(self)
        self.style().polish(self)


class MetricCard(Card):
    """Compact metric display with value + detail label."""

    def __init__(self, title: str, value: str, detail: str = "",
                 accent: str = "cyan", parent: Optional[QWidget] = None):
        super().__init__(title, parent=parent, accent=accent)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.content.addWidget(self.value_label)

        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("Muted")
        self.content.addWidget(self.detail_label)

    def update_value(self, value: str):
        self.value_label.setText(value)

    def update_detail(self, detail: str):
        self.detail_label.setText(detail)


class HealthRow(QWidget):
    """Health/health-status row with icon + title + detail."""

    def __init__(self, icon_enum, title: str, detail: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.detail_label: QLabel
        line = QHBoxLayout(self)
        line.setContentsMargins(0, 4, 0, 4)
        line.setSpacing(10)

        glyph = QLabel()
        glyph.setPixmap(self.style().standardIcon(icon_enum).pixmap(QSize(18, 18)))
        glyph.setObjectName("HealthGlyph")
        line.addWidget(glyph)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        heading = QLabel(title)
        heading.setObjectName("BodyText")
        sub = QLabel(detail)
        sub.setObjectName("Muted")
        sub.setWordWrap(True)
        copy.addWidget(heading)
        copy.addWidget(sub)
        line.addLayout(copy, 1)

        self.detail_label = sub


__all__ = ["Card", "MetricCard", "HealthRow", "GlassMixin"]