import base64
import copy
import os
import random
import secrets
import time
from datetime import datetime
from argon2 import PasswordHasher

from PySide6.QtWidgets import (
    QApplication, QDialog, QSizePolicy, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QDialogButtonBox, QLabel,
    QMessageBox, QCheckBox, QListWidget, QListWidgetItem,
    QWidget, QTreeWidget, QTreeWidgetItem, QComboBox, QProgressBar,
    QGraphicsDropShadowEffect, QScrollArea, QApplication, QMenu, QFileDialog
)
from PySide6.QtCore import QBuffer, QDir, QIODevice, QPoint, QSize, Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve, QByteArray
from PySide6.QtGui import QIcon, QPalette, QColor, QPixmap, QMovie, QGuiApplication, QImageReader, QKeySequence

from config import CUTE_COPY_ICON_BASE64, CUTE_SAVE_ICON_BASE64

class ProxySettingsDialog(QDialog):
    """
    一个用于配置代理服务器的对话框。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.setMinimumWidth(450)
 
        # --- 创建控件 ---
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setPlaceholderText("例如: http://user:pass@127.0.0.1:8888 或 socks5://...")
 
        self.proxy_mode_combo = QComboBox()
        # 使用 .addItem(文本, 数据) 的方式，方便我们获取内部值
        self.proxy_mode_combo.addItem("不使用代理 (推荐)", "none")
        self.proxy_mode_combo.addItem("自动检测系统代理", "system") # 新增选项
        self.proxy_mode_combo.addItem("使用自定义代理", "custom") # 重命名旧选项
 
        # --- 按钮 ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
 
        # --- 布局 ---
        form_layout = QFormLayout()
        form_layout.addRow("代理模式:", self.proxy_mode_combo) # 模式放前面更符合逻辑
        form_layout.addRow("代理服务器 URL:", self.proxy_url_input)
        
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        
        # 说明文字
        note_label = QLabel(
            "<i><b>- 不使用代理:</b> 所有网络请求将直连，忽略任何系统代理。<br>"
            "<b>- 系统代理:</b> 自动使用您操作系统设置的代理。<br>"
            "<b>- 自定义代理:</b> 仅使用您在上方填写的代理地址。<br><br>"
            "注: 此设置不影响核心的FRP隧道连接。</i>"
        )
        note_label.setTextFormat(Qt.RichText)
        main_layout.addWidget(note_label)
        main_layout.addWidget(button_box)
    def set_settings(self, settings: dict):
        """用当前的配置信息来填充对话框里的控件"""
        self.proxy_url_input.setText(settings.get("proxy_url", ""))
        
        mode_to_set = settings.get("proxy_mode", "none")
        index = self.proxy_mode_combo.findData(mode_to_set)
        if index != -1:
            self.proxy_mode_combo.setCurrentIndex(index)
 
    def get_settings(self) -> dict:
        """从对话框的控件中获取用户输入的配置信息"""
        return {
            "proxy_url": self.proxy_url_input.text().strip(),
            "proxy_mode": self.proxy_mode_combo.currentData()
        }

# --- 辅助函数：端口验证 ---
def is_valid_port(port_str):
    try:
        port = int(port_str)
        if 1024 <= port <= 65535: return True
        return False
    except (ValueError, TypeError): return False

# --- 后台工作线程 ---
class WorkerThread(QThread):
    finished = Signal()
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ph = PasswordHasher(
            time_cost=self.config['ARGON2_TIME_COST'],
            memory_cost=self.config['ARGON2_MEMORY_COST'],
            parallelism=self.config['ARGON2_PARALLELISM']
        )
    def run(self):
        try: self.ph.hash(secrets.token_hex(16))
        except Exception: pass
        finally: self.finished.emit()

# 创建密码重置对话框
class ResetPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("重置密码")
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QFormLayout(self)
        self.nickname_input = QLineEdit()
        self.token_input = QLineEdit()
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        
        layout.addRow("您的昵称:", self.nickname_input)
        layout.addRow("收到的重置令牌:", self.token_input)
        layout.addRow("您的新密码:", self.new_password_input)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_data(self):
        if self.exec() == QDialog.Accepted:
            nickname = self.nickname_input.text().strip()
            token = self.token_input.text().strip()
            new_password = self.new_password_input.text() # 不strip，允许密码包含空格
            
            if not (nickname and token and new_password):
                QMessageBox.warning(self, "提示", "所有字段都不能为空。")
                return None
            return {"nickname": nickname, "token": token, "new_password": new_password}
        return None
    
class ImageViewerDialog(QDialog):
    def __init__(self, image_data: QByteArray, parent=None):
        super().__init__(parent)
        
        # 创建数据的物理深拷贝，彻底隔离数据源。
        # bytes(image_data) -> 将Qt数据转为不可变的Python字节串 (创建副本)
        # QByteArray(...) -> 用Python字节串创建一个全新的、独立的Qt字节数组
        self.image_data = QByteArray(bytes(image_data))
 
        # 用这份独立的数据初始化所有需要的对象
        if self.image_data.isEmpty():
            QTimer.singleShot(0, self.reject) # 立即关闭无效对话框
            return
            
        # 为所有操作创建一个统一的、可重复使用的QBuffer
        self.buffer = QBuffer(self.image_data)
        self.buffer.open(QIODevice.ReadOnly)
 
        # 使用这个buffer进行格式检查
        reader = QImageReader(self.buffer)
        self.image_format = reader.format().toLower()
        original_size = reader.size()
 
        if original_size.isEmpty():
             self.setWindowTitle("无效图片")
             self.resize(300, 200)
             label = QLabel("无法读取图片内容。", self)
             label.setAlignment(Qt.AlignCenter)
             layout = QVBoxLayout(self)
             layout.addWidget(label)
             self.setLayout(layout)
             return # 提前返回
 
        # --- 窗口尺寸和布局计算 ---
        screen_size = QGuiApplication.primaryScreen().availableGeometry().size()
        scale_limit = 0.9
        target_image_size = original_size.scaled(screen_size * scale_limit, Qt.KeepAspectRatio)
        dialog_width = min(screen_size.width(), target_image_size.width() + 40)
        dialog_height = min(screen_size.height(), target_image_size.height() + 40)
        self.setWindowTitle("图片查看器")
        self.resize(dialog_width, dialog_height)
        self.setModal(True)
        
        # --- 成员变量初始化 ---
        self.panning = False
        self.last_mouse_pos = QPoint()
        self.original_pixmap = None
        self.movie = None
        
        if original_size.width() > 0:
            self.scale_factor = target_image_size.width() / original_size.width()
        else:
            self.scale_factor = 1.0
 
        # --- UI控件创建 ---
        self.image_label = QLabel()
        self.image_label.setBackgroundRole(QPalette.Window)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.scroll_area = QScrollArea()
        self.scroll_area.setBackgroundRole(QPalette.Window)
        self.scroll_area.setWidget(self.image_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)
 
        # --- 加载并显示图片 ---
        self._load_and_display_image(target_image_size)
        self._update_cursor()
 
    def _load_and_display_image(self, target_size):
        # 确保QMovie从头开始读取数据流
        if self.image_format == b'gif':
            # 因为QImageReader已经读过buffer，必须将指针拨回开头！
            self.buffer.seek(0)
            
            self.movie = QMovie(self) # 先创建QMovie实例
            self.movie.setDevice(self.buffer) # 然后设置它的设备
            self.movie.setCacheMode(QMovie.CacheAll)
 
            self.image_label.setMovie(self.movie)
            self.movie.start()
            self.image_label.resize(self.movie.currentPixmap().size())
        else:
            self.original_pixmap = QPixmap()
            # 从头加载数据，因为seek(0)已经完成 (虽然对pixmap影响不大，但逻辑统一)
            self.original_pixmap.loadFromData(self.image_data)
            
            scaled_pixmap = self.original_pixmap.scaled(
                target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.resize(scaled_pixmap.size())
 
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_pannable():
            self.panning = True
            self.last_mouse_pos = event.globalPosition().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
 
    def mouseMoveEvent(self, event):
        if self.panning:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.last_mouse_pos
            self.last_mouse_pos = current_pos
            h_bar = self.scroll_area.horizontalScrollBar()
            v_bar = self.scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)
 
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self._update_cursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
 
    def _is_pannable(self):
        h_bar = self.scroll_area.horizontalScrollBar()
        v_bar = self.scroll_area.verticalScrollBar()
        return h_bar.isVisible() or v_bar.isVisible()
        
    def _update_cursor(self):
        if self._is_pannable():
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()
 
    def keyPressEvent(self, event):
        """处理键盘按键事件，包括 Esc 关闭和 Ctrl+C 复制。"""
        
        # 使用 matches() 方法来检测标准的快捷键组合
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_image_to_clipboard() # 调用我们已经写好的复制方法
            event.accept() # 标记事件已处理
            return # 退出函数
            
        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return
 
        # 如果不是我们关心的按键，则交给父类处理
        super().keyPressEvent(event)
 
    def wheelEvent(self, event):
        ctrl_pressed = event.modifiers() & Qt.ControlModifier
        if self.original_pixmap and not self.original_pixmap.isNull() and ctrl_pressed:
            angle = event.angleDelta().y()
            if angle > 0: self.scale_factor *= 1.15
            else: self.scale_factor *= 0.85
            
            new_width = self.scale_factor * self.original_pixmap.width()
            new_height = self.scale_factor * self.original_pixmap.height()
            
            if new_width < 20 or new_height < 20:
                if angle < 0: self.scale_factor /= 0.85
                return
 
            new_size = QSize(int(new_width), int(new_height))
            scaled_pixmap = self.original_pixmap.scaled(
                new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.resize(scaled_pixmap.size())
            
            self._update_cursor()
            event.accept()
        else:
            super().wheelEvent(event)

    def contextMenuEvent(self, event):
        """
        为图片查看器添加右键菜单，包含“复制”和“保存”。
        """
        menu = QMenu(self)
 
        # --- 1. 创建“复制”动作 ---
        copy_action = menu.addAction("复制")
        copy_icon_pixmap = QPixmap()
        copy_icon_pixmap.loadFromData(base64.b64decode(CUTE_COPY_ICON_BASE64))
        copy_action.setIcon(QIcon(copy_icon_pixmap))
        
        # --- 2. 创建“保存”动作 ---
        save_action = menu.addAction("保存")
        save_icon_pixmap = QPixmap()
        save_icon_pixmap.loadFromData(base64.b64decode(CUTE_SAVE_ICON_BASE64))
        save_action.setIcon(QIcon(save_icon_pixmap))
        
        # --- 3. 执行菜单并根据选择的动作调用相应的方法 ---
        selected_action = menu.exec(event.globalPos())
        
        if selected_action == copy_action:
            self.copy_image_to_clipboard()
        elif selected_action == save_action:
            self.save_image()
 
    def copy_image_to_clipboard(self):
        """
        将当前显示的图片复制到系统剪贴板。
        """
        clipboard = QApplication.clipboard()
        pixmap_to_copy = None
 
        # 判断是GIF还是静态图
        if self.movie and self.movie.isValid():
            # 如果是GIF，获取当前帧的Pixmap
            pixmap_to_copy = self.movie.currentPixmap()
        elif self.original_pixmap and not self.original_pixmap.isNull():
            # 如果是静态图，直接使用原始的Pixmap
            # 注意：这里我们复制的是未缩放的原图，保证质量
            pixmap_to_copy = self.original_pixmap
        
        # 如果成功获取到了有效的Pixmap，就设置到剪贴板
        if pixmap_to_copy and not pixmap_to_copy.isNull():
            clipboard.setPixmap(pixmap_to_copy)
            # 【可选】给用户一个提示
            status_tip = "图片已复制到剪贴板！"
            if self.parent() and hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(status_tip, 2000)
            else:
                # 如果找不到statusBar，可以用QMessageBox，但可能会有点打扰
                QMessageBox.information(self, "成功", status_tip)
        else:
            QMessageBox.warning(self, "复制失败", "无法获取有效的图片数据进行复制。")
 
    def save_image(self):
        """
        处理图片保存的逻辑。
        """
        format_str = self.image_format.data().decode('ascii', 'ignore') 
        if not format_str: format_str = 'png'
        
        default_filter = f"{format_str.upper()} 文件 (*.{format_str})"
        filters = f"{default_filter};;所有文件 (*)"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"MoeFRP_{timestamp}.{format_str}"
        
        from PySide6.QtCore import QStandardPaths # 在函数内部导入，避免污染全局
    
        pictures_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        # 如果找不到“图片”文件夹，就退回到用户的主目录
        save_dir = pictures_dir or QDir.homePath()
 
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            os.path.join(save_dir, default_filename), # 使用我们找到的安全路径
            filters
        )
 
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(self.image_data)
                QMessageBox.information(self, "成功", f"图片已成功保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存文件时出错: {e}")
        
# --- 美化的延时对话框 ---
class HardenedDelayDialog(QDialog):
    _instance_active = False

    DEFAULT_CONFIG = {
        "MIN_DELAY_MS": 2300,
        "MAX_DELAY_MS": 4300,
        "ARGON2_TIME_COST": 3,
        "ARGON2_MEMORY_COST": 16384, # 16MB
        "ARGON2_PARALLELISM": 2,
    }

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        if HardenedDelayDialog._instance_active:
            self.is_valid_instance = False; return
        
        HardenedDelayDialog._instance_active = True
        self.is_valid_instance = True

        self.config = self.DEFAULT_CONFIG.copy()
        if config: self.config.update(config)

        # --- 调整执行顺序 ---

        # 1. 基础窗口设置
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 130)

        # 2. 创建背景和布局
        self.background_widget = QWidget(self)
        self.background_widget.setGeometry(0, 0, self.width(), self.height())
        layout = QVBoxLayout(self.background_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 3. 创建所有UI控件
        self.label = QLabel("安全验证中...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100); self.progress_bar.setValue(0); self.progress_bar.setTextVisible(False)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        # 4. 现在所有控件都已存在，可以安全地设置样式和位置
        self.setup_styles()
        self.randomize_position()

        # 5. 最后，设置动画和逻辑
        self.total_delay_time = random.randint(self.config['MIN_DELAY_MS'], self.config['MAX_DELAY_MS'])
        self.animation = QPropertyAnimation(self.progress_bar, b"value")
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        
        self.worker = WorkerThread(self.config)
        self.worker.finished.connect(self.on_worker_finished)
        self.is_worker_finished = False

    def setup_styles(self):
        self.background_widget.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2E3440, stop:1 #3B4252);
                border: 1px solid #4C566A;
                border-radius: 12px;
            }
        """)
        self.label.setStyleSheet("color: #E5E9F0; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #434C5E;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #88C0D0, stop:1 #5E81AC);
                border-radius: 5px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 100))
        # 应用阴影到背景QWidget上，而不是主对话框
        self.background_widget.setGraphicsEffect(shadow)

    def randomize_position(self):
        parent = self.parent()
        if parent:
            parent_geo = parent.geometry(); parent_center = parent_geo.center()
            x = parent_center.x() - self.width()//2 + random.randint(-20,20)
            y = parent_center.y() - self.height()//2 + random.randint(-20,20)
            self.move(x, y)

    def start_delay(self):
        if not self.is_valid_instance: return
        self.start_time = time.monotonic()
        self.timer.start(100)
        self.worker.start()
        self.exec()

    def update_progress(self):
        """由UI定时器主导视觉进度"""
        elapsed_ms = (time.monotonic() - self.start_time) * 1000
        progress_value = int((elapsed_ms / self.total_delay_time) * 100)
        
        # 使用动画平滑地更新到目标值
        current_target = min(progress_value, 99) # 最高到99%，等待worker
        if current_target > self.progress_bar.value():
            self.animation.stop() # 停止旧动画
            self.animation.setDuration(250) # 设置一个固定的平滑过渡时间
            self.animation.setEndValue(current_target)
            self.animation.start()

        # 检查关闭条件
        if elapsed_ms >= self.total_delay_time and self.is_worker_finished:
            self.finalize_and_close()

    def on_worker_finished(self):
        self.is_worker_finished = True
        # 不直接关闭，让 update_progress 来做决定

    def finalize_and_close(self):
        """执行最后的动画并关闭窗口"""
        if self.timer.isActive(): self.timer.stop()
        
        self.animation.stop()
        self.animation.setDuration(300)
        self.animation.setEndValue(100)
        self.animation.finished.connect(self.accept)
        self.animation.start()
    
    def done(self, result):
        HardenedDelayDialog._instance_active = False
        super().done(result)

