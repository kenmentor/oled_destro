from PySide6.QtWidgets  import QApplication , QMainWindow, QPushButton 

class ButtonHolder(QMainWindow):
    def __init__ (self,text):
        super().__init__()
        
        button = QPushButton(text)
        
        
        button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

        button.clicked.connect(self.onclicked)
        self.setCentralWidget(button)
        
    def onclicked (self,data):
        print(data)
        print("hello world .........")
