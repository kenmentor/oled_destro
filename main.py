import os
import sys
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

_START = time.monotonic()


def _mark(label):
    print(f"[startup] {label}: {time.monotonic() - _START:6.2f}s", flush=True)


class Preloader(QThread):
    """Imports the heavy modules (torch, kokoro, pocket-tts, PyMuPDF...) off the
    GUI thread so the splash stays responsive. Only imports happen here -- no
    QWidget creation -- so thread affinity is never violated."""

    ready = Signal()
    failed = Signal(str)
    # Real progress (0-100) + status text while the splash is showing
    progress = Signal(int, str)

    def run(self):
        try:
            self.progress.emit(5, "Importing ML libraries (slow first run)...")
            import torch
            _mark("torch imported")
            torch.set_num_threads(os.cpu_count() or 4)
            torch.set_num_interop_threads(1)
            self.progress.emit(45, "Importing AI engine...")
            import component.main_window  # noqa: F401
            _mark("widgets imported")
            self.progress.emit(80, "Building interface...")
            self.ready.emit()
        except Exception as e:
            self.failed.emit(repr(e))
            import traceback
            traceback.print_exc()


class StartupController(QObject):
    """GUI-thread owner of the startup sequence. Its slots are delivered queued
    to the GUI thread, so it is always safe to build QWidgets here."""

    def __init__(self, splash):
        super().__init__()
        self.splash = splash
        self.preloader = Preloader()
        self.preloader.ready.connect(self._build)
        self.preloader.failed.connect(self._failed)
        self.preloader.progress.connect(self.splash.set_progress)
        self.preloader.start()

    @Slot()
    def _build(self):
        _mark("preloader ready, building window")
        from component.main_window import mainWindow

        self.window = mainWindow(app)
        _mark("window built")
        # Splash reflects 100% once the window is fully constructed; the engine
        # loads after the window is shown, triggered by its show event.
        self.splash.set_progress(100, "Ready")
        self.splash.close_with_fade(self.window, after_ms=100)

    @Slot(str)
    def _failed(self, message):
        self.splash.set_status(f"Startup failed: {message}")
        print("OLED DESTRO failed to start:", message)
        QApplication.quit()


from component.splash_screen import SplashScreen

splash = SplashScreen()
splash.show()
_mark("splash shown")
controller = StartupController(splash)

sys.exit(app.exec())