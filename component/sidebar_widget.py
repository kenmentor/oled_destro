from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtCore import Qt,Signal

class Navigation:
    home   = 0
    history= 1
    plugin = 2
    model = 3
    voice  = 4
  
class SideBar(QFrame):
    nav_request = Signal(int)
    
    def __init__(self):
        super().__init__()
        
        self.setFixedWidth(240) # Clean professional width
        self.setObjectName("SideBar")
        
        # Main Sidebar Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 40) # Generous top/bottom padding
        layout.setSpacing(8)

        # 1. APP LOGO / TITLE
        self.logo = QLabel("OLED AUDIO")
        self.logo.setObjectName("SidebarLogo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Enforce mutual exclusivity (only one button highlighted at a time)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # 2. NAVIGATION BUTTONS
        self.btn_home = self.create_nav_button("Home", True ,Navigation.home)

        self.btn_plugin = self.create_nav_button("plugin",False,Navigation.plugin)
        self.btn_history = self.create_nav_button("History", False,Navigation.history)
        self.btn_model = self.create_nav_button("Models",False,Navigation.model)
        # Voice Studio is hidden for the current release.
        # self.btn_voice = self.create_nav_button("Voice Studio",False,Navigation.voice)
        # 3. SETTINGS & BOTTOM ITEMS
    
        
        # ASSEMBLE Layout elements
        layout.addWidget(self.logo)
        layout.addSpacing(32) 
        layout.addWidget(self.btn_home) # Clean spacing transition from logo to menu
        layout.addWidget(self.btn_plugin)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_model)
        
        layout.addStretch() 

        self.apply_style()
        

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
            #SideBar {
                background-color: #060606;
                border-right: 1px solid #1E2230;
            }
            
            /* Sleek bold typography for app logo header */
            #SidebarLogo {
                font-size: 18px;
                font-weight: 800;
                color: #FFFFFF;
                letter-spacing: 3px;
                margin-bottom: 10px;
                padding-bottom: 8px;
                border-bottom: 2px solid #FF6B1A; /* vibrant orange accent */
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
                color: #F8FAFC;
            }

            /* THE ACTIVE PILL SELECTOR — vibrant orange accent */
            QPushButton:checked {
                background-color: #FF6B1A; /* Vibrant matching orange */
                color: #FFFFFF;            /* Crisp white foreground text */
                font-weight: 700;
                border: none;              /* Clears old left border indicator line layout */
            }

            /* Quick responsive layout click reaction */
            QPushButton:pressed {
                background-color: #FF8A3D;
                color: #FFFFFF;
            }
        """)