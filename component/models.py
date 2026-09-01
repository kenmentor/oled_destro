import sys 
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QApplication, QWidget, QScrollArea)
from PySide6.QtCore import Qt
from modules.DataBase import jsonDB 
statebase = jsonDB()


class Model(QFrame):
    def __init__(self, model_name):
        super().__init__()
        self.setObjectName("ModelCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Internal Content Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        self.modelname = model_name
        self.title_label = QLabel(model_name)
        self.title_label.setObjectName("ModelName")
        
       
        self.status_tag = QLabel("READY")
        self.status_tag.setObjectName("StatusTag")
        
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.status_tag)
        
        
        self.applystyle()
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:   
            statebase.model = self.modelname
            event.accept()
            
            
    def applystyle(self):
        # Strict matching of Screen1's rigid boxy layout & color tokens
        self.setStyleSheet("""
            QFrame#ModelCard {
                background-color: #121212;
                border: 1px solid #1C1C1E;
                border-radius: 0px; /* Sharp rigid system look */
            }
            QFrame#ModelCard:hover {
                border-color: #E4E4E7; /* Highlight accent interactive state */
                background-color: #141416;
            }
            QLabel#ModelName {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Inter', system-ui, sans-serif;
            }
            QLabel#StatusTag {
                font-size: 10px;
                font-weight: 700;
                color: #9BE8A8;
                font-family: 'Inter', system-ui, sans-serif;
                letter-spacing: 0.5px;
            }
        """)


class ModelScreen(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("ModelScreen")
        
        # Main Layout Container
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(16)
        
        # --- 1. Header Section ---
        self.header_container = QFrame()
        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.screen_title = QLabel("AVAILABLE MODELS")
        self.screen_title.setObjectName("SectionTitle")
        self.header_layout.addWidget(self.screen_title)
        self.header_layout.addStretch()
        
        # --- 2. Scrollable Body Area (Protects layout from scaling breaks) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("GridScrollArea")
        
        self.container_widget = QWidget()
        self.container_widget.setObjectName("GridContainer")
        
        # Build grid contents via modelcomponent
        self.modelcomponent()
        
        self.scroll_area.setWidget(self.container_widget)
        
        # Assemble Main Framework Layout
        self.root_layout.addWidget(self.header_container)
        self.root_layout.addWidget(self.scroll_area, stretch=1)
        
        # Apply Screen Level Aesthetic Styling
        self.applystyle()

    def getModels(self):
        return ["kokoro", "pocket"]

    def align(self, data, row, widget):
        """Constructs a clean boxy layout alignment across grid spaces."""
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(12)  # Tight spacing alignment
        
        hlayout = QHBoxLayout()
        hlayout.setSpacing(12)
        
        for i, item in enumerate(data):
            card_widget = widget(item)
            hlayout.addWidget(card_widget)
            
            # Flush row if limit hit or list ends
            if (i + 1) % row == 0 or i == len(data) - 1:
                # If it's the last row and not complete, add stretch spacing to balance grid
                if i == len(data) - 1 and (i + 1) % row != 0:
                    hlayout.addStretch(row - ((i + 1) % row))
                vlayout.addLayout(hlayout)
                hlayout = QHBoxLayout()
                hlayout.setSpacing(12)
                
        return vlayout

    def modelcomponent(self):
        # Bind the layout array architecture directly inside the inner container widget
        layout = QVBoxLayout(self.container_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        models = self.getModels()
        
        # Align with 2 model items per row
        grid_arrangement = self.align(data=models, row=2, widget=Model)
        layout.addLayout(grid_arrangement)
        layout.addStretch() # Forces items to align securely from top down

    def applystyle(self):
        self.setStyleSheet("""
            #ModelScreen, #GridContainer {
                background-color: #0A0A0A;
            }
            
            #GridScrollArea {
                background-color: #0A0A0A;
            }
            
            QLabel#SectionTitle {
                font-family: 'Inter', system-ui, sans-serif;
                font-size: 11px;
                font-weight: 700;
                color: #48484A;
                letter-spacing: 1px;
            }
            
            /* Customizing scrollbar track to stay clean and thin */
            QScrollBar:vertical {
                border: none;
                background: #0A0A0A;
                width: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #1C1C1E;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

