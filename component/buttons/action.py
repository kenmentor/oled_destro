from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

class ButtonHolder(QWidget):
    def __init__(self, text, callBack, icon_path=None):
        super().__init__()
        
        # Main Layout for the component
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # The Actual Button
        self.button = QPushButton(text)
        self.button.setCursor(Qt.PointingHandCursor) # Change cursor to hand on hover
        # self.button.setMinimumHeight(45)
        
        # Connect Callback
        self.button.clicked.connect(callBack)
        
        # Apply the "Matured" Styling
        self.apply_styles()
        
        # Add a subtle shadow for depth
        self.add_shadow()

        self.layout.addWidget(self.button)

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30)) # Very faint shadow
        self.button.setGraphicsEffect(shadow)

    def setEnabled(self, status):
        """Override setEnabled to keep logic clean in Screen1"""
        self.button.setEnabled(status)

    def set_text(self, text):
        self.button.setText(text)

    def set_generate_mode(self, on):
        """Vibrant orange primary button for Generate / Select PDF."""
        if on:
            self.button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B1A;
                color: #FFFFFF;
                border: 1px solid #FF6B1A;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'Inter', system-ui, sans-serif;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #FF8A3D; color: #FFFFFF; }
            QPushButton:pressed { background-color: #E0550E; color: #FFFFFF; }
            QPushButton:disabled {
                background-color: transparent; border: 1px solid #1C1C1E; color: #3A3A3C;
            }
            """)

    def set_cancel_mode(self, on):
        """Red button while a generation is running (also cancels on click)."""
        if on:
            self.button.setStyleSheet("""
            QPushButton {
                background-color: #FF3B30;
                color: #FFFFFF;
                border: 1px solid #FF3B30;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'Inter', system-ui, sans-serif;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover { background-color: #E0281E; }
            QPushButton:pressed { background-color: #C02118; }
            """)

    def apply_styles(self):
        self.button.setStyleSheet("""
    QPushButton {
    background-color: #121212;
    color: #E2E8F0;
    border: 1px solid #1C1C1E;
    border-radius: 5px;      
    padding: 8px 16px;            
    font-size: 13px;
    font-family: 'Inter', system-ui, sans-serif;
    font-weight: 700;
    letter-spacing: 0.5px;   
}

QPushButton:hover {
    background-color: #161618;
    border-color: #FF6B1A;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #FF6B1A;
    border-color: #FF6B1A;
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: transparent;
    border-color: #1C1C1E;
    color: #3A3A3C;           
}""")