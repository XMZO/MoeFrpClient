# ImageLabel.py

from PySide6.QtWidgets import QGraphicsBlurEffect, QLabel, QSizePolicy

from PySide6.QtGui import QColor, QPixmap, QResizeEvent, QMovie, QPainter, QPainterPath
from PySide6.QtCore import QByteArray, Qt, Signal

class ImageLabel(QLabel):

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = QPixmap()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setScaledContents(False)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

        self.clear()


    def paintEvent(self, event):
        if self._original_pixmap.isNull() or (self.movie() and self.movie().isValid()):
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)


        path = QPainterPath()
        path.addRoundedRect(self.rect(), 8, 8)
        painter.setClipPath(path)


        bg_pixmap = self._original_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(30)
        blurred_bg = self.apply_effect_to_pixmap(bg_pixmap, blur_effect)
        painter.drawPixmap(self.rect(), blurred_bg)




        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)


        fg_pixmap = self._original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        x = (self.width() - fg_pixmap.width()) / 2
        y = (self.height() - fg_pixmap.height()) / 2
        painter.drawPixmap(int(x), int(y), fg_pixmap)



    @staticmethod
    def apply_effect_to_pixmap(src: QPixmap, effect) -> QPixmap:

        from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
        if src.isNull():
            return QPixmap()

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem()
        item.setPixmap(src)
        item.setGraphicsEffect(effect)
        scene.addItem(item)


        res = QPixmap(src.size())
        res.fill(Qt.transparent)


        pr = QPainter(res)
        scene.render(pr, res.rect(), src.rect())
        pr.end()

        return res



    def set_pixmap_from_data(self, image_data: QByteArray):

        if self.movie():
            self.movie().stop()
            self.setMovie(None)

        if not image_data or image_data.isEmpty():
            self.clear()
            return


        success = self._original_pixmap.loadFromData(image_data)

        if not success:
            self.clear()
            return


        self.setText("")
        self.setPixmap(QPixmap())
        self.update()

    def update_scaled_pixmap(self):

        if not self._original_pixmap.isNull():

            self.update()

    def resizeEvent(self, event: QResizeEvent):


        if not self._original_pixmap.isNull():
            self.update_scaled_pixmap()
        super().resizeEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def setMovie(self, movie: QMovie):

        self._original_pixmap = QPixmap()


        if movie and movie.isValid():
            self.setText("")
            self.setStyleSheet("""
                ImageLabel {
                    background-color: #2E3440;
                    border-radius: 8px;
                    margin-top: 10px;
                }
            """)

        super().setMovie(movie)

        if movie and movie.isValid():
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)


    def clear(self):

        if self.movie():
            self.movie().stop()
            self.setMovie(None)


        self._original_pixmap = QPixmap()


        self.setText("正在加载色图...")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            ImageLabel {
                background-color: #2E3440;
                border-radius: 8px;
                color: #D8DEE9;
                font-style: italic;
                margin-top: 10px;
            }
        """)
        self.update()