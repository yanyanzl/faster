# 更新日志

版本号规则：`主版本.次版本.修订`，唯一来源是 `faster.py` 顶部的 `__version__`。

## v0.1.1 —— 更名为 Faster
- 程序更名为 **Faster**：窗口标题、exe / app / dmg 名称、文件名（faster.py / faster_gui.py）、定时任务名称全部更新。
- 升级兼容：自动把旧数据目录 `~/.pc_optimizer` 迁移为 `~/.faster`（含启动项备份清单），并清理 v0.1.0 创建的旧定时任务，重新点一次“保存并启用定时任务”即可。

## v0.1.0 —— 基础版本（Baseline）
后续所有开发都以此为起点，改动请记录在本文件。

**存储**：垃圾/缓存清理、大文件列表（大→小自选）、重复文件查找
**速度**：启动项管理（可恢复）、后台进程结束、卸载程序
**安全**：启发式风险扫描（进程/端口/持久化/hosts/临时目录/防护状态）、调用 Defender / ClamAV 查杀
**界面**：tkinter 图形界面 + 命令行版
**自动清理**：每天/每周/每月定时（Windows 计划任务 / macOS launchd / Linux systemd 或 cron）、自定义文件夹规则
**管理员权限**：按需提权（系统级清理、系统级启动项、完整端口扫描、macOS 移除 /Applications 应用），Windows 可一键以管理员重启
**打包**：PyInstaller 脚本 + GitHub Actions 云端打包（Windows exe / macOS dmg）
