# utils.py

import hashlib
import os
import sys

from PySide6.QtCore import QObject, QEvent, QSize
from PySide6.QtGui import QCursor, QKeySequence, QPixmap, QIcon, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication

class GlobalCopyInterceptor(QObject):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
 
    def eventFilter(self, watched, event):
        # 只关心键盘按下事件
        if event.type() == QEvent.Type.KeyPress:
            # 检查是否是标准的“复制”快捷键
            if event.matches(QKeySequence.StandardKey.Copy):
                
                # 获取主窗口的图片标签控件
                image_label = self.main_window.placeholder_image_label
                if not image_label:
                    return super().eventFilter(watched, event)
 
                # 检查鼠标是否在图片标签上
                widget_under_cursor = QApplication.widgetAt(QCursor.pos())
                is_on_image_label = False
                temp_widget = widget_under_cursor
                while temp_widget is not None:
                    if temp_widget == image_label:
                        is_on_image_label = True
                        break
                    temp_widget = temp_widget.parent()
                
                # 如果在图片上，则执行复制并拦截事件
                if is_on_image_label:
                    self.main_window.copy_current_image_to_clipboard()
                    return True # 核心：拦截事件，不再传递
 
        # 对于所有其他事件，正常传递
        return super().eventFilter(watched, event)

def resource_path(relative_path):
    """ 获取资源的绝对路径, 兼容开发模式和PyInstaller打包后的单文件模式 """
    try:
        # PyInstaller 会创建一个临时文件夹 _MEIPASS，并将所有数据文件放在那里
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是在打包模式下运行，就使用当前文件的路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# SHA-256哈希计算函数
def get_file_sha256(filepath):
    """计算文件的SHA-256哈希值"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # 逐块读取，防止大文件撑爆内存
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# def create_emoji_icon(emoji: str, size: int = 16) -> QIcon:
#     """
#     将一个Emoji字符转换为QIcon对象。
#  
#     :param emoji: 要转换的Emoji字符，例如 "🔄"。
#     :param size: 图标的尺寸（宽度和高度）。
#     :return: 包含该Emoji的QIcon对象。
#     """
#     # 1. 创建一个指定大小的、透明的QPixmap作为画布
#     pixmap = QPixmap(QSize(size, size))
#     pixmap.fill(QColor("transparent"))  # 填充透明背景
#  
#     # 2. 创建一个QPainter在Pixmap上绘制
#     painter = QPainter(pixmap)
    
#     # 3. 设置字体
#     font = QFont()
#     font.setFamily("Segoe UI Emoji")
#     font.setPixelSize(int(size * 0.8)) # Emoji的大小通常比画布小一点，留出边距
#     painter.setFont(font)
#  
#     # 4. 在画布中央绘制Emoji
#     #    Qt的drawText会自动处理字符的居中
#     painter.drawText(pixmap.rect(), 0, emoji) # 0表示水平和垂直都居中
#  
#     # 5. 结束绘制
#     painter.end()
#  
#     return QIcon(pixmap)

def _get_value_from_path(data, path):
    """
    根据点(.)分隔的路径字符串，从嵌套的字典或列表中提取值。
    例如: get_value_from_path(data, "data.0.urls.regular")
    """
    try:
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, list):
                # 如果是列表，将键转换为整数索引
                current = current[int(key)]
            elif isinstance(current, dict):
                # 如果是字典，直接用键获取
                current = current[key]
            else:
                # 如果路径中间遇到非字典/列表类型，则无法继续
                return None
        return current
    except (KeyError, IndexError, ValueError, TypeError):
        # 任何路径错误（键不存在、索引越界等）都安全返回None
        return None