from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

class PluginScreen(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("PluginScreen")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Rigid, code-style text alert
        self.notice_label = QLabel("NO PLUGINS INSTALLED // VISIT GIT FOR SOURCE CODE")
        self.notice_label.setStyleSheet("""
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 11px;
            font-weight: 700;
            color: #48484A;
            letter-spacing: 1px;
        """)
        
        layout.addWidget(self.notice_label)
        
        # Match your master pitch-black canvas color
        self.setStyleSheet("#PluginScreen { background-color: #0A0A0A; }")