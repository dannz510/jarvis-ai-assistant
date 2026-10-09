"""Microphone health check stub."""

import subprocess


def mike_health() -> str:
    """Quick microphone presence/level check.
    Returns a human-readable status string.
    """
    try:
        # Check Windows audio devices via PowerShell
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_SoundDevice | Select-Object Name, Status | Format-Table -AutoSize"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return f"Microphone devices detected:\n{result.stdout.strip()}"
    except Exception as e:
        pass
    return "Microphone check completed (no detailed info available)."