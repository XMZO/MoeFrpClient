import ctypes
from datetime import datetime
import hashlib
import sys, os, json, subprocess, toml, uuid, copy
import tempfile
from ImageLabel import ImageLabel
import copy
import re
import random
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFormLayout, QGroupBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QLabel, QStyle, QInputDialog, QListWidget, QListWidgetItem,
    QSplitter, QStackedWidget, QAbstractItemView, QMenu
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QSettings, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QIcon, QColor, QPixmap, QMovie, QImageReader
# 【新增】导入Qt网络模块

from api import ApiClient
from Dialogs import (LoginDialog, ManageSharesDialog, CreateShareDialog, 
                     ProxyEditDialog, NodeEditDialog, HardenedDelayDialog,
                     ImageViewerDialog, QFileDialog)
# --- 自定义模块导入 ---
from config import (
    CLOUD_SERVER_URL, CLIENT_VERSION, CLIENT_VERSION_STR, VERSION_SECRET,
    IMAGE_SOURCES, IMAGE_REFRESH_INTERVAL_MS, IMAGE_FETCH_GLOBAL_TIMEOUT_MS
)
from utils import resource_path, get_file_sha256
from security import EncryptionManager
from frpc_runner import run_frpc_service
from threads import PingThread, RefreshThread, LogReaderThread, ImageFetcherThread