# --- LoginDialog 和其他类 ---
class LoginDialog(QDialog):
    def __init__(self, title="登录", parent=None, remembered_nickname="", remembered_password=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        self.setModal(True)
        
        # 首先判断当前模式
        is_login_mode = "登录" in title

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.nickname_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        form_layout.addRow("昵称:", self.nickname_input)
        form_layout.addRow("密码:", self.password_input)

        # 只在注册模式下添加邀请码字段
        if not is_login_mode:
            self.invite_code_label = QLabel("邀请码:")
            self.invite_code_input = QLineEdit()
            form_layout.addRow(self.invite_code_label, self.invite_code_input)

        layout.addLayout(form_layout)
        
        # --- 创建并添加底部的控件 ---
        bottom_layout = QHBoxLayout()
        if is_login_mode:
            self.remember_me_checkbox = QCheckBox("记住密码")
            self.forgot_password_button = QPushButton("忘记密码?")
            self.forgot_password_button.setStyleSheet("background: transparent; border: none; color: #88C0D0; text-decoration: underline;")
            self.forgot_password_button.setCursor(Qt.PointingHandCursor)
            
            bottom_layout.addWidget(self.remember_me_checkbox)
            bottom_layout.addStretch()
            bottom_layout.addWidget(self.forgot_password_button)
        else:
            # 注册模式下，底部留空
            bottom_layout.addStretch()

        layout.addLayout(bottom_layout)
        
        # --- 只添加一次按钮 ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # --- 预填充数据，只在登录模式下 ---
        if is_login_mode:
            self.nickname_input.setText(remembered_nickname)
            self.password_input.setText(remembered_password)
            if remembered_nickname and remembered_password:
                self.remember_me_checkbox.setChecked(True)
    
    def get_credentials(self):
        if self.exec() == QDialog.Accepted:
            nickname = self.nickname_input.text().strip()
            password = self.password_input.text().strip()
            
            # 安全地获取控件状态，不存在的控件返回默认值
            remember_me = self.remember_me_checkbox.isChecked() if hasattr(self, 'remember_me_checkbox') else False
            invite_code = self.invite_code_input.text().strip().upper() if hasattr(self, 'invite_code_input') else ""

            if not (nickname and password):
                QMessageBox.warning(self, "提示", "昵称和密码均不能为空。")
                return None, None, False, None

            is_registering = "注册" in self.windowTitle()
            if is_registering and not invite_code:
                QMessageBox.warning(self, "提示", "注册需要有效的邀请码。")
                return None, None, False, None

            return nickname, password, remember_me, invite_code
        return None, None, False, None

class NodeEditDialog(QDialog):
    def __init__(self, parent=None, node_data=None):
        super().__init__(parent);self.setWindowTitle("编辑服务器节点");self.setMinimumWidth(400);layout=QFormLayout(self);self.remark_input=QLineEdit();self.addr_input=QLineEdit();self.port_input=QLineEdit();self.token_input=QLineEdit();layout.addRow("节点备注:",self.remark_input);layout.addRow("服务器地址:",self.addr_input);layout.addRow("服务端口:",self.port_input);layout.addRow("认证Token:",self.token_input);button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);layout.addWidget(button_box)
        if node_data:self.remark_input.setText(node_data.get('remark',''));self.addr_input.setText(node_data.get('server_addr',''));self.port_input.setText(str(node_data.get('server_port','')));self.token_input.setText(node_data.get('token',''))
    def get_data(self):
        remark=self.remark_input.text().strip();addr=self.addr_input.text().strip();port_str=self.port_input.text().strip()
        if not remark or not addr or not port_str:QMessageBox.warning(self,"错误","备注、地址和端口不能为空。");return None
        if not is_valid_port(port_str):QMessageBox.warning(self,"端口错误","服务器端口号必须是 1024 到 65535 之间的数字。");return None
        return{'remark':remark,'server_addr':addr,'server_port':int(port_str),'token':self.token_input.text().strip()}
