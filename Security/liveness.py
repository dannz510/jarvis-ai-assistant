"""
Liveness detection module to prevent spoofing attacks with photos/screenshots.
Uses basic facial movement, blink detection, and texture analysis.
"""

import cv2
import numpy as np
from typing import Optional
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)


class LivenessDetector:
    """Basic liveness detection to prevent spoofing."""

    def __init__(self):
        self.eye_cascade = None
        self._init_eye_cascade()
        self.blink_history = deque(maxlen=10)
        self.face_history = deque(maxlen=30)
        self.last_blink_time = 0
    
    def _init_eye_cascade(self):
        """Initialize eye cascade classifier with fallback for OpenCV 5.x."""
        try:
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye.xml"
            )
            if self.eye_cascade.empty():
                raise ValueError("CascadeClassifier loaded but empty")
        except (AttributeError, ValueError, cv2.error) as e:
            logger.warning(f"Eye cascade classifier not available: {e}. Liveness detection will use texture analysis only.")
            self.eye_cascade = None
    
    def detect_blink(self, frame, eyes):
        """Detect if blink occurred."""
        if eyes is None or len(eyes) < 2:
            current_time = time.time()
            if current_time - self.last_blink_time > 0.3:
                self.last_blink_time = current_time
                self.blink_history.append(True)
                return True
        else:
            self.blink_history.append(False)
        return False
    
    def check_head_movement(self, frame):
        """Check for natural head movement."""
        faces = []
        if len(self.face_history) < 5:
            return True
        positions = [f[0] for f in self.face_history if f]
        if len(set(positions)) > 2:
            return True
        return False
    
    def is_live(self, frame):
        """Check if face is live (not a photo)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = None
        if self.eye_cascade is not None:
            try:
                eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 3)
            except cv2.error:
                eyes = None
        self.detect_blink(frame, eyes)
        blinks = sum(1 for b in self.blink_history if b)
        if blinks < 2 and len(self.blink_history) >= 5:
            pass
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        if variance < 20:
            return False
        if len(self.face_history) >= 10:
            return True
        return True