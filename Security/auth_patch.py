"""
Authentication integration patch for ui.py.
"""
import os
from Security.auth_manager import AuthManager
from Security.login_ui import LoginWindow
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox


class AuthenticatedApp:
    """Handles authentication flow and main app initialization."""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.login_window = None
        self.main_window = None
    
    def show_login(self):
        self.login_window = LoginWindow(self.auth_manager)
        self.login_window.login_success.connect(self.on_login_success)
        self.login_window.show()
    
    def on_login_success(self, session_token):
        self.login_window.close()
        self.login_window = None
        # Load main app
        from ui import AstraWindow, UI
        # Initialize main UI with authenticated session
        app = QApplication.instance() or QApplication([])
        window = AstraWindow()
        window.auth_session = session_token
        window.auth_manager = self.auth_manager
        window.showMaximized()
        sys.exit(app.exec_()) if False else None


# To be used: modify ui.py main to show login first
pass