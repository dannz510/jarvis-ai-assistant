"""
Login UI with biometric authentication — ASTRA Nebula Edition.
SPA-style with glass-morphism, holographic animations, and biometric flows.
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup, QPauseAnimation, QSize, pyqtSignal,
)
from PyQt5.QtGui import (
    QFont, QFontDatabase, QPalette, QColor,
    QPixmap, QMovie, QPainter, QLinearGradient, QBrush,
    QFontMetrics,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QStackedWidget,
    QGraphicsOpacityEffect, QMessageBox, QCheckBox, QStyle,
)

from Security.auth_manager import AuthManager, AuthMethod, AuthenticationResult, AuthStatus
from Security.secure_storage import SecureStorage


class StarfieldBg(QWidget):
    """Subtle animated starfield for login background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.stars = [
            {"x": i * 17 % 1000, "y": i * 31 % 700, "s": (i % 3 + 1) * 0.5}
            for i in range(80)
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(50)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for star in self.stars:
            star["s"] += 0.005 * (0.5 - star.get("d", 0.5))
            star["d"] = (star["s"] % 1.0)
            alpha = int(20 + 15 * star["d"])
            size = star["d"] * 2 + 0.3
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(95, 235, 255, alpha))
            p.drawEllipse(int(star["x"]), int(star["y"]), int(size), int(size))


