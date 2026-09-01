from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QStackedWidget, QFrame, QPushButton, QMessageBox
from component.sidebar_widget import SideBar
from component.left_pannel_widget import leftPannel
from component.screen import Screen1
from component.toast import show_info
from component.audioplayer import AudioPlayer
from PySide6.QtCore import Qt
from component.voice_screen import VoiceStudio
from component.history_screen import HistoryScreen
from component.plugin_screen import PluginScreen
from component.models import ModelScreen


class mainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
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
        app.processEvents()
        self.leftPannel = leftPannel()
        app.processEvents()

        self.sidebar.nav_request.connect(self.route_to_screen)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        # Shared music-player overlay — spans full width and is present on every screen.
        self.music_player = AudioPlayer()

        #  0 = home   1 = history   2 = plugin   3 = model   4 = voice
        self.home = Screen1(self.music_player)
        import sys; print("[mainwindow] home built", flush=True)
        self.history = HistoryScreen()
        import sys; print("[mainwindow] history built", flush=True)
        self.pluginScreeen = PluginScreen()
        import sys; print("[mainwindow] plugin built", flush=True)
        self.ModelScreen = ModelScreen()
        import sys; print("[mainwindow] model built", flush=True)
        self.voice = VoiceStudio()
        import sys; print("[mainwindow] voice built", flush=True)

        self.content_stack.addWidget(self.home)
        self.content_stack.addWidget(self.history)
        self.content_stack.addWidget(self.pluginScreeen)
        self.content_stack.addWidget(self.ModelScreen)
        self.content_stack.addWidget(self.voice)

        # History rows can play their audio in the home-screen player.
        self.history.play_audio.connect(self.home.Audio_player.load)

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

    def _on_model_reload_request(self, model_name):
        if getattr(self.home, "_generating", False):
            self.home._pending_model = model_name
            self.home.updateprogress(f"Switching to {model_name} — queued")
            show_info(self.window(), "Finish generation first — model will switch next")
            return
        self.home.loader.switch_model(model_name)

    def route_to_screen(self, target_index):
        print("[route_to_screen]->", target_index)
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
        """)