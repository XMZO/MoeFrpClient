@echo off
rem 设置窗口标题
title PyInstaller - FRP客户端打包工具

echo.
echo ==========================================================
echo.
echo           FRP高级客户端 - PyInstaller 打包脚本
echo.
echo ==========================================================
echo.

:: --- 步骤 0: 检查并激活虚拟环境 ---

:: 定义虚拟环境的路径和激活脚本的路径
set VENV_DIR=venv_pack
set ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat

:: 检查虚拟环境目录是否存在
if not exist "%VENV_DIR%" (
    echo [错误] 虚拟环境目录 '%VENV_DIR%' 不存在！
    echo.
    echo [提示] 请先运行 `python -m venv %VENV_DIR%` 并安装依赖。
    goto end
)

:: 检查激活脚本是否存在
if not exist "%ACTIVATE_SCRIPT%" (
    echo [错误] 找不到虚拟环境的激活脚本: %ACTIVATE_SCRIPT%
    goto end
)

echo [步骤 1/4] 正在激活虚拟环境 '%VENV_DIR%'...
:: 调用激活脚本。这会修改当前命令行会话的环境变量，使后续命令在虚拟环境内执行。
call "%ACTIVATE_SCRIPT%"
echo [INFO] 虚拟环境已激活。
echo.

:: --- 步骤 1: 检查 spec 文件 ---

:: 定义spec文件名
set SPEC_FILE=me.spec

:: 检查 spec 文件是否存在
if not exist "%SPEC_FILE%" (
    echo [错误] 找不到配置文件: %SPEC_FILE%
    echo.
    echo [提示] 请确保您已经创建了 %SPEC_FILE% 文件。
    goto end
)

echo [步骤 2/4] 开始使用 PyInstaller (通过 %SPEC_FILE%) 进行打包...
echo.

:: 执行PyInstaller命令，使用 --clean 来清理旧的缓存
:: --noconfirm 会在覆盖旧文件时不弹出确认提示
pyinstaller --clean --noconfirm %SPEC_FILE%

:: 检查打包是否成功
if %errorlevel% neq 0 (
    echo.
    echo [错误] PyInstaller 打包失败！请检查上面的错误信息。
    goto end
)

echo.
echo [步骤 3/4] 打包成功！开始清理临时文件...
echo.

:: --- 修改后的清理逻辑 ---
:: 只删除 PyInstaller 生成的 build 文件夹
:: spec 文件被保留

if exist "build" (
    echo  - 正在删除 build 文件夹...
    rmdir /s /q "build"
)

echo.
echo [步骤 4/4] 清理完成！
echo.
echo ==========================================================
echo.
echo           ? 打包成功！?
echo.
echo           最终的EXE文件位于 `dist` 文件夹中。
echo           配置文件 `%SPEC_FILE%` 已保留。
echo.
echo ==========================================================
echo.

:end
pause