import sys
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QLabel, QProgressBar
)


class SplashScreen(QWidget):
    """Frameless, rounded startup splash with a progress bar + status text."""

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

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1B1B1E;
                border: 1px solid #2E2E33;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #FF6B1A; /* vibrant orange accent */
                border-radius: 3px;
            }
        """)

        self.status_label = QLabel("Starting up...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #A0AAB0;")

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def set_progress(self, value, text=None):
        """Set the progress bar to a real percentage and (optionally) status text."""
        self.progress_bar.setValue(max(0, min(100, int(value))))
        if text is not None:
            self.status_label.setText(text)

    def set_status(self, text):
        """Update only the status text without guessing a percentage."""
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
        # thin orange accent border
        border = QColor("#7A310B")
        painter.setPen(border)
        painter.drawPath(path)
        # vibrant orange accent line across the top edge
        accent = QColor("#FF6B1A")
        painter.setPen(accent)
        painter.drawLine(
            int(self.width() * 0.18), 2, int(self.width() * 0.82), 2
        )


if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow
    app = QApplication(sys.argv)
    w = QMainWindow()
    w.resize(600, 400)
    s = SplashScreen()
    s.show()
    QTimer.singleShot(1500, lambda: s.close_with_fade(w))
    sys.exit(app.exec())