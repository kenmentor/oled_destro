import sys 
import os 
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QFileDialog, 
                                QLabel, QProgressBar, QComboBox, QWidget)
from PySide6.QtCore import Slot, QThreadPool, Qt,QThread

from component.buttons.action import ButtonHolder
from modules.documentToTextModule import DocumentToText
from component.textEditor import TextEdit
from component.engineloader import Worker, ModelTask
from modules.utils import Utils
from modules.DataBase import jsonDB, modelDB
from component.audioplayer import AudioPlayer 
from component.toast import show_success, show_error, show_info 
from modules.voiceLibrary import VoiceLibrary 

document_tool = DocumentToText()
utils = Utils()
stateBase = jsonDB()

class Screen1(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Screen1")
        
        # --- 1. Main Layout & Container ---
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(16)
        self.progress_count = 0 

        # --- 2. Header Section (Title & Select) ---
        self.footer = QFrame()
        self.header_layout = QHBoxLayout(self.footer)
        self.header_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Initializing AI Engine...")
        self.status_label.setObjectName("StatusLabel")
        
        self.btn_home = ButtonHolder("Select PDF", self.selectFile)
        self.btn_home.setFixedWidth(120)
        self.btn_home.setObjectName("PrimaryAction")

        self.btn_continue = ButtonHolder("Generate Audio", self.toggle_generate)
        self.btn_continue.setEnabled(False) 
        self.btn_continue.setFixedWidth(150)  
        self.btn_continue.setFixedHeight(34)

        self.header_layout.addWidget(self.btn_continue)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.btn_home)
        
        self.Audio_player = AudioPlayer()

        self.editor = TextEdit()
        self.editor.setObjectName("MainEditor")
        self.editor.textChanged.connect(self.update_document_text)
        self.editor.setFrameStyle(QFrame.Shape.NoFrame)

        # --- Footer (voice dropdown only; progress moved to the config panel) ---
        self.header = QFrame()
        self.footer_layout = QHBoxLayout(self.header)
        self.footer_layout.setContentsMargins(0, 8, 0, 0)
        self.footer_layout.setSpacing(10)
        
        self.select_voice = QComboBox()
        self.select_voice.setObjectName("VoiceDropdown")
        self.select_voice.setFixedWidth(200)
        self.select_voice.setFixedHeight(34)
        self.select_voice.currentIndexChanged.connect(self.onindexChange)
        self.select_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.loadVoice()  

        self.header.setObjectName("footer")
        self.footer_layout.addWidget(self.select_voice)
        self.footer_layout.addStretch()

        # Progress is surfaced on the left config panel's small bar.
        self._progress_target = None

        # --- Assemble Main Layout ---
        self.root_layout.addWidget(self.footer)
        self.root_layout.addWidget(self.editor, stretch=1)
        self.root_layout.addWidget(self.Audio_player)
        

        # --- Threading Setup ---
        self.threadpool = QThreadPool.globalInstance()
        self.init_engine_worker()
        
        self.apply_styles()

    def onindexChange(self, index):
        # Use the plain stored value (item data), not the display badge text.
        voice = self.select_voice.itemData(index)
        if voice is None:
            voice = self.select_voice.currentText()
        stateBase.voice = voice
        display = self.select_voice.currentText()
        # Pocket voices (defaults or clones) only work with the pocket engine.
        if self.is_pocket_voice(voice) and stateBase.model != "pocket":
            show_info(self.window(), f"'{display}' needs the Pocket engine - switching model")
            stateBase.model = "pocket"
            self.loadVoice()

    @staticmethod
    def is_clone_voice(voice):
        return VoiceLibrary().exists(voice)

    @staticmethod
    def is_pocket_voice(voice):
        """True if the voice lives only in the pocket engine (default or clone)."""
        from modules.ttsEgine import POCKET
        if POCKET.default_voice_path(voice):
            return True
        return VoiceLibrary().exists(voice)

    def loadVoice(self):
        voices = []
        current_model = stateBase.model
        try:
            if current_model == "pocket":
                # Pre-installed default voices + user clones.
                from modules.ttsEgine import POCKET
                voices = list(POCKET.list_default_voices())
            else:
                voices = utils.get_voice("./modules/voices")
        except Exception as e:
            print(f"[Engine Fallback Warning]: {e}")

        clones = VoiceLibrary().names()
        for clone in clones:
            if clone not in voices:
                voices.append(clone)

        self.select_voice.blockSignals(True)
        self.select_voice.clear()
        for idx, voice in enumerate(voices):
            is_clone = VoiceLibrary().exists(voice)
            label = voice if not is_clone else f"{voice} (clone)"
            self.select_voice.addItem(label, voice)
        if self.select_voice.count() == 0:
            self.select_voice.addItem("No voice available - create a clone", "")
            self.select_voice.setEnabled(False)
        else:
            self.select_voice.setEnabled(True)
        self.select_voice.blockSignals(False)

        # Select the currently configured voice if present
        current = stateBase.voice
        idx = self.select_voice.findData(current)
        self.select_voice.setCurrentIndex(idx if idx >= 0 else 0)

    def apply_styles(self):
        self.setStyleSheet("""
            #Screen1 { background-color: #0A0A0A; }
            QLabel#StatusLabel {
                font-size: 12px; font-weight: 600; color: #48484A;
                font-family: 'Inter', system-ui, sans-serif; letter-spacing: 0.5px;
            }
            #footer { margin: 0px; padding: 0px; }
            #MainEditor {
                background-color: #121212; border: 1px solid #1C1C1E;
                border-radius: 0px; padding: 12px; color: #FFFFFF; 
                font-size: 13px; font-family: 'Inter', system-ui, sans-serif;
            }
            #AppProgress {
                background-color: #121212; border: 1px solid #1C1C1E;
                border-radius: 0px; font-size: 10px; color: white;
            }
            #AppProgress::chunk { background-color: #E4E4E7; border-radius: 0px; }
            QComboBox#VoiceDropdown {
                background-color: #121212; border: 1px solid #1C1C1E; border-radius: 0px;
                padding-left: 10px; color: #FFFFFF; font-size: 12px; font-weight: 600;
            }
            QComboBox#VoiceDropdown:hover { border-color: #E4E4E7; }
            QComboBox#VoiceDropdown::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right;
                width: 26px; border-left: 1px solid #1C1C1E;
            }
            QComboBox#VoiceDropdown QAbstractItemView {
                background-color: #121212; border: 1px solid #1C1C1E;
                color: #A1A1AA; selection-background-color: #E4E4E7; selection-color: #000000;
            }
            QPushButton {
                font-family: 'Inter', system-ui, sans-serif; font-size: 11px;
                font-weight: 700; border-radius: 0px; padding: 6px 12px;
            }
            QPushButton#PrimaryAction { background-color: #121212; border: 1px solid #1C1C1E; color: #E2E8F0; }
            QPushButton#PrimaryAction:hover { background-color: #161618; border-color: #2C2C2E; color: #FFFFFF; }
        """)
        # Generate and Select PDF use the white-on-black active style.
        self.btn_continue.set_generate_mode(True)
        self.btn_home.set_generate_mode(True)

    def init_engine_worker(self):
        # Using a distinct dedicated thread strictly for initializing the engine
        self.engine_thread = QThread()
        self.loader = Worker()
        self.loader.moveToThread(self.engine_thread)
        self.engine_thread.started.connect(self.loader.worker_job) 
        self.loader.progress.connect(self.status_label.setText)
        self.loader.finished.connect(self.on_engine_ready)
        self.engine_thread.start()

    @Slot(object)
    def on_engine_ready(self, engine):
        if engine is None:
            self.status_label.setText("Engine failed to load")
            show_error(self.window(), "AI engine failed to load. Check the model files and try again.")
            return
        self.tts_engine = engine
        self.status_label.setText("AI Engine Ready")
        self.btn_continue.setEnabled(True)
        show_success(self.window(), "AI engine ready")
        
    def updateprogress(self, message):
        self.status_label.setText(message)

    def bind_progress_bar(self, bar):
        self._progress_target = bar

    def _progress_bar(self):
        return self._progress_target

    def updateProgressCounter(self, count):
        print(f"[updateProgressCounter]->count {count}")
        bar = self._progress_bar()
        if bar is None:
            return
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        bar.setValue(count)
        
    def selectFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self, dir=".",
            filter="Documents (*.pdf *.docx *.txt);;All Files (*)"
        )
        if file_path:
            self.updateprogress(f"Processing: {os.path.basename(file_path)}...")
            show_info(self.window(), f"Extracting text from {os.path.basename(file_path)}...")
            worker = ModelTask(document_tool.process_document, file_path)
            worker.signals.finished.connect(self.loadText)
            worker.signals.error.connect(lambda err: show_error(self.window(), f"Could not read document:\n{err}"))
            self.threadpool.start(worker)
            
    @Slot()
    def update_document_text(self):
        text = self.editor.toPlainText()
        document_tool.update_text(text)
        
    def loadText(self, text=""):
        self.editor.setPlainText(text)
        show_success(self.window(), f"Document loaded ({len(text or '')} characters)")

    def toggle_generate(self):
        """Runs generation, or cancels an in-progress run (button turns red)."""
        if getattr(self, "_generating", False):
            self.cancel_generation()
            return
        self.generate()

    def generate(self):
        if not hasattr(self, 'tts_engine'):
            self.updateprogress("Error: Engine not loaded")
            show_error(self.window(), "AI engine is not ready yet. Please wait.")
            return

        text = document_tool.get_all_chunks()
        if not text:
            self.updateprogress("No text found to synthesize")
            show_error(self.window(), "No text found to synthesize. Load a document first.")
            return

        selected_voice_id = stateBase.voice
        print(f"[Synthesizer Directive] Extracting stream data using Model ID: {selected_voice_id}")

        # Pocket voice must be a default or cloned voice; kokoro needs a .pt file.
        if stateBase.model == "pocket" and not self.is_pocket_voice(selected_voice_id):
            show_error(
                self.window(),
                "Pocket model needs a voice. Pick one of the defaults or create a clone.",
            )
            self.updateprogress("No usable voice selected for Pocket model")
            return

        # Setting up the task and passing signals as a tracking object keyword arg
        import threading
        self._cancel_event = threading.Event()
        worker = ModelTask(
            self.loader.process_synthesis,
            text, signals=None, model=stateBase.model,
            cancel_event=self._cancel_event,
        )
        worker.signals.progress.connect(self.updateprogress)
        worker.signals.finished.connect(self.on_synthesis_complete)
        worker.signals.count.connect(self.updateProgressCounter)
        worker.signals.chunk_ready.connect(self.on_synthesis_chunk_ready)
        worker.signals.error.connect(lambda err: show_error(self.window(), f"Generation failed:\n{err}"))

        self._generating = True
        self.btn_continue.setEnabled(True)
        self.btn_continue.set_text("Cancel")
        self.btn_continue.set_cancel_mode(True)
        self.threadpool.start(worker)

    def cancel_generation(self):
        if getattr(self, "_cancel_event", None) is not None:
            self._cancel_event.set()
            self.updateprogress("Cancelling…")

    def on_synthesis_chunk_ready(self, path):
        """Start playing the growing WAV as soon as the first audio is written."""
        self.Audio_player.load_live(path)

    def on_synthesis_complete(self, result):
        bar = self._progress_bar()
        if bar is not None:
            bar.setValue(0)
            bar.setRange(0, 1)
        self._generating = False
        self.btn_continue.set_text("Generate Audio")
        self.btn_continue.set_generate_mode(True)
        self.btn_continue.setEnabled(True)
        # Reclaim RAM. Kokoro/pytorch grows slightly on every run (known leak,
        # #152) and the slowdown tracks memory growth - so periodically rebuild
        # the engine to reset it and keep generation fast.
        import gc
        gc.collect()
        self._gen_count = getattr(self, "_gen_count", 0) + 1
        if result and self._gen_count >= 4 and hasattr(self, "loader"):
            self._gen_count = 0
            self.status_label.setText("Refreshing engine…")
            self.loader.switch_model(stateBase.model)
        if result:
            self.updateprogress("Synthesis Complete!")
            self.Audio_player.load(result)
            show_success(self.window(), "Audio generated and ready to play")
        else:
            cancelled = getattr(self, "_cancel_event", None) is not None \
                and self._cancel_event.is_set()
            self._cancel_event = None
            if cancelled:
                self.updateprogress("Generation cancelled")
                show_info(self.window(), "Generation cancelled")
            else:
                self.updateprogress("No audio was generated")
                show_error(self.window(), "Synthesis produced no audio")