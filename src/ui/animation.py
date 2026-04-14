# src/ui/animation.py
"""
JARVIS Visual Animation
Audio-reactive glowing orb — responds to voice amplitude and frequency
"""

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QPen, QCursor
import sys
import math


class JarvisAnimation(QWidget):
    """Audio-reactive animated overlay"""

    def __init__(self):
        super().__init__()

        # Window setup
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Appear above fullscreen apps (Chrome fullscreen, etc.)
        # macOS window level: NSScreenSaverWindowLevel + 1 = 1001
        try:
            from AppKit import NSApp, NSFloatingWindowLevel, NSScreenSaverWindowLevel
            self._macos_level = int(NSScreenSaverWindowLevel) + 1
        except ImportError:
            self._macos_level = 1001  # fallback constant

        # Animation state
        self._pulse_radius = 100
        self._glow_opacity = 0.0
        self.is_animating = False
        self.pulse_phase = 0

        # Audio-reactive state (set from outside)
        self._audio_level = 0.0       # 0.0–1.0 amplitude
        self._audio_freq = 0.0        # dominant frequency in Hz
        self._level_smooth = 0.0      # smoothed level for rendering

        # Base colors — shifted by frequency
        self._base_primary = QColor(64, 156, 255)
        self._base_secondary = QColor(100, 200, 255)
        self.primary_color = QColor(self._base_primary)
        self.secondary_color = QColor(self._base_secondary)
        self.glow_color = QColor(64, 156, 255, 150)

        # Timer for animation updates
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)

        # Fade in/out
        self.fade_animation = QPropertyAnimation(self, b"glow_opacity")
        self.fade_animation.setDuration(500)

        self.hide()

    @pyqtProperty(float)
    def glow_opacity(self):
        return self._glow_opacity

    @glow_opacity.setter
    def glow_opacity(self, value):
        self._glow_opacity = value
        self.update()

    def set_audio_data(self, level: float, dominant_freq: float):
        """Feed audio data for reactive visuals. Thread-safe (GIL)."""
        self._audio_level = min(level, 1.0)
        self._audio_freq = dominant_freq

    def show_animation(self, duration_ms=3000):
        """Show the animation for a specified duration"""
        cursor_pos = QCursor.pos()
        screen_geometry = None
        for screen in QApplication.instance().screens():
            if screen.geometry().contains(cursor_pos):
                screen_geometry = screen.geometry()
                break
        if screen_geometry is None:
            screen_geometry = QApplication.instance().primaryScreen().geometry()

        self.setGeometry(screen_geometry)
        self.show()
        self.raise_()

        self.is_animating = True
        self.pulse_phase = 0
        self._audio_level = 0.0
        self._audio_freq = 0.0
        self._level_smooth = 0.0

        # Fade in
        self.fade_animation.stop()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

        self.animation_timer.start(30)  # ~33 FPS

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.hide_animation)

    def hide_animation(self):
        """Hide with fade out"""
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self._glow_opacity)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_fade_complete)
        self.fade_animation.start()

    def _on_fade_complete(self):
        self.animation_timer.stop()
        self.is_animating = False
        self.hide()
        self.fade_animation.finished.disconnect(self._on_fade_complete)

    def update_animation(self):
        """Update animation state every frame"""
        if not self.is_animating:
            return

        self.pulse_phase += 0.05

        # Smooth the audio level (lerp toward target)
        self._level_smooth += (self._audio_level - self._level_smooth) * 0.3

        # Base pulse + audio-reactive expansion
        base_pulse = 30 * math.sin(self.pulse_phase)
        audio_boost = self._level_smooth * 120  # up to 120px extra when loud
        self._pulse_radius = 100 + base_pulse + audio_boost

        # Map dominant frequency to color shift
        # Voice range: ~80Hz (deep) → ~1000Hz (bright)
        # Low freq → deep blue/purple, high freq → bright cyan/white
        freq = self._audio_freq
        if freq > 0 and self._level_smooth > 0.02:
            freq_norm = max(0.0, min((freq - 80) / 920, 1.0))

            r = int(40 + freq_norm * 80)          # 40–120
            g = int(100 + freq_norm * 155)         # 100–255
            b = 255
            self.primary_color = QColor(r, g, b)

            r2 = int(80 + freq_norm * 100)         # 80–180
            g2 = int(160 + freq_norm * 95)          # 160–255
            b2 = 255
            self.secondary_color = QColor(r2, g2, b2)
        else:
            # No voice — drift back to base blue
            self.primary_color = QColor(self._base_primary)
            self.secondary_color = QColor(self._base_secondary)

        self.update()

    def paintEvent(self, event):
        """Draw the audio-reactive orb"""
        if self._glow_opacity <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() // 2
        cy = self.height() // 2

        # Outer glow rings — expand with audio
        for i in range(3):
            radius = self._pulse_radius + (i * 40)
            opacity = self._glow_opacity * (0.3 - i * 0.1)

            gradient = QRadialGradient(cx, cy, radius)

            core_color = QColor(self.primary_color)
            core_color.setAlphaF(opacity * 0.8)
            gradient.setColorAt(0.0, core_color)

            mid_color = QColor(self.secondary_color)
            mid_color.setAlphaF(opacity * 0.4)
            gradient.setColorAt(0.5, mid_color)

            outer_color = QColor(self.primary_color)
            outer_color.setAlphaF(0)
            gradient.setColorAt(1.0, outer_color)

            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(cx - radius), int(cy - radius),
                int(radius * 2), int(radius * 2)
            )

        # Bright core — pulses brighter with audio
        core_intensity = 0.9 + self._level_smooth * 0.1
        core_radius = 30 + self._level_smooth * 20  # core grows with voice
        core_gradient = QRadialGradient(cx, cy, core_radius)

        bright_core = QColor(255, 255, 255)
        bright_core.setAlphaF(min(self._glow_opacity * core_intensity, 1.0))
        core_gradient.setColorAt(0.0, bright_core)

        glow_core = QColor(self.primary_color)
        glow_core.setAlphaF(self._glow_opacity * 0.6)
        core_gradient.setColorAt(0.7, glow_core)

        transparent = QColor(self.primary_color)
        transparent.setAlphaF(0)
        core_gradient.setColorAt(1.0, transparent)

        painter.setBrush(core_gradient)
        painter.drawEllipse(
            int(cx - core_radius), int(cy - core_radius),
            int(core_radius * 2), int(core_radius * 2)
        )

        # Outer ring — reacts to audio
        ring_radius = self._pulse_radius + 60
        ring_pen = QPen(self.primary_color)
        ring_width = 2 + int(self._level_smooth * 4)  # thicker when loud
        ring_pen.setWidth(ring_width)
        ring_color = QColor(self.primary_color)
        ring_color.setAlphaF(self._glow_opacity * (0.4 + self._level_smooth * 0.4))
        ring_pen.setColor(ring_color)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            int(cx - ring_radius), int(cy - ring_radius),
            int(ring_radius * 2), int(ring_radius * 2)
        )


