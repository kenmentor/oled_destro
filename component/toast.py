from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel
)

_CARD = "#17171A"
_BORDER = "#2E2E33"
_TEXT = "#ECEDEE"
_MUTED = "#9A9AA0"

_KIND_ACCENT = {
    "success": QColor("#6EE7A0"),
    "info": QColor("#D7D7DB"),
    "error": QColor("#FF6B66"),
    "warning": QColor("#F2C879"),
}

_TOASTS = []


def _reflow_all():
    per_parent = {}
    for t in _TOASTS:
        per_parent.setdefault(t._parent, []).append(t)
    for parent, toasts in per_parent.items():
        y = parent.height() - 28
        for t in reversed(toasts):
            t.adjustSize()
            x = (parent.width() - t.width()) // 2
            t.move(x, y - t.height())
            y -= t.height() + 12


class Toast(QFrame):
    """A refined, monochrome toast — subtle, minimal, never garish."""

    def __init__(self, message, parent, kind="info", duration=3200):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._parent = parent
        self._duration = duration
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)

        accent = _KIND_ACCENT.get(kind, _KIND_ACCENT["info"])
        self._accent = accent

        self._build_ui(message, accent)

        self.setStyleSheet(f"""
            Toast {{
                background-color: {_CARD};
                border: 1px solid {_BORDER};
                border-radius: 10px;
            }}
        """)

        if parent is not None:
            parent.installEventFilter(self)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.close)

    def _build_ui(self, message, accent):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(
            f"color: {accent.name()}; font-size: 9px; background: transparent;"
        )
        text = QLabel(message)
        text.setStyleSheet(
            f"color: {_TEXT}; font-size: 12px; font-weight: 500; "
            "font-family: 'Inter', system-ui, sans-serif; background: transparent;"
        )
        text.setWordWrap(True)

        layout.addWidget(dot)
        layout.addWidget(text)

    def paintEvent(self, event):
        # small accent bar on the left edge
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        painter.fillPath(path, QColor(_CARD))
        accent = self._accent
        accent.setAlpha(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(0, (self.height() - 18) // 2, 3, 18, 1.5, 1.5)
        painter.end()

    def eventFilter(self, obj, event):
        if obj is self._parent and event.type() == QEvent.Type.Resize:
            _reflow_all()
        return super().eventFilter(obj, event)

    def show(self):
        super().show()
        self.adjustSize()
        self._fade_in.start()
        self._timer.timeout.connect(self.fade_out)
        self._timer.start(self._duration)
        _reflow_all()

    def fade_out(self):
        if self._opacity.opacity() > 0.01:
            self._fade_out.start()
        else:
            self.close()


def show_toast(parent, message, kind="info", duration=3200):
    toast = Toast(message, parent, kind=kind, duration=duration)
    _TOASTS.append(toast)
    toast.show()

    def _cleanup():
        if toast in _TOASTS:
            _TOASTS.remove(toast)
        _reflow_all()

    toast._timer.timeout.connect(_cleanup)
    return toast


def show_success(parent, message):
    return show_toast(parent, message, kind="success")


def show_error(parent, message):
    return show_toast(parent, message, kind="error", duration=5200)


def show_info(parent, message):
    return show_toast(parent, message, kind="info")


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget

    app = QApplication(sys.argv)
    win = QMainWindow()
    central = QWidget()
    win.setCentralWidget(central)
    layout = QVBoxLayout(central)
    btn = QPushButton("Show toasts")
    layout.addWidget(btn)
    win.resize(500, 400)
    win.show()

    from PySide6.QtCore import QTimer
    QTimer.singleShot(300, lambda: (show_success(win, "Audio generated successfully"),
                                    show_error(win, "Engine failed to start")))
    sys.exit(app.exec())