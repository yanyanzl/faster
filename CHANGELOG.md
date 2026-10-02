# 更新日志

版本号规则：`主版本.次版本.修订`，唯一来源是 `faster.py` 顶部的 `__version__`。

## v0.2.0 —— 钱包安全（5 个本地功能）
全部在本地运行，不联网（仅“下载 BIP39 词表”除外），不接触/保存/上传私钥与助记词。新增模块 `faster_crypto.py`，界面新增“钱包安全”页签（5 个子页）。
1. **钱包文件保护**：识别 wallet.dat、keystore（UTC--）、Exodus/Electrum 钱包、主流浏览器钱包扩展数据等；垃圾清理、大文件、重复文件、自动清理、废纸篓清空、`safe_remove` 一律跳过。“钱包文件”页可查看清单，并标出位于云同步目录（OneDrive/iCloud/Dropbox 等）的钱包。
2. **助记词 / 私钥泄露扫描**：BIP39 助记词（词表 + 校验和验证，12/15/18/21/24 词）、WIF 私钥、xprv/yprv/zprv、Solana 密钥文件、带上下文的 64 位十六进制私钥；覆盖文本/Office 文件；只报位置与类型，不回显内容；位于云同步目录自动升为高危。缺少词表时退化为启发式检测。
3. **挖矿木马检测**：进程名/命令行特征、矿池端口连接、临时目录高 CPU 进程；启动项/计划任务/cron 里的挖矿命令并入“风险扫描”。
4. **剪贴板地址劫持检测**：BTC/ETH(EVM)/TRON/LTC/DOGE/SOL 地址（含校验位验证）；短时间内被替换提醒，“首尾相同、中间不同”判为高危；另有“校验收款地址”小工具。仅在内存中保存。
5. **区块链数据目录识别**：Bitcoin/Litecoin/Dogecoin Core、geth、Monero、IPFS、Reth、Erigon、Lighthouse、Electrum、Exodus；列出总大小、可重新同步部分与钱包相关部分。只提示，不自动删除。
- 新增单元测试（`python -m unittest discover -s tests`，CI 打包前自动运行）、`fetch_wordlist.py`（打包时下载并校验 BIP39 词表）。

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
