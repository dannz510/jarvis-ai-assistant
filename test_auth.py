#!/usr/bin/env python3
"""
Test biometric authentication system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Security.auth_manager import AuthManager
from Security.auth_types import AuthMethod, AuthStatus

def test_auth():
    auth_manager = AuthManager()
    print("=== ASTRA Biometric Auth Test ===")
    print("Available users:")
    users = auth_manager.storage.list_users()
    if users:
        for u in users:
            print(f"  - {u['username']} ({u['display_name']})")
    else:
        print("  No users registered")
        print("  Testing registration...")
        profile = auth_manager.register_user("testuser", "Test User", pin="123456")
        if profile:
            print(f"  Registered: {profile.username}")
        else:
            print("  Registration failed")
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_auth()
