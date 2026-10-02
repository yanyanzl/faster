# Faster v0.2.0 · 打包说明

成品：
- Windows：`Faster-0.2.0.exe`（单文件，双击运行）
- macOS：`Faster-0.2.0.dmg`（打开后把 Faster 拖进“应用程序”）

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

## 版本管理（v0.2.0 作为基础版本）
- 版本号只改 `faster.py` 顶部的 `__version__`；界面标题、`--version`、dmg/exe 文件名、Mac 的应用信息都会自动跟随。
- 把当前代码固化为基线（建议）：
  ```
  git init && git add . && git commit -m "v0.2.0 baseline"
  git tag v0.2.0
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

## v0.2 钱包安全功能说明（“钱包安全”页签）
| 子页 | 做什么 | 要点 |
|---|---|---|
| 钱包文件 | 找出本机钱包文件并标注云同步风险 | 这些文件会被所有清理功能自动跳过 |
| 区块链数据 | 识别节点/钱包数据目录和可重新同步的大小 | 只提示，不自动删除 |
| 密钥泄露扫描 | 找明文保存的助记词/私钥 | 不回显内容；图片/截图、便签数据库、PDF 不在范围内 |
| 挖矿检测 | 找挖矿木马 | 你自己运行的矿工也会被标出（高危后面有说明） |
| 剪贴板守护 | 发现地址被替换；校验收款地址 | 需手动开启，只在内存里记录 |

**BIP39 词表**：助记词的“校验和验证”需要官方英文词表。打包版会在打包时自动下载并内置（`fetch_wordlist.py`，下载后做结构 + 官方测试向量双重校验，不通过就不用）。
从源码运行时，在“密钥泄露扫描”页点“获取 BIP39 词表”即可；没有词表时会退化为“关键词 + 单词数”的启发式检测（结果为中危、未校验）。

**运行测试**：`python -m unittest discover -s tests -v`

**重要提醒**：Faster 永远不会向你索要助记词/私钥。扫描发现明文助记词/私钥时，最稳妥的做法是：把资产转到全新生成的钱包，新助记词抄写在纸上离线保存，再删除或加密旧的明文文件。固态硬盘上的“删除”不保证数据无法恢复。

## FAQ
  ```
  macOS 的 Gatekeeper 可能拦截：Faster 还没有 Apple 的开发者签名和公证，所以系统无法确认它没问题。不是程序有问题，用下面任一方法放行即可。

  方法一：系统设置里放行（macOS 15 Sequoia 及以后）
  先把 Faster 从 dmg 拖进「应用程序」。
  双击打开一次，出现上面的提示后点「完成」或「好」。
  打开「系统设置 → 隐私与安全性」，往下滚动，找到「已阻止使用 Faster」，点旁边的「仍要打开」。
  输入开机密码或用触控 ID 确认，之后再点「打开」。
  这个操作只需要做一次，以后可以正常双击打开。

  方法二：一条命令去掉隔离标记（最省事）
  打开「终端」，执行：
  xattr -cr /Applications/Faster.app

  然后正常双击打开。如果你的 Faster.app 不在「应用程序」里，就把路径换成实际位置。这条命令只是去掉系统给下载文件打的「来自网络」标记，不会修改程序本身。

  方法三：较早的 macOS（14 及以前）
  在「应用程序」里右键 Faster → 打开 → 再点「打开」，同样只需一次。
  ```