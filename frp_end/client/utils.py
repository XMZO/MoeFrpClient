# utils.py



import hashlib
import os
import sys


def resource_path(relative_path):
    """ 获取资源的绝对路径, 兼容开发模式和PyInstaller打包后的单文件模式 """
    try:
        # PyInstaller 会创建一个临时文件夹 _MEIPASS，并将所有数据文件放在那里
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是在打包模式下运行，就使用当前文件的路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# SHA-256哈希计算函数
def get_file_sha256(filepath):
    """计算文件的SHA-256哈希值"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # 逐块读取，防止大文件撑爆内存
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def _get_value_from_path(data, path):
    """
    根据点(.)分隔的路径字符串，从嵌套的字典或列表中提取值。
    例如: get_value_from_path(data, "data.0.urls.regular")
    """
    try:
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, list):
                # 如果是列表，将键转换为整数索引
                current = current[int(key)]
            elif isinstance(current, dict):
                # 如果是字典，直接用键获取
                current = current[key]
            else:
                # 如果路径中间遇到非字典/列表类型，则无法继续
                return None
        return current
    except (KeyError, IndexError, ValueError, TypeError):
        # 任何路径错误（键不存在、索引越界等）都安全返回None
        return None