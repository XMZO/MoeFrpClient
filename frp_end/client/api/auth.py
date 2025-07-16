# api/auth.py
from .base import BaseClient

class AuthEndpoints(BaseClient):
    """处理用户注册、登录、会话等相关的API端点。"""

    def register(self, nickname, password, invite_code):
        """注册新用户。"""
        return self._make_request(
            'POST', '/api/register',
            json={'nickname': nickname, 'password': password, 'invite_code': invite_code}
        )
    
    def get_login_challenge(self, nickname):
        """请求登录用的一次性挑战码。"""
        return self._make_request('POST', '/api/login/get_challenge', json={'nickname': nickname})

    def login(self, nickname, password, version, version_secret, dll_hash, challenge, proof):
        """使用完整凭据进行登录。"""
        return self._make_request(
            'POST', '/api/login', 
            json={
                'nickname': nickname, 
                'password': password, 
                'version': version,
                'version_secret': version_secret,
                'dll_hash': dll_hash,
                'challenge': challenge,
                'proof': proof
            }
        )
    
    def perform_password_reset(self, nickname, reset_token, new_password):
        """执行密码重置。"""
        return self._make_request(
            'POST', '/api/perform_password_reset', 
            json={
                'nickname': nickname,
                'reset_token': reset_token,
                'new_password': new_password
            }
        )
    
    def check_session(self, token):
        """检查会话令牌是否有效。"""
        # 这个方法返回布尔值，所以我们在这里处理一下
        success, data = self._make_request(
            'POST', '/api/session/check',
            headers={'Authorization': f"Bearer {token}"}
        )
        return success and data.get('valid', False)

