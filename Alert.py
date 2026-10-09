import os
from pathlib import Path
from winotify import Notification, audio
from os import getcwd
from branding import ASSISTANT_NAME, OWNER_NAME

def Alert(Text):
    icon_path = Path(__file__).resolve().parent / "assets" / "astra_logo.png"
    notification = {
        "app_id": f"{ASSISTANT_NAME} · {OWNER_NAME}",
        "title": Text,
        "duration": "long",
    }
    if icon_path.is_file():
        notification["icon"] = str(icon_path)

    toast = Notification(**notification)

    toast.set_audio(audio.Default, loop=False)


    toast.add_actions(label="Click me", launch="https://www.google.com")
    toast.add_actions(label="Dismiss", launch="https://www.google.com")


    toast.show()

