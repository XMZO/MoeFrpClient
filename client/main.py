import sys
from PySide6.QtWidgets import (
    QApplication
)

from MainWindow import MainWindow
# --- 自定义模块导入 ---
from utils import GlobalCopyInterceptor
from frpc_runner import run_frpc_service

if __name__ == '__main__':
    if len(sys.argv) == 3:
        config_location_arg = sys.argv[1]
        dll_path_arg = sys.argv[2]
        run_frpc_service(config_location_arg, dll_path_arg)
    else:
        app = QApplication(sys.argv)
        window = MainWindow()
        interceptor = GlobalCopyInterceptor(window)
        app.installEventFilter(interceptor)
        window.show()
        sys.exit(app.exec())