# --- 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_fetch_thread = None      # 用来持有当前正在运行的图片获取线程
        self.is_fetching_image = False      # 一个标志位，防止重复获取
        self.current_source_index = 0
        self.image_sources = IMAGE_SOURCES
        self.current_fetch_list = []
        self.image_refresh_timer = QTimer(self) # 定时器
        self.image_refresh_timer.timeout.connect(self.refresh_image)
        # 创建一个一次性定时器，用于监控整个图片获取流程的超时
        self.global_fetch_timeout_timer = QTimer(self)
        self.global_fetch_timeout_timer.setSingleShot(True) # 设置为只触发一次
        self.global_fetch_timeout_timer.timeout.connect(self.on_global_fetch_timeout)
        self.movie = None # 添加一个成员变量来持有QMovie对象
        self.movie_buffer = None
        self.buffer = None
        self.pixmap = None # <--- 在这里添加
        self.current_image_data = None
        self.current_image_data = QByteArray() # 添加成员变量保存原始图片数据
        self.is_running = False
        self.frp_process = None # 【新增】用于持有frp子进程的句柄
        self.running_config = {} # 【新增】用于存储当前运行的frp配置
        self.guest_config_path = None # 【新增】用于记录游客模式的临时配置文件路径
        self.setWindowTitle("萌！FRP 高级客户端")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowIcon(QIcon(resource_path("windows.ico")))
         # 【新】初始化 QSettings
        # 第一个参数是组织/公司名，第二个是应用名
        # 这决定了在注册表中的路径
        self.settings = QSettings("MoeFrpTool", "FRPClient")

        # 【全新】初始化加密管理器
        try:
            self.encryption_manager = EncryptionManager()
        except Exception as e:
            QMessageBox.critical(self, "加密初始化失败", f"无法创建安全环境: {e}\n程序将退出。")
            sys.exit(1)
        
        self.is_running = False; self.frp_thread = None; self.session_token = None; self.logged_in_nickname = None
        self.is_forced_exit = False
        # 【新】增加一个标志位，防止重复显示错误信息
        self.has_shown_connection_error = False
        self.api_client = ApiClient(CLOUD_SERVER_URL)
        self.session_timer = QTimer(self); self.session_timer.timeout.connect(self.check_session_status)
        self.refresh_timer = QTimer(self); self.refresh_timer.setInterval(30000); self.refresh_timer.timeout.connect(self.handle_silent_refresh)
        self.profiles = {'guest': {'type': 'guest', 'data': {}}}; self.current_profile_id = 'guest'
        
        self.init_ui()
        self.update_ui_for_login_status(False)
        self.version_label = QLabel(f"版本: {CLIENT_VERSION_STR}")
        # statusBar() 会在需要时自动创建状态栏
        self.statusBar().addPermanentWidget(self.version_label, 1)
        self.refresh_image()

    def refresh_image(self):
        """
        【最终修正】根据权重随机选择一个源优先尝试，其他源作为备用。
        """
        if self.is_fetching_image:
            print("[Image Fetch] 正在获取图片，请勿重复操作。")
            return
    
        self.image_refresh_timer.stop()
        self.is_fetching_image = True
        self.global_fetch_timeout_timer.start(IMAGE_FETCH_GLOBAL_TIMEOUT_MS)
        print("[Image Fetch] 开始获取新图片...")
    
        # --- 【核心改动：基于权重创建本次尝试的有序列表】 ---
        if IMAGE_SOURCES:
            sources_population = list(IMAGE_SOURCES)
            weights = [source.get('weight', 1) for source in sources_population]
    
            try:
                # 1. 根据权重随机选择一个源，作为本次的首选
                primary_source = random.choices(sources_population, weights=weights, k=1)[0]
                
                # 2. 创建本次的尝试列表：首选源在最前，其他源打乱顺序作为备用
                self.current_fetch_list = [primary_source]
                fallbacks = [s for s in sources_population if s != primary_source]
                random.shuffle(fallbacks) # 打乱备用源的顺序
                self.current_fetch_list.extend(fallbacks)
    
            except (IndexError, ValueError):
                # 如果配置错误（例如权重列表为空），则退回普通顺序
                self.current_fetch_list = list(IMAGE_SOURCES)
        else:
            self.current_fetch_list = []
        # --- 核心改动结束 ---
    
        self.current_source_index = 0  # 每次都从新列表的第一个开始尝试
    
        if self.current_image_data.isEmpty():
            self.placeholder_image_label.setText("正在加载色图...")
            self.placeholder_image_label.setEnabled(False)
    
        self._try_fetch_from_source()

    def on_global_fetch_timeout(self):
        """
        【全新】当整个图片获取流程超过预设时间后，此方法被调用。
        """
        # 如果此时已经不处于“获取中”状态，说明是正常完成的，直接返回
        if not self.is_fetching_image:
            return
    
        print(f"[Timeout] 全局图片获取超时（超过 {IMAGE_FETCH_GLOBAL_TIMEOUT_MS / 1000} 秒）。正在强制刷新...")
    
        # 粗暴但有效地终止当前正在下载的线程
        if self.image_fetch_thread and self.image_fetch_thread.isRunning():
            self.image_fetch_thread.terminate() # 强制终止
            self.image_fetch_thread.wait()      # 等待线程完全停止
    
        # 重置状态，以便下一次刷新可以正常启动
        self.is_fetching_image = False
        
        # 立即调用 refresh_image() 来重新开始新一轮的获取
        self.refresh_image()
    
    def _try_fetch_from_source(self):
        """
        【微调】使用 self.current_fetch_list 来获取源。
        """
        # 【改动】检查 current_fetch_list 而不是 image_sources
        if not self.current_fetch_list:
            print("[Image Fetch] 没有任何可用的图片源。")
            self.is_fetching_image = False
            return
    
        if self.current_source_index >= len(self.current_fetch_list):
            print("[Image Fetch] 已尝试所有图片源，均失败。")
            self.global_fetch_timeout_timer.stop()
            self.is_fetching_image = False
            if self.current_image_data.isEmpty():
                self.placeholder_image_label.clear()
                self.placeholder_image_label.setText("图片加载失败")
                self.placeholder_image_label.setStyleSheet("background-color: transparent; border: none; margin-top: 10px;")
                self.placeholder_image_label.setEnabled(False)
            self.image_refresh_timer.start(IMAGE_REFRESH_INTERVAL_MS)
            return
    
        # 【改动】从 self.current_fetch_list 获取源对象，并提取 'url'
        source_object = self.current_fetch_list[self.current_source_index]
        final_url = source_object.get("url")
    
        # 健壮性检查，如果url不存在则直接尝试下一个
        if not final_url:
            print(f"[Image Fetch Error] 源 {self.current_source_index} 配置错误，缺少'url'键。")
            self.on_image_fetch_error("Source config error")
            return
    
        print(f"[Image Fetch] 正在尝试源 {self.current_source_index}: {source_object.get('url')}")
    
        # 【注意】我注意到您之前代码这里有个小笔误，我帮您修正了：
        # 之前是 self.fetch_thread，但定义在__init__里的是 self.image_fetch_thread
        self.image_fetch_thread = ImageFetcherThread(source_object) 
        self.image_fetch_thread.image_ready.connect(self.on_image_loaded)
        self.image_fetch_thread.error_occurred.connect(self.on_image_fetch_error)
        self.image_fetch_thread.start()
        
    def _handle_single_source_failure(self, error_message, next_source_index):
        """ 当单个源失败时被调用，准备尝试下一个源 """
        print(f"[Image Fetch] 源 {next_source_index - 1} 失败: {error_message}")
        # 立即尝试下一个源
        self._try_fetch_from_source(next_source_index)

    def on_image_loaded(self, image_data: QByteArray):
        """
        【最终优化版】图片数据下载成功后的处理。
        结合了QImageReader验证和显式格式判断，修复了重定向GIF的加载问题。
        """
        self.global_fetch_timeout_timer.stop()
        self.current_image_data = image_data
    
        # --- 步骤 1: 使用 QImageReader 验证数据流是否可读 ---
        reader = QImageReader()
        # 为reader创建一个临时的buffer，不影响原始的image_data
        validation_buffer = QBuffer(self.current_image_data)
        validation_buffer.open(QIODevice.ReadOnly)
        reader.setDevice(validation_buffer)
    
        if not reader.canRead():
            error_msg = f"源返回了无法识别的图片数据 (来自源索引: {self.current_source_index})"
            print(f"[Image Validate] {error_msg}")
            self.on_image_fetch_error(error_msg)
            return
    
        # --- 步骤 2: 获取准确的图片格式，并据此决定处理路径 ---
        image_format = reader.format() # 返回 QByteArray，例如 b'gif', b'png'
        print(f"[Image Validate] 验证通过，图片格式为: {image_format.data().decode()}")
    
        # 清理可能正在播放的旧动画
        if self.movie and self.movie.state() != QMovie.NotRunning:
            self.movie.stop()
            self.placeholder_image_label.setMovie(None)
    
        success = False
        if image_format == b'gif':
            # --- GIF 处理路径 ---
            print("[Image Loader] 检测到GIF格式，使用QMovie加载。")
            # 为QMovie创建一个新的、独立的QBuffer
            self.movie_buffer = QBuffer(self.current_image_data) # <--- 【修改】使用 self.movie_buffer
            self.movie_buffer.open(QBuffer.ReadOnly)
            self.movie_buffer.setParent(self) # 保持 setParent 是个好习惯
        
            self.movie = QMovie(self)
            self.movie.setDevice(self.movie_buffer) # <--- 【修改】使用 self.movie_buffer
            self.movie.setCacheMode(QMovie.CacheAll)
    
            if self.movie.isValid():
                self.placeholder_image_label.setMovie(self.movie)
                self.movie.start()
                success = True
                print("[Image Loader] GIF加载成功并开始播放。")
            else:
                print("[Image Loader] 错误：格式为GIF但数据无效或损坏。")
                # 此处不进行后续处理，将会在函数末尾触发错误流程
        else:
            # --- 静态图片 (PNG, JPG, etc.) 处理路径 ---
            print(f"[Image Loader] 检测到静态图片格式 ({image_format.data().decode()})。")
            # 清除可能残留的Movie对象
            self.placeholder_image_label.setMovie(None)
            
            # 直接使用您原有的 set_pixmap_from_data 方法，如果它存在的话。
            # 如果没有，则使用标准方法。为确保代码能运行，这里使用标准方法。
            pixmap = QPixmap()
            if pixmap.loadFromData(self.current_image_data):
                self.placeholder_image_label.set_pixmap_from_data(self.current_image_data)
                success = True
                print("[Image Loader] 静态图片加载成功。")
            else:
                print("[Image Loader] 错误：加载静态图片失败。")
    
        # --- 步骤 3: 统一的收尾工作 ---
        if success:
            # placeholder_image_label 是您的显示控件，这里确保它可见
            self.placeholder_image_label.show()    
            self.placeholder_image_label.setStyleSheet("border-radius: 8px; margin-top: 10px;")
            self.placeholder_image_label.setEnabled(True)
    
            # 真正成功后，重置状态并启动下一次刷新的定时器
            self.is_fetching_image = False
            self.image_refresh_timer.start(IMAGE_REFRESH_INTERVAL_MS)
        else:
            # 如果GIF无效或静态图加载失败，都统一进入错误处理
            self.on_image_fetch_error(f"Failed to load verified image (format: {image_format.data().decode()})")
            
    def on_image_fetch_error(self, error_message: str):
        """
        【修正】当单个源获取失败时调用。职责是递增索引并触发下一次尝试。
        """
        print(f"[Image Fetch Error] 源 {self.current_source_index} 失败: {error_message}")
        
        # 递增索引，准备尝试下一个源
        self.current_source_index += 1
        
        # 【核心修正】再次调用 _try_fetch_from_source，它会自己判断该怎么做
        self._try_fetch_from_source()

    def show_original_image(self):
        """
        当左下角图片被点击时，此槽函数被调用。
        【核心修正】: 使用更严格的检查，确保数据非空才打开查看器。
        """
        # 使用 QByteArray.isEmpty() 进行准确判断
        if self.current_image_data and not self.current_image_data.isEmpty():
            viewer = ImageViewerDialog(self.current_image_data, self)
            viewer.exec()
        else:
            # 如果数据为空，就在控制台打印信息，但什么也不做
            print("[Viewer] No image data to show. Viewer will not open.")

    def init_ui(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget); main_h_layout = QHBoxLayout(main_widget); #self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        splitter = QSplitter(Qt.Horizontal); left_panel = QWidget(); right_panel = QWidget()
        splitter.addWidget(left_panel); splitter.addWidget(right_panel); splitter.setSizes([280, 720]); main_h_layout.addWidget(splitter)
        left_layout = QVBoxLayout(left_panel)
        self.account_group = QGroupBox("账户"); account_layout = QVBoxLayout(self.account_group)
        self.logged_out_widget = QWidget(); logged_out_layout = QHBoxLayout(self.logged_out_widget); logged_out_layout.setContentsMargins(0,0,0,0)
        self.register_button = QPushButton("注册"); self.login_button = QPushButton("登录"); logged_out_layout.addWidget(self.register_button); logged_out_layout.addWidget(self.login_button)
        self.logged_in_widget = QWidget(); logged_in_layout = QVBoxLayout(self.logged_in_widget); logged_in_layout.setContentsMargins(0,0,0,0)
        self.welcome_label = QLabel("欢迎, "); self.manage_shares_button = QPushButton("管理我的分享")

        # 【新增】创建一个水平布局用于放置两个退出按钮
        logout_actions_layout = QHBoxLayout()
        self.logout_button = QPushButton("退出登录")
        self.switch_account_button = QPushButton("切换账户")
        self.logout_button.setToolTip("临时退出当前会话，但保留“记住密码”信息。")
        self.switch_account_button.setToolTip("彻底退出并清除本地记住的密码，用于更换账号或在公共设备上使用。")
        logout_actions_layout.addWidget(self.logout_button)
        logout_actions_layout.addWidget(self.switch_account_button)    

        logged_in_layout.addWidget(self.welcome_label); logged_in_layout.addWidget(self.manage_shares_button)
        logged_in_layout.addLayout(logout_actions_layout)
        account_layout.addWidget(self.logged_out_widget); account_layout.addWidget(self.logged_in_widget); left_layout.addWidget(self.account_group)
        self.profile_list_group = QGroupBox("配置列表"); profile_list_layout = QVBoxLayout(self.profile_list_group)
        self.profile_list_widget = QListWidget(); self.profile_list_widget.currentItemChanged.connect(self.on_profile_changed)
        profile_list_layout.addWidget(self.profile_list_widget)
        profile_actions_layout = QHBoxLayout(); self.new_profile_button = QPushButton("新建配置"); self.add_share_button = QPushButton("添加订阅"); self.delete_profile_button = QPushButton("删除选中")
        profile_actions_layout.addWidget(self.new_profile_button); profile_actions_layout.addWidget(self.add_share_button); profile_actions_layout.addWidget(self.delete_profile_button)
        profile_list_layout.addLayout(profile_actions_layout)

        # 3. 伸缩弹簧 (Spacer)
        #    这个很重要，它会把下一个组件推到底部
        left_layout.addWidget(self.profile_list_group)
        
        # 4. 【核心修正】最后添加图片占位符
        self.placeholder_image_label = ImageLabel() # 不再是 QLabel(...) 了
        # [核心] 连接 ImageLabel 的点击信号到我们的新方法
        self.placeholder_image_label.clicked.connect(self.show_original_image)
        # 【可选】因为 ImageLabel 内部已经设置好了样式，这里的很多设置可以简化或删除
        # self.placeholder_image_label.setSizePolicy(...) # 可以删除，ImageLabel内部已设置
        # self.placeholder_image_label.setMinimumSize(250, 150) # 保留这个，防止窗口过小时图片被压得太小
        # self.placeholder_image_label.setAlignment(...) # 可以删除，ImageLabel内部已设置
        self.placeholder_image_label.setMinimumSize(250, 150) 

        self.placeholder_image_label.setEnabled(False)
        left_layout.addWidget(self.placeholder_image_label)

        right_layout = QVBoxLayout(right_panel)
        self.stacked_widget = QStackedWidget()
        self.control_group = QGroupBox("控制与日志"); control_layout = QVBoxLayout(self.control_group)
        control_top_layout = QHBoxLayout()
        self.active_node_label = QLabel("运行节点:")
        self.active_node_selector = QComboBox()
        self.connect_button = QPushButton("启动连接")
        self.connect_button.setStyleSheet("background-color: #4CAF50; color: white; height: 40px; font-size: 16px;")
        control_top_layout.addWidget(self.active_node_label); control_top_layout.addWidget(self.active_node_selector, 1); control_top_layout.addWidget(self.connect_button, 1)
        self.log_output = QTextEdit(); self.log_output.setReadOnly(True)
        control_layout.addLayout(control_top_layout); control_layout.addWidget(self.log_output, 1)
        right_layout.addWidget(self.stacked_widget, 1); right_layout.addWidget(self.control_group)
        self.editable_page = QWidget(); self.build_editable_ui(QVBoxLayout(self.editable_page))
        self.shared_page = QWidget(); self.build_shared_ui(QVBoxLayout(self.shared_page))
        self.stacked_widget.addWidget(self.editable_page); self.stacked_widget.addWidget(self.shared_page)
        self.refresh_profile_list(); self.connect_signals()
    
    def build_editable_ui(self, layout):
        self.editable_frp_server_group = QGroupBox("FRP 服务器节点列表"); server_layout = QVBoxLayout(self.editable_frp_server_group)
        self.nodes_table = QTableWidget(); self.nodes_table.setColumnCount(4); self.nodes_table.setHorizontalHeaderLabels(["备注", "服务器地址", "端口", "Token(部分隐藏)"]); self.nodes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.nodes_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.nodes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        server_layout.addWidget(self.nodes_table)
        node_button_layout = QHBoxLayout(); self.add_node_button = QPushButton("添加节点"); self.edit_node_button = QPushButton("编辑节点"); self.del_node_button = QPushButton("删除节点")
        node_button_layout.addWidget(self.add_node_button); node_button_layout.addWidget(self.edit_node_button); node_button_layout.addWidget(self.del_node_button); node_button_layout.addStretch()
        server_layout.addLayout(node_button_layout); layout.addWidget(self.editable_frp_server_group)
        self.editable_proxy_group = QGroupBox("代理规则"); proxy_layout = QVBoxLayout(self.editable_proxy_group); self.editable_proxy_table = QTableWidget(); self.editable_proxy_table.setColumnCount(6)
        self.editable_proxy_table.setHorizontalHeaderLabels(["名称", "类型", "本地IP", "本地端口", "远程端口", "自定义域名"]); self.editable_proxy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        proxy_layout.addWidget(self.editable_proxy_table); proxy_button_layout = QHBoxLayout(); self.add_proxy_button = QPushButton("添加"); self.edit_proxy_button = QPushButton("编辑"); self.del_proxy_button = QPushButton("删除")
        proxy_button_layout.addWidget(self.add_proxy_button); proxy_button_layout.addWidget(self.edit_proxy_button); proxy_button_layout.addWidget(self.del_proxy_button); proxy_button_layout.addStretch()
        proxy_layout.addLayout(proxy_button_layout); layout.addWidget(self.editable_proxy_group, 1)
        action_layout = QHBoxLayout(); self.save_cloud_button = QPushButton("保存到云端"); self.share_button = QPushButton("分享此配置..."); action_layout.addStretch(); action_layout.addWidget(self.save_cloud_button); action_layout.addWidget(self.share_button)
        layout.addLayout(action_layout); layout.addStretch()
        self.add_proxy_button.clicked.connect(self.add_proxy); self.edit_proxy_button.clicked.connect(self.edit_proxy); self.del_proxy_button.clicked.connect(self.delete_proxy)
        self.save_cloud_button.clicked.connect(self.handle_cloud_save); self.share_button.clicked.connect(self.handle_create_share)
        self.add_node_button.clicked.connect(self.add_node); self.edit_node_button.clicked.connect(self.edit_node); self.del_node_button.clicked.connect(self.delete_node)

    def build_shared_ui(self, layout):
        self.shared_frp_server_group = QGroupBox("服务器配置"); server_layout = QFormLayout(self.shared_frp_server_group)
        self.node_selector = QComboBox(); self.ping_button = QPushButton("一键测速"); node_layout = QHBoxLayout(); node_layout.addWidget(self.node_selector, 1); node_layout.addWidget(self.ping_button);
        self.node_label = QLabel("服务器: ******** (完整模式)")
        server_layout.addRow("选择节点:", node_layout); server_layout.addRow(self.node_label); layout.addWidget(self.shared_frp_server_group)
        self.shared_proxy_group = QGroupBox("代理规则"); proxy_layout = QVBoxLayout(self.shared_proxy_group); self.shared_proxy_table = QTableWidget(); self.shared_proxy_table.setColumnCount(6)
        self.shared_proxy_table.setHorizontalHeaderLabels(["名称", "类型", "本地IP", "本地端口", "远程端口", "自定义域名"]); self.shared_proxy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        proxy_layout.addWidget(self.shared_proxy_table); proxy_button_layout = QHBoxLayout(); self.shared_add_proxy_button = QPushButton("添加"); self.shared_edit_proxy_button = QPushButton("编辑"); self.shared_del_proxy_button = QPushButton("删除")
        proxy_button_layout.addWidget(self.shared_add_proxy_button); proxy_button_layout.addWidget(self.shared_edit_proxy_button); proxy_button_layout.addWidget(self.shared_del_proxy_button); proxy_button_layout.addStretch()
        proxy_layout.addLayout(proxy_button_layout); layout.addWidget(self.shared_proxy_group, 1); layout.addStretch()
        self.ping_button.clicked.connect(self.handle_ping_nodes)
        self.shared_add_proxy_button.clicked.connect(self.add_proxy); self.shared_edit_proxy_button.clicked.connect(self.edit_proxy); self.shared_del_proxy_button.clicked.connect(self.delete_proxy)

    def connect_signals(self):
        self.register_button.clicked.connect(self.handle_register); self.login_button.clicked.connect(self.handle_login)
        self.manage_shares_button.clicked.connect(self.handle_manage_shares)
         # 【新】为两个退出按钮连接信号
        self.logout_button.clicked.connect(self.handle_logout)
        self.switch_account_button.clicked.connect(self.handle_switch_account)
        # 【修改】将原有的 logout_button 连接到新的 handle_logout 函数
        self.logout_button.clicked.connect(self.handle_logout)
        # 【新增】为“切换账户”按钮连接到新的 handle_switch_account 函数
        self.switch_account_button.clicked.connect(self.handle_switch_account)
        self.new_profile_button.clicked.connect(self.handle_new_profile)
        self.add_share_button.clicked.connect(self.handle_add_subscription); self.delete_profile_button.clicked.connect(self.handle_delete_profile)
        self.connect_button.clicked.connect(self.toggle_connection)
    
    def on_profile_changed(self, current, previous):
        if self.is_running: return
        if previous: self.save_current_ui_to_profile(previous.data(Qt.UserRole))
        if current:
            self.current_profile_id = current.data(Qt.UserRole)
            self.load_data_for_profile(self.current_profile_id)
        elif self.profile_list_widget.count() == 0: self.refresh_profile_list()

    def save_current_ui_to_profile(self, profile_id):
        if not profile_id: return
        profile = self.profiles.get(profile_id)
        if not profile: return
        if profile['type'] in ['guest', 'cloud']: profile['data'] = self.get_config_from_ui()
        elif profile['type'] == 'share' and profile.get('is_template'):
            user_params = {'proxies': self.get_proxies_from_ui()}
            if hasattr(self, 'node_selector'): user_params['node_remark'] = self.node_selector.currentText()
            profile['user_params'] = user_params
    
    def load_data_for_profile(self, profile_id):
        profile = self.profiles.get(profile_id, {}); profile_type = profile.get('type', 'guest'); self.log_output.clear()
        self.active_node_label.setVisible(False); self.active_node_selector.setVisible(False); self.active_node_selector.clear()
        if profile_type == 'share':
            self.stacked_widget.setCurrentWidget(self.shared_page)
            is_template = profile.get('is_template', False)
            self.shared_proxy_group.setEnabled(is_template); self.node_selector.parent().setVisible(is_template); self.node_label.setVisible(not is_template)
            if is_template:
                self.node_selector.clear(); self.update_active_node_selector(profile.get('nodes',[]), self.node_selector)
                if profile.get('user_params', {}).get('node_remark'): self.node_selector.setCurrentText(profile.get('user_params').get('node_remark'))
                proxies = profile.get('user_params', {}).get('proxies', [])
            else:
                success, data = self.api_client.use_share(profile['share_id'], {}); proxies = data.get('final_toml_data', {}).get('proxies', []) if success else []
            self.set_proxies_to_ui(proxies)
        else:
            self.stacked_widget.setCurrentWidget(self.editable_page); self.set_config_to_ui(profile.get('data', {}))
            nodes = self.get_nodes_from_ui()
            if nodes:
                self.active_node_label.setVisible(True); self.active_node_selector.setVisible(True)
                self.update_active_node_selector(nodes, self.active_node_selector)
            is_cloud = profile_type == 'cloud'
            self.save_cloud_button.setVisible(is_cloud); self.share_button.setVisible(is_cloud)
        self.update_ui_for_run_status(self.is_running)

    def get_config_from_ui(self): return {'nodes': self.get_nodes_from_ui(), 'proxies': self.get_proxies_from_ui()}

    def set_config_to_ui(self, data):
        nodes = data.get('nodes', [])
        if not nodes and 'serverAddr' in data: nodes = [{'remark': data.get('serverAddr', '默认节点'), 'server_addr': data.get('serverAddr', ''), 'server_port': data.get('serverPort', ''), 'token': data.get('auth', {}).get('token', '')}]
        self.set_nodes_to_ui(nodes); self.set_proxies_to_ui(data.get('proxies', []))

    def get_proxies_from_ui(self):
        table = self.editable_proxy_table if self.stacked_widget.currentWidget() == self.editable_page else self.shared_proxy_table
        proxies = []
        for row in range(table.rowCount()):
            proxies.append({'name': table.item(row, 0).text(), 'type': table.item(row, 1).text(), 'local_ip': table.item(row, 2).text(), 'local_port': table.item(row, 3).text(), 'remote_port': table.item(row, 4).text(), 'custom_domains': table.item(row, 5).text()})
        return proxies

    def set_proxies_to_ui(self, proxies):
        table = self.editable_proxy_table if self.stacked_widget.currentWidget() == self.editable_page else self.shared_proxy_table
        table.setRowCount(0)
        if not proxies: return
        for proxy in proxies:
            row = table.rowCount(); table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(proxy.get('name', ''))); table.setItem(row, 1, QTableWidgetItem(proxy.get('type', '')))
            table.setItem(row, 2, QTableWidgetItem(proxy.get('local_ip', ''))); table.setItem(row, 3, QTableWidgetItem(str(proxy.get('local_port', ''))))
            table.setItem(row, 4, QTableWidgetItem(str(proxy.get('remote_port', '')))); table.setItem(row, 5, QTableWidgetItem(proxy.get('custom_domains', '')))
    
    def get_nodes_from_ui(self):
        nodes = [];
        for row in range(self.nodes_table.rowCount()):
            item = self.nodes_table.item(row, 0)
            if item and item.data(Qt.UserRole): nodes.append(item.data(Qt.UserRole))
        return nodes

    def set_nodes_to_ui(self, nodes):
        self.nodes_table.setRowCount(0)
        if not nodes: return
        for node in nodes:
            row = self.nodes_table.rowCount(); self.nodes_table.insertRow(row)
            remark_item = QTableWidgetItem(node.get('remark', '')); remark_item.setData(Qt.UserRole, node)
            token = node.get('token', ''); token_display = f"{token[:3]}..." if len(token) > 3 else ("有" if token else "无")
            self.nodes_table.setItem(row, 0, remark_item); self.nodes_table.setItem(row, 1, QTableWidgetItem(node.get('server_addr', '')))
            self.nodes_table.setItem(row, 2, QTableWidgetItem(str(node.get('server_port', '')))); self.nodes_table.setItem(row, 3, QTableWidgetItem(token_display))

    def update_ui_for_login_status(self, is_logged_in):
        self.logged_out_widget.setVisible(not is_logged_in)
        self.logged_in_widget.setVisible(is_logged_in)
    
        # 【修改】确保两个按钮的可见性都受登录状态控制
        self.logout_button.setVisible(is_logged_in)
        self.switch_account_button.setVisible(is_logged_in)
    
        self.new_profile_button.setEnabled(is_logged_in)
        self.add_share_button.setEnabled(is_logged_in)
        self.delete_profile_button.setEnabled(is_logged_in)
        if is_logged_in: 
            self.welcome_label.setText(f"欢迎, <b>{self.logged_in_nickname}</b>")
        else: 
            # 清除欢迎语并刷新列表
            self.welcome_label.setText("欢迎, ") 
            self.refresh_profile_list()

    def update_ui_for_run_status(self, is_running):
        self.is_running = is_running
        self.account_group.setEnabled(not is_running); self.profile_list_group.setEnabled(not is_running)
        self.stacked_widget.setEnabled(not is_running); self.active_node_selector.setEnabled(not is_running)
        self.connect_button.setText("停止连接" if is_running else "启动连接")
        self.connect_button.setStyleSheet(f"background-color: {'#f44336' if is_running else '#4CAF50'}; color: white; height: 40px; font-size: 16px;")
    

    def handle_register(self):
        dialog = LoginDialog("注册新账户", self)
        nickname, password, _, invite_code = dialog.get_credentials()
        if not (nickname and password and invite_code): return
        delay_dialog = HardenedDelayDialog(self)
        delay_dialog.start_delay()
        success, message = self.api_client.auth.register(nickname, password, invite_code)
        if success: QMessageBox.information(self, "成功", "注册成功！请使用此昵称和密码登录。")
        else: QMessageBox.critical(self, "注册失败", str(message))
    
    def handle_forgot_password(self):
        """【新增】处理“忘记密码”点击事件"""
        # 导入ResetPasswordDialog，确保它在Dialogs.py中已定义
        from Dialogs import ResetPasswordDialog
        
        reset_dialog = ResetPasswordDialog(self)
        data = reset_dialog.get_data()
        if not data:
            return

        # 调用新的API接口
        success, message = self.api_client.auth.perform_password_reset(
            data['nickname'], data['token'], data['new_password']
        )
        
        if success:
            QMessageBox.information(self, "成功", message.get("message", "密码重置成功！"))
        else:
            QMessageBox.critical(self, "失败", f"密码重置失败: {message}")

    # 【新增】把XOR解密函数变成一个类方法或全局函数，方便多处调用
    def _xor_cipher(self, data, key):
        return bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(data)])

    def handle_login(self):
        """
        处理用户登录，采用“先强制延时，后网络验证”的线性流程。
        【已修复 dll_hash 未定义的问题】
        """
        # 1. 获取用户凭据 (不变)
        settings = self._load_local_settings()
        dialog = LoginDialog("登录", self,
                             remembered_nickname=settings.get('nickname', ''),
                             remembered_password=settings.get('password', ''))
        dialog.forgot_password_button.clicked.connect(self.handle_forgot_password)
        nickname, password, remember_me, _ = dialog.get_credentials()
        if not (nickname and password):
            return
 
        # 2. 【核心】首先，完整地执行安全延时 (不变)
        self.log_to_gui("正在进行安全延时以防止爆破...")
        delay_dialog = HardenedDelayDialog(self)
        delay_dialog.start_delay() # 这会阻塞2-4秒，直到动画播放完毕
        self.log_to_gui("安全延时完成。")
 
        # 3. 延时结束后，才开始执行所有网络和计算逻辑
        try:
            # ================================================================
            # --- a. 准备本地凭据【核心修改区域】---
            # ================================================================
            self.log_to_gui("正在准备安全凭据...")
            
            # 步骤 1: 找到 frp_core-R.dat 文件
            dll_path = resource_path("MoeFrpClient.mfc")
            if not os.path.exists(dll_path):
                raise FileNotFoundError("核心组件 'MoeFrpClient.mfc' 未找到！")

            dll_hash = get_file_sha256(dll_path)
 
            # 健壮性检查：确保 dll_hash 不是空的
            if not dll_hash:
                raise ValueError("未能成功计算核心组件的哈希值。")
            
            # ================================================================
            # --- 【修改结束】---
            # ================================================================
 
            # b. 获取挑战码 (不变)
            self.log_to_gui("正在从服务器获取安全挑战码...")
            success, challenge_data = self.api_client.auth.get_login_challenge(nickname)
            if not success:
                raise Exception(f"获取挑战码失败: {challenge_data}")
            challenge = challenge_data.get('challenge')
 
            # c. 计算登录证明 (不变，但现在 dll_hash 有值了)
            self.log_to_gui("正在计算登录证明(Proof)...")
            message_to_hash = f"{VERSION_SECRET}:{dll_hash}:{CLIENT_VERSION}:{challenge}"
            h = hashlib.sha256()
            h.update(message_to_hash.encode('utf-8'))
            proof = h.hexdigest()
 
            # d. 正式登录 (不变，但现在 dll_hash 有值了)
            self.log_to_gui("正在发送登录请求...")
            success, data = self.api_client.auth.login(
                nickname, password, CLIENT_VERSION, VERSION_SECRET, dll_hash, challenge, proof
            )
 
            # e. 处理结果 (不变)
            if success:
                self.session_token = data.get('session_token')
                self.logged_in_nickname = nickname
                if remember_me:
                    self._save_local_settings(nickname, password)
                else:
                    self._clear_local_settings()
 
                self.update_ui_for_login_status(True)
                self.handle_cloud_load()
                self.session_timer.start(30000)
                self.refresh_timer.start()
                self.log_to_gui(f"欢迎，{nickname}！登录成功。", "green")
            else:
                raise Exception(str(data))
 
        except Exception as e:
            # 捕获整个过程中的任何错误
            self.log_to_gui(f"登录失败: {e}", "red")
            QMessageBox.critical(self, "登录失败", str(e))

    def handle_logout(self, show_confirm=True):
        """
        【临时退出】
        只清除当前会话，不删除本地存储的凭证。
        """
        if show_confirm:
            reply = QMessageBox.question(self, "确认退出登录", "您确定要退出当前登录吗？\n（“记住密码”信息将保留）",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.log_to_gui("正在退出当前会话...", "orange")
        
        # 步骤1: 清除会话信息
        self.session_token = None
        self.logged_in_nickname = None
        
        # 步骤2: 停止所有后台定时器
        self.session_timer.stop()
        self.refresh_timer.stop()
        
        # 【注意】这里不调用 _clear_local_settings()
        
        # 步骤4: 更新UI到未登录状态
        self.update_ui_for_login_status(False)
        
        # 步骤5: 重置配置字典和UI列表，仅保留游客模式
        self.profiles = {'guest': {'type': 'guest', 'data': {}}}
        self.refresh_profile_list()
        
        self.log_to_gui("您已成功退出。")
        self.statusBar().showMessage("已退出登录", 3000)

    def handle_switch_account(self):
        """
        【切换账户/彻底清除】
        退出登录并清除本地所有记住的凭证。
        """
        reply = QMessageBox.question(self, "确认切换账户", 
                                     "您确定要彻底退出并清除本地记住的密码吗？\n\n此操作用于更换账号或在公共设备上使用。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
            
        # 调用“临时退出”，但不显示确认对话框，因为它已经执行了大部分通用逻辑
        self.handle_logout(show_confirm=False) 
        
        # 额外执行清除本地凭证的操作
        self._clear_local_settings()
        
        self.log_to_gui("本地凭证已清除，您可以登录新账户。")
        self.statusBar().showMessage("本地凭证已清除", 3000)
    
    def force_logout(self, message):
        self.refresh_timer.stop()
        self.session_timer.stop()
        if self.is_running:
            self.stop_frp() # stop_frp会自己处理两种文件的清理
        else:
            # 如果没有在运行，也要手动清理可能残留的文件
            self._cleanup_guest_config_file()
    
        self.is_forced_exit = True
        QMessageBox.critical(self, "强制下线", f"{message}\n\n您的账户已在其他设备登录或会话已过期，本程序将关闭。")
        self.close()

    def handle_silent_refresh(self):
        if not self.session_token or self.is_running: return
        self.refresh_thread = RefreshThread(self.api_client.config, self.session_token) # 传递 config 部分
        self.refresh_thread.finished.connect(self.on_silent_refresh_finished) 
        self.refresh_thread.start()
        self.statusBar().showMessage("正在后台同步配置...", 1500)

    def on_silent_refresh_finished(self, success, data):
        if not success:
            if "会话无效" in str(data) or "会话已过期" in str(data): self.force_logout(str(data))
            else: self.statusBar().showMessage(f"后台同步失败: {data}", 3000)
            return
            
        current_id = self.profile_list_widget.currentItem().data(Qt.UserRole) if self.profile_list_widget.currentItem() else None
        new_profiles = {'guest': self.profiles.get('guest', {'type': 'guest', 'data': {}})}
        
        # 处理个人云端配置 (逻辑不变)
        for config in data.get('personal_configs', []):
            try: 
                new_profiles[config['config_id']] = {'type': 'cloud', 'profile_name': config['profile_name'], 'data': json.loads(config['config_json'])}
            except: 
                continue

        # --- 【核心修改】在这里处理订阅 ---
        for sub in data.get('subscriptions', []):
            try:
                sub_id = sub['subscription_id']
                
                # 从服务器获取节点信息
                nodes_data = json.loads(sub.get('share_config_json', '{}')).get('nodes', [])
                
                # 【智能合并】检查本地是否已存在此订阅的配置
                existing_profile = self.profiles.get(sub_id)
                
                final_user_params = {}
                # 如果本地存在且是一个分享配置，则优先使用本地的 user_params
                if existing_profile and existing_profile.get('type') == 'share':
                    final_user_params = existing_profile.get('user_params', {})
                # 否则 (例如首次加载)，使用从服务器获取的 user_params
                else:
                    final_user_params = json.loads(sub.get('user_params_json', '{}'))

                # 使用合并后的 user_params 构建新的配置项
                new_profiles[sub_id] = {
                    'type': 'share', 
                    'share_id': sub.get('share_id'), 
                    'share_name': sub.get('share_name'), 
                    'is_template': sub.get('is_template'), 
                    'user_params': final_user_params, # <-- 使用最终确定的 user_params
                    'nodes': nodes_data
                }
            except: 
                continue
        # ------------------------------------

        # 只有在数据确实发生变化时才更新UI
        if new_profiles != self.profiles:
            self.profiles = new_profiles
            self.refresh_profile_list(current_id)
            self.statusBar().showMessage("配置列表已更新！", 2000)

    def handle_cloud_load(self):
        if not self.session_token: return
        success, data = self.api_client.config.get_all_configs(self.session_token)
        if success:
            self.on_silent_refresh_finished(success, data)
            if self.profile_list_widget.count() > 1: self.profile_list_widget.setCurrentRow(1)
            else: self.profile_list_widget.setCurrentRow(0)
            QMessageBox.information(self, "成功", "已从云端加载所有配置！")
        else:
            if "会话无效" in str(data) or "会话已过期" in str(data): self.force_logout(str(data))
            else: QMessageBox.critical(self, "错误", f"加载配置失败: {data}")

    def handle_cloud_save(self):
        if not self.session_token: return
        self.save_current_ui_to_profile(self.current_profile_id)
        personal_configs = [{'config_id': k, 'profile_name': v['profile_name'], 'config_json': json.dumps(v['data'])} for k, v in self.profiles.items() if v.get('type') == 'cloud']
        subscriptions = {k: {'share_id': v.get('share_id'), 'user_params': v.get('user_params', {})} for k, v in self.profiles.items() if v.get('type') == 'share'}
        payload = {'personal_configs': personal_configs, 'subscriptions': subscriptions}
        success, message = self.api_client.config.save_all_configs(self.session_token, payload)
        if success: self.statusBar().showMessage("所有云端配置和订阅已保存！", 2000)
        else:
            if "会话无效" in str(message) or "会话已过期" in str(message): self.force_logout(str(message))
            else: QMessageBox.critical(self, "错误", f"保存配置失败: {message}")

    def handle_create_share(self):
        profile = self.profiles.get(self.current_profile_id)
        if not profile or profile['type'] != 'cloud': QMessageBox.warning(self, "提示", "只能分享您自己的云端配置。"); return
        self.save_current_ui_to_profile(self.current_profile_id); dialog = CreateShareDialog(profile['data'], self)
        if dialog.exec():
            share_data = dialog.get_data();
            if not share_data: return
            success, data = self.api_client.share.create(self.session_token, share_data)
            if success: QInputDialog.getText(self, "分享创建成功", "请复制您的分享ID:", text=data['share_id'])
            else: QMessageBox.critical(self, "失败", f"创建分享失败: {data}")

    def handle_manage_shares(self):
        if not self.session_token: return
        dialog = ManageSharesDialog(self.api_client.share, self.session_token, self); dialog.exec()

    def handle_add_subscription(self):
        if not self.session_token: return
        share_id, ok = QInputDialog.getText(self, "添加分享订阅", "请输入您收到的分享ID:")
        if ok and share_id:
            success, data = self.api_client.share.get_public_info(share_id)
            if success:
                new_sub_id = f"sub-{uuid.uuid4()}"; self.profiles[new_sub_id] = {'type': 'share', 'share_id': share_id, **data, 'user_params': {}}
                self.refresh_profile_list(); self.handle_cloud_save()
                QMessageBox.information(self, "成功", f"已成功订阅分享 '{data['share_name']}'！")
            else: QMessageBox.critical(self, "失败", f"添加订阅失败: {data}")

    def handle_delete_profile(self):
        item = self.profile_list_widget.currentItem();
        if not item: return
        profile_id = item.data(Qt.UserRole)
        if profile_id == 'guest': QMessageBox.warning(self, "提示", "游客模式不能删除。"); return
        profile = self.profiles[profile_id]; profile_name = profile.get('profile_name') or profile.get('share_name')
        reply = QMessageBox.question(self, "确认", f"确定要删除配置 '{profile_name}' 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: del self.profiles[profile_id]; self.refresh_profile_list(); self.handle_cloud_save()
    
    def handle_new_profile(self):
        if not self.session_token: QMessageBox.warning(self, "提示", "请先登录。"); return
        name, ok = QInputDialog.getText(self, "新建配置", "请输入新配置的名称:")
        if ok and name:
            new_id = f"conf-{uuid.uuid4()}"; self.profiles[new_id] = {'type': 'cloud', 'profile_name': name, 'data': {}}
            self.refresh_profile_list(new_id)

    def handle_ping_nodes(self):
        """【已修正】测速时，获取原始节点数据，而不是显示的文本"""
        if self.node_selector.count() == 0: return

        # 从每个条目的关联数据(userData)中获取节点信息来ping
        nodes_to_ping = [self.node_selector.itemData(i) for i in range(self.node_selector.count())]
        
        if not nodes_to_ping: return
        
        self.ping_thread = PingThread(nodes_to_ping)
        self.ping_thread.result_ready.connect(self.update_ping_result)
        self.ping_thread.finished.connect(lambda: self.ping_button.setEnabled(True))
        self.ping_button.setEnabled(False)
        self.ping_thread.start()

    def update_ping_result(self, index, latency):
        """【已修正】只修改显示的文本，不影响关联数据"""
        try:
            # 从关联数据中获取原始的、干净的备注名
            original_remark = self.node_selector.itemData(index).get('remark', '未知节点')
            
            if latency != -1:
                # 只更新 setItemText
                self.node_selector.setItemText(index, f"{original_remark} ({latency:.2f} ms)")
            else:
                self.node_selector.setItemText(index, f"{original_remark} (超时)")
        except Exception:
            pass # 防止在ping的过程中，下拉框被清空导致index越界

    def toggle_connection(self):
        """根据当前运行状态，决定是启动还是停止frp服务"""
        if self.is_running:
            self.stop_frp()
        else:
            self.start_frp()

    def start_frp(self):
        """
        【重构版】启动内置的frp服务。
        现在由主进程负责解密和创建临时DLL，并将路径传递给子进程。
        """
        self.has_shown_connection_error = False
        self.log_output.clear()
        
        # 确保之前的临时文件被清理干净
    
        try:
            # =========================================================================
            # --- 步骤 1: 【核心改动】在主进程中解密并创建临时 frp_core.dll ---
            # =========================================================================
            # === 步骤 1: 找到打包好的 frp_core.dll ===
            self.log_to_gui("正在定位核心组件...")
            dll_path = resource_path("MoeFrpClient.mfc")
            if not os.path.exists(dll_path):
                raise FileNotFoundError("核心组件 'MoeFrpClient.mfc' 未能被正确打包或找到！")
            
            self.log_to_gui(f"核心组件已定位")
 
            # === 步骤 2: 准备配置文件路径 (config_location_arg)，这部分逻辑不变 ===
            self.save_current_ui_to_profile(self.current_profile_id)
            profile = self.profiles[self.current_profile_id]
            config_location_arg = ""
            # =========================================================================
            
            # --- 步骤 2: 准备配置文件路径 (config_location_arg)，这部分逻辑不变 ---
            self.save_current_ui_to_profile(self.current_profile_id)
            profile = self.profiles[self.current_profile_id]
            
            config_location_arg = ""
    
            if profile['type'] == 'guest':
                # ... (游客模式的配置生成逻辑完全不变) ...
                self.log_to_gui("正在准备游客模式（本地）配置...")
                selected_node = self.active_node_selector.currentData()
                if not selected_node: raise ValueError("请选择一个运行节点。")
                proxies = self.get_proxies_from_ui()
                config_dict = {'serverAddr': selected_node.get('server_addr'), 'serverPort': int(selected_node.get('server_port')), 'auth': {'token': selected_node.get('token', '')}}
                final_proxies = []
                for p in proxies:
                    proxy_type=p.get('type')
                    if not proxy_type: continue
                    new_p = {'name': p.get('name'), 'type': proxy_type}
                    if p.get('local_ip'): new_p['localIP'] = p.get('local_ip')
                    if p.get('local_port'): new_p['localPort'] = int(p.get('local_port'))
                    if proxy_type in ['http', 'https']:
                        if p.get('custom_domains'): new_p['custom_domains'] = [d.strip() for d in str(p.get('custom_domains')).split(',') if d.strip()]
                    elif proxy_type in ['tcp', 'udp', 'stcp', 'xtcp']:
                        if p.get('remote_port'): new_p['remotePort'] = int(p.get('remote_port'))
                    final_proxies.append(new_p)
                if final_proxies: config_dict['proxies'] = final_proxies
                config_dict['log'] = {'level': 'info'}
                self.running_config = copy.deepcopy(config_dict)
                config_content = toml.dumps(config_dict)
                temp_dir = tempfile.gettempdir()
                unique_filename = f"frpc_guest_{uuid.uuid4().hex[:12]}.toml"
                self.guest_config_path = os.path.join(temp_dir, unique_filename)
                with open(self.guest_config_path, "w", encoding='utf-8') as f: f.write(config_content)
                self.log_to_gui(f"临时配置文件已创建: {self.guest_config_path}")
                config_location_arg = self.guest_config_path
            else: # 在线模式
                config_dict = {}
                if profile['type'] == 'share':
                    # ... (分享模式的配置生成逻辑完全不变) ...
                     self.log_to_gui("正在从云端获取分享配置...")
                     selected_node_data = self.node_selector.currentData()
                     if not selected_node_data: raise ValueError("请选择一个有效的节点。")
                     selected_node_remark = selected_node_data.get('remark')
                     user_params = {'node_remark': selected_node_remark}
                     if profile.get('is_template'): user_params['proxies'] = self.get_proxies_from_ui()
                     success, data = self.api_client.share.use(profile['share_id'], user_params)
                     if not success: raise Exception(str(data))
                     config_dict = data.get('final_toml_data', {})
                elif profile['type'] == 'cloud':
                    # ... (云端模式的配置生成逻辑完全不变) ...
                     selected_node = self.active_node_selector.currentData()
                     if not selected_node: raise ValueError("请选择一个运行节点。")
                     proxies = self.get_proxies_from_ui()
                     config_dict = {'serverAddr': selected_node.get('server_addr'),'serverPort': int(selected_node.get('server_port')),'auth': {'token': selected_node.get('token', '')}}
                     final_proxies = []
                     for p in proxies:
                         proxy_type = p.get('type')
                         if not proxy_type: continue
                         new_p = {'name': p.get('name'), 'type': p.get('type')}
                         if p.get('local_ip'): new_p['localIP'] = p.get('local_ip')
                         if p.get('local_port'): new_p['localPort'] = int(p.get('local_port'))
                         if p.get('type') in ['http', 'https']:
                             if p.get('custom_domains'): new_p['custom_domains'] = [d.strip() for d in str(p.get('custom_domains')).split(',') if d.strip()]
                         elif p.get('type') in ['tcp', 'udp', 'stcp', 'xtcp']:
                             if p.get('remote_port'): new_p['remotePort'] = int(p.get('remote_port'))
                         final_proxies.append(new_p)
                     if final_proxies: config_dict['proxies'] = final_proxies
                config_dict['log'] = {'level': 'info'}
                self.running_config = copy.deepcopy(config_dict)
                config_content = toml.dumps(config_dict)
                self.log_to_gui("正在向服务器申请配置票据...")
                success, data = self.api_client.config.request_config_ticket(self.session_token, config_content)
                if not success: raise Exception(f"无法获取配置票据: {data}")
                config_id = data.get('config_id')
                if not config_id: raise Exception("服务器未返回有效的配置票据。")
                config_location_arg = f"{CLOUD_SERVER_URL.rstrip('/')}/api/get_temp_config/{config_id}"
            
            # --- 步骤 3: 启动子进程，并传入两个参数 ---
            self.log_to_gui("正在启动内置frp服务...")
            
            # 【核心改动】命令现在包含两个参数：配置文件路径和DLL路径
            command = []
            if getattr(sys, 'frozen', False):
                command = [sys.executable, config_location_arg, dll_path]
            else:
                command = [sys.executable, sys.argv[0], config_location_arg, dll_path]
            
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            self.frp_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=creation_flags,
                bufsize=1
            )
            
            self.log_reader_thread = LogReaderThread(self.frp_process.stdout)
            self.log_reader_thread.new_log_line.connect(self.handle_frpc_log)
            self.log_reader_thread.finished.connect(self.on_frp_finished)
            self.log_reader_thread.start()
    
            self.update_ui_for_run_status(True)
            self.log_to_gui(f"内置frp服务已在独立进程(PID: {self.frp_process.pid})中启动。")
    
        except Exception as e:
            self.log_to_gui(f"启动frp服务失败: {e}", "red")
            self.update_ui_for_run_status(False)
        

    def stop_frp(self):
        """
        【最终健壮版】通过操作系统信号终止frp子进程，并确保清理所有临时文件。
        """
        # 1. 停止子进程
        # 检查frp_process对象是否存在，并且通过poll()确认进程是否仍在运行
        if hasattr(self, 'frp_process') and self.frp_process and self.frp_process.poll() is None:
            self.log_to_gui("正在停止内置frp服务...", "orange")
            try:
                self.frp_process.terminate()
                try:
                    # 等待最多5秒，让进程自行退出
                    self.frp_process.wait(timeout=5)
                    self.log_to_gui("服务已成功停止。")
                except subprocess.TimeoutExpired:
                    self.log_to_gui("服务未在5秒内响应，正在强制停止...", "red")
                    self.frp_process.kill()
                    self.frp_process.wait() # 等待kill生效
            except Exception as e:
                self.log_to_gui(f"停止服务时发生错误: {e}", "red")
    
        # 2. 清理所有相关临时文件 (DLL和guest toml)
        #    无论进程是否成功停止，都应该执行清理
        self._cleanup_guest_config_file()
        
        # 3. 更新UI状态
        #    将frp_process句柄清空，防止重复操作
        self.frp_process = None
        if self.is_running:
            self.update_ui_for_run_status(False)
    
    def on_frp_finished(self):
        """
        【最终健壮版】当frp子进程的日志管道关闭时（意味着进程已结束），此方法被调用。
        """
        # 打印日志，但只在用户不是主动停止时打印
        if self.is_running: 
            if "已停止" not in self.log_output.toPlainText():
                self.log_to_gui("连接已断开（frp进程已退出）。", "orange")
        
        # 统一调用stop_frp的清理和UI更新逻辑
        # 这里的stop_frp不会再次尝试停止进程，因为if里的poll()会返回非None
        # 但它会确保清理和UI更新逻辑被完整执行
        self.stop_frp()

    def log_to_gui(self, message, color="black"):
        """这个函数现在只负责将格式化好的信息显示到UI上"""
        self.log_output.setTextColor(QColor(color))
        self.log_output.append(message)

    def handle_frpc_log(self, line: str):
        """【已最终修正】精确处理frpc的日志，只显示必要信息"""
        # 清理可能存在的ANSI颜色代码
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', line).strip()

        # 如果是空行，直接忽略
        if not clean_line:
            return

        # 1. 优先检查是否是【代理启动成功】的标志
        # 这是最重要的、必须给用户看的正面反馈
        if "start proxy success" in clean_line:
            proxies_to_check = self.running_config.get('proxies', self.get_proxies_from_ui())
            if not proxies_to_check: return
            
            for proxy in proxies_to_check:
                if f"[{proxy.get('name')}]" in clean_line:
                    local_ip = proxy.get('localIP', proxy.get('local_ip', '127.0.0.1'))
                    local_port = proxy.get('localPort', proxy.get('local_port', ''))
                    local_info = f"本地 [{local_ip}:{local_port}]"
                    remote_info = ""
                    server_addr = ""
                    profile = self.profiles.get(self.current_profile_id, {})
                    
                    if profile.get('type') == 'share':
                        if profile.get('is_template'): server_addr = self.node_selector.currentData().get('server_addr', '未知服务器')
                        else: server_addr = self.running_config.get('serverAddr', '分享服务器')
                    else:
                        node_data = self.active_node_selector.currentData()
                        if node_data: server_addr = node_data.get('server_addr', '未知服务器')
                    
                    proxy_type = proxy.get('type')
                    if proxy_type in ['http', 'https']:
                        domain = str(proxy.get('custom_domains', '')).split(',')[0].strip()
                        remote_info = f"请通过 [{proxy_type}://{domain}] 访问" if domain else "但未指定自定义域名"
                    else:
                        remote_port = proxy.get('remotePort', proxy.get('remote_port'))
                        remote_info = f"已在远程 [{server_addr}:{remote_port}] 开启" if server_addr and remote_port else "但未指定远程端口"
                    
                    friendly_message = f"  ✅ 提示: {local_info} 的服务已就绪，{remote_info}。"
                    self.log_to_gui(friendly_message, "#2E8B57") # 绿色
                    # 成功后，不需要再处理其他日志，直接返回
                    return
            # 如果没找到匹配的proxy，也直接返回
            return

        # 2. 检查是否是【连接失败】的致命错误
        # 这是最重要的负面反馈
        sensitive_failures = ["login to the server failed", "dial tcp", "connect to server error"]
        if any(keyword in clean_line for keyword in sensitive_failures):
            # 显示我们自己的友好错误提示，并用红色
            self.log_to_gui("❌ 错误: 连接服务器失败，请检查网络或节点配置。", "red")
            self.has_shown_connection_error = True
            # 失败后，也不需要再处理其他日志，直接返回
            return
        if "login to server success" in clean_line:
            # 重置错误标志，因为登录成功意味着连接已经恢复
            self.has_shown_connection_error = False
            self.log_to_gui("  - 登录服务器成功...", "gray")
            return

        # 3. 对于所有其他日志（包括 "login to server success", "start frpc service" 等）
        # 我们选择【不显示】，以保持UI的绝对干净。
        # 如果需要调试，可以取消下面一行的注释，在控制台查看所有被忽略的日志。
        # print(f"[FRPC IGNORED]: {clean_line}")

    def add_proxy(self):
        profile = self.profiles.get(self.current_profile_id, {}); is_share = profile.get('type') == 'share'
        if is_share and not profile.get('is_template'): QMessageBox.warning(self, "提示", "完整模式的分享不能修改代理规则。"); return
        dialog = ProxyEditDialog(self)
        if dialog.exec():
            data = dialog.get_data();
            if not data: return
            if not data['name']: QMessageBox.warning(self, "提示", "规则名称不能为空."); return
            proxies = self.get_proxies_from_ui()
            if any(p['name'] == data['name'] for p in proxies): QMessageBox.warning(self, "提示", f"规则名称 '{data['name']}' 已存在."); return
            proxies.append(data); self.set_proxies_to_ui(proxies)

    def edit_proxy(self):
        table = self.editable_proxy_table if self.stacked_widget.currentWidget() == self.editable_page else self.shared_proxy_table
        selected = table.selectionModel().selectedRows()
        if not selected: return
        row = selected[0].row(); proxies = self.get_proxies_from_ui(); dialog = ProxyEditDialog(self, proxies[row])
        if dialog.exec(): 
            new_data = dialog.get_data()
            if new_data: proxies[row] = new_data; self.set_proxies_to_ui(proxies)

    def delete_proxy(self):
        table = self.editable_proxy_table if self.stacked_widget.currentWidget() == self.editable_page else self.shared_proxy_table
        selected = table.selectionModel().selectedRows()
        if not selected: return
        proxies = self.get_proxies_from_ui(); del proxies[selected[0].row()]; self.set_proxies_to_ui(proxies)
        
    def add_node(self):
        dialog = NodeEditDialog(self)
        if dialog.exec():
            node_data = dialog.get_data()
            if node_data:
                nodes = self.get_nodes_from_ui(); nodes.append(node_data)
                self.set_nodes_to_ui(nodes); self.update_active_node_selector(nodes, self.active_node_selector)

    def edit_node(self):
        selected = self.nodes_table.selectionModel().selectedRows()
        if not selected: return
        row = selected[0].row(); nodes = self.get_nodes_from_ui(); dialog = NodeEditDialog(self, nodes[row])
        if dialog.exec():
            new_data = dialog.get_data()
            if new_data:
                nodes[row] = new_data; self.set_nodes_to_ui(nodes)
                self.update_active_node_selector(nodes, self.active_node_selector)

    def delete_node(self):
        selected = self.nodes_table.selectionModel().selectedRows()
        if not selected: return
        reply = QMessageBox.question(self, "确认", "确定要删除选中的节点吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            row = selected[0].row(); nodes = self.get_nodes_from_ui(); del nodes[row]
            self.set_nodes_to_ui(nodes); self.update_active_node_selector(nodes, self.active_node_selector)

    def update_active_node_selector(self, nodes, selector):
        current_data = selector.currentData()
        selector.clear()
        if nodes:
            for node in nodes:
                remark = node.get('remark', '未命名节点')
                # 第一个参数是显示文本，第二个是关联数据
                selector.addItem(remark, userData=node)
                # 【新】为条目设置 ToolTip，显示原始名称
                selector.setItemData(selector.count() - 1, remark, Qt.ToolTipRole)
            
            if current_data:
                # findData 现在会根据我们存入的完整字典来查找
                index = selector.findData(current_data)
                if index != -1:
                    selector.setCurrentIndex(index)

    def refresh_profile_list(self, pre_selected_id=None):
        id_to_select = pre_selected_id or (self.profile_list_widget.currentItem().data(Qt.UserRole) if self.profile_list_widget.currentItem() else self.current_profile_id)
        self.profile_list_widget.clear()
        
        # --- 游客模式图标 ---
        guest_item = QListWidgetItem("💨 游客模式 (本地临时)")
        guest_item.setData(Qt.UserRole, "guest")
        self.profile_list_widget.addItem(guest_item)
        
        if self.session_token:
            for profile_id, profile_data in self.profiles.items():
                item = None
                # --- 云端配置图标 ---
                if profile_data.get('type') == 'cloud':
                    item = QListWidgetItem(f"☁️ {profile_data['profile_name']}")
                
                # --- 【核心修改】分享配置图标 ---
                elif profile_data.get('type') == 'share':
                    is_template = profile_data.get('is_template', False)
                    share_name = profile_data.get('share_name', '未知分享')
                    if is_template:
                        # 模板分享：使用类似“设置”或“工具”的图标
                        icon = self.style().standardIcon(QStyle.SP_ToolBarHorizontalExtensionButton)
                        item = QListWidgetItem(icon, f"🔧 {share_name} [模板]")
                    else:
                        # 完整分享：使用类似“链接”或“网络”的图标
                        icon = self.style().standardIcon(QStyle.SP_DriveNetIcon)
                        item = QListWidgetItem(icon, f"🔗 {share_name} [完整]")
                
                if item:
                    item.setData(Qt.UserRole, profile_id)
                    self.profile_list_widget.addItem(item)

        found = False
        if id_to_select:
            for i in range(self.profile_list_widget.count()):
                if self.profile_list_widget.item(i).data(Qt.UserRole) == id_to_select:
                    self.profile_list_widget.setCurrentRow(i)
                    found = True
                    break
        if not found and self.profile_list_widget.count() > 0:
            self.profile_list_widget.setCurrentRow(0)

    def check_session_status(self):
        if not self.session_token: self.session_timer.stop(); return
        class SessionCheckThread(QThread):
            finished = Signal(bool)
            def __init__(self, api_client, token):
                super().__init__()
                self.api_client = api_client
                self.token = token
            def run(self):
                self.finished.emit(self.api_client.auth.check_session(self.token))
        
        def on_check_finished(is_valid):
            if not is_valid: self.force_logout("您的会话已在别处登录或已过期。")

        self.session_check_thread = SessionCheckThread(self.api_client, self.session_token)
        self.session_check_thread.finished.connect(on_check_finished)
        self.session_check_thread.start()
        
    def _load_local_settings(self):
        """【全新】从注册表/QSettings加载并解密凭证"""
        try:
            # 从 QSettings 中读取加密后的凭证字符串
            encrypted_data_str = self.settings.value("credentials_bundle", "")
            if not encrypted_data_str:
                return {}
            
            # 解密
            encrypted_data = encrypted_data_str.encode()
            decrypted_data = self.encryption_manager.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception:
            self._clear_local_settings()
            return {}
        
    def _save_local_settings(self, nickname, password):
        """【全新】加密凭证并存入注册表/QSettings"""
        # 加密
        data_to_encrypt = json.dumps({'nickname': nickname, 'password': password}).encode()
        encrypted_data = self.encryption_manager.encrypt(data_to_encrypt)
        
        # 将加密后的字节串转换为字符串后存入 QSettings
        self.settings.setValue("credentials_bundle", encrypted_data.decode())
        
    def _clear_local_settings(self):
        """【全新】清除注册表/QSettings中的凭证和系统密钥环中的主密钥"""
        # 清除 QSettings 中的键
        self.settings.remove("credentials_bundle")
        
        # 清除系统密钥环中的主密钥
        if hasattr(self, 'encryption_manager'):
            self.encryption_manager.delete_all_credentials()
    # main.py, in class MainWindow:

    def contextMenuEvent(self, event):
        """
        当在主窗口的空白区域右键点击时，显示一个上下文菜单。
        这个方法是Qt内置的，我们只是重写它。
        """
        # 创建一个菜单对象，父级为当前窗口 (self)
        menu = QMenu(self)
        
        # 添加一个“刷新图片”的动作到菜单中
        # 这个动作的 triggered 信号会和下面的 menu.exec() 配合使用
        refresh_action = menu.addAction("🔄 刷新图片")
        
        # 添加一个“另存为”的动作，只有在有图片数据时才可用
        if self.current_image_data and not self.current_image_data.isEmpty():
            save_action = menu.addAction("🖼️ 另存为...")
        else:
            save_action = None
 
        # 在鼠标点击的全局位置显示菜单，并等待用户操作
        # .exec() 会阻塞，直到用户选择一个动作或点击菜单外部
        # 它会返回用户点击的那个 QAction 对象
        selected_action = menu.exec(event.globalPos())
        
        # 判断用户点击的是哪个动作
        if selected_action == refresh_action:
            # 如果是刷新动作，就调用我们早已写好的刷新方法
            self.refresh_image()
        
        elif selected_action == save_action:
            # 如果是保存动作，就调用一个新方法来处理保存逻辑
            self.save_current_image_as()
 
 
    def save_current_image_as(self):
        """
        【新增方法】用于处理“另存为”逻辑，代码从 ImageViewerDialog 中借鉴。
        """
        if not self.current_image_data or self.current_image_data.isEmpty():
            return
 
        # 使用 QImageReader 来准确获取图片格式 (例如 'png', 'gif')
        reader = QImageReader()
        buffer = QBuffer(self.current_image_data)
        buffer.open(QIODevice.ReadOnly)
        reader.setDevice(buffer)
        
        format_str = reader.format().toLower().data().decode('ascii', 'ignore')
        if not format_str: format_str = 'png' # 提供一个默认格式
 
        default_filter = f"{format_str.upper()} 文件 (*.{format_str})"
        filters = f"{default_filter};;所有文件 (*)"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{timestamp}.{format_str}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            os.path.join(os.path.expanduser("~"), default_filename), # 使用os兼容性更好的方式
            filters
        )
 
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(self.current_image_data)
                self.statusBar().showMessage(f"图片已保存到 {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存文件时出错: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'is_forced_exit') and self.is_forced_exit:
            event.accept()
            return
    
        if self.profile_list_widget.currentItem():
            self.save_current_ui_to_profile(self.profile_list_widget.currentItem().data(Qt.UserRole))
    
        if self.is_running:
            reply = QMessageBox.question(self, "确认退出", "frpc 正在运行中，确定要退出吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # 保存云端配置（如果已登录）
        if self.session_token:
            self.handle_cloud_save()
    
        # 【核心】调用统一的停止和清理方法
        self.stop_frp()
    
        # 等待旧的frp_thread（如果存在的话）
        if hasattr(self, 'frp_thread') and self.frp_thread and self.frp_thread.isRunning():
            self.frp_thread.wait()
            
        event.accept()

    def _cleanup_guest_config_file(self):
        """【全新】清理游客模式下创建的临时配置文件"""
        # 检查路径是否存在
        if self.guest_config_path and os.path.exists(self.guest_config_path):
            try:
                os.remove(self.guest_config_path)
                print(f"[Cleanup] 临时配置文件 {self.guest_config_path} 已删除。")
            except OSError as e:
                print(f"[Cleanup Error] 删除临时文件失败: {e}")
        # 无论成功与否，都将路径变量重置为None
        self.guest_config_path = None
    
if __name__ == '__main__':
    if len(sys.argv) == 3:
        config_location_arg = sys.argv[1]
        dll_path_arg = sys.argv[2]
        run_frpc_service(config_location_arg, dll_path_arg)
    else:
        app = QApplication(sys.argv)
        # 【重要】确保你的 ImageLabel.py 文件存在且无误
        window = MainWindow()
        window.show()
        sys.exit(app.exec())