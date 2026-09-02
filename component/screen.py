import sys 
import os 
import uuid as _uuid
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QFileDialog, 
                                QLabel, QProgressBar, QComboBox, QWidget, QApplication,
                                QMessageBox)
from PySide6.QtCore import Slot, QThreadPool, Qt, QThread, QTimer


def uuid4_hex():
    return _uuid.uuid4().hex[:12]

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
    def __init__(self, audio_player=None):
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
        
        self.Audio_player = audio_player if audio_player is not None else AudioPlayer()

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

        # Optional shared music-player overlay (injected by main_window).
        self._pending_model = None

        # --- Threading Setup ---
        self.threadpool = QThreadPool.globalInstance()
        # Initialize loader (but don't start thread yet - done in mainWindow.start_engine_loading)
        self.engine_thread = QThread()
        self.loader = Worker()
        self.loader.moveToThread(self.engine_thread)
        # Smooth determinate animation for the engine/model-load progress bar.
        self._load_target = 0
        self._load_anim = QTimer(self)
        self._load_anim.setInterval(30)
        self._load_anim.timeout.connect(self._tick_load_anim)
        self.loader.step.connect(self._on_engine_step)
        import sys; print("[screen1] init done", flush=True)
        
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
        # Thread and loader already created in __init__; just connect signals and start.
        self.engine_thread.started.connect(self.loader.worker_job)
        self.engine_thread.start()

    @Slot(object)
    def on_engine_ready(self, engine):
        if engine is None:
            self.status_label.setText("Engine failed to load")
            bar = self._progress_bar()
            if bar is not None:
                bar.hide()
                bar.setRange(0, 1)
                bar.setValue(0)
            self._load_anim.stop()
            show_error(self.window(), "AI engine failed to load. Check the model files and try again.")
            return
        self.tts_engine = engine
        self.status_label.setText("AI Engine Ready")
        self.btn_continue.setEnabled(True)
        # Ensure the load bar reaches 100%, then tuck it away.
        self._load_target = 100
        if not self._load_anim.isActive():
            self._load_anim.start()
        QTimer.singleShot(600, self._hide_load_bar)
        show_success(self.window(), "AI engine ready")
        # Offer to resume a generation that was interrupted by a crash/shutdown.
        if not getattr(self, "_recovery_checked", False):
            self._recovery_checked = True
            QTimer.singleShot(800, self._prompt_resume)
        
    def updateprogress(self, message):
        self.status_label.setText(message)

    def bind_progress_bar(self, bar):
        self._progress_target = bar
        bar.hide()

    def _progress_bar(self):
        return self._progress_target

    @Slot(int, str)
    def _on_engine_step(self, pct, msg):
        """Determinate 0-100% progress for the engine/model load."""
        self.status_label.setText(msg)
        self._load_target = max(0, min(100, int(pct)))
        bar = self._progress_bar()
        if bar is None:
            return
        bar.show()
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        if not self._load_anim.isActive():
            self._load_anim.start()

    def _tick_load_anim(self):
        """Ease the bar value toward the latest checkpoint so it visibly climbs."""
        bar = self._progress_bar()
        if bar is None:
            self._load_anim.stop()
            return
        cur = bar.value()
        target = self._load_target
        if cur < target:
            step = max(1, (target - cur) // 10)
            bar.setValue(min(target, cur + step))
        if cur >= target:
            self._load_anim.stop()

    def _hide_load_bar(self):
        bar = self._progress_bar()
        if bar is not None:
            bar.hide()
            bar.setRange(0, 1)
            bar.setValue(0)

    def _on_loader_progress(self, msg):
        """Show/hide the progress bar to reflect the app loading state."""
        bar = self._progress_bar()
        if bar is None:
            return
        if "Loading" in msg:
            bar.show()
            bar.setRange(0, 0)
            bar.setTextVisible(False)
            bar.setValue(0)
        elif "Ready" in msg:
            bar.hide()
            bar.setRange(0, 1)
            bar.setValue(0)

    def updateProgressCounter(self, count):
        print(f"[updateProgressCounter]->count {count}")
        bar = self._progress_bar()
        if bar is None:
            return
        bar.show()
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        bar.setValue(count)
        
    def selectFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self, dir=".",
            filter="Documents (*.pdf *.docx *.txt);;All Files (*)"
        )
        if file_path:
            self.updateprogress(f"Loading: {os.path.basename(file_path)}...")
            bar = self._progress_bar()
            if bar is not None:
                bar.show()
                bar.setRange(0, 0)
                bar.setTextVisible(False)
                bar.setValue(0)
            worker = ModelTask(document_tool.process_document, file_path)
            worker.signals.finished.connect(self.loadText)
            worker.signals.error.connect(lambda err: self._on_load_error(err))
            self.threadpool.start(worker)

    def _on_load_error(self, err):
        bar = self._progress_bar()
        if bar is not None:
            bar.hide()
            bar.setRange(0, 1)
            bar.setValue(0)
        show_error(self.window(), f"Could not read document:\n{err}")

    @Slot()
    def update_document_text(self):
        text = self.editor.toPlainText()
        document_tool.update_text(text)

    def loadText(self, text=""):
        bar = self._progress_bar()
        if bar is not None:
            bar.hide()
            bar.setRange(0, 1)
            bar.setValue(0)
        self.editor.setPlainText(text)
        show_success(self.window(), f"Document loaded ({len(text or '')} characters)")

    def _set_generate_mode(self, normal=True):
        """Reset the Generate/Cancel button to a known idle state."""
        self.btn_continue.set_text("Generate Audio")
        self.btn_continue.set_generate_mode(True)
        self.btn_continue.setEnabled(True)
        self._generating = False

    def toggle_generate(self):
        """Runs generation, or stops an in-progress run (button turns red)."""
        if getattr(self, "_generating", False):
            self.stop_generation()
            return
        self.generate()

    def generate(self):
        if not hasattr(self, 'tts_engine'):
            self.updateprogress("Error: Engine not loaded")
            show_error(self.window(), "AI engine is not ready yet. Please wait.")
            return

        # --- React instantly so the UI feels responsive before any heavy work ---
        self.status_label.setText("Preparing generation...")
        self.btn_continue.setEnabled(False)
        self.btn_continue.set_text("Preparing...")
        QApplication.processEvents()

        try:
            text = document_tool.get_all_chunks()
        except Exception as e:
            self.updateprogress("Error reading text")
            self._set_generate_mode()
            show_error(self.window(), f"Could not read document text:\n{e}")
            return
        if not text:
            self.updateprogress("No text found to synthesize")
            self._set_generate_mode()
            show_error(self.window(), "No text found to synthesize. Load a document first.")
            return
        QApplication.processEvents()

        selected_voice_id = stateBase.voice
        print(f"[Synthesizer Directive] Extracting stream data using Model ID: {selected_voice_id}")

        # Pocket voice must be a default or cloned voice; kokoro needs a .pt file.
        if stateBase.model == "pocket" and not self.is_pocket_voice(selected_voice_id):
            show_error(
                self.window(),
                "Pocket model needs a voice. Pick one of the defaults or create a clone.",
            )
            self._set_generate_mode()
            self.updateprogress("No usable voice selected for Pocket model")
            return

        # Setting up the task and passing signals as a tracking object keyword arg
        import threading
        from modules.recovery import GenerationJob
        # Reserve a stable output path now so recovery knows exactly where the
        # WAV will be written, and persist an "active" job for crash recovery.
        out_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"synth_{uuid4_hex()}.wav")
        job = GenerationJob(
            job_id=os.path.splitext(os.path.basename(out_path))[0],
            chunks=text, voice=selected_voice_id, model=stateBase.model,
            out_path=out_path, status="active",
        )
        job.save()
        self._active_job = job

        self._cancel_event = threading.Event()
        worker = ModelTask(
            self.loader.process_synthesis,
            text, signals=None, model=stateBase.model,
            cancel_event=self._cancel_event, job=job,
        )
        worker.signals.progress.connect(self.updateprogress)
        worker.signals.finished.connect(self.on_synthesis_complete)
        worker.signals.count.connect(self.updateProgressCounter)
        worker.signals.chunk_ready.connect(self.on_synthesis_chunk_ready)
        # Any error must also reset the UI so the button never stays stuck.
        worker.signals.error.connect(
            lambda err: (show_error(self.window(), f"Generation failed:\n{err}"),
                         self.on_synthesis_complete(None))
        )

        # Show combining/streaming progress bar and switch to Stop.
        bar = self._progress_bar()
        if bar is not None:
            bar.show()
            bar.setRange(0, 0)
            bar.setTextVisible(False)
            bar.setValue(0)
        self.status_label.setText("Extracting stream data...")
        self._generating = True
        self.btn_continue.setEnabled(True)
        self.btn_continue.set_text("Stop Generation")
        self.btn_continue.set_cancel_mode(True)
        QApplication.processEvents()
        self.threadpool.start(worker)

    def stop_generation(self):
        """Request a stop of the in-progress run; button shows 'Stopping…' until done."""
        if not getattr(self, "_generating", False):
            return
        if getattr(self, "_cancel_event", None) is None:
            return
        self._cancel_event.set()
        self.btn_continue.set_text("Stopping…")
        self.btn_continue.setEnabled(False)
        self.updateprogress("Stopping generation…")
        show_info(self.window(), "Stopping generation…")

    def on_synthesis_chunk_ready(self, path):
        """Start playing the growing WAV as soon as the first audio is written."""
        self.Audio_player.load_live(path)

    def on_synthesis_complete(self, result):
        bar = self._progress_bar()
        if bar is not None:
            bar.setValue(0)
            bar.setRange(0, 1)
            bar.hide()
        self._generating = False
        self.btn_continue.set_text("Generate Audio")
        self.btn_continue.set_generate_mode(True)
        self.btn_continue.setEnabled(True)
        # Apply a model switch that was requested while generating.
        pending = getattr(self, "_pending_model", None)
        if pending:
            self._pending_model = None
            self.loader.switch_model(pending)
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

    # --- crash recovery -----------------------------------------------------
    def _prompt_resume(self):
        """If an interrupted generation was found, ask the user whether to resume."""
        from modules.recovery import latest_active
        job = latest_active()
        if job is None:
            return
        if not os.path.exists(job.out_path):
            job.remove()
            return
        ret = QMessageBox.information(
            self.window(),
            "Recover last generation",
            "Found an interrupted generation.\n\n"
            f"{os.path.basename(job.out_path)}\n"
            f"({job.completed}/{len(job.chunks)} chunks saved — partial audio is playable & downloadable)\n\n"
            "Resume it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.resume_last_generation(job)

    def resume_last_generation(self, job=None):
        """Continue a previously interrupted generation from the last saved chunk."""
        if job is None:
            from modules.recovery import latest_active
            job = latest_active()
        if job is None:
            self.updateprogress("No recovery job found")
            return False
        if not os.path.exists(job.out_path):
            job.remove()
            self.updateprogress("Recovery audio is missing")
            return False

        self.status_label.setText("Resuming last generation…")
        self._active_job = job

        import threading
        self._cancel_event = threading.Event()
        worker = ModelTask(
            self.loader.process_synthesis,
            job.chunks, signals=None, model=job.model,
            cancel_event=self._cancel_event, job=job, resume_completed=job.completed,
        )
        worker.signals.progress.connect(self.updateprogress)
        worker.signals.finished.connect(self.on_synthesis_complete)
        worker.signals.count.connect(self.updateProgressCounter)
        worker.signals.chunk_ready.connect(self.on_synthesis_chunk_ready)
        worker.signals.error.connect(
            lambda err: (show_error(self.window(), f"Generation failed:\n{err}"),
                         self.on_synthesis_complete(None))
        )

        bar = self._progress_bar()
        if bar is not None:
            bar.show()
            bar.setRange(0, 0)
            bar.setTextVisible(False)
            bar.setValue(0)
        self._generating = True
        self.btn_continue.setEnabled(True)
        self.btn_continue.set_text("Stop Generation")
        self.btn_continue.set_cancel_mode(True)
        # The partial audio is already playable/downloadable — surface it now.
        self.Audio_player.load_live(job.out_path)
        QApplication.processEvents()
        self.threadpool.start(worker)
        return True