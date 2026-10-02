#!/bin/bash
# 在 macOS 上运行：  bash build_mac.sh
# 会自动创建独立虚拟环境(.venv-build)，不会改动系统 / Homebrew 的 Python。
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
VER=$(grep -m1 '^__version__' faster.py | cut -d'"' -f2)
echo "版本：v$VER"

if ! "$PY" -c "import tkinter" 2>/dev/null; then
  echo "× 当前 Python 缺少 tkinter（图形界面需要）。请二选一后重试："
  echo "    brew install python-tk        # Homebrew 用户"
  echo "    或安装 https://www.python.org/downloads/macos/ 的官方 Python（自带 tkinter）"
  exit 1
fi

echo "[1/4] 创建虚拟环境..."
rm -rf .venv-build
"$PY" -m venv .venv-build
source .venv-build/bin/activate

echo "[2/4] 安装打包依赖..."
python -m pip install --upgrade pip pyinstaller -r requirements.txt

echo "[3/4] 打包 Faster.app ..."
python fetch_wordlist.py || echo "警告：未能下载 BIP39 词表，助记词扫描将退化为启发式检测（联网后重新打包即可）"
ADD=()
if [ -f bip39_english.txt ]; then ADD=(--add-data "bip39_english.txt:."); fi
python -m PyInstaller --noconfirm --clean --windowed --name Faster --icon icon.icns \
  --osx-bundle-identifier com.faster.app --collect-submodules send2trash "${ADD[@]}" faster_gui.py

echo "写入版本号并重新签名..."
PL=dist/Faster.app/Contents/Info.plist
for k in CFBundleShortVersionString CFBundleVersion; do
  /usr/libexec/PlistBuddy -c "Set :$k $VER" "$PL" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :$k string $VER" "$PL"
done
codesign --force --deep --sign - dist/Faster.app

echo "[4/4] 生成 dmg 安装镜像..."
rm -rf dist/dmg && mkdir -p dist/dmg
cp -R dist/Faster.app dist/dmg/
ln -s /Applications dist/dmg/Applications
hdiutil create -volname "Faster" -srcfolder dist/dmg -ov -format UDZO "dist/Faster-$VER.dmg"

deactivate
echo "完成！成品：$(pwd)/dist/Faster-$VER.dmg  以及  dist/Faster.app"
