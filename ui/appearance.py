# ui/appearance.py
#
# Application appearance helpers:
#   * load_bundled_fonts() registers the fonts shipped in assets/fonts with
#     Qt so OUR OWN app's UI renders correctly, in this process only.
#   * install_fonts_system_wide() copies those same fonts into the current
#     user's OS font folder (no admin rights, no install dialog) so that
#     OTHER programs — Microsoft Word, LibreOffice — also have them
#     available when they open a generated .docx. Without this, Word/LO
#     substitute a fallback font per missing font name, which is why
#     generated contracts could show inconsistent fonts/sizes across fields
#     depending on what happened to already be installed.
#   * apply_light_palette() forces a consistent light palette + Fusion style so
#     input text stays dark even when the customer's OS theme is dark
#     (otherwise the white-background inputs show white-on-white text).

import os
import sys
import shutil
import logging
import platform

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


def _user_font_dir():
    """Per-user, no-admin-required font directory for the current OS."""
    system = platform.system()
    if system == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            return None
        return os.path.join(local_appdata, "Microsoft", "Windows", "Fonts")
    if system == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    # Linux and everything else XDG-like
    return os.path.expanduser("~/.local/share/fonts")


def _register_windows_font(dest_path, family_hint):
    """Add the HKCU registry entry Windows needs to pick up a per-user font
    placed in %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts (the same mechanism
    used by Explorer's "Install for me only")."""
    try:
        import winreg
    except ImportError:  # pragma: no cover - non-Windows
        return
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows NT\CurrentVersion\Fonts",
            0,
            winreg.KEY_SET_VALUE,
        )
        with key:
            value_name = f"{family_hint} (TrueType)"
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, os.path.basename(dest_path))
    except OSError as e:  # pragma: no cover - defensive
        logger.warning("Could not register font in registry: %s (%s)", family_hint, e)


def install_fonts_system_wide():
    """Silently install the bundled fonts into the current user's OS font
    folder (no admin rights, no dialogs) so external programs — Word,
    LibreOffice — render generated documents with the correct fonts instead
    of substituting fallbacks. Safe to call on every startup: files are only
    (re)copied when missing or changed.

    Returns the number of font files installed/updated.
    """
    src_dir = fonts_dir()
    if not os.path.isdir(src_dir):
        return 0

    dest_dir = _user_font_dir()
    if not dest_dir:
        logger.warning("Could not determine a per-user font directory for this OS")
        return 0

    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        logger.warning("Could not create font directory %s: %s", dest_dir, e)
        return 0

    is_windows = platform.system() == "Windows"
    installed = 0
    for name in sorted(os.listdir(src_dir)):
        if not name.lower().endswith((".ttf", ".otf")):
            continue
        src_path = os.path.join(src_dir, name)
        dest_path = os.path.join(dest_dir, name)
        try:
            needs_copy = (
                not os.path.exists(dest_path)
                or os.path.getsize(dest_path) != os.path.getsize(src_path)
            )
            if needs_copy:
                shutil.copy2(src_path, dest_path)
            if is_windows:
                family_hint = os.path.splitext(name)[0]
                _register_windows_font(dest_path, family_hint)
            if needs_copy:
                installed += 1
        except OSError as e:
            logger.warning("Could not install font %s: %s", name, e)

    if installed and not is_windows:
        # Refresh fontconfig's cache so LibreOffice/other apps see the new
        # fonts immediately instead of waiting for their own periodic scan.
        try:
            import subprocess
            subprocess.run(["fc-cache", "-f", dest_dir], capture_output=True, timeout=30)
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("fc-cache refresh failed: %s", e)

    logger.info("Installed %d fonts into %s (per-user, no admin required)", installed, dest_dir)
    return installed


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
