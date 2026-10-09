"""Speaker health check stub."""

import subprocess


def speaker_health_test() -> str:
    """Quick speaker/playback device check.
    Returns a human-readable status string.
    """
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_SoundDevice | Where-Object {$_.Name -like '*speaker*' -or $_.Name -like '*output*' -or $_.Name -like '*headphone*'} | Select-Object Name, Status | Format-Table -AutoSize"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return f"Speaker devices detected:\n{result.stdout.strip()}"
    except Exception as e:
        pass
    return "Speaker check completed (no detailed info available)."