@echo off
rem ���ô��ڱ���
title PyInstaller - FRP�ͻ��˴������

echo.
echo ==========================================================
echo.
echo           FRP�߼��ͻ��� - PyInstaller ����ű�
echo.
echo ==========================================================
echo.

:: --- ���� 0: ��鲢�������⻷�� ---

:: �������⻷����·���ͼ���ű���·��
set VENV_DIR=venv_pack
set ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat

:: ������⻷��Ŀ¼�Ƿ����
if not exist "%VENV_DIR%" (
    echo [����] ���⻷��Ŀ¼ '%VENV_DIR%' �����ڣ�
    echo.
    echo [��ʾ] �������� `python -m venv %VENV_DIR%` ����װ������
    goto end
)

:: ��鼤��ű��Ƿ����
if not exist "%ACTIVATE_SCRIPT%" (
    echo [����] �Ҳ������⻷���ļ���ű�: %ACTIVATE_SCRIPT%
    goto end
)

echo [���� 1/4] ���ڼ������⻷�� '%VENV_DIR%'...
:: ���ü���ű�������޸ĵ�ǰ�����лỰ�Ļ���������ʹ�������������⻷����ִ�С�
call "%ACTIVATE_SCRIPT%"
echo [INFO] ���⻷���Ѽ��
echo.

:: --- ���� 1: ��� spec �ļ� ---

:: ����spec�ļ���
set SPEC_FILE=me.spec

:: ��� spec �ļ��Ƿ����
if not exist "%SPEC_FILE%" (
    echo [����] �Ҳ��������ļ�: %SPEC_FILE%
    echo.
    echo [��ʾ] ��ȷ�����Ѿ������� %SPEC_FILE% �ļ���
    goto end
)

echo [���� 2/4] ��ʼʹ�� PyInstaller (ͨ�� %SPEC_FILE%) ���д��...
echo.

:: ִ��PyInstaller���ʹ�� --clean ������ɵĻ���
:: --noconfirm ���ڸ��Ǿ��ļ�ʱ������ȷ����ʾ
pyinstaller --clean --noconfirm %SPEC_FILE%

:: ������Ƿ�ɹ�
if %errorlevel% neq 0 (
    echo.
    echo [����] PyInstaller ���ʧ�ܣ���������Ĵ�����Ϣ��
    goto end
)

echo.
echo [���� 3/4] ����ɹ�����ʼ������ʱ�ļ�...
echo.

:: --- �޸ĺ�������߼� ---
:: ֻɾ�� PyInstaller ���ɵ� build �ļ���
:: spec �ļ�������

if exist "build" (
    echo  - ����ɾ�� build �ļ���...
    rmdir /s /q "build"
)

echo.
echo [���� 4/4] ������ɣ�
echo.
echo ==========================================================
echo.
echo           ? ����ɹ���?
echo.
echo           ���յ�EXE�ļ�λ�� `dist` �ļ����С�
echo           �����ļ� `%SPEC_FILE%` �ѱ�����
echo.
echo ==========================================================
echo.

:end
pause