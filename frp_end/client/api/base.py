# api/base.py
import requests
import json

class BaseClient:
    """所有API端点类的基类，提供通用的请求方法。"""
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _make_request(self, method, endpoint, **kwargs):
        """
        一个私有的辅助方法，用于向API发送请求。
        处理URL构建、错误处理和JSON解析等通用逻辑。
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            # 处理HTTP错误状态 (4xx, 5xx)
            if response.status_code >= 400:
                try:
                    message = response.json().get('error', f"服务器错误 {response.status_code}")
                except json.JSONDecodeError:
                    message = f"服务器返回错误状态 {response.status_code}, 且响应非JSON格式"
                return False, message
            # 处理成功响应
            try:
                return True, response.json()
            except json.JSONDecodeError:
                # 成功但没有JSON响应体 (例如 204 No Content)
                return True, {}
        except requests.exceptions.RequestException as e:
            return False, f"网络错误: {e}"
