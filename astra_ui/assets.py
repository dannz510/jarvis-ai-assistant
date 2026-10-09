import os
import glob

from PyQt5.QtGui import QFontDatabase

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
TEXTURES_DIR = os.path.join(ASSETS_DIR, "textures")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

_LOADED = False


def load_assets(app=None):
    """Load bundled fonts/textures into the running QApplication."""
    global _LOADED
    if _LOADED:
        return
    if os.path.isdir(FONTS_DIR):
        for font_path in glob.glob(os.path.join(FONTS_DIR, "*.ttf")) + \
                glob.glob(os.path.join(FONTS_DIR, "*.otf")):
            try:
                QFontDatabase.addApplicationFont(font_path)
            except Exception:
                pass
    _LOADED = True