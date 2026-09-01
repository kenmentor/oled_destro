from PySide6.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QStackedWidget, QFrame, QPushButton
from component.sidebar_widget import SideBar
from component.left_pannel_widget import leftPannel
from component.screen import Screen1
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

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SideBar()
        self.leftPannel = leftPannel()
        self.sidebar.nav_request.connect(self.route_to_screen)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        #  0 = home   1 = history   2 = plugin   3 = model   4 = voice
        self.home        = Screen1()
        self.history     = HistoryScreen()
        self.pluginScreeen = PluginScreen()
        self.ModelScreen = ModelScreen()
        self.voice       = VoiceStudio()

        self.content_stack.addWidget(self.home)
        self.content_stack.addWidget(self.history)
        self.content_stack.addWidget(self.pluginScreeen)
        self.content_stack.addWidget(self.ModelScreen)
        self.content_stack.addWidget(self.voice)

        # History rows can play their audio in the home-screen player.
        self.history.play_audio.connect(self.home.Audio_player.load)

        # Left-panel model switch reloads the engine with spinner feedback.
        self.leftPannel.model_reload_request.connect(self.home.loader.switch_model)
        self.home.loader.switch_finished.connect(self.leftPannel.on_model_switched)

        # Generation progress surfaces on the left config panel's small bar.
        self.home.bind_progress_bar(self.leftPannel.progress_bar)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack)
        main_layout.addWidget(self.leftPannel)
        self.apply_styles()

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