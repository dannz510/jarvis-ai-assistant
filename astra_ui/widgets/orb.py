import math
import random
from typing import Optional, Tuple, Dict, Any

from PyQt5.QtCore import Qt, QTimer, QRect, QRectF
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient, QConicalGradient,
    QPainterPath, QFont, QFontMetrics,
)
from PyQt5.QtWidgets import QWidget, QSizePolicy


# ============================================================
# Mode → (speed, intensity, color) for animation behavior
# Matches the original CoreOrb PROFILES but expanded
# ============================================================
def _rgba(c: QColor, alpha: float) -> QColor:
    return QColor(c.red(), c.green(), c.blue(), max(0, min(255, int(alpha))))


PROFILE_COLORS: Dict[str, QColor] = {
    "idle": QColor(41, 211, 241),
    "listening": QColor(76, 244, 222),
    "user_paused": QColor(105, 207, 235),
    "processing": QColor(75, 192, 255),
    "thinking": QColor(92, 173, 255),
    "tool_selection": QColor(241, 194, 110),
    "executing": QColor(255, 170, 94),
    "observing": QColor(104, 220, 255),
    "responding": QColor(93, 232, 222),
    "speaking": QColor(105, 239, 255),
    "success": QColor(109, 242, 171),
    "error": QColor(255, 117, 113),
    "interrupted": QColor(255, 209, 131),
    "waiting_for_clarification": QColor(245, 195, 110),
    "booting": QColor(99, 205, 255),
}

# (rotation_speed, intensity, color)
PROFILES: Dict[str, Tuple[float, float, QColor]] = {
    "idle":            (0.018, 0.55, PROFILE_COLORS["idle"]),
    "listening":       (0.035, 0.85, PROFILE_COLORS["listening"]),
    "user_paused":     (0.022, 0.70, PROFILE_COLORS["user_paused"]),
    "processing":      (0.032, 0.78, PROFILE_COLORS["processing"]),
    "thinking":        (0.040, 0.90, PROFILE_COLORS["thinking"]),
    "tool_selection":  (0.046, 0.95, PROFILE_COLORS["tool_selection"]),
    "executing":       (0.055, 1.00, PROFILE_COLORS["executing"]),
    "observing":       (0.030, 0.80, PROFILE_COLORS["observing"]),
    "responding":      (0.025, 0.75, PROFILE_COLORS["responding"]),
    "speaking":        (0.032, 1.00, PROFILE_COLORS["speaking"]),
    "success":         (0.050, 1.00, PROFILE_COLORS["success"]),
    "error":           (0.025, 0.75, PROFILE_COLORS["error"]),
    "interrupted":     (0.070, 0.85, PROFILE_COLORS["interrupted"]),
    "waiting_for_clarification": (0.020, 0.68, PROFILE_COLORS["waiting_for_clarification"]),
    "booting":         (0.060, 0.85, PROFILE_COLORS["booting"]),
}


