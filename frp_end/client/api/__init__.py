# api/__init__.py
from .auth import AuthEndpoints
from .config import ConfigEndpoints
from .share import ShareEndpoints

class ApiClient:
    """
    API客户端的门面 (Facade)。
    它将不同业务领域的API端点组合在一起，提供统一的访问入口。
    
    使用方法:
    client = ApiClient("http://your.api.server")
    client.auth.login(...)
    client.config.get_all_configs(...)
    client.share.create(...)
    """
    def __init__(self, base_url):
        """
        初始化API客户端。
        :param base_url: 服务器API的基础URL。
        """
        self.auth = AuthEndpoints(base_url)
        self.config = ConfigEndpoints(base_url)
        self.share = ShareEndpoints(base_url)
