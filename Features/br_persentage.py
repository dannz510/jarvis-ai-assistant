"""Brightness percentage check stub (Windows)."""

import subprocess


def check_br_persentage() -> str:
    """Get current display brightness percentage."""
    try:
        # WMI: WmiMonitorBrightness is not always available; use Win32_DesktopMonitor + PowerShell
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness -ErrorAction SilentlyContinue).CurrentBrightness"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return f"Brightness: {result.stdout.strip()}%"
    except Exception:
        pass
    return "Brightness info unavailable (WMI not supported or no external monitor)."