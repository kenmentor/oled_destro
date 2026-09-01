import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QFrame, QVBoxLayout, 
                             QFileDialog, QStackedWidget, QLabel, QProgressBar, 
                             QWidget, QHBoxLayout, QGraphicsDropShadowEffect)
from PySide6.QtCore import QObject, QThread, Signal, Slot, QMetaObject, Qt
from PySide6.QtGui import QFont, QColor

# --- YOUR MODULE IMPORTS ---
from component.buttons.action import ButtonHolder
from modules.documentToTextModule import DocumentToText
from component.textEditor import TextEdit
from modules.ttsEgine import TTSEngine

# GLOBAL STYLESHEET (The "Make it look good" part)
STYLE_SHEET = """
    QMainWindow { background-color: #0F0F0F; }
    
    QFrame#MainPage, QFrame#LoadPage { 
        background-color: #161616; 
        border-radius: 15px; 
    }

    QLabel { color: #E0E0E0; font-family: 'Inter', 'Segoe UI'; }
    
    /* Style the Text Editor */
    QPlainTextEdit {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 10px;
        color: #BBB;
        font-size: 14px;
    }

    /* Style the Progress Bar */
    QProgressBar {
        border: none;
        background-color: #252525;
        height: 6px;
        border-radius: 3px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #0078D4;
        border-radius: 3px;
    }
"""

class GenerationWorker(QObject):
    finished = Signal()
    status_update = Signal(str)

    def __init__(self, engine, document):
        super().__init__()
        self.engine = engine
        self.document = document

    @Slot()
    def run(self):
        try:
            chunks = self.document.get_all_chunks()
            for idx, chunk_text in enumerate(chunks):
                self.status_update.emit(f"Generating voice {idx+1}/{len(chunks)}...")
                for _ in self.engine.synthesize(chunk_text): pass
            self.status_update.emit("Finished!")
        finally: self.finished.emit()

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenCode Studio")
        self.resize(1100, 750)
        self.setStyleSheet(STYLE_SHEET)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.document = DocumentToText()
        self.tts_engine = None

        self.init_ui()
        self.warmup_ai()

    def apply_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 150))
        widget.setGraphicsEffect(shadow)

    def init_ui(self):
        # 1. LOADING SCREEN
        load_page = QFrame(); load_page.setObjectName("LoadPage")
        l_lay = QVBoxLayout(load_page); l_lay.setAlignment(Qt.AlignCenter)
        
        logo = QLabel("O P E N C O D E"); logo.setFont(QFont("Arial", 30, QFont.Bold))
        self.load_status = QLabel("Waking up AI..."); self.load_status.setStyleSheet("color: #888;")
        self.bar = QProgressBar(); self.bar.setFixedWidth(300); self.bar.setRange(0, 0)
        
        l_lay.addStretch(); l_lay.addWidget(logo, 0, Qt.AlignCenter); l_lay.addSpacing(10)
        l_lay.addWidget(self.load_status, 0, Qt.AlignCenter); l_lay.addWidget(self.bar, 0, Qt.AlignCenter); l_lay.addStretch()
        
        # 2. HOME SCREEN
        home_page = QFrame(); home_page.setObjectName("MainPage")
        h_lay = QVBoxLayout(home_page); h_lay.setAlignment(Qt.AlignCenter)
        
        welcome = QLabel("Welcome Back"); welcome.setFont(QFont("Arial", 24, QFont.Bold))
        sub = QLabel("Select a PDF document to start your narration."); sub.setStyleSheet("color: #777;")
        btn_pick = ButtonHolder("Import Document", self.select_file)
        
        h_lay.addStretch(); h_lay.addWidget(welcome, 0, Qt.AlignCenter); h_lay.addWidget(sub, 0, Qt.AlignCenter)
        h_lay.addSpacing(30); h_lay.addWidget(btn_pick, 0, Qt.AlignCenter); h_lay.addStretch()

        # 3. EDITOR SCREEN
        editor_page = QFrame()
        e_lay = QVBoxLayout(editor_page); e_lay.setContentsMargins(30, 30, 30, 30)

        nav = QHBoxLayout()
        self.title_label = QLabel("New Project"); self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        btn_back = ButtonHolder("Close", lambda: self.stack.setCurrentIndex(1))
        nav.addWidget(self.title_label); nav.addStretch(); nav.addWidget(btn_back)

        self.editor = TextEdit()
        footer = QHBoxLayout()
        self.status = QLabel("Ready")
        self.btn_gen = ButtonHolder("Run Generation", self.generate_audio)
        footer.addWidget(self.status); footer.addStretch(); footer.addWidget(self.btn_gen)

        e_lay.addLayout(nav); e_lay.addSpacing(20); e_lay.addWidget(self.editor); e_lay.addSpacing(20); e_lay.addLayout(footer)

        self.stack.addWidget(load_page)
        self.stack.addWidget(home_page)
        self.stack.addWidget(editor_page)

    def warmup_ai(self):
        class Loader(QThread):
            done = Signal(object)
            def run(self): self.done.emit(TTSEngine())
        self.loader = Loader(); self.loader.done.connect(self.on_ready); self.loader.start()

    def on_ready(self, engine):
        self.tts_engine = engine
        self.stack.setCurrentIndex(1)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF (*.pdf)")
        if path:
            self.document.process_document(path)
            self.editor.setPlainText(self.document.full_text)
            self.title_label.setText(path.split("/")[-1])
            self.stack.setCurrentIndex(2)

    def generate_audio(self):
        self.btn_gen.setEnabled(False)
        self.document.full_text = self.editor.toPlainText()
        self.worker_thread = QThread()
        self.worker = GenerationWorker(self.tts_engine, self.document)
        self.worker.moveToThread(self.worker_thread)
        self.worker.status_update.connect(self.status.setText)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(lambda: self.btn_gen.setEnabled(True))
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainApp(); win.show(); sys.exit(app.exec())
