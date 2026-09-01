from PySide6.QtWidgets import QComboBox, QFrame, QProgressBar, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtCore import Qt,Signal,Slot
from modules.DataBase import jsonDB,modelDB
from modules.utils import Utils
from modules.voiceLibrary import VoiceLibrary

STATEDB = jsonDB()
MODELDB = modelDB()
utils = Utils()

VALID_MODELS = ["kokoro", "pocket"]

class Navigation:
    home   = 0
    history= 1
    plugin = 2
    model = 3
  
class leftPannel(QFrame):
    nav_request = Signal(int)
    model_reload_request = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self.setFixedWidth(240)
        self.setObjectName("leftPannel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 40) 
        layout.setSpacing(8)
        self.model_label = QLabel("Select Model")
        self.model_label.setObjectName("label")
        self.model_label.setStyleSheet("""
                                       #label {
                                           color:gray;
                                           font-size:10px;
                                       }""")
        self.voice_label = QLabel("Select Voice")
        self.voice_label.setObjectName("label")
        self.voice_label.setStyleSheet("""
                                               #label {
                                                   color:gray;
                                                   font-size:10px;
                                               }
                                               
                                               """)
        # 1. APP LOGO / TITLE
        self.logo = QLabel("Configuration")
        self.logo.setObjectName("leftPannelLogo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("AppProgress")
        self.progress_bar.setFixedHeight(10) 
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        
        self.select_voice = QComboBox()
        self.select_voice.setObjectName("VoiceDropdown")
        self.select_voice.setFixedWidth(200)
        self.select_voice.setFixedHeight(34)
        self.select_voice.currentIndexChanged.connect(self.onchage_voice)
        self.select_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.loadVoice()  
        
        self.select_model = QComboBox()
        self.select_model.setObjectName("VoiceDropdown")
        self.select_model.setFixedWidth(200)
        self.select_model.setFixedHeight(34)
        self.select_model.currentIndexChanged.connect(self.onchage_model)
        self.select_model.setCursor(Qt.CursorShape.PointingHandCursor)
        self.loadModel()
        
        
        
    

        # 2. NAVIGATION BUTTONS
        self.btn_home = self.create_nav_button("Select Voice", True ,Navigation.home)

        self.btn_plugin = self.create_nav_button("Select Model",False,Navigation.plugin)

        # 3. SETTINGS & BOTTOM ITEMS
    
        
        # ASSEMBLE Layout elements
        layout.addWidget(self.logo)
        layout.addSpacing(32)
        layout.addWidget(self.model_label)
        layout.addWidget(self.select_model)  
        layout.addWidget(self.voice_label)
        layout.addWidget(self.select_voice)
        layout.addWidget(self.progress_bar, stretch=1)
          
        layout.addStretch() 
        self.apply_style()
        
    def onchage_voice(self, index):
        voice = self.select_voice.itemData(index)
        if voice is None:
            voice = self.select_voice.currentText()
        STATEDB.voice = voice
        # A pocket voice (default or clone) requires the pocket engine.
        if self._is_pocket_voice(voice) and STATEDB.model != "pocket":
            STATEDB.model = "pocket"
            self.loadModel()
            self.loadVoice()

    @staticmethod
    def _is_pocket_voice(voice):
        from modules.ttsEgine import POCKET
        if POCKET.default_voice_path(voice):
            return True
        return VoiceLibrary().exists(voice)

    def onchage_model(self, index):
        model = self.select_model.itemData(index) or self.select_model.currentText()
        if model not in VALID_MODELS:
            model = "kokoro"
        if model == STATEDB.model:
            self.loadVoice()
            return
        STATEDB.model = model
        self.loadVoice()
        # Show immediate feedback: indeterminate spinner while engine reloads.
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.model_reload_request.emit(model)

    @Slot(object)
    def on_model_switched(self, ok):
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if ok else 0)
        self.loadVoice()

    def loadVoice(self):
        model = STATEDB.model
        voices = []
        try:
            if model == "pocket":
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
        for voice in voices:
            label = f"{voice} (clone)" if VoiceLibrary().exists(voice) else voice
            self.select_voice.addItem(label, voice)
        if self.select_voice.count() == 0:
            self.select_voice.addItem("No voice available - create a clone", "")
            self.select_voice.setEnabled(False)
        else:
            self.select_voice.setEnabled(True)
        self.select_voice.blockSignals(False)

        cur = STATEDB.voice
        idx = self.select_voice.findData(cur)
        self.select_voice.setCurrentIndex(idx if idx >= 0 else 0)

    def loadModel(self):
        self.select_model.blockSignals(True)
        self.select_model.clear()
        for model in VALID_MODELS:
            self.select_model.addItem(model.upper(), model)
        self.select_model.blockSignals(False)
        cur = STATEDB.model
        idx = self.select_model.findData(cur)
        self.select_model.setCurrentIndex(idx if idx >= 0 else 0)
    
    
    def create_nav_button(self, text, active=False, index=1):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(44) 
        
        # Register to the tracker group
        self.button_group.addButton(btn)
        btn.clicked.connect(lambda checked, idx=index: self.nav_request.emit(idx))
        
        return btn

    def apply_style(self):
        self.setStyleSheet("""
            /* The deep pitch-black base panel wrapper */
            #leftPannel {
                background-color: #060606;
                border-right: 1px solid #1E2230;
            }

            #AppProgress {
                background-color: #1B1B1E;
                border: 1px solid #2E2E33;
                border-radius: 5px;
            }
            #AppProgress::chunk {
                background-color: #FFFFFF;
                border-radius: 5px;
            }
            
            /* Sleek bold typography for app logo header */
            #leftPannelLogo {
                font-size: 18px;
                font-weight: 800;
                color: #FFFFFF;
                letter-spacing: 3px;
                margin-bottom: 10px;
                font-family: 'Inter', system-ui, sans-serif;
            }

            /* Unselected item style states */
            QPushButton {
                background-color: transparent;
                color: #FFFFFF; /* Clean muted slate gray from the layout image */
                border-radius: 5px; /* Perfect capsule pill-shape (height / 2) */
                padding-left: 24px;
                text-align: left;
                font-size: 14px;
                font-weight: 600;
                border: none;
                font-family: 'Inter', system-ui, sans-serif;
            }

            /* Interactive ambient background hover highlight */
            QPushButton:hover {
                background-color: #12141C;
               
            }

            /* THE ACTIVE PILL SELECTOR (Matches reference image perfectly) */
            QPushButton:checked {
                background-color: #FFFFFF; /* Shifts to stunning solid white capsule wrapper */
                color: #000000;            /* Crisp black text foreground clarity */
                font-weight: 700;
                border: none;              /* Clears old left border indicator line layout */
            }

            /* Quick responsive layout click reaction */
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)