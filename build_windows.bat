@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f %%v in ('python get_version.py') do set VER=%%v
echo 版本：v%VER%
echo [1/2] 安装打包依赖...
python -m pip install --upgrade pip pyinstaller -r requirements.txt || goto :err
echo [2/2] 打包 Faster.exe ...
python fetch_wordlist.py || echo 警告：未能下载 BIP39 词表，助记词扫描将退化为启发式检测（联网后重新打包即可）
set ADD=
if exist bip39_english.txt set ADD=--add-data "bip39_english.txt;."
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name Faster --icon icon.ico --collect-submodules send2trash %ADD% faster_gui.py || goto :err
echo.
copy /y dist\Faster.exe dist\Faster-%VER%.exe >nul
echo 完成！成品：%~dp0dist\Faster-%VER%.exe
pause
exit /b 0
:err
echo 打包失败，请检查上面的错误信息（需要先安装 Python 3.9+，勾选 Add Python to PATH）。
pause
exit /b 1
