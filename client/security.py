# security.py
import base64
import os
import platform
import subprocess
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

# --- 加密管理器 ---
class EncryptionManager:
    # Keyring 服务名，用于在系统中唯一标识应用
    _KEYRING_SERVICE_NAME = "FRP_Client_Tool_V3_Keyring"
    _KEYRING_USERNAME = "encrypted_master_key_bundle"

    # Argon2id KDF 参数
    _ITERATIONS = 3
    _MEMORY_COST = 64 * 1024
    _PARALLELISM = 2
    _HASH_LEN = 32

    def __init__(self):
        self.master_key = self._load_or_create_master_key()
        if self.master_key:
            self.cipher_suite = Fernet(self.master_key)
        else:
            raise RuntimeError("无法初始化或从系统密钥环中获取主加密密钥。")

    def _get_machine_guid(self):
        """获取机器唯一ID作为加密主密钥的'密码'"""
        try:
            if platform.system() == "Windows":
                guid = subprocess.check_output('wmic csproduct get uuid', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
            elif platform.system() == "Linux":
                if os.path.exists('/etc/machine-id'):
                     with open('/etc/machine-id', 'r') as f: guid = f.read().strip()
                else: guid = subprocess.check_output('hostid', shell=True, stderr=subprocess.DEVNULL).decode().strip()
            elif platform.system() == "Darwin":
                 guid = subprocess.check_output("ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'", shell=True, stderr=subprocess.DEVNULL).decode().strip()
            else: guid = os.getlogin() + platform.node()
            return guid
        except Exception: return "fallback_guid_string_if_all_fails"

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """使用 Argon2id 从密码和盐派生密钥"""
        kdf = Argon2id(
            salt=salt,
            length=self._HASH_LEN,
            iterations=self._ITERATIONS,
            lanes=self._PARALLELISM,
            memory_cost=self._MEMORY_COST,
        )
        key = kdf.derive(password)
        return base64.urlsafe_b64encode(key)

    def _load_or_create_master_key(self):
        """从系统密钥环加载“主密钥包”，然后用机器码解密它。"""
        try:
            # 1. 派生“保护密钥”
            protector_salt = b'frp-tool-protector-salt-v4-keyring'
            machine_password = self._get_machine_guid().encode()
            protector_key = self._derive_key(machine_password, protector_salt)
            protector_cipher = Fernet(protector_key)

            # 2. 从系统密钥环获取“加密的主密钥包”
            encrypted_bundle_str = keyring.get_password(
                self._KEYRING_SERVICE_NAME,
                self._KEYRING_USERNAME
            )

            if encrypted_bundle_str:
                try:
                    # 3. 解密“包”以获取真正的“主密钥”
                    encrypted_bundle = encrypted_bundle_str.encode()
                    decrypted_master_key = protector_cipher.decrypt(encrypted_bundle)
                    return decrypted_master_key
                except Exception:
                    # 解密失败（机器变了），清除所有凭证
                    self.delete_all_credentials()
            
            # 4. 如果没获取到，则创建新密钥
            new_master_key = Fernet.generate_key()
            encrypted_bundle = protector_cipher.encrypt(new_master_key)
            
            # 5. 将“加密的主密钥包”存入密钥环
            keyring.set_password(
                self._KEYRING_SERVICE_NAME,
                self._KEYRING_USERNAME,
                encrypted_bundle.decode() # keyring 存储字符串
            )
            return new_master_key
        except Exception as e:
            print(f"!!! FATAL ERROR in _load_or_create_master_key: {e}")
            import traceback
            traceback.print_exc()
            return None

    def encrypt(self, data: bytes) -> bytes:
        return self.cipher_suite.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        return self.cipher_suite.decrypt(token)
    
    def delete_master_key_from_keyring(self):
        """只删除密钥环中的主密钥"""
        try:
            keyring.delete_password(self._KEYRING_SERVICE_NAME, self._KEYRING_USERNAME)
        except Exception: pass
    
    def delete_all_credentials(self):
        """用于清除所有本地凭证"""
        # 从密钥环中删除
        try:
                self.delete_master_key_from_keyring()
        except Exception: pass