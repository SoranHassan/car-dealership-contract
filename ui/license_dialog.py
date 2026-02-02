from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

class LicenseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("فعال‌سازی نرم‌افزار")

        layout = QVBoxLayout()

        self.label = QLabel("لطفاً رمز فعال‌سازی را وارد کنید:")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input)

        self.btn = QPushButton("تأیید")
        self.btn.clicked.connect(self.accept)
        layout.addWidget(self.btn)

        self.setLayout(layout)

    def get_key(self):
        return self.input.text().strip()