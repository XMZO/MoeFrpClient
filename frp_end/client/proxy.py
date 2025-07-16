# proxy.py
"""
一个简单的模块，用于在应用程序范围内管理全局代理设置。
"""
# 【新增】从 typing 模块导入 Optional
from typing import Optional

class ProxyManager:
    """
    一个静态类，用于存储和提供代理配置。
    """
    _proxy_config = None

    @staticmethod
    def set_proxy(proxy_url: Optional[str]): # 【修改这里】
        """
        设置全局代理。
        支持 http 和 socks5 格式, 例如:
        - "http://127.0.0.1:7890"
        - "socks5://127.0.0.1:1080"
        - "socks5h://127.0.0.1:1080" (h代表dns也走代理)

        如果 proxy_url 为 None 或空字符串, 则清除代理设置。
        """
        if proxy_url:
            ProxyManager._proxy_config = {
                "http": proxy_url,
                "https": proxy_url,
            }
        else:
            ProxyManager._proxy_config = None

    @staticmethod
    def get_proxies() -> Optional[dict]:
        """
        获取适用于 requests 库的代理字典。
        """
        return ProxyManager._proxy_config