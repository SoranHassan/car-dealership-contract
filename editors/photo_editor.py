from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QWidget
import logging

# تنظیم لاگر ساده برای این ماژول
logger = logging.getLogger(__name__)


class CropFrame(QWidget):
    """قاب سبز رنگ برای نشان دادن ناحیه برش"""
    
    def __init__(self, w, h, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        # مهم: اجازه می‌دهد موس از روی این ویجت به ویجت زیرین برود
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        # اطمینان از اینکه قاب همیشه روی بقیه است
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        # قاب سبز با ضخامت 3 پیکسل
        pen = QPen(QColor(0, 255, 0), 3)
        painter.setPen(pen)
        # حذف براش (شفاف)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, self.width(), self.height())


class SimpleImageViewer(QWidget):
    """ویجت نمایش و ویرایش تصویر با قابلیت زوم و درگ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.zoom = 1.0
        self.offset = QPoint(0, 0)
        self.dragging = False
        self.last_pos = QPoint()
        self._parent_app = self._find_parent_app()

    def _find_parent_app(self):
        """پیدا کردن والد اصلی که ممکن است db داشته باشد"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'db') and parent.db:
                return parent
            parent = parent.parent()
        return None

    def _safe_log(self, action, message="", data=None):
        """لاگ کردن بدون خطا - اگر db وجود نداشت، فقط ignore کن"""
        try:
            if self._parent_app and hasattr(self._parent_app, 'db') and self._parent_app.db:
                self._parent_app.db.logger.log(action, message, data)
        except Exception as e:
            # لاگ ندادن بهتر از کرش کردن برنامه است
            logging.warning(f"Log failed in photo_editor: {e}")

    def load_image(self, path):
        try:
            self.pixmap = QPixmap(path)
            if self.pixmap.isNull():
                logger.error(f"Failed to load image: {path}")
                return False
            self.zoom = 1.0
            self.offset = QPoint(0, 0)
            self.update()
            self._safe_log("image_load", "", {"path": path})
            return True
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap:
            self.dragging = True
            self.last_pos = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.dragging and self.pixmap:
            pos = event.position().toPoint()
            delta = pos - self.last_pos
            self.offset += delta
            self.last_pos = pos
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def wheelEvent(self, event):
        if not self.pixmap:
            return
        delta = event.angleDelta().y()
        # محدود کردن زوم (حداقل 0.1، حداکثر 10)
        if delta > 0:
            self.zoom = min(self.zoom * 1.1, 10.0)
        else:
            self.zoom = max(self.zoom / 1.1, 0.1)
        self.update()

    def paintEvent(self, event):
        if not self.pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # محاسبه اندازه تصویر پس از زوم
        scaled = self.pixmap.scaled(
            self.pixmap.size() * self.zoom,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # محاسبه موقعیت برای وسط چین شدن
        x = self.offset.x() + (self.width() - scaled.width()) / 2
        y = self.offset.y() + (self.height() - scaled.height()) / 2

        painter.drawPixmap(int(x), int(y), scaled)

    def export_crop(self, crop_rect):
        """
        برش ناحیه مشخص شده از تصویر
        crop_rect: مستطیل ناحیه برش (به مختصات صفحه)
        """
        if not self.pixmap:
            return None

        # ایجاد تصویر خالی به اندازه ناحیه برش
        img = QImage(crop_rect.width(), crop_rect.height(), QImage.Format_ARGB32)
        img.fill(Qt.white)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # محاسبه تصویر زوم شده
        scaled = self.pixmap.scaled(
            self.pixmap.size() * self.zoom,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # محاسبه موقعیت تصویر در ویجت
        x = self.offset.x() + (self.width() - scaled.width()) / 2
        y = self.offset.y() + (self.height() - scaled.height()) / 2

        # رسم بخش مورد نظر از تصویر
        painter.drawPixmap(
            -crop_rect.x() + int(x),
            -crop_rect.y() + int(y),
            scaled
        )

        painter.end()

        self._safe_log(
            "image_crop", "",
            {
                "crop_x": crop_rect.x(),
                "crop_y": crop_rect.y(),
                "crop_w": crop_rect.width(),
                "crop_h": crop_rect.height()
            }
        )

        return img


class PhotoEditorDialog(QDialog):
    """دیالوگ ویرایش تصویر با قابلیت برش"""
    
    # اندازه استاندارد برای عکس کارشناسی (بر حسب اینچ * 96 DPI)
    # 3.88 x 3.8 اینچ ≈ 372 x 365 پیکسل
    CROP_WIDTH = int(3.88 * 96)   # ~372
    CROP_HEIGHT = int(3.8 * 96)   # ~365
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ویرایش تصویر کارشناسی")
        self.setMinimumSize(700, 700)
        self.setModal(True)  # دیالوگ مودال
        
        # ذخیره والد اصلی برای دسترسی به db
        self.main_app = self._find_main_app(parent)
        
        layout = QVBoxLayout(self)
        
        # ویور تصویر
        self.viewer = SimpleImageViewer(self)
        layout.addWidget(self.viewer)
        
        # قاب برش
        self.crop_frame = CropFrame(self.CROP_WIDTH, self.CROP_HEIGHT, self)
        self.crop_frame.raise_()
        
        # دکمه تأیید
        self.btn_confirm = QPushButton("تأیید و ادامه")
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_confirm.clicked.connect(self.accept)
        layout.addWidget(self.btn_confirm)
        
        # دکمه انصراف
        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel)
        
        self._safe_log("photo_editor_open", "Photo editor dialog opened")

    def _find_main_app(self, parent):
        """پیدا کردن آبجکت اصلی App که دارای db باشد"""
        while parent:
            if hasattr(parent, 'db') and parent.db:
                return parent
            parent = parent.parent()
        return None

    def _safe_log(self, action, message="", data=None):
        """لاگ امن بدون کرش کردن برنامه"""
        try:
            if self.main_app and hasattr(self.main_app, 'db') and self.main_app.db:
                self.main_app.db.logger.log(action, message, data)
        except Exception as e:
            logging.warning(f"Log failed in PhotoEditorDialog: {e}")

    def resizeEvent(self, event):
        """وقتی اندازه دیالوگ تغییر می‌کند، قاب برش را وسط قرار بده"""
        self.crop_frame.move(
            (self.width() - self.CROP_WIDTH) // 2,
            (self.height() - self.CROP_HEIGHT) // 2
        )
        self.crop_frame.raise_()  # اطمینان از اینکه قاب روی همه چیز است
        super().resizeEvent(event)

    def showEvent(self, event):
        """وقتی دیالوگ نمایش داده می‌شود، قاب برش را تنظیم کن"""
        super().showEvent(event)
        # اطمینان از موقعیت صحیح قاب برش
        self.crop_frame.move(
            (self.width() - self.CROP_WIDTH) // 2,
            (self.height() - self.CROP_HEIGHT) // 2
        )
        self.crop_frame.raise_()

    def load_image(self, path):
        """بارگذاری تصویر در ویور"""
        if not path or not os.path.exists(path):
            logger.error(f"Image path does not exist: {path}")
            return False
        
        success = self.viewer.load_image(path)
        if success:
            self._safe_log("photo_editor_load", "", {"path": path})
        else:
            logger.error(f"Failed to load image: {path}")
        return success

    def get_final_image(self):
        """دریافت تصویر نهایی پس از برش"""
        crop_rect = QRect(
            self.crop_frame.x(),
            self.crop_frame.y(),
            self.CROP_WIDTH,
            self.CROP_HEIGHT
        )
        
        # اطمینان از اینکه مستطیل برش در محدوده معتبر است
        if crop_rect.x() < 0:
            crop_rect.setX(0)
        if crop_rect.y() < 0:
            crop_rect.setY(0)
        
        self._safe_log(
            "photo_editor_export", "",
            {"crop_w": self.CROP_WIDTH, "crop_h": self.CROP_HEIGHT}
        )
        
        return self.viewer.export_crop(crop_rect)


# اضافه کردن import os برای توابع بالا
import os