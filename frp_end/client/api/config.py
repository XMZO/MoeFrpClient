# api/config.py
from .base import BaseClient

class ConfigEndpoints(BaseClient):
    """处理用户配置（云端配置、订阅）相关的API端点。"""

    def request_config_ticket(self, token, config_content):
        """请求一个一次性的配置票据 (config_id)。"""
        return self._make_request(
            'POST', '/api/request_config_ticket', 
            headers={'Authorization': f"Bearer {token}"},
            json={'config_content': config_content}
        )

    def get_all_configs(self, token):
        """获取用户的所有配置（个人配置和订阅）。"""
        return self._make_request('GET', '/api/configs', headers={'Authorization': f"Bearer {token}"})

    def save_all_configs(self, token, payload):
        """
        以完全同步的方式保存所有用户配置。
        :param payload: 包含 'personal_configs' 和 'subscriptions' 的字典。
        """
        return self._make_request(
            'POST', '/api/configs',
            headers={'Authorization': f"Bearer {token}"},
            json=payload
        )