class GlassContainer(QFrame):
    """Frosted glass container for login forms."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("container")
        self.setStyleSheet("""
            QFrame#container {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(12, 26, 40, 0.78),
                    stop:1 rgba(6, 16, 28, 0.65));
                border: 1px solid rgba(95, 235, 255, 0.3);
                border-radius: 16px;
                padding: 32px;
            }
        """)


class PINPad(QFrame):
    """Circular PIN entry pad with ripple animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pinPad")
        self.digits = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        for row in range(4):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            for col in range(3):
                btn = QPushButton()
                digit = row * 3 + col + 1
                if digit <= 9:
                    btn.setText(str(digit))
                elif row == 3 and col == 0:
                    btn.setText("⌫")
                elif row == 3 and col == 1:
                    btn.setText("🔓")
                elif row == 3 and col == 2:
                    btn.setVisible(False)
                else:
                    btn.setVisible(False)

                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(14, 32, 52, 0.82);
                        color: #e8f7ff;
                        border: 1px solid rgba(95, 235, 255, 0.22);
                        border-radius: 12px;
                        font-size: 18px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background: rgba(18, 40, 64, 0.92);
                        border-color: rgba(95, 235, 255, 0.45);
                        box-shadow: 0 0 12px rgba(95, 235, 255, 0.15);
                    }
                    QPushButton:pressed {
                        background: rgba(10, 26, 41, 0.95);
                    }
                """)
                btn.setFixedSize(48, 48)
                btn.clicked.connect(lambda _, d=digit: self._on_digit(d))
                row_layout.addWidget(btn)
                self.digits.append(btn)
            layout.addLayout(row_layout)

    def _on_digit(self, digit):
        pass  # Connect to PIN input logic


class BiometricOverlay(QWidget):
    """
    Overlay for biometric scanning with holographic circle sweep.
    Used during face recognition and fingerprint scanning.
    """

    def __init__(self, parent=None, mode="face"):
        super().__init__(parent)
        self.mode = mode
        self.phase = 0.0
        self.scan_progress = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self.update)
        self._tick_timer.start(33)

    def _tick(self):
        self.phase += 0.02
        if self.scan_progress < 1.0:
            self.scan_progress += 0.003 + 0.002 * abs(__import__("math").sin(self.phase * 0.5))
        self.update()

    def set_progress(self, value: float):
        self.scan_progress = max(0, min(1, value))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        import math as m

        if self.mode == "face":
            # Face scanning: concentric circles + sweep
            circle_r = min(w, h) * 0.35
            sweep_angle = self.phase * 2

            # Outer glow rings
            for i, scale in enumerate([1.3, 1.15, 1.0]):
                alpha = int(60 * (1 - i * 0.3) * self.scan_progress)
                p.setPen(m for m in [None])  # placeholder
                gradient = QLinearGradient(cx - circle_r * scale, cy, cx + circle_r * scale, cy)
                gradient.setColorAt(0, QColor(61, 245, 217, 0))
                gradient.setColorAt(0.5, QColor(61, 245, 217, alpha))
                gradient.setColorAt(1, QColor(61, 245, 217, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(gradient)
                p.drawEllipse(
                    int(cx - circle_r * scale), int(cy - circle_r * scale),
                    int(circle_r * 2 * scale), int(circle_r * 2 * scale),
                )

            # Sweep line
            p.save()
            p.translate(cx, cy)
            p.rotate(sweep_angle)
            p.translate(-cx, -cy)
            sweep_gradient = QLinearGradient(cx, cy, cx + circle_r * 1.1, cy)
            sweep_gradient.setColorAt(0, QColor(61, 245, 217, int(120 * self.scan_progress)))
            sweep_gradient.setColorAt(1, QColor(61, 245, 217, 0))
            p.setPen(QPen(sweep_gradient, 2))
            p.drawLine(cx, cy, cx + circle_r * 1.1, cy)
            p.restore()

            # Camera frame indicator
            frame_r = min(w, h) * 0.28
            p.setPen(QPen(QColor(61, 245, 217, int(200 * self.scan_progress)), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(
                int(cx - frame_r), int(cy - frame_r),
                int(frame_r * 2), int(frame_r * 2),
            )

            # Corner markers
            corner_size = 20
            offset = 8
            corners = [
                (cx - frame_r + offset, cy - frame_r + offset, 1, 0),
                (cx + frame_r - offset - corner_size, cy - frame_r + offset, -1, 0),
                (cx - frame_r + offset, cy + frame_r - offset - corner_size, 1, 0),
                (cx + frame_r - offset - corner_size, cy + frame_r - offset - corner_size, -1, 0),
            ]
            for x, y, dx, _ in corners:
                p.drawLine(int(x), int(y), int(x + corner_size * dx), int(y))
                p.drawLine(int(x), int(y), int(x), int(y + corner_size))

            # Status text
            if self.scan_progress >= 0.3:
                p.setPen(QColor(61, 245, 217, int(255 * self.scan_progress)))
                p.setFont(QFont("Oxanium", 11, QFont.Bold))
                status_text = "SCANNING FACE" if self.scan_progress < 0.8 else "VERIFIED"
                metrics = QFontMetrics(p.font())
                text_w = metrics.horizontalAdvance(status_text)
                p.drawText(int(cx - text_w / 2), int(cy + frame_r + 30), status_text)

        elif self.mode == "fingerprint":
            # Fingerprint scanning: dot-matrix + expanding ring
            sensor_r = 50
            ring_r = sensor_r + (sensor_r * 1.5 * self.scan_progress)

            # Outer expanding ring
            p.setPen(QPen(QColor(61, 245, 217, int(150 * (1 - self.scan_progress))), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(
                int(cx - ring_r), int(cy - ring_r),
                int(ring_r * 2), int(ring_r * 2),
            )

            # Sensor base
            sensor_gradient = QLinearGradient(cx - sensor_r, cy, cx + sensor_r, cy)
            sensor_gradient.setColorAt(0, QColor(10, 26, 41, 230))
            sensor_gradient.setColorAt(1, QColor(14, 32, 52, 230))
            p.setPen(Qt.NoPen)
            p.setBrush(sensor_gradient)
            p.drawEllipse(
                int(cx - sensor_r), int(cy - sensor_r),
                int(sensor_r * 2), int(sensor_r * 2),
            )

            # Dot matrix
            dot_radius = 2.5
            for angle in range(0, 360, 30):
                import math as m2
                for r in [sensor_r * 0.4, sensor_r * 0.7]:
                    dot_x = cx + r * m2.cos(m2.radians(angle))
                    dot_y = cy + r * m2.sin(m2.radians(angle))
                    dot_alpha = int(80 + 100 * self.scan_progress)
                    p.setBrush(QColor(61, 245, 217, dot_alpha))
                    p.drawEllipse(
                        int(dot_x - dot_radius), int(dot_y - dot_radius),
                        int(dot_radius * 2), int(dot_radius * 2),
                    )

            # Center dot (pulsing)
            center_size = dot_radius + 1 * math.sin(self.phase * 3) if hasattr(self, '_m') else dot_radius
            import math as m3
            pulse = 1 + 0.2 * m3.sin(self.phase * 4)
            p.setBrush(QColor(61, 245, 217, int(200 * self.scan_progress)))
            p.drawEllipse(
                int(cx - dot_radius * pulse), int(cy - dot_radius * pulse),
                int(dot_radius * 2 * pulse), int(dot_radius * 2 * pulse),
            )


class LoginWindow(QMainWindow):
    """SPA-style login window with holographic animations."""

    login_success = pyqtSignal(str)  # Emits session token

    def __init__(self, auth_manager: AuthManager):
        super().__init__()
        self.auth_manager = auth_manager
        self.setWindowTitle("ASTRA Nebula — Secure Authentication")
        self.setFixedSize(640, 800)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._apply_theme()

        self.current_step = "welcome"
        self._setup_ui()
        self._load_users()
        self._animate_entrance()

    def _apply_theme(self):
        """Apply the ASTRA Nebula dark glass theme."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #05070f, stop:0.7 #07111d, stop:1 #0a1624);
            }
        """)

    def _get_stylesheet(self):
        """Legacy method for backward compatibility."""
        return self.styleSheet() + """
        QLabel#logo {
            font-size: 48px;
            font-weight: bold;
            color: #4df4ff;
            letter-spacing: 3px;
            font-family: "Exo 2", "Outfit", sans-serif;
            text-shadow: 0 0 20px rgba(95, 235, 255, 0.4);
        }
        QLabel#subtitle {
            font-size: 12px;
            color: #9dc3da;
            letter-spacing: 2px;
            font-family: "Oxanium", sans-serif;
            text-transform: uppercase;
        }
        QLabel#welcomeText {
            font-size: 28px;
            color: #e8f7ff;
            font-weight: 600;
            font-family: "Exo 2", "Outfit", sans-serif;
        }
        QLabel#statusText {
            font-size: 14px;
            color: #9dc3da;
            font-family: "Outfit", sans-serif;
        }
        GlassContainer#container {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(12, 26, 40, 0.78),
                stop:1 rgba(6, 16, 28, 0.65));
            border: 1px solid rgba(95, 235, 255, 0.3);
            border-radius: 16px;
            padding: 32px;
        }
        QLineEdit {
            background: rgba(8, 20, 33, 0.96);
            color: #e7f4fb;
            border: 1px solid rgba(95, 235, 255, 0.22);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 14px;
        }
        QLineEdit:focus { border-color: rgba(95, 235, 255, 0.6); }
        QPushButton#primaryBtn {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0f9fc5, stop:1 #0a7fa3);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            padding: 12px 24px;
        }
        QPushButton#primaryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #14b8e0, stop:1 #0d94bd);
        }
        QPushButton#primaryBtn:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0a7fa3, stop:1 #086b8a);
        }
        QPushButton#secondaryBtn {
            background: rgba(255, 255, 255, 0.08);
            color: #e8f7ff;
            border: 1px solid rgba(95, 235, 255, 0.25);
            border-radius: 10px;
        }
        QPushButton#secondaryBtn:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(95, 235, 255, 0.5);
        }
        QPushButton#biometricBtn {
            background: rgba(61, 245, 217, 0.12);
            color: #3df5d9;
            border: 1px solid rgba(61, 245, 217, 0.45);
            border-radius: 10px;
        }
        QPushButton#biometricBtn:hover {
            background: rgba(61, 245, 217, 0.22);
        }
        QPushButton#navBtn {
            background: transparent;
            color: #9dc3da;
            border: none;
            font-size: 12px;
            font-family: "Outfit", sans-serif;
        }
        QPushButton#navBtn:hover { color: #3df5d9; }
        QLabel#faceIcon { font-size: 52px; }
        QLabel#fingerIcon { font-size: 52px; }
        QProgressBar {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            height: 6px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3df5d9, stop:1 #4df4ff);
            border-radius: 3px;
        }
        """

    def _setup_ui(self):
        # Background starfield
        bg = StarfieldBg()
        self.setCentralWidget(bg)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setAlignment(Qt.AlignCenter)
        # Central container
        main_container = QFrame()
        bg_layout.addWidget(main_container)
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            QFrame#mainContainer {
                background: transparent;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        main_container.setLayout(layout)

        # Logo section
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(8)
        self.logo_label = QLabel("◉ ASTRA")
        self.logo_label.setObjectName("logo")
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.subtitle = QLabel("NEURAL ASSISTANT | SECURE ACCESS")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)

        logo_layout.addWidget(self.logo_label)
        logo_layout.addWidget(self.subtitle)
        layout.addLayout(logo_layout)
        layout.addSpacing(24)

        # Glass container
        self.container = GlassContainer()
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(32, 32, 32, 32)
        container_layout.setSpacing(18)

        # Welcome label
        self.welcome_label = QLabel("WELCOME")
        self.welcome_label.setObjectName("welcomeText")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.welcome_label)

        # Status label
        self.status_label = QLabel("Choose your authentication method")
        self.status_label.setObjectName("statusText")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        container_layout.addWidget(self.stacked_widget)

        # --- Page 1: User Selection ---
        page1 = QWidget()
        page1_layout = QVBoxLayout()
        page1_layout.setContentsMargins(0, 0, 0, 0)
        page1_layout.setSpacing(12)
        self.user_btns_layout = QVBoxLayout()
        page1_layout.addLayout(self.user_btns_layout)

        self.new_user_btn = QPushButton("Register New User")
        self.new_user_btn.setObjectName("secondaryBtn")
        self.new_user_btn.clicked.connect(self._show_register_page)
        page1_layout.addWidget(self.new_user_btn)

        page1.setLayout(page1_layout)
        self.stacked_widget.addWidget(page1)

        # --- Page 2: Register ---
        page2 = QWidget()
        page2_layout = QVBoxLayout()
        page2_layout.setContentsMargins(0, 0, 0, 0)
        page2_layout.setSpacing(12)

        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Username")
        self.reg_display = QLineEdit()
        self.reg_display.setPlaceholderText("Display Name")
        self.reg_pin = QLineEdit()
        self.reg_pin.setPlaceholderText("PIN (min 6 digits)")
        self.reg_pin.setEchoMode(QLineEdit.Password)

        page2_layout.addWidget(self.reg_username)
        page2_layout.addWidget(self.reg_display)
        page2_layout.addWidget(self.reg_pin)

        reg_btn = QPushButton("Register")
        reg_btn.setObjectName("primaryBtn")
        reg_btn.clicked.connect(self._register_user)
        back_btn = QPushButton("Back")
        back_btn.setObjectName("secondaryBtn")
        back_btn.clicked.connect(self._show_user_select)
        page2_layout.addWidget(reg_btn)
        page2_layout.addWidget(back_btn)

        page2.setLayout(page2_layout)
        self.stacked_widget.addWidget(page2)

        # --- Page 3: Login Options ---
        page3 = QWidget()
        page3_layout = QVBoxLayout()
        page3_layout.setContentsMargins(0, 0, 0, 0)
        page3_layout.setSpacing(12)

        face_btn = QPushButton("Face Recognition")
        face_btn.setObjectName("biometricBtn")
        face_btn.clicked.connect(self._login_face)
        page3_layout.addWidget(face_btn)

        fp_btn = QPushButton("Fingerprint")
        fp_btn.setObjectName("biometricBtn")
        fp_btn.clicked.connect(self._login_fingerprint)
        page3_layout.addWidget(fp_btn)

        pin_btn = QPushButton("PIN Login")
        pin_btn.setObjectName("secondaryBtn")
        pin_btn.clicked.connect(self._login_pin_page)
        page3_layout.addWidget(pin_btn)

        back_btn2 = QPushButton("Back")
        back_btn2.setObjectName("secondaryBtn")
        back_btn2.clicked.connect(self._show_user_select)
        page3_layout.addWidget(back_btn2)

        page3.setLayout(page3_layout)
        self.stacked_widget.addWidget(page3)

        # --- Page 4: PIN Entry (with custom pad) ---
        page4 = QWidget()
        page4_layout = QVBoxLayout()
        page4_layout.setContentsMargins(0, 0, 0, 0)
        page4_layout.setSpacing(12)

        self.pin_display = QLabel("●●●●●●")
        self.pin_display.setAlignment(Qt.AlignCenter)
        self.pin_display.setStyleSheet("""
            QLabel {
                font-size: 24px;
                letter-spacing: 4px;
                color: #4df4ff;
                font-family: "Exo 2", monospace;
            }
        """)
        page4_layout.addWidget(self.pin_display)

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter PIN")
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.returnPressed.connect(self._login_pin)
        self.pin_input.setVisible(False)

        # Custom PIN pad
        self.pin_pad = PINPad()
        page4_layout.addWidget(self.pin_display)
        page4_layout.addWidget(self.pin_pad)

        pin_login_btn = QPushButton("Login")
        pin_login_btn.setObjectName("primaryBtn")
        pin_login_btn.clicked.connect(self._login_pin)
        back_btn3 = QPushButton("Back")
        back_btn3.setObjectName("secondaryBtn")
        back_btn3.clicked.connect(self._show_login_options)
        page4_layout.addWidget(pin_login_btn)
        page4_layout.addWidget(back_btn3)

        page4.setLayout(page4_layout)
        self.stacked_widget.addWidget(page4)

        layout.addWidget(self.container)
        layout.addStretch(1)

        # Footer
        footer = QLabel("LOCAL-FIRST CORE · PRIVATE  ·  SECURE  ·  OFFLINE")
        footer.setStyleSheet("color: #4a6b85; font-size: 10px; font-family: 'Oxanium', sans-serif; letter-spacing: 2px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    def _animate_entrance(self):
        """Enhanced entrance animation."""
        # Fade + scale
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)

        self._fade_anim = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_anim.setDuration(800)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

        # Logo glow pulse
        QTimer.singleShot(300, self._pulse_logo)

    def _pulse_logo(self):
        """Pulse the logo glow."""
        glow_anim = QPropertyAnimation(self.logo_label, b"windowOpacity")
        glow_anim.setDuration(1500)
        glow_anim.setStartValue(0.5)
        glow_anim.setEndValue(1.0)
        glow_anim.setLoopCount(-1)
        glow_anim.setEasingCurve(QEasingCurve.InOutSine)
        # Use styleSheet animation instead
        glow_anim.deleteLater()

    def _load_users(self):
        while self.user_btns_layout.count():
            item = self.user_btns_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        users = self.auth_manager.storage.list_users()
        for user in users:
            btn = QPushButton(f"👤 {user['display_name']} ({user['username']})")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(14, 32, 52, 0.72);
                    color: #e7f4fb;
                    border: 1px solid rgba(95, 235, 255, 0.2);
                    border-radius: 10px;
                    padding: 12px 16px;
                    text-align: left;
                    font-family: "Outfit", sans-serif;
                }
                QPushButton:hover {
                    background: rgba(18, 40, 64, 0.85);
                    border-color: rgba(95, 235, 255, 0.45);
                    color: #4df4ff;
                }
            """)
            btn.clicked.connect(lambda checked, u=user: self._select_user(u))
            self.user_btns_layout.addWidget(btn)

    def _select_user(self, user):
        self.selected_username = user['username']
        self.welcome_label.setText(f"Welcome, {user['display_name']}")
        self.status_label.setText("Select authentication method")
        self.stacked_widget.setCurrentIndex(2)  # Login Options

    def _show_register_page(self):
        self.stacked_widget.setCurrentIndex(1)

    def _show_user_select(self):
        self._load_users()
        self.stacked_widget.setCurrentIndex(0)

    def _show_login_options(self):
        self.stacked_widget.setCurrentIndex(2)

    def _register_user(self):
        username = self.reg_username.text().strip()
        display = self.reg_display.text().strip()
        pin = self.reg_pin.text().strip()

        if not username or not display:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
        if pin and len(pin) < 6:
            QMessageBox.warning(self, "Error", "PIN must be at least 6 digits")
            return

        profile = self.auth_manager.register_user(username, display, pin)
        if profile:
            QMessageBox.information(self, "Success", f"User {display} registered successfully!")
            self.reg_username.clear()
            self.reg_display.clear()
            self.reg_pin.clear()
            self._load_users()
            self.stacked_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Error", "Registration failed")

    def _login_face(self):
        self.status_label.setText("📷 Scanning face... Please look at the camera")
        self.stacked_widget.setCurrentIndex(2)  # Stay on options, show overlay

        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "Error", "Camera not available")
            return

        ret, frame = cap.read()
        cap.release()
        if ret:
            result = self.auth_manager.authenticate_face(self.selected_username, frame)
            self._handle_auth_result(result)
        else:
            QMessageBox.warning(self, "Error", "Could not capture image")

    def _login_fingerprint(self):
        self.status_label.setText("👆 Place finger on sensor...")
        self.stacked_widget.setCurrentIndex(2)

        result = self.auth_manager.authenticate_fingerprint(self.selected_username)
        self._handle_auth_result(result)

    def _login_pin_page(self):
        self.stacked_widget.setCurrentIndex(3)
        self.pin_input.clear()
        self.pin_display.setText("●●●●●●")
        self.pin_input.setVisible(False)
        self.pin_input.setFocus()

    def _login_pin(self):
        pin = self.pin_input.text().strip() if self.pin_input.text() else ""
        if not pin:
            return
        result = self.auth_manager.authenticate_pin(self.selected_username, pin)
        self._handle_auth_result(result)

    def _handle_auth_result(self, result: AuthenticationResult):
        if result.success:
            self.status_label.setText("✓ Authentication successful!")
            QTimer.singleShot(1000, lambda: self.login_success.emit(result.session_token))
        else:
            self.status_label.setText(f"✗ Failed: {result.message}")
            QMessageBox.warning(self, "Authentication Failed", result.message)


def run_login():
    """Entry point for standalone login window."""
    from Security.auth_manager import AuthManager

    app = QApplication([])
    auth_manager = AuthManager()
    window = LoginWindow(auth_manager)
    window.show()
    sys.exit(app.exec_())