class ManageSharesDialog(QDialog):
    def __init__(self,share_api_client,session_token,parent=None):
        super().__init__(parent);self.share_api_client = share_api_client;self.session_token=session_token;self.setWindowTitle("管理我的分享");self.setMinimumSize(500,300);layout=QVBoxLayout(self);self.list_widget=QListWidget();self.list_widget.setToolTip("双击可复制分享ID");layout.addWidget(QLabel("您创建的分享列表："));layout.addWidget(self.list_widget);button_layout=QHBoxLayout();self.refresh_button=QPushButton("刷新列表");self.close_button=QPushButton("关闭");button_layout.addWidget(self.refresh_button);button_layout.addStretch();button_layout.addWidget(self.close_button);layout.addLayout(button_layout);self.refresh_button.clicked.connect(self.refresh_list);self.close_button.clicked.connect(self.reject);self.list_widget.itemDoubleClicked.connect(self.copy_share_id);self.refresh_list()
    def refresh_list(self):
        self.list_widget.clear()
        success, data = self.share_api_client.list_my(self.session_token)
        if not success:
            QMessageBox.critical(self, "错误", f"获取分享列表失败: {data}")
            return
        if not data:
            self.list_widget.addItem("您还没有创建任何分享。")
            return

        for share in data:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)

            # --- 在这里根据类型设置不同的文本 ---
            if share['is_template']:
                share_type_text = "<font color='#3498DB'><b>[模板]</b></font>" # 蓝色文字
            else:
                share_type_text = "<font color='#F39C12'><b>[完整]</b></font>" # 橙色文字

            # 将类型文本和分享名称组合起来
            label = QLabel(f"{share_type_text} <b>{share['share_name']}</b> (ID: {share['share_id']})")
            # ---------------------------------------------------

            label.setTextFormat(Qt.RichText)
            revoke_button = QPushButton("撤销")
            revoke_button.setProperty("share_id", share['share_id'])
            revoke_button.setProperty("share_name", share['share_name'])
            revoke_button.clicked.connect(self.handle_revoke_share)

            item_layout.addWidget(label, 1)
            item_layout.addWidget(revoke_button)

            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
    def handle_revoke_share(self):
        share_id=self.sender().property("share_id");share_name=self.sender().property("share_name");reply=QMessageBox.question(self,"确认撤销",f"您确定要永久撤销分享 '{share_name}' 吗？\n\n所有订阅了此分享的用户将立即无法使用。",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 使用 share_api_client 进行调用。
            success, message = self.share_api_client.revoke(self.session_token, share_id)
            if success:
                QMessageBox.information(self, "成功", "分享已成功撤销。")
                self.refresh_list()
            else:
                QMessageBox.critical(self, "失败", f"撤销分享失败: {message}")
    def copy_share_id(self,item):
        widget=self.list_widget.itemWidget(item)
        if not widget:return
        label_text=widget.findChild(QLabel).text()
        try:share_id=label_text.split("ID: ")[1].split(")")[0];QApplication.clipboard().setText(share_id);QMessageBox.information(self,"已复制",f"分享ID '{share_id}' 已复制到剪贴板。")
        except IndexError:pass
class CreateShareDialog(QDialog):
    def __init__(self,current_config,parent=None):
        super().__init__(parent);self.setWindowTitle("创建分享");self.setMinimumWidth(400);self.current_config=current_config;self.layout=QVBoxLayout(self);form_layout=QFormLayout();self.share_name_input=QLineEdit();self.is_template_checkbox=QCheckBox("作为模板分享 (对方可自定义本地端口等)");self.nodes_tree=QTreeWidget();self.nodes_tree.setHeaderHidden(True);form_layout.addRow("分享名称:",self.share_name_input);form_layout.addRow(self.is_template_checkbox);form_layout.addRow("包含的节点(模板模式):",self.nodes_tree);self.is_template_checkbox.toggled.connect(self.nodes_tree.setVisible);self.populate_nodes();self.layout.addLayout(form_layout);button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);self.layout.addWidget(button_box)
    def populate_nodes(self):
        self.nodes_tree.clear()
        nodes = []
        
        # --- 增加对多种配置格式的兼容 ---
        
        # 优先级1：检查是否存在 'nodes' 列表 (多节点模式)
        if 'nodes' in self.current_config and isinstance(self.current_config.get('nodes'), list):
            nodes = self.current_config['nodes']
        
        # 优先级2：如果不是多节点，检查是否存在单节点信息（兼容驼峰和下划线）
        elif self.current_config.get('serverAddr') or self.current_config.get('server_addr'):
            node_data = {
                # 兼容驼峰和下划线，构造一个标准的节点字典
                'remark': self.current_config.get('remark', self.current_config.get('serverAddr', self.current_config.get('server_addr'))),
                'server_addr': self.current_config.get('serverAddr', self.current_config.get('server_addr')),
                'server_port': self.current_config.get('serverPort', self.current_config.get('server_port')),
                'token': self.current_config.get('auth', {}).get('token', self.current_config.get('token', ''))
            }
            # 将这个单节点字典放入列表中
            nodes.append(node_data)
        # --------------------------------------------

        if nodes:
            # 将解析出的所有节点填充到UI树中
            for node in nodes:
                # 确保有一个默认备注
                remark = node.get('remark') or node.get('server_addr') or "未命名节点"
                item = QTreeWidgetItem(self.nodes_tree)
                item.setText(0, remark)
                item.setFlags(item.flags()|Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)
                item.setCheckState(0, Qt.Checked)
            self.is_template_checkbox.setEnabled(True)
        else:
            self.is_template_checkbox.setChecked(False)
            self.is_template_checkbox.setEnabled(False)
        
        # 根据复选框状态决定是否显示节点树
        self.nodes_tree.setVisible(self.is_template_checkbox.isChecked())
    def get_data(self):
        if not self.share_name_input.text().strip():QMessageBox.warning(self,"提示","分享名称不能为空。");return None
        share_name=self.share_name_input.text().strip();is_template=self.is_template_checkbox.isChecked()
        final_config_data = {}
        if is_template:
            nodes=[]
            if'nodes'in self.current_config and isinstance(self.current_config['nodes'],list):nodes=self.current_config['nodes']
            elif'serverAddr'in self.current_config:nodes=[{"remark":self.current_config.get('serverAddr'),"server_addr":self.current_config.get('serverAddr'),"server_port":self.current_config.get('serverPort'),"token":self.current_config.get('auth',{}).get('token')}]
            selected_nodes=[]
            for i in range(self.nodes_tree.topLevelItemCount()):
                item=self.nodes_tree.topLevelItem(i)
                if item.checkState(0)==Qt.Checked:selected_nodes.append(nodes[i])
            if not selected_nodes:QMessageBox.warning(self,"提示","模板分享至少需要选择一个节点。");return None
            final_config_data['nodes']=selected_nodes
        else:
            # --- 处理“完整分享”的创建 ---
            
            # 1. 拷贝一份原始配置，防止修改原对象
            original_config = copy.deepcopy(self.current_config)

            # 2. 构造服务器部分，强制使用驼峰式
            final_config_data['serverAddr'] = original_config.get('serverAddr', original_config.get('server_addr', ''))
            final_config_data['serverPort'] = int(original_config.get('serverPort', original_config.get('server_port', 0)))
            auth_info = original_config.get('auth', {})
            final_config_data['auth'] = {'token': str(auth_info.get('token', ''))}

            # 3. 清洗和转换代理列表
            clean_proxies = []
            for p_in in original_config.get('proxies', []):
                if not isinstance(p_in, dict): continue
                # 直接在这里就完成格式转换
                p_out = {}
                p_out['name'] = p_in.get('name')
                p_out['type'] = p_in.get('type')
                # 兼容从UI获取的下划线式键名
                p_out['localIP'] = p_in.get('local_ip', '127.0.0.1')
                p_out['localPort'] = int(p_in.get('local_port', 0))
                if p_out['type'] in ['http', 'https']:
                    if p_in.get('custom_domains'):
                        p_out['custom_domains'] = [d.strip() for d in str(p_in.get('custom_domains')).split(',') if d.strip()]
                else:
                    p_out['remotePort'] = int(p_in.get('remote_port', 0))
                clean_proxies.append(p_out)
            
            if clean_proxies:
                final_config_data['proxies'] = clean_proxies
        
        # 返回最终封装好的、格式完全正确的数据
        return {
            "share_name": share_name,
            "is_template": is_template,
            "config_data": final_config_data # 使用净化过的数据
        }
        