class OrbVisualizer(QWidget):
    """
    Upgraded neural-core visualizer.

    Visual features:
      - Far bloom glow
      - Rotating energy rings (background + accent)
      - Holographic light sweep
      - 3D node field + link network
      - Mic-reactive expanding ripples
      - Particle field with orbiting micro-particles
      - FFT visualizer bars (low/mid/high frequency bands)
      - Core sphere with layered radial gradients
      - Specular sheen
      - Breathing pulse synced to phase + audio
      - Mouse-parallax tilt

    API-compatible with the original CoreOrb class.
    """

    # ============================================================
    #  Life-cycle
    # ============================================================
    def __init__(self):
        super().__init__()
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        # --- State ---
        self.phase: float = 0.0
        self.mode: str = "idle"
        self.audio_level: float = 0.0
        self.frequency_bands: Dict[str, float] = {"low": 0.0, "mid": 0.0, "high": 0.0}
        self.progress: Optional[float] = None
        self.tool_activity: str = ""
        self.pointer_offset: Tuple[float, float] = (0.0, 0.0)

        # --- 3D node field ---
        self._build_node_field(78)

        # --- Particles ---
        self._particles: list = []
        self._build_particles(16)

        # --- Ripples (mic reactive) ---
        self._ripples: list = []  # each: [radius, alpha]

        # --- Timer ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)  # 25ms optimal, 40ms stable

    # ============================================================
    #  Node field generation (golden spiral)
    # ============================================================
    def _build_node_field(self, count: int):
        golden_angle = math.pi * (3 - math.sqrt(5))
        self.nodes = []
        for index in range(count):
            y = 1 - 2 * (index + 0.5) / count
            ring = math.sqrt(1 - y * y)
            angle = index * golden_angle
            self.nodes.append((
                math.cos(angle) * ring,
                y,
                math.sin(angle) * ring,
            ))
        # Pre-compute links (edges shorter than threshold)
        self.links = []
        threshold = 0.26
        for first, node in enumerate(self.nodes):
            for second in range(first + 1, count):
                other = self.nodes[second]
                dist = sum((node[a] - other[a]) ** 2 for a in range(3))
                if dist < threshold:
                    self.links.append((first, second))

    # ============================================================
    #  Particle field generation
    # ============================================================
    def _build_particles(self, count: int):
        self._particles.clear()
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            radius_ratio = random.uniform(0.85, 1.05)
            self._particles.append({
                "angle": angle,
                "radius_ratio": radius_ratio,
                "speed": random.uniform(0.3, 0.8) * 0.015,
                "size": random.uniform(1.2, 2.8),
                "orbit_phase": random.uniform(0, math.tau),
                "orbit_radius": random.uniform(0.04, 0.12),
            })

    # ============================================================
    #  API Methods (backward-compatible with CoreOrb)
    # ============================================================
    def set_mode(self, mode):
        """Set visualization mode (same API as CoreOrb)."""
        aliases = {"tool_call": "executing", "completed": "success", "interrupted": "listening"}
        normalized = str(getattr(mode, "value", mode)).casefold()
        self.mode = aliases.get(normalized, normalized if normalized in PROFILES else "idle")
        self.update()

    def set_audio_level(self, value):
        self.audio_level = max(0.0, min(1.0, float(value)))
        self.update()

    def set_frequency_bands(self, low=0.0, mid=0.0, high=0.0):
        self.frequency_bands = {
            "low": max(0.0, min(1.0, float(low))),
            "mid": max(0.0, min(1.0, float(mid))),
            "high": max(0.0, min(1.0, float(high))),
        }
        self.set_audio_level(max(self.frequency_bands.values()))

    def trigger_pulse(self):
        self.phase = (self.phase + math.pi / 2) % (2 * math.pi)
        self.update()

    def trigger_success(self):
        self.set_mode("success")
        self.trigger_pulse()

    def trigger_error(self):
        self.set_mode("error")
        self.trigger_pulse()

    def set_tool_activity(self, tool_name):
        self.tool_activity = str(tool_name or "")
        self.set_mode("executing")

    def set_progress(self, value):
        self.progress = None if value is None else max(0.0, min(1.0, float(value)))
        self.update()

    def interrupt(self):
        self.set_mode("interrupted")

    def reset(self):
        self.set_mode("idle")
        self.set_audio_level(0.0)
        self._ripples.clear()
        self.progress = None
        self.tool_activity = ""

    # ============================================================
    #  Mouse interaction (parallax tilt)
    # ============================================================
    def mouseMoveEvent(self, event):
        w = max(1, self.width())
        h = max(1, self.height())
        self.pointer_offset = (
            max(-1.0, min(1.0, (event.x() - w / 2) / (w / 2))),
            max(-1.0, min(1.0, (event.y() - h / 2) / (h / 2))),
        )
        self.update()

    def leaveEvent(self, _event):
        self.pointer_offset = (0.0, 0.0)
        self.update()

    # ============================================================
    #  Animation tick
    # ============================================================
    def _tick(self):
        speed, intensity, accent = PROFILES.get(self.mode, PROFILES["idle"])
        self.phase = (self.phase + speed) % (2 * math.pi)

        # Decay audio level
        self.audio_level *= 0.92

        # Decay frequency bands
        self.frequency_bands["low"] *= 0.88
        self.frequency_bands["mid"] *= 0.90
        self.frequency_bands["high"] *= 0.92

        # Spawn ripple on mic activity
        if self.audio_level > 0.18 and random.random() < 0.35:
            self._ripples.append([0.85, 200.0])

        # Update ripples
        new_ripples = []
        for r in self._ripples:
            r[0] += 0.028 + self.audio_level * 0.015
            r[1] -= 1.2 + self.audio_level * 2.0
            if r[1] > 0:
                new_ripples.append(r)
        self._ripples = new_ripples

        self.update()

    # ============================================================
    #  Paint — all visual layers
    # ============================================================
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2

        speed, intensity, accent = PROFILES.get(self.mode, PROFILES["idle"])
        base_radius = min(w, h) * 0.32

        # --- Breathing + mouse parallax + audio pulse ---
        breath = 1.0 + 0.012 * math.sin(self.phase * 2.4)
        audio_pulse = 0.035 * self.audio_level
        low_pump = 0.028 * self.frequency_bands["low"]
        radius = base_radius * (breath + audio_pulse + low_pump)

        # Parallax shift (subtle)
        cx += self.pointer_offset[0] * radius * 0.04
        cy += self.pointer_offset[1] * radius * 0.04

        # Parallax tilt for 3D effect
        tilt_x = self.pointer_offset[0] * 0.12
        tilt_y = self.pointer_offset[1] * 0.12

        # --- 1. Far Bloom ---
        self._paint_far_bloom(p, cx, cy, radius, accent, intensity)

        # --- 2. Energy Rings ---
        self._paint_energy_rings(p, cx, cy, radius, accent, intensity, speed)

        # --- 3. Holographic Light Sweep ---
        self._paint_light_sweep(p, cx, cy, radius, accent, intensity)

        # --- 4. Mid Glow ---
        self._paint_mid_glow(p, cx, cy, radius, accent, intensity)

        # --- 5. Core Sphere ---
        self._paint_core(p, cx, cy, radius, accent, intensity)

        # --- 6. Node Field + Links ---
        self._paint_node_field(p, cx, cy, radius, accent, intensity, tilt_x, tilt_y)

        # --- 7. Mic Reactive Ripples ---
        self._paint_ripples(p, cx, cy, radius, accent, intensity)

        # --- 8. Particle Field ---
        self._paint_particles(p, cx, cy, radius, accent, intensity)

        # --- 9. FFT Visualizer ---
        self._paint_fft_visualizer(p, cx, cy, radius, accent, intensity)

        # --- 10. Tool Activity Text ---
        if self.tool_activity and intensity > 0.3:
            self._paint_tool_activity(p, cx, cy, radius, self.tool_activity)

        # --- 11. Progress indicator ---
        if self.progress is not None:
            self._paint_progress(p, cx, cy, radius * 1.2, self.progress, accent)

    # ============================================================
    #  Layer painters
    # ============================================================

    def _paint_far_bloom(self, p: QPainter, cx: float, cy: float, radius: float,
                         accent: QColor, intensity: float):
        bloom_radius = radius * 2.8
        glow = QRadialGradient(cx, cy, bloom_radius)
        glow.setColorAt(0.0, _rgba(accent, 35 * intensity))
        glow.setColorAt(0.45, _rgba(accent, 22 * intensity))
        glow.setColorAt(0.75, _rgba(accent, 12 * intensity))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(
            int(cx - bloom_radius), int(cy - bloom_radius),
            int(bloom_radius * 2), int(bloom_radius * 2),
        )

    def _paint_energy_rings(self, p: QPainter, cx: float, cy: float, radius: float,
                            accent: QColor, intensity: float, speed: float):
        ring_configs = [
            (1.18, 0.25, 1.0, 1.0, math.pi / 2),
            (1.42, -0.32, 0.7, 1.15, math.pi / 2.5),
            (1.68, 0.42, 0.45, 1.3, math.pi / 3),
        ]
        for mult, rotation_factor, alpha_factor, width_factor, rot_speed in ring_configs:
            r = radius * mult
            rot = self.phase * rot_speed + speed * 100
            rect_w = r * 2 * 0.96
            rect_h = r * 2 * 0.28

            p.save()
            p.translate(cx, cy)
            p.rotate(math.degrees(rot))
            p.translate(-cx, -cy)

            path = QPainterPath()
            path.addEllipse(cx, cy - rect_h / 2, rect_w, rect_h)

            ring_color = _rgba(accent, alpha_factor * 95 * intensity)
            grad = QConicalGradient(cx, cy - rect_h / 2, 90)
            grad.setColorAt(0.0, _rgba(accent, 0))
            grad.setColorAt(0.3, ring_color)
            grad.setColorAt(0.5, _rgba(accent, alpha_factor * 110 * intensity))
            grad.setColorAt(0.7, ring_color)
            grad.setColorAt(1.0, _rgba(accent, 0))

            pen = QPen(grad, width_factor)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            p.restore()

    def _paint_light_sweep(self, p: QPainter, cx: float, cy: float, radius: float,
                           accent: QColor, intensity: float):
        sweep_angle = self.phase * 0.9
        sweep_width = math.radians(75)
        outer_r = radius * 1.65
        inner_r = radius * 0.95

        p.save()
        p.translate(cx, cy)
        p.rotate(sweep_angle)
        p.translate(-cx, -cy)

        path = QPainterPath()
        path.arcTo(
            cx - outer_r, cy - outer_r,
            outer_r * 2, outer_r * 2,
            0, 47,
        )
        path.arcTo(
            cx - inner_r, cy - inner_r,
            inner_r * 2, inner_r * 2,
            47, -47,
        )
        path.closeSubpath()

        alpha = intensity * (0.4 + 0.3 * self.audio_level) * 140
        grad = QConicalGradient(cx, cy, 0)
        grad.setColorAt(0.0, _rgba(accent, 0))
        grad.setColorAt(0.15, _rgba(accent, int(alpha * 0.7)))
        grad.setColorAt(0.3, _rgba(accent, int(alpha)))
        grad.setColorAt(0.45, _rgba(accent, int(alpha * 0.6)))
        grad.setColorAt(1.0, _rgba(accent, 0))

        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.fillPath(path, grad)
        p.restore()

    def _paint_mid_glow(self, p: QPainter, cx: float, cy: float, radius: float,
                        accent: QColor, intensity: float):
        glow_radius = radius * 1.55
        glow = QRadialGradient(cx, cy, glow_radius)
        glow.setColorAt(0.0, _rgba(accent, 60 * intensity))
        glow.setColorAt(0.55, _rgba(accent, 32 * intensity))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(
            int(cx - glow_radius), int(cy - glow_radius),
            int(glow_radius * 2), int(glow_radius * 2),
        )

    def _paint_core(self, p: QPainter, cx: float, cy: float, radius: float,
                    accent: QColor, intensity: float):
        # Specular sheen offset
        offset_x = radius * 0.18 + self.pointer_offset[0] * radius * 0.02
        offset_y = radius * 0.22 + self.pointer_offset[1] * radius * 0.02

        core_center_x = cx + offset_x
        core_center_y = cy + offset_y

        core_gradient = QRadialGradient(
            core_center_x - radius * 0.26,
            core_center_y - radius * 0.30,
            radius * 1.45,
        )

        core_intensity = intensity * (1.0 + self.audio_level * 0.5)
        core_gradient.setColorAt(0.0, _rgba(QColor(200, 255, 255), 245 * core_intensity))
        core_gradient.setColorAt(
            0.25, _rgba(accent, 200 * core_intensity))
        core_gradient.setColorAt(
            0.70, _rgba(QColor(15, 60, 105), 140 * core_intensity))
        core_gradient.setColorAt(1.0, QColor(4, 23, 49, 0))

        p.setBrush(core_gradient)
        rim_color = _rgba(QColor(72, 248, 255), 180 * intensity)
        p.setPen(QPen(rim_color, 1.3))
        p.drawEllipse(
            int(core_center_x - radius * 0.72), int(core_center_y - radius * 0.72),
            int(radius * 1.44), int(radius * 1.44),
        )

        # Inner hotspot
        hotspot_r = radius * 0.18 * (1 + self.audio_level * 0.3)
        p.setBrush(_rgba(QColor(220, 255, 255), 235))
        p.setPen(Qt.NoPen)
        p.drawEllipse(
            int(core_center_x - hotspot_r), int(core_center_y - hotspot_r),
            int(hotspot_r * 2), int(hotspot_r * 2),
        )

        # Progress ring (if active)
        if self.progress is not None and 0 < self.progress < 1:
            p.save()
            p.translate(core_center_x, core_center_y)
            p.rotate(-90)
            p.translate(-core_center_x, -core_center_y)
            pen = QPen(_rgba(accent, 220), 2.5)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            span = int(360 * self.progress)
            p.drawArc(
                int(core_center_x - radius * 0.76), int(core_center_y - radius * 0.76),
                int(radius * 1.52), int(radius * 1.52),
                0, span * 16,
            )
            p.restore()

    def _paint_node_field(self, p: QPainter, cx: float, cy: float, radius: float,
                          accent: QColor, intensity: float,
                          tilt_x: float, tilt_y: float):
        yaw = self.phase * 0.38 + tilt_x
        pitch = math.sin(self.phase * 0.31) * 0.16 + tilt_y
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        cos_p, sin_p = math.cos(pitch), math.sin(pitch)

        projected = []
        for x, y, z in self.nodes:
            rx = x * cos_y - z * sin_y
            rz = x * sin_y + z * cos_y
            ry = y * cos_p - rz * sin_p
            rz = y * sin_p + rz * cos_p
            perspective = 1.0 / (1.45 - rz * 0.24)
            spread = radius * 1.32 * perspective
            projected.append((
                cx + rx * spread,
                cy + ry * spread,
                rz,
            ))

        # Draw links
        for first, second in self.links:
            x1, y1, z1 = projected[first]
            x2, y2, z2 = projected[second]
            depth = (z1 + z2 + 2) * 0.25
            link_alpha = int((12 + depth * 78) * intensity * (0.8 + self.audio_level * 1.2))
            if link_alpha < 30:
                continue
            p.setPen(QPen(_rgba(accent, link_alpha), 0.6))
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw nodes (depth sorted, back to front)
        sorted_nodes = sorted(range(len(projected)), key=lambda i: projected[i][2], reverse=True)
        for idx in sorted_nodes:
            x, y, depth = projected[idx]
            alpha = int(60 + (depth + 1) * 90) * intensity
            if depth < -0.2:
                alpha = int(alpha * 0.4)
            diameter = 1.8 + (depth + 1) * 1.2
            audio_boost = 1.0 + self.frequency_bands["high"] * 0.6
            diameter *= audio_boost
            p.setPen(Qt.NoPen)
            p.setBrush(_rgba(accent, min(235, int(alpha * audio_boost))))
            p.drawEllipse(
                int(x - diameter / 2), int(y - diameter / 2),
                int(diameter), int(diameter),
            )

    def _paint_ripples(self, p: QPainter, cx: float, cy: float, radius: float,
                       accent: QColor, intensity: float):
        for cur_radius, alpha in self._ripples:
            r = radius * cur_radius
            ripple_alpha = int(alpha * intensity * (0.5 + self.frequency_bands["low"] * 0.5))
            p.setPen(QPen(_rgba(accent, ripple_alpha), 1.0 + (cur_radius * 0.3)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(
                int(cx - r), int(cy - r),
                int(r * 2), int(r * 2),
            )

    def _paint_particles(self, p: QPainter, cx: float, cy: float, radius: float,
                         accent: QColor, intensity: float):
        for particle in self._particles:
            # Orbit around the sphere
            orbit_angle = self.phase * particle["speed"] * 0.15 + particle["orbit_phase"]
            orbit_r = particle["orbit_radius"]
            px = cx + math.cos(orbit_angle) * radius * particle["radius_ratio"] + \
                 math.cos(orbit_angle + math.pi / 2) * radius * orbit_r
            py = cy + math.sin(orbit_angle) * radius * particle["radius_ratio"] * 0.55 + \
                 math.sin(orbit_angle + math.pi / 2) * radius * orbit_r * 0.55

            size = particle["size"] * (1.0 + self.audio_level * 0.5)
            alpha = int(120 * intensity * (1.0 + self.frequency_bands["mid"] * 0.8))

            p.setPen(Qt.NoPen)
            p.setBrush(_rgba(accent, min(200, alpha)))
            p.drawEllipse(
                int(px - size / 2), int(py - size / 2),
                int(size), int(size),
            )

    def _paint_fft_visualizer(self, p: QPainter, cx: float, cy: float, radius: float,
                              accent: QColor, intensity: float):
        # 3 concentric arcs: low (inner), mid, high (outer)
        bands = [
            self.frequency_bands["low"],
            self.frequency_bands["mid"],
            self.frequency_bands["high"],
        ]
        band_colors = [
            QColor(61, 245, 217),   # teal
            QColor(77, 244, 255),   # cyan
            QColor(157, 123, 255),  # violet
        ]
        band_radii = [0.88, 1.08, 1.32]
        segments = 24
        max_height = radius * 0.09

        for band_idx, (value, color, r_mult) in enumerate(zip(bands, band_colors, band_radii)):
            if value <= 0.01:
                continue

            band_angle_step = 360.0 / segments
            inner_r = radius * r_mult
            outer_r = inner_r + max_height * value * intensity

            p.save()
            p.translate(cx, cy)
            p.rotate(self.phase * (60 if band_idx % 2 == 0 else -45))

            for seg in range(segments):
                angle = seg * band_angle_step
                start_angle = int(angle * 16)
                span_angle = int((band_angle_step * 0.75) * 16)
                inner_rect = inner_r
                outer_rect = outer_r

                # Create a path for the arc segment
                path = QPainterPath()
                path.arcTo(cx - outer_rect, cy - outer_rect, outer_rect * 2, outer_rect * 2,
                           angle, band_angle_step * 0.75)
                path.arcTo(cx - inner_rect, cy - inner_rect, inner_rect * 2, inner_rect * 2,
                           angle + band_angle_step * 0.75, -(band_angle_step * 0.75))
                path.closeSubpath()

                alpha = int(180 * intensity * value * (0.7 + band_idx * 0.15))
                p.setPen(Qt.NoPen)
                p.setBrush(_rgba(color, max(30, alpha)))
                p.drawPath(path)

            p.restore()

    def _paint_tool_activity(self, p: QPainter, cx: float, cy: float, radius: float,
                             text: str):
        label = text[:24] + ("…" if len(text) > 24 else "")
        font = QFont("Outfit", "Segoe UI", 7)
        font.setBold(True)
        font.setPixelSize(int(10 * intensity))
        p.setFont(font)
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(label)
        text_height = metrics.height()
        y_pos = cy + radius * 1.15 + text_height / 2
        x_pos = cx - text_width / 2

        # Subtle glow behind text
        p.setOpacity(0.7)
        p.setPen(QPen(_rgba(QColor(15, 60, 105), 90)))
        p.drawText(int(x_pos + 1), int(y_pos + 1), label)
        p.setOpacity(1.0)
        p.setPen(QPen(_rgba(QColor(200, 255, 255), 220)))
        p.drawText(int(x_pos), int(y_pos), label)

    def _paint_progress(self, p: QPainter, cx: float, cy: float, radius: float,
                        progress: float, accent: QColor):
        if progress is None:
            return
        pen = QPen(_rgba(accent, 200), 2.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        span = int(360 * progress)
        p.drawArc(
            int(cx - radius), int(cy - radius),
            int(radius * 2), int(radius * 2),
            0, span * 16,
        )


# ============================================================
# Backward-compatible alias (original class name)
# ============================================================
CoreOrb = OrbVisualizer

__all__ = ["OrbVisualizer", "CoreOrb", "PROFILES"]