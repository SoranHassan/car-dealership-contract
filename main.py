from PySide6.QtWidgets import QApplication
from ui.license_manager import license_check
from ui.app import App
import sys

app = QApplication(sys.argv)

if not license_check():
    sys.exit()

window = App()
window.show()
sys.exit(app.exec())