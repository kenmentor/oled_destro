import sys
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QLabel
)


class Spinner(QWidget):
    """Indeterminate circular loading spinner (custom painted, GPU-cheap)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._rotate)
        self._timer.start()

    def _rotate(self):
        self._angle = (self._angle + 4.0) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)

        # Track
        pen_track = QPen(QColor("#26262B"))
        pen_track.setWidthF(4)
        p.setPen(pen_track)
        p.drawEllipse(r)

        # Spinning arc (monochrome white/gray)
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(-self._angle * 16), int(80 * 16))

        p.end()


class SplashScreen(QWidget):
    """Frameless, rounded startup splash with a live spinner + status text."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(440, 260)
        self._fade_out = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(14)

        title = QLabel("OLED DESTRO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; letter-spacing: 2px;")

        subtitle = QLabel("TEXT-TO-SPEECH STUDIO")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #4A5568; letter-spacing: 3px;")

        spinner = Spinner()
        spinner_container = QWidget()
        sl = QVBoxLayout(spinner_container)
        sl.setContentsMargins(0, 8, 0, 8)
        sl.addWidget(spinner, 0, Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Starting up...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #A0AAB0;")

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(spinner_container)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def set_status(self, text):
        self.status_label.setText(text)

    def close_with_fade(self, window, after_ms=250):
        """Fade out the splash then show `window`."""
        if self._fade_out is not None:
            return
        self._fade_out = QTimer(self)
        self._fade_out.setSingleShot(True)
        self._fade_out.timeout.connect(
            lambda: (self.close(), window.show())
        )
        self._fade_out.start(after_ms)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#1B1B1E"))
        grad.setColorAt(1.0, QColor("#0B0B0C"))
        painter.fillPath(path, QBrush(grad))
        # thin neutral accent border
        border = QColor("#2E2E33")
        painter.setPen(border)
        painter.drawPath(path)


if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow
    app = QApplication(sys.argv)
    w = QMainWindow()
    w.resize(600, 400)
    s = SplashScreen()
    s.show()
    QTimer.singleShot(1500, lambda: s.close_with_fade(w))
    sys.exit(app.exec())