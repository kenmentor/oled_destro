from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QSize, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen


class ActionButton(QPushButton):
    """A QPushButton with an animated circular busy spinner.

    While `set_busy(True)` is active, a rotating arc is painted over the button
    so any processing state has clear motion feedback, even while disabled."""
    SPIN_INTERVAL = 90       # ms per tick
    SPIN_STEP = 24           # degrees advanced per tick
    SPIN_SPAN = 240          # arc sweep length in degrees

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._spinner_active = False
        self._spinner_angle = 0
        self._spinner_color = "#FF6B1A"
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(self.SPIN_INTERVAL)
        self._spinner_timer.timeout.connect(self._on_spin_tick)

    def set_busy(self, active: bool, color=None):
        """Toggle the animated spinner; `color` optionally overrides the arc."""
        if color is not None:
            self._spinner_color = color
        active = bool(active)
        if active == self._spinner_active:
            return
        self._spinner_active = active
        if active:
            self._spinner_angle = 0
            self._spinner_timer.start()
        else:
            self._spinner_timer.stop()
        self.update()

    def set_spinner_color(self, color):
        if color != self._spinner_color:
            self._spinner_color = color
            self.update()

    def _on_spin_tick(self):
        self._spinner_angle = (self._spinner_angle + self.SPIN_STEP) % 360
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._spinner_active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 5.0
        cx = self.width() - 14.0
        cy = self.height() / 2.0
        pen = QPen(QColor(self._spinner_color))
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(
            QRectF(cx - r, cy - r, r * 2, r * 2),
            int((self._spinner_angle - 90) * 16),
            int(self.SPIN_SPAN * 16),
        )
        p.end()

class ButtonHolder(QWidget):
    def __init__(self, text, callBack, icon_path=None):
        super().__init__()
        
        # Main Layout for the component
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # The Actual Button
        self.button = ActionButton(text)
        self.button.setCursor(Qt.PointingHandCursor) # Change cursor to hand on hover
        # self.button.setMinimumHeight(45)
        
        # Connect Callback
        self.button.clicked.connect(callBack)
        
        # Apply the "Matured" Styling
        self.apply_styles()
        
        # Add a subtle shadow for depth
        self.add_shadow()

        self.layout.addWidget(self.button)

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30)) # Very faint shadow
        self.button.setGraphicsEffect(shadow)

    def setEnabled(self, status):
        """Override setEnabled to keep logic clean in Screen1"""
        self.button.setEnabled(status)

    def set_text(self, text):
        self.button.setText(text)

    def set_busy(self, on):
        """Show/hide the animated processing spinner on the button."""
        self.button.set_busy(on)

    def set_generate_mode(self, on):
        """Vibrant orange primary button for Generate / Select PDF."""
        if on:
            self.button.set_spinner_color("#1B0A02")
        if on:
            self.button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B1A;
                color: #FFFFFF;
                border: 1px solid #FF6B1A;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'Inter', system-ui, sans-serif;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #FF8A3D; color: #FFFFFF; }
            QPushButton:pressed { background-color: #E0550E; color: #FFFFFF; }
            QPushButton:disabled {
                background-color: transparent; border: 1px solid #1C1C1E; color: #3A3A3C;
            }
            """)

    def set_cancel_mode(self, on):
        """Red button while a generation is running (also cancels on click)."""
        if on:
            self.button.set_spinner_color("#FFFFFF")
        if on:
            self.button.setStyleSheet("""
            QPushButton {
                background-color: #FF3B30;
                color: #FFFFFF;
                border: 1px solid #FF3B30;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'Inter', system-ui, sans-serif;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #E0281E; }
            QPushButton:pressed { background-color: #C02118; }
            """)

    def apply_styles(self):
        self.button.setStyleSheet("""
    QPushButton {
    background-color: #121212;
    color: #E2E8F0;
    border: 1px solid #1C1C1E;
    border-radius: 5px;      
    padding: 8px 16px;            
    font-size: 13px;
    font-family: 'Inter', system-ui, sans-serif;
    font-weight: 700;
    letter-spacing: 0.5px;   
}

QPushButton:hover {
    background-color: #161618;
    border-color: #FF6B1A;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #FF6B1A;
    border-color: #FF6B1A;
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: transparent;
    border-color: #1C1C1E;
    color: #3A3A3C;           
}""")