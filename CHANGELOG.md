# 更新日志

版本号规则：`主版本.次版本.修订`，唯一来源是 `faster.py` 顶部的 `__version__`。

## v0.4.0 —— 更新与加固、程序签名、基线对比、排除设置、新外观
**新的检查（都接入“一键诊断”，每一项都带可以直接执行的按钮）**
- **补丁与更新检查**（`faster_patch.py`）：Windows 最近一次补丁安装时间、是否需要重启、（联网）待安装的更新；macOS 自动更新开关、（联网）待安装的更新；Linux 可更新软件包数量与其中的安全更新、软件包索引是否过期、需要重启、（联网）dnf 更新；已停止维护的软件（Flash / QuickTime / Silverlight / Python 2 / Java 6·7）。
- **程序签名验证**（`faster_sig.py`）：开机启动项 + 从用户目录运行的进程（深度：所有运行中的进程）；Windows Authenticode、macOS codesign（ad-hoc 视为无签名）、Linux 软件包归属；规则：签名被破坏→严重，从临时目录运行的无签名进程→严重，无签名的启动项→注意。动作：停用启动项 / 结束进程 / 复制 SHA-256。
- **基线对比**（`faster_baseline.py`）：记录启动项、计划任务、对外监听端口、hosts、管理员账户、SSH 授权密钥、已安装程序，之后只报告新增；新增管理员账户 / SSH 密钥 → 严重。动作：设为基线 / 接受变化 / 停用新增的启动项。
- **安全加固检查**（`faster_harden.py`）：Windows（UAC、自动登录、远程桌面、SMBv1、Secure Boot、BitLocker）、macOS（FileVault、自动登录、访客账户、屏幕锁、Time Machine）、Linux（磁盘加密、SSH root 登录/密码登录、自动安全更新、屏幕锁、Secure Boot）、以及各系统通用的对外开放高风险端口（Telnet / FTP / 远程桌面 / VNC）。修复方式：打开对应系统设置，或给出可复制的命令（需要管理员权限的修改不会替你做）。
- 诊断分为 **5 大类**：性能 / 存储 / 安全 / 加固与更新 / 钱包；“诊断”页签新增 3 个子页：**程序签名**、**基线对比**、**加固与更新**；新增 3 个动作：`copy_text`、`set_baseline`、`accept_baseline`，并把“打开系统设置”整理成可测试的命令表。
**排除设置**
- “大文件”和“重复文件”页顶部新增“排除”面板：勾选文件类型分组（视频 / 图片 / 音频 / 文档 / 压缩包 / 磁盘镜像·虚拟机）+ 自定义扩展名，用**文件夹选择器**添加要排除的文件夹（含子文件夹）；两个页面各自独立保存（`~/.faster/settings.json`），不会冲掉语言等其它设置；扫描结束时在底部提示“已排除：…”；深度诊断也遵守这些设置。
**外观**
- 新增 `faster_theme.py`：统一配色 / 字体 / 控件样式（clam 主题；macOS 保持原生）；概览页横幅 + 资源卡片；诊断页健康分仪表盘 + 分类分数 + 彩色卡片；表格斑马纹；主要按钮高亮；主题设置任何一步失败都静默退回默认外观。
**质量**
- 新增 `tests/test_v04.py`（排除规则、签名风险规则与状态映射、基线差异与存取、补丁/加固结果结构与各级别阈值、修复→动作的转换、系统设置命令表一致性、主题的容错），GUI 冒烟测试覆盖排除面板与 3 个新子页（中文 + 英文）；约 150 条英文译文；`faster_diag.parse_exe` 移到 `faster_sig`。
- Added: updates & hardening checks, program signature verification, baseline comparison, per-page exclusions for large files / duplicates, and a refreshed look.

## v0.3.1 —— 诊断中心：一键诊断，每个问题都有可以直接执行的按钮
- **“诊断”页签（原“性能诊断”）扩展成全面诊断**，覆盖 **性能 / 存储 / 安全 / 钱包** 四大类：内存、交换、CPU、启动项、运行时间、电源计划；磁盘、垃圾、回收站；系统防护（防火墙 / Defender / Gatekeeper / SIP）、可疑启动项、挖矿木马、hosts；云同步目录里的钱包文件与明文密钥、BIP39 词表。勾选“深度诊断”另查大文件、重复文件、整个主目录的钱包与密钥、深度风险扫描。
- **结果做成卡片**：级别（严重 / 注意 / 提示 / 良好）+ 现状 + 建议 + **动作按钮**；总健康分 + 四类分数。动作分两种：**直接执行**（清理垃圾、清空回收站/工具回收站、停用可疑启动项、停用影响高的启动项、结束进程、打开系统安全/防火墙/电源设置、下载词表……都先确认，完成后显示“✓ 已处理”）和**跳转**（到对应页面并自动开始扫描，可预填参数）。
- **目标页面同样列出建议操作**：垃圾清理 / 还原中心 / 启动项 / 启动影响 / 后台进程 / 风险扫描 / 钱包安全 页顶部新增“💡 建议操作（来自上次诊断）”面板，只显示本页可直接执行且未处理的动作，没有就隐藏。
- “概览”页的“一键体检”换成“🔍 一键诊断”；“诊断”页签挪到第二位；诊断可取消，并显示当前检查的项目。
- 重构：`find_duplicates` 移到核心模块；系统防护与 hosts 检查拆成结构化函数（`security_posture_items`、`hosts_entries`），旧的风险扫描行为不变；新增 `cloud_roots()`。
- 测试：新增 `tests/fake_tk.py`（假 tkinter）和 `tests/test_gui_smoke.py`——不需要显示器，就能把诊断中心、各页签、所有动作按钮在中文/英文下真正跑一遍；另新增动作结构、页面归属、“每个动作都有处理函数”、安全/钱包/存储诊断映射等 20 多项测试；新增约 110 条英文译文。
- Added: a full diagnosis center (performance / storage / security / wallet) with per-problem action buttons and suggested-action panels on the target pages.

