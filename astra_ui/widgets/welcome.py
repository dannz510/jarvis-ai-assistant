"""
ASTRA Nebula — Welcome Screen.
Full-screen holographic welcome with 3D logo + particle animation.
"""

import math
import random
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QFont, QFontDatabase
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class Starfield(QWidget):
    """Animated starfield background."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setMouseTracking(True)
        self.stars = []
        for _ in range(120):
            self.stars.append({
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "z": random.uniform(0.1, 1.0),
                "twinkle": random.uniform(0, math.tau),
                "size": random.uniform(0.3, 1.4),
            })
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        for star in self.stars:
            star["twinkle"] += 0.015
            star["z"] -= 0.001
            if star["z"] <= 0:
                star["z"] = 1.0
                star["x"] = random.uniform(0, 1)
                star["y"] = random.uniform(0, 1)

            sx = star["x"] * w
            sy = star["y"] * h
            depth = 1.0 - star["z"]
            brightness = depth * 0.8 + 0.2
            alpha = int(brightness * 180 * (0.5 + 0.5 * math.sin(star["twinkle"])))
            size = star["size"] * depth * 2 + 0.5

            p.setPen(Qt.NoPen)
            p.setBrush(QColor(95, 235, 255, max(0, alpha)))
            p.drawEllipse(QPointF(sx, sy), size, size)


class ParticleStream(QWidget):
    """Animated particle stream that forms text."""

    def __init__(self, target_text="ASTRA"):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.target_text = target_text
        self.particles = []
        self.phase = 0.0
        self._spawn_particles()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _spawn_particles(self):
        for i, char in enumerate(self.target_text):
            for _ in range(30):
                self.particles.append({
                    "char": char,
                    "x": random.uniform(-50, 50),
                    "y": random.uniform(-20, 20),
                    "target_x": i * 32 - (len(self.target_text) * 16),
                    "target_y": 0,
                    "vx": random.uniform(-0.3, 0.3),
                    "vy": random.uniform(-0.2, 0.2),
                    "progress": random.uniform(0, 1),
                    "size": random.uniform(12, 18),
                })

    def _tick(self):
        self.phase += 0.02
        for p in self.particles:
            if p["progress"] < 1.0:
                p["progress"] += 0.008 + random.uniform(0, 0.004)
            else:
                p["progress"] = 1.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        font = QFont("Exo 2", 16, QFont.Bold)
        p.setFont(font)

        for particle in self.particles:
            x = cx + particle["x"] + (particle["target_x"] - particle["x"]) * particle["progress"]
            y = cy + particle["y"] + (particle["target_y"] - particle["y"]) * particle["progress"]
            alpha = int(255 * particle["progress"])
            color = QColor(95, 235, 255, alpha)
            p.setPen(color)
            p.drawText(int(x), int(y), particle["char"])


class WelcomeScreen(QWidget):
    """
    Full-screen welcome screen with holographic effects.
    Fires `welcome_complete` signal when user clicks to continue.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Starfield background (full screen, behind everything)
        self.starfield = Starfield()
        layout.addWidget(self.starfield)

        # Main content overlay
        overlay = QHBoxLayout()
        overlay.addStretch(1)
        overlay_container = QVBoxLayout()
        overlay_container.setSpacing(24)

        # Logo / Orb
        self.logo_label = QLabel()
        self.logo_label.setText("◉ ASTRA")
        self.logo_label.setStyleSheet("""
            QLabel {
                color: #4df4ff;
                font-family: "Exo 2", "Outfit", sans-serif;
                font-size: 48px;
                font-weight: 700;
                letter-spacing: 4px;
                text-shadow: 0 0 20px rgba(95, 235, 255, 0.5);
            }
        """)
        self.logo_label.setAlignment(Qt.AlignCenter)
        overlay_container.addWidget(self.logo_label)

        # Subtitle
        self.subtitle = QLabel("NEURAL ASSISTANT · LOCAL FIRST")
        self.subtitle.setStyleSheet("""
            QLabel {
                color: #9dc3da;
                font-family: "Oxanium", "Outfit", sans-serif;
                font-size: 14px;
                letter-spacing: 2px;
                text-transform: uppercase;
            }
        """)
        self.subtitle.setAlignment(Qt.AlignCenter)
        overlay_container.addWidget(self.subtitle)

        # Quick stats
        stats = QHBoxLayout()
        stats.setSpacing(20)
        self._add_stat(stats, "MODEL", "phi3-mini")
        self._add_stat(stats, "RUNTIME", "Ollama")
        self._add_stat(stats, "VOICE", "Offline")
        overlay_container.addLayout(stats)

        # Progress bar
        self.progress_bar = self._create_progress_bar()
        overlay_container.addWidget(self.progress_bar)

        # Click to continue
        self.continue_btn = QPushButton("↵ ENTER THE NEXUS")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f9fc5, stop:1 #0a7fa3);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-family: "Oxanium", "Outfit", sans-serif;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #14b8e0, stop:1 #0d94bd);
                box-shadow: 0 0 20px rgba(95, 235, 255, 0.4);
            }
        """)
        overlay_container.addWidget(self.continue_btn)

        overlay.addStretch(1)

        layout.addLayout(overlay)

        # --- Particle stream (behind logo) ---
        self._particle_stream = ParticleStream("ASTRA")
        self._particle_stream.setGeometry(0, 0, self.width(), self.height())

        # --- Entrance animation ---
        self._animate_entrance()

    def _add_stat(self, parent, label, value):
        stat = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("QLabel { color: #6f93b3; font-size: 10px; font-family: 'Oxanium', sans-serif; }")
        lbl.setAlignment(Qt.AlignCenter)
        val = QLabel(value)
        val.setStyleSheet("QLabel { color: #4df4ff; font-size: 16px; font-weight: 600; font-family: 'Exo 2', sans-serif; }")
        val.setAlignment(Qt.AlignCenter)
        stat.addWidget(lbl)
        stat.addWidget(val)
        parent.addLayout(stat)

    def _create_progress_bar(self):
        progress = QWidget()
        progress.setFixedHeight(4)
        progress.setStyleSheet("""
            QWidget {
                background: rgba(95, 235, 255, 0.08);
                border-radius: 2px;
            }
        """)
        # Animated fill via child
        self._progress_fill = QWidget()
        self._progress_fill.setFixedHeight(4)
        self._progress_fill.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3df5d9, stop:1 #4df4ff);
                border-radius: 2px;
            }
        """)

        bar_layout = QHBoxLayout(progress)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)
        bar_layout.addWidget(self._progress_fill)
        bar_layout.addStretch()

        self._progress_bar = progress
        self._progress_anim = QPropertyAnimation(self._progress_fill, b"maximumWidth")
        self._progress_anim.setDuration(3000)
        self._progress_anim.setStartValue(0)
        self._progress_anim.setEndValue(progress.width())
        self._progress_anim.setEasingCurve(QEasingCurve.OutCubic)

        return progress

    def _animate_entrance(self):
        """Full entrance animation sequence."""
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(800)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        fade.start()

        # Pulse the orb label
        pulse = QPropertyAnimation(self.logo_label, b"windowOpacity")
        # Use scale transform instead
        self.logo_label.setGraphicsEffect(None)

        # Start progress bar animation after delay
        QTimer.singleShot(500, self._progress_anim.start)

    def resizeEvent(self, event):
        if hasattr(self, "_particle_stream"):
            self._particle_stream.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)


# Alias for backward compatibility
StarfieldBg = Starfield
