from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QWidget


class CropFrame(QWidget):
    def __init__(self, w, h, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(0, 255, 0), 3)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width(), self.height())


class SimpleImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.zoom = 1.0
        self.offset = QPoint(0, 0)
        self.dragging = False
        self.last_pos = QPoint()

    def load_image(self, path):
        self.pixmap = QPixmap(path)
        self.zoom = 1.0
        self.offset = QPoint(0, 0)
        self.update()
        if hasattr(self.parent(), "db"):
            self.parent().db.logger.log("image_load", "", {"path": path})

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
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
        if delta > 0:
            self.zoom *= 1.1
        else:
            self.zoom /= 1.1
        self.update()

    def paintEvent(self, event):
        if not self.pixmap:
            return

        painter = QPainter(self)

        scaled = self.pixmap.scaled(
            self.pixmap.size() * self.zoom,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        x = self.offset.x() + (self.width() - scaled.width()) / 2
        y = self.offset.y() + (self.height() - scaled.height()) / 2

        painter.drawPixmap(int(x), int(y), scaled)

    def export_crop(self, crop_rect):
        if not self.pixmap:
            return None

        img = QImage(crop_rect.width(), crop_rect.height(), QImage.Format_ARGB32)
        img.fill(Qt.white)

        painter = QPainter(img)

        scaled = self.pixmap.scaled(
            self.pixmap.size() * self.zoom,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        x = self.offset.x() + (self.width() - scaled.width()) / 2
        y = self.offset.y() + (self.height() - scaled.height()) / 2

        painter.drawPixmap(
            -crop_rect.x() + int(x),
            -crop_rect.y() + int(y),
            scaled
        )

        painter.end()

        if hasattr(self.parent(), "db"):
            self.parent().db.logger.log(
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ویرایش تصویر")
        self.setMinimumSize(700, 700)

        layout = QVBoxLayout(self)
        self.viewer = SimpleImageViewer(self)
        layout.addWidget(self.viewer)

        self.crop_w = int(3.88 * 96)
        self.crop_h = int(3.32 * 96)

        self.crop_frame = CropFrame(self.crop_w, self.crop_h, self)
        self.crop_frame.raise_()

        btn = QPushButton("تأیید")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        if hasattr(self, "db"):
            self.db.logger.log("photo_editor_open", "")

    def resizeEvent(self, event):
        self.crop_frame.move(
            (self.width() - self.crop_w) // 2,
            (self.height() - self.crop_h) // 2
        )

    def load_image(self, path):
        self.viewer.load_image(path)
        if hasattr(self, "db"):
            self.db.logger.log("photo_editor_load", "", {"path": path})

    def get_final_image(self):
        crop_rect = QRect(
            self.crop_frame.x(),
            self.crop_frame.y(),
            self.crop_w,
            self.crop_h
        )

        if hasattr(self, "db"):
            self.db.logger.log(
                "photo_editor_export", "",
                {"crop_w": self.crop_w, "crop_h": self.crop_h}
            )

        return self.viewer.export_crop(crop_rect)