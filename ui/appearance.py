# ui/appearance.py
#
# Application appearance helpers:
#   * load_bundled_fonts() registers the fonts shipped in assets/fonts so the
#     UI (and its stylesheets that ask for "Aria" / "Pelak" / …) render
#     correctly WITHOUT the customer having to install any font.
#   * apply_light_palette() forces a consistent light palette + Fusion style so
#     input text stays dark even when the customer's OS theme is dark
#     (otherwise the white-background inputs show white-on-white text).

import os
import sys
import logging

from PySide6.QtGui import QFontDatabase, QPalette, QColor

logger = logging.getLogger(__name__)


def _project_root():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fonts_dir():
    return os.path.join(_project_root(), "assets", "fonts")


def load_bundled_fonts():
    """Register every bundled .ttf/.otf with Qt for this run of the app.

    Returns the number of font files successfully registered.
    """
    directory = fonts_dir()
    if not os.path.isdir(directory):
        logger.warning("Bundled fonts directory not found: %s", directory)
        return 0

    loaded = 0
    for name in sorted(os.listdir(directory)):
        if name.lower().endswith((".ttf", ".otf")):
            font_id = QFontDatabase.addApplicationFont(os.path.join(directory, name))
            if font_id != -1:
                loaded += 1
            else:
                logger.warning("Could not load bundled font: %s", name)

    logger.info("Loaded %d bundled fonts from %s", loaded, directory)
    return loaded


def apply_light_palette(app):
    """Force a light, theme-independent palette so the app looks the same on
    every machine regardless of the OS light/dark setting."""
    try:
        app.setStyle("Fusion")
    except Exception:  # pragma: no cover - defensive
        pass

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f0f0f0"))
    palette.setColor(QPalette.WindowText, QColor("#1b1b1b"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f5f5f5"))
    palette.setColor(QPalette.Text, QColor("#1b1b1b"))          # input text
    palette.setColor(QPalette.Button, QColor("#f0f0f0"))
    palette.setColor(QPalette.ButtonText, QColor("#1b1b1b"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#1b1b1b"))
    palette.setColor(QPalette.PlaceholderText, QColor("#7a7a7a"))
    palette.setColor(QPalette.Highlight, QColor("#1C4D8D"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
