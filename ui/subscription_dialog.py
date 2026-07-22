# ui/subscription_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


class SubscriptionLoginDialog(QDialog):
    """دیالوگ ورود با نام کاربری و رمز عبورِ اشتراک (سرور مرکزی)."""

    def __init__(self, license_client, parent=None):
        super().__init__(parent)
        self.license_client = license_client
        self.setWindowTitle("ورود به حساب اشتراک AutoGarideh")
        self.setMinimumWidth(380)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 5px; font-size: 13px; }
            QPushButton { background-color: #1C4D8D; color: white; padding: 8px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #163d6f; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("نام کاربری:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("رمز عبور:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #c0392b;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.btn_login = QPushButton("ورود")
        self.btn_login.clicked.connect(self._attempt_login)
        layout.addWidget(self.btn_login)

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.status_label.setText("لطفاً نام کاربری و رمز عبور را وارد کنید.")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("در حال بررسی...")
        try:
            success, message = self.license_client.login(username, password)
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("ورود")

        if success:
            self.accept()
        else:
            self.status_label.setText(message)
