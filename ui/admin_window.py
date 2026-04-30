# ui/admin_window.py - نسخه با نمایش جزئیات روی کلیک
import json
import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableView, QTreeView,
    QMessageBox, QFrame, QLineEdit, QApplication
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QStandardItemModel, QStandardItem


class AdminWindow(QWidget):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("🎛️ AutoGarideh | پنل مدیریت")
        self.resize(1350, 800)
        self.setMinimumSize(1100, 650)

        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                color: #ffffff;
                font-family: 'Segoe UI', 'Inter', 'Arial';
                font-size: 12px;
            }
            QFrame#headerCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #161b22, stop:1 #0d1117);
                border-radius: 12px;
                min-height: 65px;
                border: 1px solid #30363d;
            }
            #headerTitle {
                font-size: 18px;
                font-weight: bold;
                color: #e94560;
            }
            #headerSub {
                font-size: 11px;
                color: #8b949e;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
            QPushButton#dangerBtn {
                background-color: #21262d;
                border: 1px solid #30363d;
            }
            QPushButton#dangerBtn:hover {
                background-color: #da3633;
                border: none;
            }
            QPushButton#refreshBtn {
                background-color: #238636;
            }
            QPushButton#refreshBtn:hover {
                background-color: #2ea043;
            }
            QFrame#statCard {
                background-color: #161b22;
                border-radius: 12px;
                border: 1px solid #30363d;
                min-height: 85px;
            }
            #statIcon {
                font-size: 32px;
            }
            #statValue {
                font-size: 24px;
                font-weight: bold;
                color: #e94560;
            }
            #statLabel {
                font-size: 11px;
                color: #8b949e;
            }
            QFrame#searchCard {
                background-color: #161b22;
                border-radius: 10px;
                border: 1px solid #30363d;
                min-height: 45px;
            }
            QLineEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #e94560;
            }
            QTabWidget::pane {
                background-color: #161b22;
                border-radius: 10px;
                border: 1px solid #30363d;
            }
            QTabBar::tab {
                background-color: #21262d;
                color: #8b949e;
                padding: 8px 22px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #e94560;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #30363d;
                color: #ffffff;
            }
            QTreeView, QTableView {
                background-color: #0d1117;
                alternate-background-color: #161b22;
                selection-background-color: #e94560;
                selection-color: white;
                border: none;
                font-size: 12px;
                outline: 0;
            }
            QTreeView::item, QTableView::item {
                padding: 8px;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #e94560;
                padding: 8px;
                font-weight: bold;
                border: none;
                font-size: 12px;
            }
            QFrame#footerCard {
                background-color: #161b22;
                border-radius: 10px;
                min-height: 40px;
                border: 1px solid #30363d;
            }
            #footerLabel {
                color: #8b949e;
                font-size: 11px;
            }
            #recordCount {
                background-color: #21262d;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 11px;
                color: #e94560;
                font-weight: bold;
            }
        """)

        self._setup_ui()
        self._load_data()

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)

        # ===== هدر =====
        header = QFrame()
        header.setObjectName("headerCard")
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 8, 20, 8)

        title_w = QWidget()
        tl = QVBoxLayout(title_w)
        tl.setSpacing(2)
        title = QLabel("🎛️ AutoGarideh Manager")
        title.setObjectName("headerTitle")
        sub = QLabel("سیستم مدیریت و گزارش‌گیری")
        sub.setObjectName("headerSub")
        tl.addWidget(title)
        tl.addWidget(sub)

        self.db_status = QLabel("🟢 متصل")
        self.db_status.setStyleSheet("background-color: #21262d; padding: 4px 12px; border-radius: 20px; font-size: 11px;")

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
        main.addWidget(header)

        # ===== کارت آمار =====
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stat_total = self._stat_card("📊", "کل قراردادها", "0")
        self.stat_today = self._stat_card("📅", "امروز", "0")
        self.stat_paid = self._stat_card("✅", "پرداخت شده", "0")
        self.stat_unpaid = self._stat_card("⏳", "پرداخت نشده", "0")
        stats.addWidget(self.stat_total)
        stats.addWidget(self.stat_today)
        stats.addWidget(self.stat_paid)
        stats.addWidget(self.stat_unpaid)
        main.addLayout(stats)

        # ===== جستجو =====
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
        main.addWidget(search_box)

        # ===== تب‌ها =====
        self.tabs = QTabWidget()
        
        # تب قراردادها (درختی)
        contract_tab = QWidget()
        c_layout = QVBoxLayout(contract_tab)
        c_layout.setContentsMargins(8, 8, 8, 8)
        
        self.tree = QTreeView()
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(15)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setAnimated(True)
        c_layout.addWidget(self.tree)
        self.tabs.addTab(contract_tab, "📄 قراردادها")
        
        # تب لاگ‌ها
        log_tab = QWidget()
        l_layout = QVBoxLayout(log_tab)
        l_layout.setContentsMargins(8, 8, 8, 8)
        self.table_logs = QTableView()
        self.table_logs.setAlternatingRowColors(True)
        l_layout.addWidget(self.table_logs)
        self.tabs.addTab(log_tab, "📋 لاگ‌ها")
        
        # تب تنظیمات
        set_tab = QWidget()
        set_layout = QVBoxLayout(set_tab)
        set_layout.setContentsMargins(8, 8, 8, 8)
        self.table_settings = QTableView()
        self.table_settings.setAlternatingRowColors(True)
        set_layout.addWidget(self.table_settings)
        self.tabs.addTab(set_tab, "⚙️ تنظیمات")
        
        main.addWidget(self.tabs)

        # ===== فوتر =====
        footer = QFrame()
        footer.setObjectName("footerCard")
        f = QHBoxLayout(footer)
        f.setContentsMargins(15, 5, 15, 5)
        self.footer_text = QLabel("💡 روی هر قرارداد دوبار کلیک کنید تا جزئیات کامل نمایش داده شود")
        self.footer_text.setObjectName("footerLabel")
        self.record_count = QLabel("0")
        self.record_count.setObjectName("recordCount")
        f.addWidget(self.footer_text)
        f.addStretch()
        f.addWidget(self.record_count)
        main.addWidget(footer)

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

    def _load_data(self):
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            total = cur.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
            today = cur.execute("SELECT COUNT(*) FROM contracts WHERE date(created_at) = date('now')").fetchone()[0]
            paid = cur.execute("SELECT COUNT(*) FROM contracts WHERE is_payed = 1").fetchone()[0]
            unpaid = cur.execute("SELECT COUNT(*) FROM contracts WHERE is_payed = 0 OR is_payed IS NULL").fetchone()[0]

            self.stat_total.value_label.setText(f"{total:,}")
            self.stat_today.value_label.setText(f"{today:,}")
            self.stat_paid.value_label.setText(f"{paid:,}")
            self.stat_unpaid.value_label.setText(f"{unpaid:,}")
            self.record_count.setText(f"{total:,} قرارداد")

            # ===== ایجاد درخت با جزئیات کامل =====
            rows = cur.execute("""
                SELECT contract_number, buyer_id, seller_id, date_shamsi, is_payed, 
                       price_info, description_text, created_at,
                       seller_json, buyer_json, car_json, deal_json
                FROM contracts ORDER BY contract_number DESC LIMIT 300
            """).fetchall()

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["قراردادها (برای دیدن جزئیات کلیک کنید)", ""])
            
            for r in rows:
                # آیتم اصلی (قرارداد)
                status_icon = "✅" if r['is_payed'] == 1 else "❌" if r['is_payed'] == 0 else "❓"
                parent = QStandardItem(f"{status_icon}  قرارداد #{r['contract_number']}  |  {r['buyer_id']}  |  {r['date_shamsi']}")
                parent.setEditable(False)
                
                # اطلاعات پایه
                basic_info = QStandardItem("📋 اطلاعات پایه")
                basic_info.setEditable(False)
                
                basic_info.appendRow([QStandardItem("شماره قرارداد"), QStandardItem(str(r['contract_number']))])
                basic_info.appendRow([QStandardItem("خریدار"), QStandardItem(r['buyer_id'])])
                basic_info.appendRow([QStandardItem("فروشنده"), QStandardItem(r['seller_id'])])
                basic_info.appendRow([QStandardItem("تاریخ معامله"), QStandardItem(r['date_shamsi'])])
                basic_info.appendRow([QStandardItem("تاریخ ثبت"), QStandardItem(r['created_at'][:10] if r['created_at'] else "-")])
                basic_info.appendRow([QStandardItem("وضعیت پرداخت"), QStandardItem("پرداخت شده" if r['is_payed'] == 1 else "پرداخت نشده")])
                basic_info.appendRow([QStandardItem("نحوه پرداخت"), QStandardItem(r['price_info'] or "-")])
                basic_info.appendRow([QStandardItem("توضیحات"), QStandardItem((r['description_text'] or "-")[:100])])
                
                parent.appendRow(basic_info)
                
                # اطلاعات فروشنده از JSON
                if r['seller_json']:
                    try:
                        seller_data = json.loads(r['seller_json'])
                        seller_info = QStandardItem("👤 اطلاعات فروشنده")
                        seller_info.setEditable(False)
                        for k, v in seller_data.items():
                            seller_info.appendRow([QStandardItem(k), QStandardItem(str(v))])
                        parent.appendRow(seller_info)
                    except:
                        pass
                
                # اطلاعات خریدار از JSON
                if r['buyer_json']:
                    try:
                        buyer_data = json.loads(r['buyer_json'])
                        buyer_info = QStandardItem("👥 اطلاعات خریدار")
                        buyer_info.setEditable(False)
                        for k, v in buyer_data.items():
                            buyer_info.appendRow([QStandardItem(k), QStandardItem(str(v))])
                        parent.appendRow(buyer_info)
                    except:
                        pass
                
                # اطلاعات خودرو از JSON
                if r['car_json']:
                    try:
                        car_data = json.loads(r['car_json'])
                        car_info = QStandardItem("🚗 اطلاعات خودرو")
                        car_info.setEditable(False)
                        for k, v in car_data.items():
                            car_info.appendRow([QStandardItem(k), QStandardItem(str(v))])
                        parent.appendRow(car_info)
                    except:
                        pass
                
                model.appendRow(parent)
            
            self.tree.setModel(model)
            self.tree.setColumnWidth(0, 450)
            self.tree.setColumnWidth(1, 0)  # ستون دوم مخفی
            self.tree.expandToDepth(0)  # فقط سطح اول باز باشد
            self.tree.clicked.connect(self._on_item_clicked)  # کلیک برای باز شدن
            
            # لاگ‌ها
            logs = cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 200").fetchall()
            if logs:
                m = QStandardItemModel()
                m.setHorizontalHeaderLabels(list(logs[0].keys()))
                for r in logs:
                    m.appendRow([QStandardItem(str(r[k]) if r[k] else "") for k in r.keys()])
                self.table_logs.setModel(m)
                self.table_logs.resizeColumnsToContents()

            # تنظیمات
            sets = cur.execute("SELECT * FROM settings").fetchall()
            if sets:
                m = QStandardItemModel()
                m.setHorizontalHeaderLabels(list(sets[0].keys()))
                for r in sets:
                    m.appendRow([QStandardItem(str(r[k]) if r[k] else "") for k in r.keys()])
                self.table_settings.setModel(m)
                self.table_settings.resizeColumnsToContents()

            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def _on_item_clicked(self, index):
        """وقتی روی آیتم کلیک می‌شود، اگر باز نیست باز کن"""
        if not self.tree.isExpanded(index):
            self.tree.expand(index)
        else:
            self.tree.collapse(index)

    def _search(self):
        txt = self.search_input.text().strip()
        if not txt:
            self._load_data()
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT contract_number, buyer_id, seller_id, date_shamsi, is_payed, price_info
                FROM contracts 
                WHERE buyer_id LIKE ? OR seller_id LIKE ? OR contract_number LIKE ?
                ORDER BY contract_number DESC LIMIT 200
            """, (f"%{txt}%", f"%{txt}%", f"%{txt}%")).fetchall()
            conn.close()
            
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["قراردادها (نتیجه جستجو)", ""])
            
            for r in rows:
                status_icon = "✅" if r['is_payed'] == 1 else "❌"
                parent = QStandardItem(f"{status_icon}  قرارداد #{r['contract_number']}  |  {r['buyer_id']}  |  {r['date_shamsi']}")
                parent.setEditable(False)
                
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
            
        except Exception as e:
            pass