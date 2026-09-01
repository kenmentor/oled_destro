import sys
from PySide6.QtWidgets import QMainWindow, QToolBar, QApplication, QLabel, QFrame, QVBoxLayout, QWidget
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Premium Sidebar App")
        self.resize(800, 500)

        # 1. Create the ToolBar & Move to the Left Side (Sidebar)
        self.navbar = QToolBar("Main Navbar")
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.navbar)
        
        # Enforce vertical layout matching the design image
        self.navbar.setOrientation(Qt.Orientation.Vertical)

        # LOCK it down completely
        self.navbar.setMovable(False)    
        self.navbar.setFloatable(False)  

        # 2. Add Navigation Items & Make them Checkable (Togglable)
        home_act = QAction("Home", self)
        profile_act = QAction("Profile", self)
        settings_act = QAction("Settings", self)

        # Turn them into mutually exclusive buttons (Pill toggles)
        nav_group = QActionGroup(self)
        for act in [home_act, profile_act, settings_act]:
            act.setCheckable(True)
            nav_group.addAction(act)
        
        # Set Home active by default
        home_act.setChecked(True)

        # Assemble the sidebar
        self.navbar.addAction(home_act)
        self.navbar.addAction(profile_act)
        self.navbar.addAction(settings_act)

        # 3. Create the Elevated Content Panel (Matches the main workspace card)
        self.central_frame = QFrame()
        self.central_frame.setObjectName("CentralWorkspace")
        
        # Content Layout inside the workspace container
        content_layout = QVBoxLayout(self.central_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        
        self.content_label = QLabel("Content Area Window")
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.content_label)
        
        self.setCentralWidget(self.central_frame)

        # Apply the Global Adminsax Design System
        self.apply_premium_theme()

    def apply_premium_theme(self):
        self.setStyleSheet("""
            /* The deep pitch-black base window background */
            QMainWindow {
                background-color: #090A0F;
            }
            
            /* Sidebar Navigation Container styling */
            QToolBar {
                background-color: #090A0F;
                border: none;
                border-right: 1px solid #1E2230;
                padding-top: 30px;
                padding-left: 12px;
                padding-right: 12px;
                spacing: 10px; /* Distance between buttons */
            }
            
            /* Modern capsule buttons inside the sidebar */
            QToolButton {
                background-color: transparent;
                color: #73778C; /* Muted gray for inactive items */
                font-family: 'Inter', system-ui, sans-serif;
                font-size: 14px;
                font-weight: 600;
                border-radius: 12px;
                padding: 12px 24px;
                text-align: left;
                min-width: 130px; /* Formats them into balanced wide pill-shapes */
            }
            
            /* Subtle layout highlight on hover */
            QToolButton:hover {
                background-color: #12141C;
                color: #F8FAFC;
            }
            
            /* THE ACTIVE PILL: Flips to solid white with black text just like the image */
            QToolButton:checked {
                background-color: #FFFFFF;
                color: #000000;
            }
            
            /* The elevated content panel container card on the right */
            #CentralWorkspace {
                background-color: #12141C;
                border: 1px solid #1E2230;
                border-radius: 20px;
                margin: 20px; /* Creates breathing space away from the sidebar and window boundaries */
            }
            
            /* Main header panel labels */
            QLabel {
                color: #94A3B8;
                font-family: 'Inter', system-ui, sans-serif;
                font-size: 16px;
                font-weight: 500;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())