"""
ASTRA Nebula — Animation Engine.
Centralized animation orchestrator for consistent timing/easing.
"""

from typing import Dict
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation
from PyQt5.QtWidgets import QWidget


class AnimationEngine:
    """
    Centralized animation orchestrator.
    All UI animations should go through here for consistent timing.
    """

    # --- Durations (ms) ---
    TIMINGS: Dict[str, int] = {
        "micro":    80,    # Button press, toggle
        "fast":    180,    # Card hover, input focus
        "medium":  260,    # Page transition, panel open
        "slow":    400,    # Mode transition, orb state change
        "entrance": 800,    # Window open, welcome
        "ripple":  600,    # Ripple expand (mic)
        "sweep":   0,      # Continuous (linear)
        "orbit":   0,      # Continuous (linear)
    }

    # --- Easings ---
    EASINGS: Dict[str, QEasingCurve] = {
        "standard":       QEasingCurve.OutCubic,
        "emphasized":     QEasingCurve.OutQuart,
        "decel":          QEasingCurve.OutCubic,
        "accel":          QEasingCurve.OutCubic,
        "sharp":          QEasingCurve.Linear,
        "gentle":         QEasingCurve.OutQuad,
        "bounce_in":      QEasingCurve.OutBack,
        "bounce_out":     QEasingCurve.OutBack,
    }

    @classmethod
    def animate(cls, target, property_name, start, end, duration=None,
                easing="standard", delay=0):
        """Create a QPropertyAnimation with standardized settings."""
        anim = QPropertyAnimation(target, property_name)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration or cls.TIMINGS["fast"])
        anim.setEasingCurve(cls.EASINGS.get(easing, QEasingCurve.OutCubic))
        if delay > 0:
            group = QSequentialAnimationGroup()
            group.addAnimation(QPauseAnimation(delay))
            group.addAnimation(anim)
            return group
        return anim

    @classmethod
    def stagger(cls, targets, property_name, values, base_delay=100, duration=None):
        """Stagger animations for a list of targets."""
        group = QSequentialAnimationGroup()
        for i, (target, val) in enumerate(zip(targets, values)):
            anim = cls.animate(
                target, property_name, 0, val,
                duration=duration, easing="standard",
            )
            group.addAnimation(QPauseAnimation(i * base_delay))
            group.addAnimation(anim)
        return group

    @classmethod
    def pulse(cls, target, property_name, base_value, peak_value=None,
              duration=600, easing="standard"):
        """Create a pulse animation (used for emphasis)."""
        if peak_value is None:
            peak_value = base_value * 1.2

        group = QSequentialAnimationGroup()
        up = cls.animate(
            target, property_name, base_value, peak_value,
            duration=duration // 2, easing="decel",
        )
        down = cls.animate(
            target, property_name, peak_value, base_value,
            duration=duration // 2, easing="accel",
        )
        group.addAnimation(up)
        group.addAnimation(down)
        return group


class HoverEffect:
    """
    Helper to add hover glow + transform to any QWidget.
    Uses QGraphicsEffect for glow, property animation for scale.
    """

    @staticmethod
    def install(target: QWidget, glow_color="#4df4ff", scale_factor=1.02):
        from PyQt5.QtGraphicsEffects import QGraphicsDropShadowEffect

        target._hover_glow = QGraphicsDropShadowEffect()
        target._hover_glow.setBlurRadius(0)
        target._hover_glow.setXOffset(0)
        target._hover_glow.setYOffset(0)
        target._hover_glow.setColor(glow_color)
        target.setGraphicsEffect(target._hover_glow)

        target._hover_anim = AnimationEngine.animate(
            target._hover_glow, b"blurRadius",
            0, 16, duration=AnimationEngine.TIMINGS["fast"],
            easing="standard",
        )

        # Store original transform
        target._hover_scale_anim = AnimationEngine.animate(
            target, b"scale",  # Note: requires setScale on the widget
            target.scale() if hasattr(target, 'scale') else 1.0,
            target.scale() * scale_factor if hasattr(target, 'scale') else scale_factor,
            duration=AnimationEngine.TIMINGS["fast"],
        )


__all__ = ["AnimationEngine", "HoverEffect"]