## v0.3.0 —— 性能诊断、前后对比、可取消的扫描、还原中心
**更快**
- 新增“性能诊断”页签：**瓶颈诊断**（磁盘/内存/交换/CPU/启动项/运行时间/垃圾/Windows 电源计划 → 健康分 + 建议，可一键跳转到处理页）、**启动影响**（按正在运行的进程估算每个启动项的内存与平均 CPU，排序后可直接停用，明确标注为估算）、**前后对比**（状态快照历史，可任选两条对比）。
- 清理垃圾、停用启动项、结束进程时**自动记录“前/后”快照**，完成后直接显示效果（磁盘剩余、内存占用、启动项…）。
- 命令行新增菜单 `10`：性能诊断（只读）。
**更好用**
- **取消与进度**：垃圾扫描、大文件、重复文件、钱包文件、区块链数据、密钥泄露扫描、诊断均可取消，底部显示当前目录与计数；取消后保留部分结果。（新增 `faster_task.py`）
- **还原中心**：统一查看/还原被 Faster 移走或停用的东西——工具回收站里的文件（还原到原位置，同名不覆盖）、系统回收站记录、已停用的启动项；可永久删除/清空工具回收站。新增“还原记录”（`~/.faster/trash/ledger.jsonl`），删除文件时自动记录原路径。
- 提示文字改为如实说明：文件移入回收站不会立即释放磁盘空间，清空后才会。
**质量**
- 新增 `faster_diag.py` 与 `tests/test_diag.py`（诊断阈值与健康分、快照对比、启动项命令解析与运行匹配、任务取消、还原记录的移除/还原/冲突/永久删除/清空/修剪，钱包文件永不入账）；新增约 110 条英文译文并通过 `tools/i18n_check.py`。
- Added: performance diagnostics, startup impact estimate, before/after snapshots, cancellable scans with progress, and a Restore center.

## v0.2.3 —— 修复 Windows 上的编码问题
- 修复在 Windows（默认 cp1252 编码）上运行测试时，打印中文会触发 `UnicodeEncodeError`，导致 CI 失败：测试里的子进程统一使用 UTF-8。
- 程序本身也加固：控制台编码无法显示某些字符时，改为显示 `?`，不再抛异常（例如英文版 Windows 控制台里用中文界面运行）。
- 测试里不再写死版本号。
- Fixed: Windows console encoding errors in tests/CLI.

## v0.2.2 —— 多语言（中文 / English）+ 英文 README
- **语言选择**：概览页顶部“语言 / Language”下拉框（跟随系统 / 简体中文 / English），切换后可立即重启；命令行菜单 `9`、`--lang en|zh`、环境变量 `FASTER_LANG`、设置文件 `~/.faster/settings.json` 同样可用。默认跟随系统语言。
- 全部界面、命令行、日志、扫描结果、定时清理与管理员辅助进程均已翻译（528 条文案）；管理员辅助进程沿用同一语言。
- 新增 `faster_i18n.py` / `faster_i18n_en.py`（以中文原文为键的目录，缺译文时退回中文）；新增语言只需补一个 `faster_i18n_xx.py`。
- 新增 `tools/i18n_check.py` 与 `tests/test_i18n.py`：检查译文是否齐全、占位符是否一致、有没有漏包的中文字符串，并验证英文模式下等级/排序/剪贴板等逻辑不受影响。
- 新增 `README.en.md`（英文版 README，末尾同样保留 FAQ）；中文 README 顶部增加语言切换链接。
- 修正 README 中打包产物文件名（带版本号）与版本管理说明。
- Added: UI language selection (Chinese / English) and an English README.

## v0.2.1 —— 修复密钥扫描误报 + 助记词表查看器
**问题**：扫描 Python 项目时出现几百条结果。原因（均已修复，并加了回归测试）：
- 没有 BIP39 词表时，用“关键词 + 一串英文单词”猜助记词，对注释/文档极易误报 → **现在没有词表就不猜**，只检测私钥，并在界面明确提示“本次没有检测助记词”。
- 文件名含 `seed` / `mnemonic` 的代码文件（如 `seed_utils.py`）被当成“文件名可疑” → 现在只对笔记/文档/图片类文件按名字提示，且不再匹配单独的 `seed`。
- 64 个数字的普通数组（查找表、S-box 等）被当成 Solana 密钥 → 现在要求整个文件就是该数组，或紧跟 `secret/keypair/私钥` 字样。
- 64 位十六进制只要附近出现“secret”就报 → 现在必须**紧跟**在 `private key / 私钥` 之后。
- 默认不再读取 `.py .js .ts .sh .html .xml .yml .ini` 等代码/配置文件（可勾选“同时扫描代码/配置文件”，此时只报强证据）；自动跳过 Python 虚拟环境（含 `pyvenv.cfg`）、`site-packages`、`vendor` 等依赖目录。
- 公开的测试助记词（BIP39 测试向量、Hardhat/Anvil/Ganache 默认值）降级为“提示”。
- 结果支持按级别筛选，最多显示 500 项。

**新增**：
- 「查看助记词表」：显示 2048 个单词（可按单词片段/序号搜索、复制全部），并显示来源、文件路径、SHA-256、校验状态。词表缺失时可一键下载并校验；扫描时若没有词表会询问是否下载。
- 仓库不再忽略 `bip39_english.txt`：运行一次 `python fetch_wordlist.py` 后可把它提交进仓库，让打包不依赖网络。

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
