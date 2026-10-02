# Faster v0.1.1 · 打包说明

成品：
- Windows：`Faster-0.1.1.exe`（单文件，双击运行）
- macOS：`Faster-0.1.1.dmg`（打开后把 Faster 拖进“应用程序”）

PyInstaller 不能跨系统打包——**Windows 版必须在 Windows 上打，Mac 版必须在 Mac 上打**。两种做法任选：

## 方法 A：GitHub 云端一键打包（推荐，不需要自己装环境）
1. 在 GitHub 新建一个仓库，把本文件夹的**全部内容**（含隐藏的 `.github` 目录）上传。
2. 打开仓库的 **Actions → Build Faster → Run workflow**。
3. 约 3~5 分钟后，在运行记录底部的 **Artifacts** 下载 `Faster-windows` 和 `Faster-macos`。
   （想发布成 Release：打个 tag，如 `git tag v1.0.0 && git push --tags`，会自动生成下载页。）

## 方法 B：在自己电脑上打包
- **Windows**：安装 Python 3.9+（勾选 Add to PATH）→ 双击 `build_windows.bat` → `dist\Faster.exe`
- **macOS**：终端运行 `bash build_mac.sh` → `dist/Faster.dmg`。脚本会自动建虚拟环境（不会遇到 externally-managed-environment 报错）。
  若提示缺少 tkinter：Homebrew 用户执行 `brew install python-tk`，或安装 python.org 的官方 Python。

## 首次运行的系统提示（未购买代码签名证书时都会出现，属正常）
- **Windows SmartScreen**：点“更多信息” → “仍要运行”。个别杀毒软件可能误报 PyInstaller 程序，可自行加入信任；
  想彻底消除需购买代码签名证书对 exe 签名。
- **macOS**：提示“无法验证开发者/已损坏”时，在“应用程序”中**右键 → 打开**；仍不行则终端执行：
  `xattr -cr /Applications/Faster.app`。（正式分发需 Apple Developer 账号签名+公证。）
- **Intel 芯片的 Mac**：`macos-latest` 产出的是 Apple 芯片版。Intel 版请用方法 B 在 Intel Mac 上打包。

## 使用注意
- “自动清理”的定时任务记录的是程序所在路径。**启用定时任务后请不要移动/重命名程序**；若移动了，重新点一次“保存并启用定时任务”。
- macOS 若要自动清理“文稿/下载”等文件夹，需在 系统设置 → 隐私与安全性 → 完全磁盘访问权限 中添加 Faster。
- 无界面执行一次清理：`Faster.exe --auto-clean`（加 `--dry-run` 为试运行）。

## 版本管理（v0.1.1 作为基础版本）
- 版本号只改 `faster.py` 顶部的 `__version__`；界面标题、`--version`、dmg/exe 文件名、Mac 的应用信息都会自动跟随。
- 把当前代码固化为基线（建议）：
  ```
  git init && git add . && git commit -m "v0.1.1 baseline"
  git tag v0.1.1
  ```
  之后每个新功能走分支/提交，并在 `CHANGELOG.md` 记一笔；推送 `v0.2.0` 之类的 tag 会让 GitHub 自动打包并发布。

## 管理员权限怎么用
程序平时以普通用户运行（更安全），**只在需要时**单独提权，界面上带 🛡 的按钮或弹窗会引导你：

| 需要管理员的功能 | 怎么触发 |
|---|---|
| 系统级垃圾清理（Windows 系统临时/更新缓存、macOS /Library/Caches、Linux apt 缓存/日志） | 垃圾清理页 → 🛡 管理员清理系统级垃圾 |
| 停用/恢复系统级启动项（HKLM、/Library/LaunchAgents） | 正常点“停用选中”，失败时会提示“是否授权重试” |
| 完整的端口/进程扫描 | 风险扫描页 → 🛡 管理员权限扫描 |
| macOS 移除 /Applications 里的应用 | 卸载时失败会提示授权重试 |

授权窗口：Windows 为 UAC 弹窗；macOS 为系统密码框；Linux 为 polkit 窗口（需已装 pkexec）。
**Windows 想一次授权全部功能**：概览页点“以管理员身份重新启动”。
提权只执行内置的固定动作，不会执行任意命令。定时自动清理仍只清理用户级内容，不需要管理员。
