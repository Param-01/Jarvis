# src/ui/animation.py
"""
JARVIS Visual Animation
Displays a glowing orb overlay when activated
"""

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QPen
import sys
import math

# For macOS all-spaces support
try:
    from ctypes import c_void_p
except:
    pass


class JarvisAnimation(QWidget):
    """Animated overlay that appears when JARVIS is activated"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |      # Always on top
            Qt.FramelessWindowHint |        # No window frame
            Qt.Tool |                       # Don't show in dock
            Qt.WindowTransparentForInput    # Click-through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # Transparent background
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # Don't steal focus
        
        # Animation state
        self._pulse_radius = 100
        self._glow_opacity = 0.0
        self.is_animating = False
        self.pulse_phase = 0
        
        # Colors - Blue/Cyan theme (like JARVIS)
        self.primary_color = QColor(64, 156, 255)      # Bright blue
        self.secondary_color = QColor(100, 200, 255)   # Cyan
        self.glow_color = QColor(64, 156, 255, 150)    # Semi-transparent blue
        
        # Timer for animation updates
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        
        # Fade in/out animations
        self.fade_animation = QPropertyAnimation(self, b"glow_opacity")
        self.fade_animation.setDuration(500)  # 500ms fade
        
        self.hide()
    
    @pyqtProperty(float)
    def glow_opacity(self):
        return self._glow_opacity
    
    @glow_opacity.setter
    def glow_opacity(self, value):
        self._glow_opacity = value
        self.update()
    
    def show_animation(self, duration_ms=3000):
        """Show the animation for a specified duration"""
        # Get the screen where the mouse cursor is
        from PyQt5.QtWidgets import QDesktopWidget
        desktop = QDesktopWidget()
        cursor_pos = desktop.cursor().pos()
        screen_number = desktop.screenNumber(cursor_pos)
        screen_geometry = desktop.screenGeometry(screen_number)
        
        # Set to full screen of current display
        self.setGeometry(screen_geometry)
        
        # Show window
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Start animation
        self.is_animating = True
        self.pulse_phase = 0
        
        # Fade in
        self.fade_animation.stop()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        
        # Start pulse animation
        self.animation_timer.start(30)  # ~33 FPS
        
        # Auto-hide after duration
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.hide_animation)
    
    def hide_animation(self):
        """Hide the animation with fade out"""
        # Fade out
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self._glow_opacity)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_fade_complete)
        self.fade_animation.start()
    
    def _on_fade_complete(self):
        """Called when fade out is complete"""
        self.animation_timer.stop()
        self.is_animating = False
        self.hide()
        self.fade_animation.finished.disconnect(self._on_fade_complete)
    
    def update_animation(self):
        """Update animation state"""
        if self.is_animating:
            self.pulse_phase += 0.05
            self._pulse_radius = 100 + (30 * math.sin(self.pulse_phase))
            self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Draw the animation"""
        if self._glow_opacity <= 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get center of screen
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # Draw multiple glowing circles (orb effect)
        for i in range(3):
            radius = self._pulse_radius + (i * 40)
            opacity = self._glow_opacity * (0.3 - i * 0.1)
            
            # Create radial gradient
            gradient = QRadialGradient(center_x, center_y, radius)
            
            # Core glow
            core_color = QColor(self.primary_color)
            core_color.setAlphaF(opacity * 0.8)
            gradient.setColorAt(0.0, core_color)
            
            # Mid glow
            mid_color = QColor(self.secondary_color)
            mid_color.setAlphaF(opacity * 0.4)
            gradient.setColorAt(0.5, mid_color)
            
            # Outer fade
            outer_color = QColor(self.glow_color)
            outer_color.setAlphaF(0)
            gradient.setColorAt(1.0, outer_color)
            
            # Draw circle
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(center_x - radius),
                int(center_y - radius),
                int(radius * 2),
                int(radius * 2)
            )
        
        # Draw central bright core
        core_radius = 30
        core_gradient = QRadialGradient(center_x, center_y, core_radius)
        
        bright_core = QColor(255, 255, 255)
        bright_core.setAlphaF(self._glow_opacity * 0.9)
        core_gradient.setColorAt(0.0, bright_core)
        
        glow_core = QColor(self.primary_color)
        glow_core.setAlphaF(self._glow_opacity * 0.6)
        core_gradient.setColorAt(0.7, glow_core)
        
        transparent = QColor(self.primary_color)
        transparent.setAlphaF(0)
        core_gradient.setColorAt(1.0, transparent)
        
        painter.setBrush(core_gradient)
        painter.drawEllipse(
            int(center_x - core_radius),
            int(center_y - core_radius),
            int(core_radius * 2),
            int(core_radius * 2)
        )
        
        # Draw outer ring (pulsing)
        ring_radius = self._pulse_radius + 60
        ring_pen = QPen(self.primary_color)
        ring_pen.setWidth(3)
        ring_color = QColor(self.primary_color)
        ring_color.setAlphaF(self._glow_opacity * 0.5)
        ring_pen.setColor(ring_color)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            int(center_x - ring_radius),
            int(center_y - ring_radius),
            int(ring_radius * 2),
            int(ring_radius * 2)
        )


class AnimationController:
    """Controller to manage JARVIS animation - Thread-safe"""
    
    def __init__(self):
        # Create QApplication if it doesn't exist (must be on main thread)
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        # DON'T create animation yet - wait until process_events is called
        self.animation = None
        
        self._show_pending = False
        self._hide_pending = False
        self._pending_duration = 3000
    
    def show(self, duration_ms=3000):
        """Show animation for specified duration (milliseconds)"""
        # Just set flags - don't create anything
        self._pending_duration = duration_ms
        self._show_pending = True
    
    def hide(self):
        """Hide animation"""
        # Just set flag
        self._hide_pending = True
    
    def process_events(self):
        """Process Qt events and any pending requests (MUST be called from main thread)"""
        if self.app:
            # Lazy create animation on first use (ensures it's on main thread)
            if self.animation is None and (self._show_pending or self._hide_pending):
                try:
                    self.animation = JarvisAnimation()
                    print("✓ Animation initialized")
                except Exception as e:
                    print(f"⚠️  Could not create animation: {e}")
                    self.animation = None
                    return
            
            # Process any pending show/hide requests
            if self._show_pending and self.animation:
                self._show_pending = False
                self.animation.show_animation(self._pending_duration)
            
            if self._hide_pending and self.animation:
                self._hide_pending = False
                self.animation.hide_animation()
            
            # Process Qt events
            self.app.processEvents()


# Standalone test
def test_animation():
    """Test the animation"""
    controller = AnimationController()
    
    print("Showing JARVIS animation...")
    controller.show(duration_ms=5000)  # Show for 5 seconds
    
    # Keep running until animation finishes
    import time
    for _ in range(60):  # 6 seconds max
        controller.process_events()
        time.sleep(0.1)
    
    print("Animation complete!")


if __name__ == "__main__":
    test_animation()