from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QStackedWidget, QFrame, QPushButton, QMessageBox
from component.sidebar_widget import SideBar
from component.left_pannel_widget import leftPannel
from component.screen import Screen1
from component.toast import show_info
from component.audioplayer import AudioPlayer
from PySide6.QtCore import Qt, QTimer


class mainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        import time as _t
        _t0 = _t.monotonic()
        def _m(label):
            print(f"[build] {label}: {_t.monotonic()-_t0:6.2f}s", flush=True)
        self.setWindowTitle("Oled DESTRO")
        self.resize(1200, 800)

        central_widget = QWidget()
        central_widget.setObjectName("MainWindow")
        self.setCentralWidget(central_widget)

        # Full-height layout: top row (sidebar | content | left panel) + full-width music bar at bottom.
        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.sidebar = SideBar()
        _m("sidebar")
        app.processEvents()
        self.leftPannel = leftPannel()
        _m("leftPannel")
        app.processEvents()

        self.sidebar.nav_request.connect(self.route_to_screen)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        # Shared music-player overlay — spans full width and present on every screen.
        self.music_player = AudioPlayer()
        _m("audioplayer")

        #  0 = home   1 = history   2 = plugin   3 = model   4 = voice
        # Only create home immediately; other screens are lazy-loaded on first navigation.
        self.home = Screen1(self.music_player)
        _m("home")

        self._history = None
        self._plugin = None
        self._model = None
        self._voice = None

        self.content_stack.addWidget(self.home)

        # History rows can play their audio in the home-screen player.
        self._get_history()
        _m("history")

        top_layout.addWidget(self.sidebar)
        top_layout.addWidget(self.content_stack)
        top_layout.addWidget(self.leftPannel)
        outer_layout.addLayout(top_layout)
        outer_layout.addWidget(self.music_player)

        # Left-panel model switch reloads the engine with spinner feedback.
        # If a switch is requested while a generation is in progress, queue it.
        self.leftPannel.model_reload_request.connect(self._on_model_reload_request)
        self.home.loader.switch_finished.connect(self.leftPannel.on_model_switched)

        # Generation progress surfaces on the left config panel's small bar.
        self.home.bind_progress_bar(self.leftPannel.progress_bar)

        self.apply_styles()
        app.processEvents()
        print("[mainwindow] init done", flush=True)

    def _get_history(self):
        if self._history is None:
            from component.history_screen import HistoryScreen
            self._history = HistoryScreen()
            self._history.play_audio.connect(self.home.Audio_player.load)
            self.content_stack.insertWidget(1, self._history)
        return self._history

    def _get_plugin(self):
        if self._plugin is None:
            from component.plugin_screen import PluginScreen
            self._plugin = PluginScreen()
            self.content_stack.insertWidget(2, self._plugin)
        return self._plugin

    def _get_model(self):
        if self._model is None:
            from component.models import ModelScreen
            self._model = ModelScreen()
            self.content_stack.insertWidget(3, self._model)
        return self._model

    def _get_voice(self):
        if self._voice is None:
            from component.voice_screen import VoiceStudio
            self._voice = VoiceStudio()
            self.content_stack.insertWidget(4, self._voice)
        return self._voice

    def _on_model_reload_request(self, model_name):
        if getattr(self.home, "_generating", False):
            self.home._pending_model = model_name
            self.home.updateprogress(f"Switching to {model_name} — queued")
            show_info(self.window(), "Finish generation first — model will switch next")
            return
        self.home.loader.switch_model(model_name)

    def route_to_screen(self, target_index):
        print("[route_to_screen]->", target_index)
        # Ensure the target screen exists before switching
        if target_index == 1:
            self._get_history()
        elif target_index == 2:
            self._get_plugin()
        elif target_index == 3:
            self._get_model()
        elif target_index == 4:
            self._get_voice()
        self.content_stack.setCurrentIndex(target_index)
        # The configuration sidebar only belongs on the home screen.
        self.leftPannel.setVisible(target_index == 0)
        # Refresh the home-screen voice list whenever we land on it
        if target_index == 0 and hasattr(self, 'home'):
            self.home.loadVoice()

    def finish_startup(self, *args):
        """Close the splash and reveal the main window (main-thread only)."""
        splash = getattr(self, "_splash", None)
        if splash is not None:
            splash.close_with_fade(self, after_ms=250)

    def showEvent(self, event):
        """Start loading the TTS engine only once the UI is fully shown/usable."""
        super().showEvent(event)
        if not getattr(self, "_engine_started", False):
            self._engine_started = True
            QTimer.singleShot(200, self.start_engine_loading)

    def start_engine_loading(self):
        """Start loading the TTS engine after the UI is responsive."""
        home = self.home
        # Progress text → status label; numeric step → determinate 0-100% bar.
        home.loader.progress.connect(home.status_label.setText)
        home.loader.finished.connect(home.on_engine_ready)
        # Start the engine thread
        home.init_engine_worker()

    def apply_styles(self):
        self.setStyleSheet("""
            #MainWindow { background-color: #0A0A0A; }
            SideBar { background-color: #060606; border-right: 1px solid #1E2230; }
            #ContentStack { background-color: transparent; }
            QWidget {
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 14px;
                color: #2D3436;
            }
            /* No ugly focus rectangle when clicking buttons/combos. */
            QPushButton:focus, QComboBox:focus, QListView:focus {
                outline: none;
            }
        """)