from PySide6.QtWidgets  import QApplication , QMainWindow, QPushButton 

class ButtonHolder(QMainWindow):
    def __init__ (self,text):
        super().__init__()
        
        button = QPushButton(text)
        
        
        button.setStyleSheet("""
            QPushButton {
                background-color: #2c2c2c;
                color: white;
                border-radius: 2px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #194d70;
            }
            QPushButton:pressed {
                background-color: #194d70;
            }
        """)

        button.clicked.connect(self.onclicked)
        self.setCentralWidget(button)
        
    def onclicked (self,data):
        print(data)
        print("hello world .........")
