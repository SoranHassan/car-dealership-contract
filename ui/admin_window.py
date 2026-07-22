# ui/admin_window.py - نسخه نهایی با تم دارک و سایزهای بهینه
import json
import sqlite3
import os
import shutil
import zipfile
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableView, QTreeView,
    QMessageBox, QFrame, QLineEdit, QApplication, QComboBox, QDateEdit, QFileDialog, QHeaderView
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QDate
from PySide6.QtGui import QStandardItemModel, QStandardItem, QDesktopServices


class AdminWindow(QWidget):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.parent_app = parent
        self.setWindowTitle("🎛️ AutoGarideh | پنل مدیریت پیشرفته")
        self.resize(1400, 850)
        self.setMinimumSize(1200, 700)

        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # متغیرها
        self.backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        self.contracts_dir = None
        self.last_contract_count = 0

        self._apply_theme()
        self._setup_ui()
        self._load_data()
        self._setup_auto_refresh()

        # انیمیشن
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def _apply_theme(self):
        """تم روشن، ساده و حرفه‌ای"""
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            /* استایل اصلی - تم روشن مدیریتی */
            QWidget {
                background-color: #f5f6f8;
                color: #1f2328;
                font-family: 'Segoe UI', 'Inter', 'Arial';
                font-size: 12px;
            }
            QLabel { background: transparent; }

            /* کارت هدر */
            QFrame#headerCard {
                background: #ffffff;
                border-radius: 12px;
                min-height: 65px;
                border: 1px solid #e1e4e8;
            }
            #headerTitle {
                font-size: 18px;
                font-weight: bold;
                color: #1C4D8D;
            }
            #headerSub {
                font-size: 11px;
                color: #6a737d;
            }
            #dbStatus {
                background-color: #e6f4ea;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 11px;
                color: #1a7f37;
            }

            /* نوار ابزار */
            QFrame#toolbarCard, QFrame#filtersCard, QFrame#searchCard, QFrame#footerCard {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e1e4e8;
            }

            /* دکمه‌ها */
            QPushButton {
                background-color: #1C4D8D;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #163d6f;
            }
            QPushButton#dangerBtn {
                background-color: #d1332f;
            }
            QPushButton#dangerBtn:hover {
                background-color: #b8241f;
            }

            /* کامبوباکس و ورودی */
            QComboBox, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 5px 10px;
                color: #1f2328;
                min-width: 100px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
                padding: 8px 12px;
                color: #1f2328;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #1C4D8D;
            }

            /* کارت آمار */
            QFrame#statCard {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e1e4e8;
                min-height: 80px;
            }
            #statIcon {
                font-size: 28px;
            }
            #statValue {
                font-size: 22px;
                font-weight: bold;
                color: #1C4D8D;
            }
            #statLabel {
                font-size: 11px;
                color: #6a737d;
            }

            /* تب‌ها */
            QTabWidget::pane {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e1e4e8;
            }
            QTabBar::tab {
                background-color: #eef0f3;
                color: #6a737d;
                padding: 7px 20px;
                margin-left: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #1C4D8D;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #dde3ea;
                color: #1f2328;
            }

            /* درخت و جدول */
            QTreeView, QTableView {
                background-color: #ffffff;
                alternate-background-color: #f5f6f8;
                selection-background-color: #cfe0f5;
                selection-color: #1f2328;
                border: none;
                font-size: 12px;
                outline: 0;
            }
            QTreeView::item, QTableView::item {
                padding: 6px;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #eef0f3;
                color: #1C4D8D;
                padding: 8px;
                font-weight: bold;
                border: none;
                font-size: 11px;
            }

            /* هشدار */
            #warningLabel {
                background-color: #d1332f;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: bold;
            }

            /* اسکرول بار */
            QScrollBar:vertical {
                background-color: #f5f6f8;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #d0d7de;
                border-radius: 4px;
                min-height: 50px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1C4D8D;
            }

            /* فوتر */
            #footerLabel {
                color: #6a737d;
                font-size: 11px;
            }
            #recordCount {
                background-color: #eef0f3;
                padding: 3px 12px;
                border-radius: 20px;
                font-size: 11px;
                color: #1C4D8D;
                font-weight: bold;
            }
        """)

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)

        # ===== هدر =====
        header = self._create_header()
        main.addWidget(header)

        # ===== ابزارهای سریع =====
        tools = self._create_toolbar()
        main.addWidget(tools)

        # ===== کارت آمار (5 تایی) =====
        stats = self._create_stats()
        main.addLayout(stats)

        # ===== فیلترهای پیشرفته =====
        filters = self._create_filters()
        main.addWidget(filters)

        # ===== جستجو =====
        search = self._create_search()
        main.addWidget(search)

        # ===== تب‌ها =====
        self.tabs = QTabWidget()
        self._create_contracts_tab()
        self._create_logs_tab()
        self._create_settings_tab()
        self._create_backup_tab()
        main.addWidget(self.tabs)

        # ===== فوتر =====
        footer = self._create_footer()
        main.addWidget(footer)

    def _create_header(self):
        header = QFrame()
        header.setObjectName("headerCard")
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 8, 20, 8)

        title_w = QWidget()
        tl = QVBoxLayout(title_w)
        tl.setSpacing(2)
        title = QLabel("🎛️ AutoGarideh Manager")
        title.setObjectName("headerTitle")
        sub = QLabel("سیستم مدیریت و گزارش‌گیری پیشرفته")
        sub.setObjectName("headerSub")
        tl.addWidget(title)
        tl.addWidget(sub)

        self.db_status = QLabel("🟢 متصل")
        self.db_status.setObjectName("dbStatus")

        btn_refresh = QPushButton("🔄 بروزرسانی")
        btn_refresh.setObjectName("refreshBtn")
        btn_refresh.clicked.connect(self._load_data)

        btn_close = QPushButton("✖ بستن")
        btn_close.setObjectName("dangerBtn")
        btn_close.clicked.connect(self.close)

        h.addWidget(title_w)
        h.addStretch()
        h.addWidget(self.db_status)
        h.addWidget(btn_refresh)
        h.addWidget(btn_close)
        return header

    def _create_toolbar(self):
        toolbar = QFrame()
        toolbar.setObjectName("toolbarCard")
        t = QHBoxLayout(toolbar)
        t.setContentsMargins(15, 8, 15, 8)
        t.setSpacing(10)

        self.btn_daily = QPushButton("📊 گزارش روزانه")
        self.btn_daily.clicked.connect(self._daily_report)
        t.addWidget(self.btn_daily)

        self.btn_monthly = QPushButton("📅 گزارش ماهانه")
        self.btn_monthly.clicked.connect(self._monthly_report)
        t.addWidget(self.btn_monthly)

        self.btn_backup_db = QPushButton("💾 بکاپ دیتابیس")
        self.btn_backup_db.clicked.connect(self._backup_database)
        t.addWidget(self.btn_backup_db)

        self.btn_backup_contracts = QPushButton("📦 بکاپ قراردادها (زیپ)")
        self.btn_backup_contracts.clicked.connect(self._backup_contracts_folder)
        t.addWidget(self.btn_backup_contracts)

        self.btn_restore = QPushButton("🔄 بازیابی از بکاپ")
        self.btn_restore.clicked.connect(self._restore_backup)
        t.addWidget(self.btn_restore)

        t.addStretch()

        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warningLabel")
        t.addWidget(self.warning_label)

        return toolbar

    def _create_stats(self):
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stat_total = self._stat_card("📊", "کل قراردادها", "0")
        self.stat_today = self._stat_card("📅", "امروز", "0")
        self.stat_paid = self._stat_card("✅", "پرداخت شده", "0")
        self.stat_unpaid = self._stat_card("⏳", "پرداخت نشده", "0")
        self.stat_month = self._stat_card("📆", "این ماه", "0")
        stats.addWidget(self.stat_total)
        stats.addWidget(self.stat_today)
        stats.addWidget(self.stat_paid)
        stats.addWidget(self.stat_unpaid)
        stats.addWidget(self.stat_month)
        return stats

    def _create_filters(self):
        filters = QFrame()
        filters.setObjectName("filtersCard")
        f = QHBoxLayout(filters)
        f.setContentsMargins(15, 8, 15, 8)
        f.setSpacing(10)

        f.addWidget(QLabel("وضعیت:"))
        self.filter_status = QComboBox()
        self.filter_status.addItems(["همه", "پرداخت شده", "پرداخت نشده"])
        self.filter_status.currentTextChanged.connect(self._apply_filters)
        f.addWidget(self.filter_status)

        f.addWidget(QLabel("از تاریخ:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setDate(QDate.currentDate().addDays(-30))
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.dateChanged.connect(self._apply_filters)
        f.addWidget(self.filter_date_from)

        f.addWidget(QLabel("تا تاریخ:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setDate(QDate.currentDate())
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.dateChanged.connect(self._apply_filters)
        f.addWidget(self.filter_date_to)

        f.addStretch()
        return filters

    def _create_search(self):
        search_box = QFrame()
        search_box.setObjectName("searchCard")
        s_layout = QHBoxLayout(search_box)
        s_layout.setContentsMargins(12, 5, 12, 5)
        icon = QLabel("🔍")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره قرارداد، کد ملی خریدار یا فروشنده...")
        self.search_input.textChanged.connect(self._search)
        s_layout.addWidget(icon)
        s_layout.addWidget(self.search_input)
        return search_box

    def _create_contracts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        self.tree = QTreeView()
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(12)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setAnimated(True)
        self.tree.doubleClicked.connect(self._open_contract_file)
        layout.addWidget(self.tree)
        self.tabs.addTab(tab, "📄 قراردادها")

    def _create_logs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("نوع لاگ:"))
        self.log_filter = QComboBox()
        self.log_filter.addItems(["همه", "error", "archive", "image", "license"])
        self.log_filter.currentTextChanged.connect(self._load_logs)
        filter_layout.addWidget(self.log_filter)
        layout.addLayout(filter_layout)

        self.table_logs = QTableView()
        self.table_logs.setAlternatingRowColors(True)
        layout.addWidget(self.table_logs)
        self.tabs.addTab(tab, "📋 لاگ‌ها")

    def _create_settings_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(15, 15, 15, 15)
        outer.setSpacing(10)

        form = QFrame()
        form.setObjectName("settingsForm")
        form.setStyleSheet("""
            #settingsForm { background-color: #ffffff; border-radius: 8px; padding: 10px; border: 1px solid #e1e4e8; }
            QLabel { color: #1f2328; font-size: 12px; }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #ffffff; color: #1f2328; border: 1px solid #d0d7de;
                border-radius: 4px; padding: 6px; font-size: 12px;
            }
        """)
        grid = QVBoxLayout(form)
        grid.setSpacing(12)

        def field_row(label_text, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(150)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            grid.addLayout(row)
            return row

        self.settings_customer_name = QLineEdit()
        self.settings_customer_name.setPlaceholderText("مثلاً: نمایشگاه اتومبیل تهران")
        field_row("نام مشتری/نمایشگاه:", self.settings_customer_name)

        self.settings_support_phone = QLineEdit()
        self.settings_support_phone.setPlaceholderText("مثلاً: 09123456789")
        field_row("شماره پشتیبانی:", self.settings_support_phone)

        logo_row = QHBoxLayout()
        self.settings_logo_path = QLineEdit()
        self.settings_logo_path.setReadOnly(True)
        btn_logo = QPushButton("انتخاب فایل...")
        btn_logo.clicked.connect(lambda: self._pick_image_file(self.settings_logo_path))
        logo_row.addWidget(self.settings_logo_path, 1)
        logo_row.addWidget(btn_logo)
        logo_container = QWidget()
        logo_container.setLayout(logo_row)
        logo_container.setMinimumHeight(32)
        field_row("لوگو:", logo_container)

        banner_row = QHBoxLayout()
        self.settings_banner_path = QLineEdit()
        self.settings_banner_path.setReadOnly(True)
        btn_banner = QPushButton("انتخاب فایل...")
        btn_banner.clicked.connect(lambda: self._pick_image_file(self.settings_banner_path))
        banner_row.addWidget(self.settings_banner_path, 1)
        banner_row.addWidget(btn_banner)
        banner_container = QWidget()
        banner_container.setLayout(banner_row)
        banner_container.setMinimumHeight(32)
        field_row("بنر پایین صفحه:", banner_container)

        self.settings_font_family = QComboBox()
        self.settings_font_family.addItems(
            ["(پیش‌فرض)", "Aria", "Aria Black", "Pelak", "Doran", "IRANSansDN"]
        )
        field_row("فونت رابط کاربری:", self.settings_font_family)

        from PySide6.QtWidgets import QSpinBox
        self.settings_font_scale = QSpinBox()
        self.settings_font_scale.setRange(70, 150)
        self.settings_font_scale.setSuffix(" %")
        self.settings_font_scale.setValue(100)
        field_row("اندازه فونت:", self.settings_font_scale)

        outer.addWidget(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save_settings = QPushButton("💾 ذخیره تنظیمات")
        btn_save_settings.setStyleSheet(
            "background-color: #2ea043; color: white; padding: 8px 20px; "
            "border-radius: 6px; font-weight: bold;"
        )
        btn_save_settings.clicked.connect(self._save_app_settings)
        btn_row.addWidget(btn_save_settings)
        outer.addLayout(btn_row)

        note = QLabel("ℹ️ تغییرات پس از بستن و اجرای دوباره برنامه اعمال می‌شوند.")
        note.setStyleSheet("color: #8b949e; font-size: 11px;")
        outer.addWidget(note)
        outer.addStretch()

        self._load_app_settings()
        self.tabs.addTab(tab, "⚙️ تنظیمات")

    def _pick_image_file(self, target_line_edit):
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب تصویر", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            target_line_edit.setText(path)

    def _load_app_settings(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings")
            values = dict(cur.fetchall())
            conn.close()
        except Exception:
            values = {}

        self.settings_customer_name.setText(values.get("customer_name", ""))
        self.settings_support_phone.setText(values.get("support_phone", ""))
        self.settings_logo_path.setText(values.get("logo_path", ""))
        self.settings_banner_path.setText(values.get("banner_path", ""))
        font_family = values.get("ui_font_family", "(پیش‌فرض)")
        idx = self.settings_font_family.findText(font_family)
        self.settings_font_family.setCurrentIndex(idx if idx >= 0 else 0)
        try:
            self.settings_font_scale.setValue(int(values.get("ui_font_scale", 100)))
        except (TypeError, ValueError):
            self.settings_font_scale.setValue(100)

    def _save_app_settings(self):
        try:
            base_dir = os.path.dirname(self.db_path)
            images_dir = os.path.join(base_dir, "assets", "images")
            os.makedirs(images_dir, exist_ok=True)

            def store_image(src_path, dest_name):
                if not src_path or not os.path.exists(src_path):
                    return None
                ext = os.path.splitext(src_path)[1] or ".png"
                dest_path = os.path.join(images_dir, dest_name + ext)
                shutil.copy2(src_path, dest_path)
                return dest_path

            logo_dest = store_image(self.settings_logo_path.text().strip(), "logo")
            banner_dest = store_image(self.settings_banner_path.text().strip(), "banner")

            values = {
                "customer_name": self.settings_customer_name.text().strip(),
                "support_phone": self.settings_support_phone.text().strip(),
                "ui_font_family": self.settings_font_family.currentText(),
                "ui_font_scale": str(self.settings_font_scale.value()),
            }
            if logo_dest:
                values["logo_path"] = logo_dest
            if banner_dest:
                values["banner_path"] = banner_dest

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            for key, value in values.items():
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
            conn.commit()
            conn.close()

            QMessageBox.information(
                self, "ذخیره شد",
                "تنظیمات ذخیره شد. برای اعمال کامل، برنامه را ببندید و دوباره اجرا کنید.",
            )
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره تنظیمات ناموفق بود:\n{e}")

    def _create_backup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        self.backup_list = QTreeView()
        self.backup_list.setAlternatingRowColors(True)
        layout.addWidget(QLabel("📁 بکاپ‌های موجود:"))
        layout.addWidget(self.backup_list)

        btn_layout = QHBoxLayout()
        btn_delete_backup = QPushButton("🗑️ حذف بکاپ")
        btn_delete_backup.clicked.connect(self._delete_selected_backup)
        btn_layout.addWidget(btn_delete_backup)

        btn_restore_backup = QPushButton("🔄 بازیابی بکاپ")
        btn_restore_backup.clicked.connect(self._restore_selected_backup)
        btn_layout.addWidget(btn_restore_backup)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "💾 بکاپ")

    def _create_footer(self):
        footer = QFrame()
        footer.setObjectName("footerCard")
        f = QHBoxLayout(footer)
        f.setContentsMargins(15, 5, 15, 5)
        self.footer_text = QLabel("💡 روی هر قرارداد دوبار کلیک کنید | ⚡ آپدیت خودکار هر 30 ثانیه")
        self.footer_text.setObjectName("footerLabel")
        self.record_count = QLabel("0")
        self.record_count.setObjectName("recordCount")
        f.addWidget(self.footer_text)
        f.addStretch()
        f.addWidget(self.record_count)
        return footer

    def _stat_card(self, icon, label, value):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        ic = QLabel(icon)
        ic.setObjectName("statIcon")
        text_w = QWidget()
        tv = QVBoxLayout(text_w)
        tv.setSpacing(2)
        val = QLabel(value)
        val.setObjectName("statValue")
        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        tv.addWidget(val)
        tv.addWidget(lbl)
        layout.addWidget(ic)
        layout.addWidget(text_w)
        layout.addStretch()
        card.value_label = val
        return card

    def _setup_auto_refresh(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(30000)

    def _auto_refresh(self):
        if self.isVisible() and self.tabs.currentIndex() == 0:
            self._load_data()

    def _load_data(self):
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            save_path = cur.execute("SELECT value FROM settings WHERE key='save_path'").fetchone()
            if save_path:
                self.contracts_dir = save_path[0]

            total = cur.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
            today = cur.execute("SELECT COUNT(*) FROM contracts WHERE date(created_at) = date('now')").fetchone()[0]
            paid = cur.execute("SELECT COUNT(*) FROM contracts WHERE is_payed = 1").fetchone()[0]
            unpaid = cur.execute("SELECT COUNT(*) FROM contracts WHERE is_payed = 0 OR is_payed IS NULL").fetchone()[0]
            this_month = cur.execute("SELECT COUNT(*) FROM contracts WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')").fetchone()[0]

            self.stat_total.value_label.setText(f"{total:,}")
            self.stat_today.value_label.setText(f"{today:,}")
            self.stat_paid.value_label.setText(f"{paid:,}")
            self.stat_unpaid.value_label.setText(f"{unpaid:,}")
            self.stat_month.value_label.setText(f"{this_month:,}")
            self.record_count.setText(f"{total:,} قرارداد")

            if unpaid > 20:
                self.warning_label.setText("⚠️ بیش از 20 قرارداد پرداخت نشده وجود دارد!")
            else:
                self.warning_label.setText("")

            self._load_tree(conn)
            self._load_logs()
            self._load_backup_list()

            self.last_contract_count = total
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def _load_tree(self, conn):
        status_filter = self.filter_status.currentText()
        date_from = self.filter_date_from.date().toString("yyyy-MM-dd")
        date_to = self.filter_date_to.date().toString("yyyy-MM-dd")

        query = """
            SELECT contract_number, buyer_id, seller_id, date_shamsi, is_payed, 
                   price_info, description_text, created_at, file_path,
                   seller_json, buyer_json, car_json, deal_json
            FROM contracts 
            WHERE date(created_at) BETWEEN ? AND ?
        """
        params = [date_from, date_to]

        if status_filter == "پرداخت شده":
            query += " AND is_payed = 1"
        elif status_filter == "پرداخت نشده":
            query += " AND (is_payed = 0 OR is_payed IS NULL)"

        query += " ORDER BY contract_number DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["قراردادها (برای دیدن جزئیات کلیک کنید)", ""])

        for r in rows:
            status_icon = "✅" if r['is_payed'] == 1 else "❌"
            parent = QStandardItem(f"{status_icon}  #{r['contract_number']}  |  {r['buyer_id']}  |  {r['date_shamsi']}")
            parent.setEditable(False)
            parent.setData(r['file_path'], Qt.UserRole)

            basic_info = QStandardItem("📋 اطلاعات پایه")
            basic_info.setEditable(False)
            basic_info.appendRow([QStandardItem("شماره"), QStandardItem(str(r['contract_number']))])
            basic_info.appendRow([QStandardItem("خریدار"), QStandardItem(r['buyer_id'])])
            basic_info.appendRow([QStandardItem("فروشنده"), QStandardItem(r['seller_id'])])
            basic_info.appendRow([QStandardItem("تاریخ"), QStandardItem(r['date_shamsi'])])
            basic_info.appendRow([QStandardItem("تاریخ ثبت"), QStandardItem(r['created_at'][:10] if r['created_at'] else "-")])
            basic_info.appendRow([QStandardItem("وضعیت"), QStandardItem("پرداخت شده" if r['is_payed'] == 1 else "پرداخت نشده")])
            basic_info.appendRow([QStandardItem("نحوه پرداخت"), QStandardItem(r['price_info'] or "-")])
            parent.appendRow(basic_info)

            for json_field, label in [("seller_json", "👤 فروشنده"), ("buyer_json", "👥 خریدار"),
                                       ("car_json", "🚗 خودرو"), ("deal_json", "📝 معامله")]:
                if r[json_field]:
                    try:
                        data = json.loads(r[json_field])
                        if isinstance(data, dict):
                            group = QStandardItem(label)
                            group.setEditable(False)
                            for k, v in data.items():
                                group.appendRow([QStandardItem(k), QStandardItem(str(v))])
                            parent.appendRow(group)
                    except:
                        pass

            model.appendRow(parent)

        self.tree.setModel(model)
        self.tree.setColumnWidth(0, 480)
        self.tree.setColumnWidth(1, 0)
        self.tree.expandToDepth(0)

    def _load_logs(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            filter_text = self.log_filter.currentText()
            
            if filter_text == "همه":
                rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 300").fetchall()
            else:
                rows = conn.execute("SELECT * FROM logs WHERE action LIKE ? ORDER BY id DESC LIMIT 300", (f"%{filter_text}%",)).fetchall()
            conn.close()

            if rows:
                m = QStandardItemModel()
                m.setHorizontalHeaderLabels(list(rows[0].keys()))
                for r in rows:
                    m.appendRow([QStandardItem(str(r[k]) if r[k] else "") for k in r.keys()])
                self.table_logs.setModel(m)
                self.table_logs.resizeColumnsToContents()
        except:
            pass

    def _load_backup_list(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        backups = [f for f in os.listdir(self.backup_dir) if f.endswith(".zip") or f.endswith(".db")]

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["نام فایل", "تاریخ", "نوع", "حجم"])
        for b in backups[:50]:
            path = os.path.join(self.backup_dir, b)
            stat = os.stat(path)
            size = stat.st_size // 1024
            date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            ftype = "دیتابیس" if b.endswith(".db") else "قراردادها"
            model.appendRow([QStandardItem(b), QStandardItem(date), QStandardItem(ftype), QStandardItem(f"{size} KB")])

        self.backup_list.setModel(model)
        self.backup_list.setColumnWidth(0, 250)

    def _apply_filters(self):
        self._load_data()

    def _search(self):
        txt = self.search_input.text().strip()
        if not txt:
            self._load_data()
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT contract_number, buyer_id, seller_id, date_shamsi, is_payed, price_info, file_path
                FROM contracts 
                WHERE buyer_id LIKE ? OR seller_id LIKE ? OR contract_number LIKE ?
                ORDER BY contract_number DESC LIMIT 200
            """, (f"%{txt}%", f"%{txt}%", f"%{txt}%")).fetchall()
            conn.close()

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["نتیجه جستجو", ""])

            for r in rows:
                status_icon = "✅" if r['is_payed'] == 1 else "❌"
                parent = QStandardItem(f"{status_icon}  #{r['contract_number']}  |  {r['buyer_id']}  |  {r['date_shamsi']}")
                parent.setEditable(False)
                parent.setData(r['file_path'], Qt.UserRole)

                basic = QStandardItem("📋 اطلاعات")
                basic.appendRow([QStandardItem("شماره"), QStandardItem(str(r['contract_number']))])
                basic.appendRow([QStandardItem("خریدار"), QStandardItem(r['buyer_id'])])
                basic.appendRow([QStandardItem("فروشنده"), QStandardItem(r['seller_id'])])
                basic.appendRow([QStandardItem("تاریخ"), QStandardItem(r['date_shamsi'])])
                basic.appendRow([QStandardItem("وضعیت"), QStandardItem("پرداخت شده" if r['is_payed'] == 1 else "پرداخت نشده")])
                parent.appendRow(basic)
                model.appendRow(parent)

            self.tree.setModel(model)
            self.tree.expandToDepth(0)
        except:
            pass

    def _open_contract_file(self, index):
        item = self.tree.model().itemFromIndex(index)
        while item.parent():
            item = item.parent()
        file_path = item.data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QDesktopServices.standardPaths().locate(QDesktopServices.standardPaths().HomeLocation, file_path))
        elif file_path:
            QMessageBox.warning(self, "خطا", f"فایل یافت نشد:\n{file_path}")

    def _daily_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM contracts WHERE date(created_at) = date('now')").fetchone()[0]
        paid = conn.execute("SELECT COUNT(*) FROM contracts WHERE date(created_at) = date('now') AND is_payed = 1").fetchone()[0]
        conn.close()
        QMessageBox.information(self, "گزارش روزانه", 
            f"📊 گزارش قراردادهای امروز ({today})\n\n📄 کل: {count}\n✅ پرداخت شده: {paid}\n❌ پرداخت نشده: {count - paid}")

    def _monthly_report(self):
        now = datetime.now()
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM contracts WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')").fetchone()[0]
        paid = conn.execute("SELECT COUNT(*) FROM contracts WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now') AND is_payed = 1").fetchone()[0]
        conn.close()
        QMessageBox.information(self, "گزارش ماهانه", 
            f"📊 گزارش قراردادهای ماه {now.strftime('%B %Y')}\n\n📄 کل: {count}\n✅ پرداخت شده: {paid}\n❌ پرداخت نشده: {count - paid}")

    def _backup_database(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_name = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join(self.backup_dir, backup_name)
        shutil.copy2(self.db_path, backup_path)
        QMessageBox.information(self, "بکاپ", f"بکاپ دیتابیس ذخیره شد:\n{backup_path}")
        self._load_backup_list()

    def _backup_contracts_folder(self):
        if not self.contracts_dir or not os.path.exists(self.contracts_dir):
            QMessageBox.warning(self, "خطا", "مسیر پوشه قراردادها یافت نشد!")
            return

        os.makedirs(self.backup_dir, exist_ok=True)
        backup_name = f"backup_contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        backup_path = os.path.join(self.backup_dir, backup_name)

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.contracts_dir):
                for file in files:
                    if file.endswith('.docx'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.contracts_dir)
                        zipf.write(file_path, arcname)

        QMessageBox.information(self, "بکاپ", f"بکاپ قراردادها ذخیره شد:\n{backup_path}\nحجم: {os.path.getsize(backup_path) // 1024} KB")
        self._load_backup_list()

    def _restore_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل بکاپ", self.backup_dir, "Backup Files (*.zip *.db)")
        if not file_path:
            return

        confirm = QMessageBox.question(self, "تأیید بازیابی", "آیا از بازیابی این بکاپ مطمئن هستید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if file_path.endswith('.db'):
                shutil.copy2(file_path, self.db_path)
                QMessageBox.information(self, "بازیابی", "دیتابیس بازیابی شد.")
            elif file_path.endswith('.zip') and self.contracts_dir:
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    zipf.extractall(self.contracts_dir)
                QMessageBox.information(self, "بازیابی", "قراردادها بازیابی شدند.")
            self._load_data()

    def _restore_selected_backup(self):
        selection = self.backup_list.selectionModel().selectedRows()
        if not selection:
            QMessageBox.warning(self, "خطا", "لطفاً یک بکاپ را انتخاب کنید.")
            return
        backup_name = selection[0].data()
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        confirm = QMessageBox.question(self, "تأیید بازیابی", f"آیا از بازیابی '{backup_name}' مطمئن هستید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if backup_name.endswith('.db'):
                shutil.copy2(backup_path, self.db_path)
            elif backup_name.endswith('.zip') and self.contracts_dir:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(self.contracts_dir)
            self._load_data()
            QMessageBox.information(self, "بازیابی", "بازیابی با موفقیت انجام شد.")

    def _delete_selected_backup(self):
        selection = self.backup_list.selectionModel().selectedRows()
        if not selection:
            QMessageBox.warning(self, "خطا", "لطفاً یک بکاپ را انتخاب کنید.")
            return
        backup_name = selection[0].data()
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        confirm = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف '{backup_name}' مطمئن هستید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            os.remove(backup_path)
            self._load_backup_list()