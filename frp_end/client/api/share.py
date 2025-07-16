# api/share.py
from .base import BaseClient

class ShareEndpoints(BaseClient):
    """处理创建、管理和使用分享相关的API端点。"""

    def create(self, token, share_data):
        """从用户配置创建新的分享。"""
        return self._make_request(
            'POST', '/api/share/create',
            headers={'Authorization': f"Bearer {token}"},
            json=share_data
        )

    def list_my(self, token):
        """列出用户创建的所有分享。"""
        return self._make_request('GET', '/api/share/list', headers={'Authorization': f"Bearer {token}"})

    def revoke(self, token, share_id):
        """撤销（删除）一个用户创建的分享。"""
        return self._make_request(
            'POST', '/api/share/revoke',
            headers={'Authorization': f"Bearer {token}"},
            json={'share_id': share_id}
        )

    def get_public_info(self, share_id):
        """获取分享的公开信息（用于订阅）。"""
        return self._make_request('GET', f'/api/share/get_public_info/{share_id}')

    def use(self, share_id, user_params):
        """使用分享以获取最终组合好的TOML数据。"""
        return self._make_request(
            'POST', '/api/share/use',
            json={'share_id': share_id, 'user_params': user_params}
        )
