import socket
import time
import requests
from PySide6.QtCore import QThread, Signal, QByteArray
from utils import _get_value_from_path


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
        self.config_api_client = config_api_client
        self.token = token

    def run(self):

        success, data = self.config_api_client.get_all_configs(self.token)
        self.finished.emit(success, data)


class LogReaderThread(QThread):
    new_log_line = Signal(str)

    def __init__(self, process_pipe, parent=None):
        super().__init__(parent)
        self.pipe = process_pipe

    def run(self):
        try:

            for line in iter(self.pipe.readline, ''):
                self.new_log_line.emit(line.strip())
        except ValueError:

            pass
        finally:
            self.pipe.close()


class ImageFetcherThread(QThread):

    image_ready = Signal(QByteArray)
    error_occurred = Signal(str)

    def __init__(self, source_object, parent=None):
        super().__init__(parent)
        self.source = source_object

    def run(self):
        try:
            image_data = None
            source_url = self.source.get("url")

            if self.source.get("is_api"):

                print(f"[API Fetch] Stage 1: Fetching JSON from {source_url}")
                api_response = requests.get(source_url, timeout=5)
                api_response.raise_for_status()
                data = api_response.json()


                json_path = self.source.get("json_path")
                if not json_path:
                    raise ValueError(f"API源 {source_url} 缺少 'json_path' 配置")


                final_image_url = _get_value_from_path(data, json_path)

                if not final_image_url or not isinstance(final_image_url, str):
                    raise ValueError(f"无法根据路径 '{json_path}' 在API响应中找到有效的图片URL")

                print(f"[API Fetch] Stage 2: Fetching actual image from {final_image_url}")
                image_response = requests.get(final_image_url, timeout=15)
                image_response.raise_for_status()
                image_data = image_response.content

            else:

                print(f"[Direct Fetch] Fetching from {source_url}")
                response = requests.get(source_url, timeout=15)
                response.raise_for_status()
                image_data = response.content

            if image_data:
                self.image_ready.emit(QByteArray(image_data))
            else:
                raise ValueError("最终未能获取到任何图片数据。")

        except Exception as e:

            self.error_occurred.emit(f"获取图片失败: {e}")