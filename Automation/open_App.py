"""Launch supported desktop applications through an explicit allowlist."""

import os
import shutil
import subprocess


APP_ALLOWLIST = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "vscode": "code.exe",
    "vs code": "code.exe",
    "visual studio code": "code.exe",
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "microsoft powerpoint": "powerpnt.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
}


def open_App(text):
    """Launch one allowlisted application using only validated subprocess calls."""
    requested = " ".join(str(text).casefold().strip().split())
    requested = requested.removesuffix(" application").removesuffix(" app").strip()
    executable = APP_ALLOWLIST.get(requested)
    if executable is None:
        raise ValueError(
            f"Unsupported application '{text}'. Supported apps: "
            + ", ".join(sorted(APP_ALLOWLIST))
        )

    resolved = shutil.which(executable)
    if resolved:
        return subprocess.Popen([resolved])
    # REMOVED: os.startfile() fallback — unsafe shell execution
    raise RuntimeError(
        f"{executable} is not installed or is not on PATH. "
        "Please install it manually or add it to PATH."
    )
