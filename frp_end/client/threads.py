# threads.py
import socket
import time
import requests
from PySide6.QtCore import QThread, Signal, QByteArray
from api.base import BaseClient
from utils import _get_value_from_path # 从 utils.py 导入

# --- 子线程定义 ---
class PingThread(QThread):
    result_ready = Signal(int, float)
    def __init__(self, nodes, parent=None): super().__init__(parent); self.nodes = nodes
    def run(self):
        for i, node in enumerate(self.nodes):
            try:
                addr = node.get('server_addr'); port = int(node.get('server_port')); start_time = time.time()
                sock = socket.create_connection((addr, port), timeout=2); end_time = time.time(); sock.close()
                self.result_ready.emit(i, (end_time - start_time) * 1000)
            except Exception: self.result_ready.emit(i, -1)

class RefreshThread(QThread):
    finished = Signal(bool, dict)
    def __init__(self, config_api_client, token, parent=None):
        super().__init__(parent)
        self.config_api_client = config_api_client # 重命名成员变量以反映其具体职责
        self.token = token
 
    def run(self):
        # 直接调用传递进来的具体客户端的方法，不再需要 .config 前缀
        success, data = self.config_api_client.get_all_configs(self.token)
        self.finished.emit(success, data)

# 用于读取子进程日志的线程
class LogReaderThread(QThread):
    new_log_line = Signal(str)

    def __init__(self, process_pipe, parent=None):
        super().__init__(parent)
        self.pipe = process_pipe

    def run(self):
        try:
            # 实时逐行读取管道中的数据
            for line in iter(self.pipe.readline, ''):
                self.new_log_line.emit(line.strip())
        except ValueError:
            # 当管道被关闭时，iter可能会抛出ValueError，是正常现象
            pass
        finally:
            self.pipe.close()

# 用于异步获取网络图片的线程
class ImageFetcherThread(QThread):
    """
    一个通用的图片获取线程。
    现在它使用全局共享的、不受系统代理影响的Session。
    """
    image_ready = Signal(QByteArray)
    error_occurred = Signal(str)
 
    def __init__(self, source_object: dict, parent=None): # 不再需要 settings 参数
        """
        构造函数现在只需要源对象。
        """
        super().__init__(parent)
        self.source = source_object
        self.is_running = True
 
    def run(self):
        # 直接从 BaseClient 获取纯净的会话对象
        session = BaseClient._get_active_session() 
        log_msg = ""
        if BaseClient._current_proxy_mode == 'system':
            log_msg = " (via system proxy)"
        elif BaseClient._current_proxy_mode == 'custom' and session.proxies:
            log_msg = f" (via custom proxy: {session.proxies.get('http')})"
 
        headers = {'User-Agent': 'MoeFRP-Client/1.0'}
        source_url = self.source.get("url")
        if not source_url:
            self.error_occurred.emit("图片源配置错误，缺少 'url' 键。")
            return
 
        try:
            image_data = None
            
            if self.source.get("is_api"):
                # --- API类型处理 ---
                print(f"[ImageFetcher] Stage 1: Fetching JSON from {source_url}{log_msg}")
                api_response = session.get(source_url, timeout=10, headers=headers)
                api_response.raise_for_status()
                data = api_response.json()
                
                json_path = self.source.get("json_path")
                if not json_path:
                    raise ValueError(f"API源 {source_url} 缺少 'json_path' 配置")
 
                final_image_url = _get_value_from_path(data, json_path)
                if not final_image_url or not isinstance(final_image_url, str):
                    raise ValueError(f"无法根据路径 '{json_path}' 在API响应中找到有效的图片URL")
 
                print(f"[ImageFetcher] Stage 2: Fetching image from {final_image_url}{log_msg}")
                image_response = session.get(final_image_url, timeout=15, headers=headers)
                image_response.raise_for_status()
                image_data = image_response.content
            
            else:
                # --- 普通图片源处理 ---
                print(f"[ImageFetcher] Direct Fetch: from {source_url}{log_msg}")
                response = session.get(source_url, timeout=15, headers=headers)
                response.raise_for_status()
                image_data = response.content
 
            if image_data:
                self.image_ready.emit(QByteArray(image_data))
            else:
                raise ValueError("最终未能获取到任何图片数据。")
 
        except requests.exceptions.ProxyError as e:
             # 捕获SOCKS代理依赖问题
            if "SOCKS support" in str(e):
                error_msg = ("SOCKS代理依赖缺失！\n\n请在命令行运行:\n 'pip install \"requests[socks]\"' \n\n然后重启程序。")
                self.error_occurred.emit(error_msg)
            else:
                self.error_occurred.emit(f"应用内代理错误: {e}")
        except Exception as e:
            self.error_occurred.emit(f"获取图片失败: {e}")
 
    def stop(self):
        self.is_running = True