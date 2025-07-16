# api/base.py
import requests
import json

class BaseClient:
    """
    所有API端点类的基类。
    能动态管理网络会话，以支持直连、系统代理和自定义代理。
    """
    
    # 两个Session，一个纯净，一个信任系统环境
    _sandboxed_session = None # trust_env = False
    _system_session = None    # trust_env = True
    
    # 当前激活的代理模式
    _current_proxy_mode = "none" # 默认直连

    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        # __init__ 不再直接持有session，而是通过 _get_active_session() 动态获取

    def _get_active_session():
        """根据当前的代理模式，返回正确的Session对象 (现在是静态方法)"""
        if BaseClient._current_proxy_mode == "system":
            if BaseClient._system_session is None:
                BaseClient._system_session = requests.Session()
                print("[BaseClient] Created system-aware Session (will use system proxies).")
            return BaseClient._system_session
        else: # "none" 或 "custom" 模式都使用沙盒化的Session
            if BaseClient._sandboxed_session is None:
                BaseClient._sandboxed_session = requests.Session()
                BaseClient._sandboxed_session.trust_env = False
                print("[BaseClient] Created sandboxed Session (will ignore system proxies).")
            return BaseClient._sandboxed_session

    def _make_request(self, method, endpoint, **kwargs):
        """一个私有的辅助方法，用于向API发送请求。"""
        url = f"{self.base_url}{endpoint}"
        
        # 动态获取当前应该使用的session
        session = BaseClient._get_active_session()

        try:
            response = session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code >= 400:
                try: message = response.json().get('error', f"Srv Error {response.status_code}")
                except json.JSONDecodeError: message = f"Srv responded {response.status_code}"
                return False, message
            try: return True, response.json()
            except json.JSONDecodeError: return True, {}
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {e}"

    @staticmethod
    def update_proxy_settings(mode: str, url: str = None):
        """
        静态方法，全局更新代理配置。
        这是控制所有网络行为的唯一入口。
        
        :param mode: "none", "system", or "custom"
        :param url: 代理URL，仅在 mode="custom" 时使用
        """
        BaseClient._current_proxy_mode = mode
        
        # 只需要对沙盒化的Session进行操作，系统Session会自动处理
        # 先确保沙盒Session存在
        if BaseClient._sandboxed_session is None:
            BaseClient._sandboxed_session = requests.Session()
            BaseClient._sandboxed_session.trust_env = False
            print("[BaseClient] Created sandboxed Session on demand.")

        # 清理旧的自定义代理设置
        BaseClient._sandboxed_session.proxies.clear()
        
        if mode == "custom" and url:
            proxies = {"http": url, "https": url}
            BaseClient._sandboxed_session.proxies.update(proxies)
            print(f"[BaseClient] Proxy mode set to 'custom'. Using: {url}")
        elif mode == "system":
            print("[BaseClient] Proxy mode set to 'system'. Will use OS settings.")
        else: # "none"
            print("[BaseClient] Proxy mode set to 'none'. Direct connection.")
