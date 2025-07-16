pyinstaller --noconsole --onefile --name "FRP高级客户端" --icon="app.ico" --add-binary "frp_core-R.dll;." main.py

python -m nuitka --onefile --windows-disable-console --windows-icon-from-ico=app.ico --output-filename="FRP高级客户端.exe" --include-data-file=frp_core.dll=frp_core.dll --plugin-enable=pyside6 --clang --lto=yes --remove-output main.py


pyinstaller main.py --onefile --windowed --noconsole ^
 --add-binary "frp/frpc.exe;frp" ^
 --hidden-import=pyexpat ^
 --hidden-import=keyring.backends.Windows