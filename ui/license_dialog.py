# ui/license_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt


class LicenseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("فعال‌سازی نرم‌افزار AutoGarideh")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        # استایل
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        self.label = QLabel("لطفاً رمز فعال‌سازی را وارد کنید:")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.extra_label = QLabel("")
        self.extra_label.setStyleSheet("color: #f44336; font-size: 12px;")
        self.extra_label.setAlignment(Qt.AlignCenter)
        self.extra_label.hide()
        layout.addWidget(self.extra_label)
        
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.input.setPlaceholderText("رمز فعال‌سازی را وارد کنید...")
        layout.addWidget(self.input)
        
        self.btn = QPushButton("تأیید و فعال‌سازی")
        self.btn.clicked.connect(self.accept)
        layout.addWidget(self.btn)
        
        # Enter key
        self.input.returnPressed.connect(self.accept)
        
        self.setLayout(layout)
        
        # تمرکز روی فیلد ورودی
        self.input.setFocus()
    
    def set_extra_message(self, message):
        """تنظیم پیام اضافی (مثل خطا)"""
        if message:
            self.extra_label.setText(message)
            self.extra_label.show()
        else:
            self.extra_label.hide()
    
    def get_key(self):
        return self.input.text().strip()