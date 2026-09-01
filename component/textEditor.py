from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
from modules.documentToTextModule import DocumentToText

document_tool = DocumentToText()

class TextEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        
        # 1. Typography Configuration
        font = QFont("Inter", 13) 
        if not font.exactMatch(): # Fallback if Inter isn't installed locally
            font = QFont("Segoe UI", 13)
        
        self.setFont(font)
        
        # 2. Workspace Behavior
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setPlaceholderText("Your document text will appear here...")
        
        # 3. Apply Design System Theme
        self.apply_reader_styles()

    def apply_reader_styles(self):
        self.setStyleSheet("""
            QPlainTextEdit {  
                color: #F8FAFC; 
                border: 1px solid #1E2230; 
                border-radius: 2px;
                padding: 5px; 
                selection-background-color: #E4E4E7;
                selection-color: #000000;
            }

            QScrollBar:vertical {
                border: none;
                background: #12141C;
                width: 10px;
                margin: 0px;
                padding-right: 2px; /* Pulls the handle away from the edge slightly */
            }
            
            QScrollBar::handle:vertical {
                background: #23283B; /* Integrated slate-gray tone */
                min-height: 40px;
                border-radius: 4px;
            } 
            QScrollBar::handle:vertical:hover {
                background: #333A50; /* Brightens slightly when interacting */
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def set_content(self, text):
        document_tool.update_text(text)
        text = document_tool.get_full_text()
        self.setPlainText(text)

    def get_content(self):
        return self.toPlainText()