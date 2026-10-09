"""Set brightness on Windows (external monitors via DDC/CI, laptop via WMI)."""

import subprocess


def set_brightness_windows(level: int) -> str:
    """Set display brightness to level (0-100).
    Tries WMI first (laptop panels), then falls back to external monitor via ddcutil if available.
    """
    level = max(0, min(100, int(level)))

    # Try WMI (laptop/internal panels)
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue).WmiSetBrightness(1,{level})"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return f"Brightness set to {level}% (WMI)."
    except Exception:
        pass

    # Try ddcutil for external monitors (if installed)
    try:
        result = subprocess.run(["ddcutil", "setvcp", "10", str(level)], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return f"Brightness set to {level}% (ddcutil)."
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return f"Could not set brightness to {level}% (no supported control method found)."