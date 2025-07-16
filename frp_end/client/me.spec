# -*- mode: python ; coding: utf-8 -*-
import os

# --- 配置区 ---
main_script = 'main.py'
exe_name = '萌！FRP高级客户端'
icon_file = 'app.ico'
version_file = 'version.txt'
upx_path = 'C:\\Program Files\\upx' 
# --- 配置区结束 ---

# 模块排除列表
excluded_modules = [
    'unittest', 'tkinter', 'doctest', 'pdb', 'lib2to3', 'asyncio',
    'setuptools', 'distutils', 'sqlite3', 'pydoc_data', 'bz2',
    'lzma'
]

# 要禁用的钩子，这是解决当前问题的关键
disabled_hooks = ['distutils', 'setuptools']

# Qt DLL 排除列表
qt_dlls_to_exclude = [
    'Qt6Bluetooth.dll', 'Qt6Nfc.dll', 'Qt6Positioning.dll', 
    'Qt6Sensors.dll', 'Qt6WebEngineCore.dll', 'Qt6WebEngineWidgets.dll', 
    'Qt6WebSockets.dll', 'Qt63D*',
]

# 额外数据文件
added_datas = [('windows.ico', '.')]
# 额外二进制文件
added_binaries = [('MoeFrpClient.mfc', '.')]

block_cipher = None

# --- 分析(Analysis)部分 ---
a = Analysis(
    [main_script],
    pathex=[],
    binaries=added_binaries,
    datas=added_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    # ↓↓↓↓ 关键中的关键 ↓↓↓↓
    disable_hooks=disabled_hooks,
    # ↑↑↑↑ 关键中的关键 ↑↑↑↑
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- DLL 过滤优化 ---
def is_excluded(filepath, exclusion_list):
    import fnmatch
    filename = os.path.basename(filepath)
    for pattern in exclusion_list:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

a.binaries = [x for x in a.binaries if not is_excluded(x[0], qt_dlls_to_exclude)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- EXE 构建部分 ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True if upx_path and os.path.exists(upx_path) else False,
    upx_dir=upx_path,
    #upx_args=['--lzma', '--best'],
    #upx_args=['--brute'],
    runtime_tmpdir=None,
    console=False,  # GUI应用，无黑框
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version=version_file,
)
