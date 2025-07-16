import base64
import os
import platform
import subprocess
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


class EncryptionManager:

    _KEYRING_SERVICE_NAME = "FRP_Client_Tool_V3_Keyring"
    _KEYRING_USERNAME = "encrypted_master_key_bundle"


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

        try:

            protector_salt = b'frp-tool-protector-salt-v4-keyring'
            machine_password = self._get_machine_guid().encode()
            protector_key = self._derive_key(machine_password, protector_salt)
            protector_cipher = Fernet(protector_key)


            encrypted_bundle_str = keyring.get_password(
                self._KEYRING_SERVICE_NAME,
                self._KEYRING_USERNAME
            )

            if encrypted_bundle_str:
                try:

                    encrypted_bundle = encrypted_bundle_str.encode()
                    decrypted_master_key = protector_cipher.decrypt(encrypted_bundle)
                    return decrypted_master_key
                except Exception:

                    self.delete_all_credentials()


            new_master_key = Fernet.generate_key()
            encrypted_bundle = protector_cipher.encrypt(new_master_key)


            keyring.set_password(
                self._KEYRING_SERVICE_NAME,
                self._KEYRING_USERNAME,
                encrypted_bundle.decode()
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

        try:
            keyring.delete_password(self._KEYRING_SERVICE_NAME, self._KEYRING_USERNAME)
        except Exception: pass

    def delete_all_credentials(self):


        try:
                self.delete_master_key_from_keyring()
        except Exception: pass