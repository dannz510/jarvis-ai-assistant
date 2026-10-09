# Update the UI main function to use authentication
"""
Updated UI with authentication
"""

# Modify the UI() function
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from Security.auth_manager import AuthManager
from Security.login_ui import LoginWindow


def main_with_auth():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    auth_manager = AuthManager()
    login_window = LoginWindow(auth_manager)
    
    def on_login_success(session_token):
        login_window.close()
        from ui import AstraWindow
        window = AstraWindow()
        window.auth_session = session_token
        window.auth_manager = auth_manager
        window.showMaximized()
    
    login_window.login_success.connect(on_login_success)
    login_window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main_with_auth()
