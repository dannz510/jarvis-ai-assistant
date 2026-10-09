#!/usr/bin/env python3
"""
ASTRA Secure Launch - Main entry point with biometric authentication
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFont
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    try:
        from Security.auth_manager import AuthManager
        from Security.login_ui import LoginWindow
        from ui import AstraWindow
        
        auth_manager = AuthManager()
        login_window = LoginWindow(auth_manager)
        
        def on_login_success(session_token):
            login_window.close()
            window = AstraWindow()
            window.auth_session = session_token
            window.auth_manager = auth_manager
            window.showMaximized()
        
        login_window.login_success.connect(on_login_success)
        login_window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error launching ASTRA: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
