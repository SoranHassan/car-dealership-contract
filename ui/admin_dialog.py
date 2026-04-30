# ui/admin_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
import hashlib

ADMIN_PASSWORD_HASH = hashlib.sha256("@Soran9978".encode()).hexdigest()


class AdminDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 ورود به پنل مدیریت")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.label = QLabel("🔐 لطفاً رمز ادمین را وارد کنید:")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("********")
        self.password_input.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.password_input)
        
        self.btn_ok = QPushButton("✅ تأیید و ورود")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self._check_password)
        layout.addWidget(self.btn_ok)
        
        self.setLayout(layout)
        
        # تمرکز روی فیلد رمز
        self.password_input.setFocus()
    
    def _check_password(self):
        password = self.password_input.text().strip()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == ADMIN_PASSWORD_HASH:
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", "❌ رمز اشتباه است!\nدسترسی غیرمجاز.")
            self.password_input.clear()
            self.password_input.setFocus()