from PySide6.QtWidgets import QApplication
from ui import App
import sys
from PySide6.QtGui import QIcon




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.setWindowIcon(QIcon("./assets/icon.jpg"))
    window.setWindowTitle("Auto Garideh")
    window.show()
    sys.exit(app.exec())