class AnimationController:
    """Controller to manage JARVIS animation — Thread-safe"""

    def __init__(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)

        self.animation = None
        self._show_pending = False
        self._hide_pending = False
        self._pending_duration = 3000

    def show(self, duration_ms=3000):
        self._pending_duration = duration_ms
        self._show_pending = True

    def hide(self):
        self._hide_pending = True

    def set_audio_level(self, level: float, freq: float):
        """Feed audio data to the animation. Safe to call from any thread."""
        if self.animation:
            self.animation.set_audio_data(level, freq)

    def process_events(self):
        """Process Qt events and pending requests (MUST call from main thread)"""
        if self.app:
            if self.animation is None and (self._show_pending or self._hide_pending):
                try:
                    self.animation = JarvisAnimation()
                    print("✓ Animation initialized")
                except Exception as e:
                    print(f"⚠️  Could not create animation: {e}")
                    self.animation = None
                    return

            if self._show_pending and self.animation:
                self._show_pending = False
                self.animation.show_animation(self._pending_duration)

            if self._hide_pending and self.animation:
                self._hide_pending = False
                self.animation.hide_animation()

            self.app.processEvents()


# Standalone test — simulates audio reactivity
def test_animation():
    import time
    import numpy as np

    controller = AnimationController()
    print("Showing audio-reactive animation (5s)...")
    controller.show(duration_ms=0)

    start = time.time()
    while time.time() - start < 5.0:
        # Simulate voice: amplitude pulses, frequency sweeps
        t = time.time() - start
        level = 0.3 + 0.5 * abs(math.sin(t * 2))
        freq = 150 + 300 * abs(math.sin(t * 0.5))
        controller.set_audio_level(level, freq)
        controller.process_events()
        time.sleep(0.03)

    controller.hide()
    for _ in range(20):
        controller.process_events()
        time.sleep(0.03)
    print("Done!")


if __name__ == "__main__":
    test_animation()
