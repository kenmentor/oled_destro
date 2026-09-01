import os
import sys
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot
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

    def run(self):
        try:
            import torch
            _mark("torch imported")
            torch.set_num_threads(os.cpu_count() or 4)
            torch.set_num_interop_threads(1)
            import widgets.main_widget  # noqa: F401
            _mark("widgets imported")
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
        self.preloader.start()

    @Slot()
    def _build(self):
        _mark("preloader ready, building window")
        from widgets.main_widget import mainWindow

        self.window = mainWindow(app)
        _mark("window built")
        home = self.window.home
        # Bind the splash so the engine-ready signal can close it.
        self.window._splash = self.splash
        home.loader.progress.connect(self.splash.set_status)
        home.loader.finished.connect(self.window.finish_startup)

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