# ImageLabel.py

from PySide6.QtWidgets import QGraphicsBlurEffect, QLabel, QSizePolicy
from PySide6.QtGui import QColor, QPixmap, QResizeEvent, QMovie, QPainter, QPainterPath
from PySide6.QtCore import QByteArray, Qt, Signal

class ImageLabel(QLabel):
    """
    一个专门用于显示图片的QLabel，它能实现圆角显示，
    在尺寸变化时保持高质量缩放，并支持点击。
    """
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = QPixmap()
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 关闭 setScaledContents，用 paintEvent 绘制
        self.setScaledContents(False) 
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        # 在初始化时就设置好初始占位符样式
        self.clear() 

    # --- 重写 paintEvent 来实现圆角裁切 ---
    def paintEvent(self, event):
        if self._original_pixmap.isNull() or (self.movie() and self.movie().isValid()):
            super().paintEvent(event)
            return
 
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 定义最终的圆角形状并裁切
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 8, 8)
        painter.setClipPath(path)
        
        # 绘制高斯模糊背景
        bg_pixmap = self._original_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(30) # 可以适当加大模糊度，让它更像色块
        blurred_bg = self.apply_effect_to_pixmap(bg_pixmap, blur_effect)
        painter.drawPixmap(self.rect(), blurred_bg)
 
        # --- 在模糊背景上绘制一个半透明的黑色蒙版 ---
        # 这个蒙版会压暗背景，从而突出前景
        # QColor(0, 0, 0, 120) -> 黑色，120是透明度 (0-255)，数值越大越暗
        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)
 
        # 在最上层绘制清晰、完整的前景图
        fg_pixmap = self._original_pixmap.scaled(
            self.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        x = (self.width() - fg_pixmap.width()) / 2
        y = (self.height() - fg_pixmap.height()) / 2
        painter.drawPixmap(int(x), int(y), fg_pixmap)
 
 
    # --- 一个静态方法，用于给Pixmap应用效果 ---
    @staticmethod
    def apply_effect_to_pixmap(src: QPixmap, effect) -> QPixmap:
        """对给定的Pixmap应用图形效果（如模糊），并返回一个新的Pixmap"""
        from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
        if src.isNull():
            return QPixmap()
        
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem()
        item.setPixmap(src)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
 
        # 创建一个和源图片一样大小的新 QPixmap 来接收渲染结果
        res = QPixmap(src.size())
        res.fill(Qt.transparent) # 用透明色填充
 
        # 使用 QPainter 将场景渲染到新的 QPixmap 上
        pr = QPainter(res)
        scene.render(pr, res.rect(), src.rect())
        pr.end()
        
        return res
 


    def set_pixmap_from_data(self, image_data: QByteArray):
        """
        从二进制数据加载原始图片，并触发重绘。
        """
        if self.movie():
            self.movie().stop()
            self.setMovie(None)

        if not image_data or image_data.isEmpty():
            self.clear()
            return
        
        # 加载数据到 _original_pixmap
        success = self._original_pixmap.loadFromData(image_data)
        
        if not success:
            self.clear()
            return

        # 加载成功后，清除文字和 setPixmap，然后调用 update() 触发 paintEvent
        self.setText("")
        self.setPixmap(QPixmap()) # 清除旧的、由父类管理的pixmap
        self.update() # 告诉Qt这个控件需要重绘 -> 进而调用我们的 paintEvent

    def update_scaled_pixmap(self):
        """
        这个函数现在只在窗口大小改变时被调用，
        它的作用是触发一次重绘，让 paintEvent 用新的尺寸重新绘制。
        """
        if not self._original_pixmap.isNull():
            # 调用 update() 来触发 paintEvent
            self.update()

    def resizeEvent(self, event: QResizeEvent):
        """触发 paintEvent"""
        # 只有在有图的情况下，resize才有意义
        if not self._original_pixmap.isNull():
            self.update_scaled_pixmap()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        """发射点击信号"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def setMovie(self, movie: QMovie):
        """确保清理静态图并统一光标行为"""
        self._original_pixmap = QPixmap() # 播放动画时，清除静态图
        
        # 在设置动画时，也应用统一的圆角背景样式
        if movie and movie.isValid():
            self.setText("") # 清除文字
            self.setStyleSheet("""
                ImageLabel {
                    background-color: #2E3440;
                    border-radius: 8px;
                    margin-top: 10px;
                }
            """)
        
        super().setMovie(movie) # 调用父类方法来设置和显示动画
        
        if movie and movie.isValid():
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)


    def clear(self):
        """
        统一的清空方法，负责恢复到初始占位状态。
        """
        if self.movie():
            self.movie().stop()
            self.setMovie(None)
        
        # 清除我们自己管理的 pixmap
        self._original_pixmap = QPixmap()
        
        # 恢复占位文字和统一的圆角背景样式
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
        # 触发一次重绘，以确保旧的图像被清除
        self.update() 
