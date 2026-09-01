import os
import time

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import (
    QAudioFormat, QAudioSource, QMediaDevices, QAudioOutput, QMediaPlayer
)
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget
)

from modules.DataBase import jsonDB
from modules.audiobuffer import AudioBuffer
from modules.voiceLibrary import VoiceLibrary
from component.toast import show_success, show_error, show_info

RECORD_DIR = "storage/recordings"


def format_time(ms):
    ms = max(int(ms or 0), 0)
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class VoiceStudio(QFrame):
    """Record or import a reference clip and turn it into a cloned voice.

    Cloned voices are audio-conditioned voice prompts. They are applied by the
    pocket (E2E-TTS) engine during synthesis.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("VoiceStudio")

        os.makedirs(RECORD_DIR, exist_ok=True)
        self.state = jsonDB()
        self.library = VoiceLibrary()

        self._recorded_pcm = []
        self._recording = False
        self._source = None

        self._build_ui()
        self._refresh_players()
        self.refresh_clones()

        self.apply_styles()

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("VOICE STUDIO")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        root.addWidget(self._build_capture_section())
        root.addWidget(self._build_create_section())
        root.addWidget(self._build_clone_section(), stretch=1)

        hint = QLabel(
            "Cloned voices are built from your reference clip and are applied "
            "by the Pocket (E2E-TTS) engine. Recording uses your default mic."
        )
        hint.setObjectName("HintLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

    def _build_capture_section(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title = QLabel("1 · CAPTURE REFERENCE VOICE")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.btn_record = QPushButton("●  Record")
        self.btn_record.setObjectName("RecordButton")
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.clicked.connect(self.toggle_record)

        self.btn_import = QPushButton("Import audio file")
        self.btn_import.setObjectName("GhostButton")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self.import_clip)

        self.clip_label = QLabel("No clip loaded")
        self.clip_label.setObjectName("ClipLabel")

        self.btn_preview = QPushButton("▶  Play")
        self.btn_preview.setEnabled(False)
        self.btn_preview.setObjectName("GhostButton")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.clicked.connect(self.toggle_preview)

        self.clip_time = QLabel("0:00")
        self.clip_time.setObjectName("TimeLabel")

        row.addWidget(self.btn_record)
        row.addWidget(self.btn_import)
        row.addStretch()
        row.addWidget(self.clip_label)
        row.addWidget(self.btn_preview)
        row.addWidget(self.clip_time)
        layout.addLayout(row)

        # Audio player is created lazily so the splash never freezes.
        self._audio_ready = False
        self._player = None
        self._player_output = None

        return card

    def _build_create_section(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        tag = QLabel("2 · SAVE AS CLONE")
        tag.setObjectName("CardTitle")
        layout.addWidget(tag)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("NameInput")
        self.name_input.setPlaceholderText("e.g. my_audiobook_voice")
        self.name_input.setFixedWidth(240)
        self.name_input.setMaxLength(40)

        self.btn_create = QPushButton("Create voice profile")
        self.btn_create.setObjectName("CreateButton")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setEnabled(False)
        self.btn_create.clicked.connect(self.create_clone)

        layout.addWidget(self.name_input)
        layout.addWidget(self.btn_create)
        layout.addStretch()
        return card

    def _build_clone_section(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title = QLabel("3 · CLONED VOICES")
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameStyle(QFrame.Shape.NoFrame)
        self.scroll.setObjectName("CloneScroll")

        self.clone_container = QWidget()
        self.clone_layout = QVBoxLayout(self.clone_container)
        self.clone_layout.setContentsMargins(0, 0, 0, 0)
        self.clone_layout.setSpacing(8)
        self.clone_layout.addStretch()

        self.scroll.setWidget(self.clone_container)
        layout.addWidget(self.scroll, stretch=1)
        return card

    # ------------------------------------------------------------ recording --
    def _ensure_audio(self):
        """Create the preview player lazily so the splash never freezes."""
        if self._audio_ready:
            return
        self._audio_ready = True
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._player_output = QAudioOutput(self)
            self._player_output.setVolume(0.9)
            self._player.setAudioOutput(self._player_output)
            self._player.playbackStateChanged.connect(self._on_preview_state)
            self._player.durationChanged.connect(
                lambda d: self.clip_time.setText(format_time(d))
            )
        devices = QMediaDevices().audioInputs()
        if not devices:
            self.btn_record.setEnabled(False)

    def toggle_record(self):
        if self._recording:
            self.stop_record()
        else:
            self.start_record()

    def start_record(self):
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            show_error(self.window(), "No microphone available")
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.stop()

        fmt = QAudioFormat()
        fmt.setSampleRate(24000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        if not device.isFormatSupported(fmt):
            show_error(self.window(), "Mic does not support required audio format (16-bit 24kHz)")
            return

        self._recorded_pcm = []
        self._source = QAudioSource(device, fmt)
        self._source.readyRead.connect(self._on_audio_ready)
        self._source.start()

        self._recording = True
        self.btn_record.setText("■  Stop")
        self.btn_record.setObjectName("StopButton")
        self.btn_record.setStyle(self.btn_record.style())
        self.clip_label.setText("Recording...")
        show_info(self.window(), "Recording started - speak clearly")

    def _on_audio_ready(self):
        if self._source is None:
            return
        data = self._source.readAll()
        self._recorded_pcm.append(bytes(data.data()))

    def stop_record(self):
        if self._source is not None:
            self._source.stop()
            self._source.disconnect()
            self._source.deleteLater()
            self._source = None

        self._recording = False
        self.btn_record.setText("●  Record")
        self.btn_record.setObjectName("RecordButton")
        self.btn_record.setStyle(self.btn_record.style())

        pcm = b"".join(self._recorded_pcm)
        if not pcm:
            self.clip_label.setText("No audio captured")
            return

        path = os.path.join(RECORD_DIR, f"rec_{int(time.time())}.wav")
        buf = AudioBuffer(sample_rate=24000, channels=1, sample_width=2)
        buf.add_chunk(pcm)
        buf.save_to_file(path)

        self._load_clip(path, source="mic")
        show_success(self.window(), "Recording saved")

    # -------------------------------------------------------------- import --
    def import_clip(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select reference audio", dir=".",
            filter="Audio (*.wav *.mp3 *.m4a *.flac *.ogg);;All Files (*)"
        )
        if path:
            self._load_clip(path, source="import")

    def _load_clip(self, path, source=""):
        self._ensure_audio()
        self._clip_path = os.path.abspath(path)
        self._clip_source = source
        self.clip_label.setText(f"{os.path.basename(path)} ({source})")
        self.btn_preview.setEnabled(True)
        self.btn_preview.setText("▶  Play")
        self._player.setSource(QUrl.fromLocalFile(self._clip_path))

        # Nudge a name suggestion from the file / timestamp.
        if not self.name_input.text().strip():
            base = os.path.splitext(os.path.basename(path))[0]
            if source == "mic":
                base = f"voice_{time.strftime('%H%M%S')}"
            self.name_input.setText(base)

        if self._player.duration() <= 0:
            self.clip_time.setText("0:00")
        else:
            self.clip_time.setText(format_time(self._player.duration()))

        self._refresh_players()
        self.btn_create.setEnabled(True)

    def toggle_preview(self):
        self._ensure_audio()
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_preview_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.btn_preview.setText("⏸  Pause" if playing else "▶  Play")

    # --------------------------------------------------------------- create --
    def create_clone(self):
        name = self.name_input.text().strip().lower().replace(" ", "_")
        if not name:
            show_error(self.window(), "Give the voice a name first")
            return
        if not getattr(self, "_clip_path", None) or not os.path.exists(self._clip_path):
            show_error(self.window(), "Load a recording or audio file first")
            return

        try:
            self.library.add(name, self._clip_path, source=self._clip_source)
        except Exception as e:
            show_error(self.window(), f"Could not create voice:\n{e}")
            return

        # Cloned voices are consumed by the pocket engine.
        self.state.model = "pocket"
        self.state.voice = name
        self.name_input.clear()
        self.btn_create.setEnabled(False)
        self._refresh_players()
        self.refresh_clones()
        show_success(self.window(), f"Voice '{name}' created and activated")

    def refresh_clones(self):
        # Rebuild the clone list UI.
        while self.clone_layout.count():
            item = self.clone_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        clones = self.library.list()
        if not clones:
            self.clone_layout.addWidget(QLabel("No cloned voices yet"))
            self.clone_layout.addStretch()
            return

        for clone in clones:
            self.clone_layout.addWidget(self._clone_row(clone))
        self.clone_layout.addStretch()

    def _clone_row(self, clone):
        row = QFrame()
        row.setObjectName("CloneRow")

        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        name_label = QLabel(clone["name"])
        name_label.setObjectName("CloneName")

        meta = QLabel(f"· {clone['source']} · {format_time(int(clone.get('created', 0)) * 1000)}")
        meta.setObjectName("CloneMeta")
        meta.setVisible(False)

        btn_use = QPushButton("Use")
        btn_use.setObjectName("UseButton")
        btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_use.clicked.connect(
            lambda _=False, n=clone["name"]: self.activate_clone(n)
        )

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("DeleteButton")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(
            lambda _=False, n=clone["name"]: self.delete_clone(n)
        )

        active = "ACTIVE" if self.state.model == "pocket" and self.state.voice == clone["name"] else ""
        if active:
            tag = QLabel(active)
            tag.setObjectName("ActiveTag")
            layout.addWidget(tag)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(meta)
        layout.addWidget(btn_use)
        layout.addWidget(btn_del)
        return row

    def activate_clone(self, name):
        self.state.model = "pocket"
        self.state.voice = name
        self._refresh_players()
        show_success(self.window(), f"'{name}' is now the active voice")

    def delete_clone(self, name):
        self.library.remove(name)
        if self.state.voice == name:
            self.state.voice = "bella"
        self._refresh_players()
        self.refresh_clones()
        show_info(self.window(), f"Voice '{name}' deleted")

    # ------------------------------------------------------------- helpers ---
    def _refresh_players(self):
        # Keep the (separate) player instances used by... nothing: placeholder.
        pass

    def apply_styles(self):
        self.setStyleSheet("""
            #VoiceStudio { background-color: #0A0A0A; }
            QFrame#Card, QFrame#CloneRow {
                background-color: #121212;
                border: 1px solid #1C1C1E;
                border-radius: 4px;
            }
            QLabel#SectionTitle, QLabel#CardTitle {
                font-family: 'Inter', system-ui, sans-serif;
                font-size: 11px; font-weight: 700; color: #48484A;
                letter-spacing: 1px;
            }
            QLabel#HintLabel {
                color: #48484A; font-size: 11px; font-family: 'Inter', system-ui, sans-serif;
            }
            QLabel#ClipLabel {
                color: #A1A1AA; font-size: 12px; font-family: 'Inter', system-ui, sans-serif;
            }
            QLabel#TimeLabel {
                color: #48484A; font-size: 11px; font-family: 'Inter', system-ui, sans-serif;
            }
            QLabel#CloneName { color: #FFFFFF; font-size: 13px; font-weight: 600;
                font-family: 'Inter', system-ui, sans-serif; }
            QLabel#CloneMeta { color: #48484A; font-size: 10px; font-family: 'Inter', system-ui, sans-serif; }
            QLabel#ActiveTag { color: #34C759; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
            QPushButton {
                font-family: 'Inter', system-ui, sans-serif; font-size: 11px; font-weight: 700;
                border-radius: 3px; padding: 6px 14px; color: #E2E8F0;
                background-color: #161618; border: 1px solid #1C1C1E;
            }
            QPushButton:hover { border-color: #E4E4E7; color: #FFFFFF; }
            QPushButton:pressed { background-color: #E4E4E7; }
            QPushButton#RecordButton { background-color: #7a2b2b; border-color: #a94442; color: #FFFFFF; }
            QPushButton#StopButton  { background-color: #FF453A; border-color: #FF453A; color: #FFFFFF; }
            QPushButton#CreateButton, QPushButton#UseButton { background-color: #E4E4E7; border-color: #E4E4E7; color: #000000; }
            QPushButton#CreateButton:hover, QPushButton#UseButton:hover { background-color: #FFFFFF; }
            QPushButton#DeleteButton { background-color: transparent; border-color: #3a3a3c; color: #7a7a7e; }
            QPushButton#DeleteButton:hover { border-color: #FF453A; color: #FF453A; }
            QLineEdit#NameInput {
                background-color: #121212; border: 1px solid #1C1C1E; border-radius: 3px;
                padding: 8px 10px; color: #FFFFFF; font-size: 12px;
                font-family: 'Inter', system-ui, sans-serif;
            }
            QScrollArea#CloneScroll { background: transparent; border: none; }
            QScrollArea#CloneScroll > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { background: #0A0A0A; width: 6px; border: none; }
            QScrollBar::handle:vertical { background: #1C1C1E; min-height: 24px; border-radius: 3px; }
        """)