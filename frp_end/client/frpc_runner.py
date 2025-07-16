# frpc_runner.py

import ctypes
import os
from datetime import datetime

def run_frpc_service(config_location, dll_path):
    """
    【核心】子进程只负责加载和运行主进程提供的DLL。
    """
    try:
        if not dll_path or not os.path.exists(dll_path):
            raise FileNotFoundError(f"核心组件DLL未在指定路径找到: {dll_path}")
        
        frpc = ctypes.CDLL(dll_path)
        c_config_location = ctypes.c_char_p(config_location.encode('utf-8'))
        frpc.StartFrpcService(c_config_location)
        print("[Child Process] frpc service has stopped.")
    except Exception as e:
        print(f"[FATAL ERROR in Child Process] An error occurred: {e}")
        with open("frpc_child_error.log", "a", encoding='utf-8') as f:
            f.write(f"{datetime.now()}: {e}\n")
        raise