class ProxyEditDialog(QDialog):
    def __init__(self,parent=None,data=None):
        super().__init__(parent);self.setWindowTitle("编辑代理规则");self.setMinimumWidth(400);self.layout=QVBoxLayout(self);self.form_layout=QFormLayout();self.name_input=QLineEdit();self.type_input=QComboBox();self.type_input.addItems(['tcp','udp','stcp','xtcp','http','https']);self.local_ip_input=QLineEdit("127.0.0.1");self.local_port_input=QLineEdit();self.remote_port_input=QLineEdit();self.custom_domains_input=QLineEdit();self.type_input.currentTextChanged.connect(self.update_fields_visibility);self.form_layout.addRow("规则名称:",self.name_input);self.form_layout.addRow("代理类型:",self.type_input);self.form_layout.addRow("本地 IP:",self.local_ip_input);self.form_layout.addRow("本地端口:",self.local_port_input);self.form_layout.addRow("远程端口:",self.remote_port_input);self.custom_domains_label=QLabel("自定义域名:");self.form_layout.addRow(self.custom_domains_label,self.custom_domains_input);self.layout.addLayout(self.form_layout);self.button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);self.button_box.accepted.connect(self.accept);self.button_box.rejected.connect(self.reject);self.layout.addWidget(self.button_box)
        if data:self.name_input.setText(data.get('name',''));self.type_input.setCurrentText(data.get('type','tcp'));self.local_ip_input.setText(data.get('local_ip','127.0.0.1'));self.local_port_input.setText(str(data.get('local_port','')));self.remote_port_input.setText(str(data.get('remote_port','')));self.custom_domains_input.setText(data.get('custom_domains',''))
        self.update_fields_visibility()
    def update_fields_visibility(self):
        is_http=self.type_input.currentText()in['http','https']
        self.form_layout.labelForField(self.remote_port_input).setVisible(not is_http);self.remote_port_input.setVisible(not is_http);self.custom_domains_label.setVisible(is_http);self.custom_domains_input.setVisible(is_http)
    def get_data(self):
        local_port_str=self.local_port_input.text().strip();remote_port_str=self.remote_port_input.text().strip()
        if local_port_str and not is_valid_port(local_port_str):QMessageBox.warning(self,"端口错误","本地端口号必须是 1024 到 65535 之间的数字。");return None
        if self.remote_port_input.isVisible()and remote_port_str and not is_valid_port(remote_port_str):QMessageBox.warning(self,"端口错误","远程端口号必须是 1024 到 65535 之间的数字。");return None
        return{'name':self.name_input.text().strip(),'type':self.type_input.currentText(),'local_ip':self.local_ip_input.text().strip(),'local_port':local_port_str,'remote_port':remote_port_str,'custom_domains':self.custom_domains_input.text().strip()}
