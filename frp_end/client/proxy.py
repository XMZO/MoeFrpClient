# proxy.py
from typing import Optional

class ProxyManager:
    _proxy_config = None

    @staticmethod
    def set_proxy(proxy_url: Optional[str]):
        if proxy_url:
            ProxyManager._proxy_config = {
                "http": proxy_url,
                "https": proxy_url,
            }
        else:
            ProxyManager._proxy_config = None

    @staticmethod
    def get_proxies() -> Optional[dict]:
        return ProxyManager._proxy_config
