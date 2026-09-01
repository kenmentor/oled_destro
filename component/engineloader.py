import os
import traceback
import uuid
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QMetaObject, Qt, Q_ARG
from component.audio_processor import database, StreamingWavWriter
from modules.DataBase import jsonDB

stateBase = jsonDB()

class WorkerSignals(QObject):
    """Signals to communicate between the background thread and the UI."""
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(str)
    count = Signal(int)
    # Fired after the first PCM chunk is written, so the player can start
    # playing/downloading the growing WAV before generation completes.
    chunk_ready = Signal(str)


class ModelTask(QRunnable):
    """A generic runnable to execute any function in a thread pool."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            if 'signals' in self.kwargs:
                self.kwargs['signals'] = self.signals

            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception:
            err_msg = traceback.format_exc()
            self.signals.error.emit(err_msg)

class Worker(QObject):
    # Long-lived signals for the initialization worker thread
    progress = Signal(str)
    finished = Signal(object)
    # Emitted after a model switch completes (separate from initial load)
    switch_finished = Signal(object)

    def __init__(self):
        super().__init__()
        self.engine = None
        # Lazy: imported on first use (avoids pulling torch/kokoro at module load).
        from modules.ttsEgine import MODEL_EGINE
        self.MODEL_EGINE = MODEL_EGINE()

    @Slot()
    def worker_job(self):
        self.progress.emit("Loading AI engine...")
        try:
            model_class = self.MODEL_EGINE.load_default()
            self.engine = model_class()
            self._ensure_valid_voice()
            self.progress.emit("AI Engine Ready")
            self.finished.emit(self.engine)
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            traceback.print_exc()
            self.finished.emit(None)

    def _ensure_valid_voice(self):
        """Make sure the stored voice is usable by the loaded engine."""
        voice = stateBase.voice or ""
        default = getattr(self.engine, "default_voice", None)
        model = getattr(self.MODEL_EGINE, "current_model", None)

        # Pocket: voice must be a default or clone.
        if model == "pocket":
            from modules.ttsEgine import POCKET
            from modules.voiceLibrary import VoiceLibrary
            if voice and (POCKET.default_voice_path(voice) or VoiceLibrary().exists(voice)):
                return
            if default:
                stateBase.voice = default
            else:
                stateBase.voice = ""
            return

        # Kokoro: voice must be an available .pt file.
        if not voice or voice == "None":
            stateBase.voice = default or ""
            return
        if voice.endswith(".pt") and not os.path.exists(f"./modules/voices/{voice}"):
            print(f"[Worker] Voice '{voice}' unavailable, resetting to '{default}'")
            stateBase.voice = default or ""

    def set_model(self, model_name):
        print("[set_model]->", model_name)
        model_class = self.MODEL_EGINE.get_model(model_name)
        self.engine = model_class()
        default = getattr(self.engine, "default_voice", None)
        # Keep the current voice if it is usable by this engine; else use default.
        def _usable(v):
            from modules.ttsEgine import POCKET
            from modules.voiceLibrary import VoiceLibrary
            if model_name == "pocket":
                return bool(v) and (POCKET.default_voice_path(v) or VoiceLibrary().exists(v))
            return bool(v)
        if _usable(stateBase.voice):
            pass
        else:
            stateBase.voice = default or ""
        print("[set_model]-> engine:", self.engine)

    @Slot(str)
    def switch_model_job(self, model_name):
        """Reload the engine for a different model, with progress feedback.

        Designed to run on the engine thread via `self.engine_thread`.
        """
        try:
            self.progress.emit(f"Loading {model_name} model...")
            self.set_model(model_name)
            self._ensure_valid_voice()
            self.progress.emit(f"{model_name} ready")
            self.switch_finished.emit(self.engine)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.progress.emit(f"Model failed to load: {e}")
            self.switch_finished.emit(None)

    def switch_model(self, model_name):
        """Queue a model switch onto the engine thread (async)."""
        thread = self.thread()
        if not thread or not thread.isRunning():
            self.progress.emit("Engine thread not running")
            self.switch_finished.emit(None)
            return
        QMetaObject.invokeMethod(
            self, "switch_model_job", Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, model_name),
        )

    def process_synthesis(self, chunks, voice="", signals=None, model=None, cancel_event=None):
        """Logic for synthesis to be called by the ThreadPool."""
        if model is not None and model != self.MODEL_EGINE.current_model:
            stateBase.model = model
            self.set_model(model)

        if not chunks:
            return None

        if cancel_event is not None and cancel_event.is_set():
            return None

        if signals:
            signals.progress.emit(f"Synthesizing {len(chunks)} chunk(s)...")

        total_chunks = len(chunks)
        chunk_weight = 100.0 / total_chunks

        # Write straight to a growing WAV so playback can begin early.
        out_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"synth_{uuid.uuid4().hex[:12]}.wav")
        writer = StreamingWavWriter(out_path, sample_rate=24000, bit_depth=16, channels=1)

        emitted_first = False
        cancelled = False
        try:
            for idx, chunk in enumerate(chunks):
                # Honour cancellation between chunks (and per-reading).
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break

                base_progress = idx * chunk_weight

                if signals:
                    signals.progress.emit(f"Synthesizing chunk {idx + 1}/{total_chunks}...")

                stream_step = 0
                for data in self.engine.synthesize(chunk, voice=stateBase.voice):
                    if cancel_event is not None and cancel_event.is_set():
                        cancelled = True
                        break
                    writer.append(data)
                    stream_step += 1

                    # Start live playback as soon as we have real audio.
                    if not emitted_first and writer.has_data:
                        emitted_first = True
                        if signals:
                            signals.chunk_ready.emit(out_path)

                    if signals:
                        sub_progress = min(stream_step * 2.5, chunk_weight * 0.95)
                        signals.count.emit(int(base_progress + sub_progress))

                if cancelled:
                    break
                if signals:
                    signals.count.emit(int((idx + 1) * chunk_weight))
        finally:
            writer.finalize()

        if cancelled:
            # Partially generated file is not registered in the library.
            try:
                os.remove(out_path)
            except OSError:
                pass
            if signals:
                signals.progress.emit("Generation cancelled")
            return None

        if writer.has_data:
            database.add(out_path)
            return out_path

        return None