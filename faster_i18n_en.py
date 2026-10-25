# -*- coding: utf-8 -*-
"""English translations. Key = the Chinese source text; placeholders {0}{1}.. must match."""

CATALOG = {
    "钱包文件":
        "Wallet files",
    "Exodus 钱包":
        "Exodus wallet",
    "Electrum 钱包":
        "Electrum wallet",
    "以太坊/EVM 密钥库":
        "Ethereum/EVM keystore",
    "比特币系钱包":
        "Bitcoin-family wallet",
    "Monero 等钱包密钥文件":
        "Monero etc. wallet key file",
    "坚果云":
        "Nutstore",
    "百度网盘":
        "Baidu Netdisk",
    "内置于程序（打包时从官方仓库下载并校验）":
        "Bundled with the app (downloaded from the official repo and verified at build time)",
    "BIP39 词表已就绪（校验通过）。":
        "BIP39 word list is ready (verification passed).",
    "高危":
        "High",
    "中危":
        "Medium",
    "提示":
        "Info",
    "浏览器钱包扩展 · {0}":
        "Browser wallet extension · {0}",
    "随源码目录提供":
        "Shipped with the source folder",
    "下载的词表未通过校验，已丢弃。":
        "The downloaded word list failed verification and was discarded.",
    "该地址不在最近 30 分钟的复制记录里（监控未开启或已过期），无法比对。":
        "This address is not in the last 30 minutes of copy history (monitoring was off or it has expired), so it cannot be compared.",
    "钱包文件通常在别处，请先在 Monero 软件里确认钱包位置":
        "The wallet file is usually elsewhere; check the wallet location in the Monero app first",
    "blocks 里可能有只存在于本机的固定内容，删除前请确认":
        "blocks may contain pinned content that exists only on this machine; confirm before deleting",
    "validators/secrets 含验证者密钥，切勿删除":
        "validators/secrets contain validator keys. Never delete them",
    "只有钱包，没有区块数据":
        "Wallets only, no blockchain data",
    "已下载到本机 ":
        "Downloaded to this machine: ",
    "下载失败：{0}":
        "Download failed: {0}",
    "疑似私钥(64位十六进制)":
        "Suspected private key (64 hex chars)",
    "“私钥/private key”字样后紧跟 64 位十六进制串":
        "64 hex characters right after the words “private key”",
    "这不是有效的区块链地址（格式或校验位不对）——请检查是否复制完整。":
        "This is not a valid blockchain address (wrong format or checksum). Please check that you copied all of it.",
    "这个地址之前被判定为“疑似替换”的地址，请勿使用，并立即查杀电脑。":
        "This address was previously flagged as a “suspected replacement”. Do not use it, and scan your computer immediately.",
    "正常":
        "OK",
    "与你最近复制的地址完全一致。":
        "Identical to the address you copied recently.",
    "与你复制的地址首尾相同但中间不一致——疑似被替换（剪贴板劫持/地址投毒）。请重新复制并逐位核对。":
        "Same first and last characters as the address you copied, but different in the middle — suspected replacement (clipboard hijacking / address poisoning). Copy it again and compare every character.",
    "比特币私钥(WIF)":
        "Bitcoin private key (WIF)",
    "校验通过的 WIF 私钥，长度 {0}":
        "Valid WIF private key (checksum passed), length {0}",
    "Solana 密钥文件":
        "Solana key file",
    "64 个字节的数组（solana-keygen 的 id.json 格式）":
        "Array of 64 bytes (solana-keygen id.json format)",
    "进程名匹配已知挖矿程序":
        "Process name matches a known miner",
    "命令行含矿池地址/挖矿参数":
        "Command line contains a mining pool address / mining parameters",
    "连接常见矿池端口 {0}":
        "Connected to common mining pool ports {0}",
    "CPU {0:.0f}% 且从临时目录运行":
        "CPU {0:.0f}% and running from a temp folder",
    "HD 钱包扩展私钥":
        "HD wallet extended private key",
    "校验通过的 {0}（可推出该钱包全部私钥）":
        "Valid {0} (checksum passed); it can derive every private key of that wallet",
    "剪贴板里的 {0} 地址在 {1:.0f} 秒内被换成了一个“首尾相同、中间不同”的地址（{2} → {3}），极可能是剪贴板劫持！请勿转账，并立即查杀。":
        "The {0} address in the clipboard was swapped within {1:.0f} s for one with the same start and end but a different middle ({2} → {3}). This is very likely clipboard hijacking! Do not send funds, and scan your computer now.",
    "剪贴板里的 {0} 地址在 {1:.0f} 秒内变成了另一个地址（{2} → {3}）。如果这不是你自己的操作，请警惕。":
        "The {0} address in the clipboard changed to a different address within {1:.0f} s ({2} → {3}). Be careful if you did not do this yourself.",
    "Solana 私钥":
        "Solana private key",
    "Base58 编码的 64 字节密钥（紧挨着“私钥”字样）":
        "Base58-encoded 64-byte key (right next to the words “private key”)",
    "已知测试助记词":
        "Known test mnemonic",
    "公开的测试助记词（BIP39 测试向量/开发工具默认值），不是你的资产":
        "A public test mnemonic (BIP39 test vector / dev-tool default), not your assets",
    "助记词(BIP39)":
        "Mnemonic (BIP39)",
    "校验通过的 {0} 个单词助记词（可恢复整个钱包）":
        "Valid {0}-word mnemonic (checksum passed); it can restore an entire wallet",
    "疑似助记词":
        "Suspected mnemonic",
    "“助记词”字样后跟 {0} 个 BIP39 单词，但校验未通过（可能抄错了某个词）":
        "{0} BIP39 words follow the words “mnemonic/seed phrase”, but the checksum failed (a word may have been copied wrongly)",
    "文件名可疑":
        "Suspicious file name",
    "文件名暗示里面可能存放助记词/私钥":
        "The file name suggests it may hold a mnemonic / private key",
    "；位于 {0} 同步目录，云端可能已有副本":
        "; located in a {0} synced folder, so a copy may already be in the cloud",
    "需要安装 psutil 才能检测挖矿进程（pip install psutil）":
        "psutil is required to detect miner processes (pip install psutil)",
    "（若是你自己运行的矿工可忽略）":
        " (ignore this if you run the miner yourself)",
    "；":
        "; ",
    "清理系统垃圾 / 缓存":
        "Clean system junk / caches",
    "\n合计可释放：{0}":
        "\nTotal reclaimable: {0}",
    "提示：清理浏览器缓存会让网页首次加载稍慢，但不会删除密码/书签。":
        "Note: clearing browser caches makes pages load slightly slower the first time, but does not delete passwords/bookmarks.",
    "✔ 已释放约 {0}":
        "✔ Freed about {0}",
    "将处理 {0} 个文件，共 {1}":
        "{0} files will be processed, {1} in total",
    "回收站":
        "Recycle Bin",
    "{0}（可手动找回）":
        "{0} (recoverable manually)",
    "✔ 已处理，释放约 {0}":
        "✔ Done, freed about {0}",
    "大文件列表（从大到小，由你决定是否删除）":
        "Large files (largest first — you decide what to delete)",
    "扫描中，请稍候……":
        "Scanning, please wait...",
    "\n⚠ 这些文件无法自动判断是否有用（可能是视频、虚拟机、安装包等），请自行甄别。":
        "\n⚠ These files can't be judged automatically (they may be videos, virtual machines, installers, etc.). Please review them yourself.",
    "重复文件查找":
        "Find duplicate files",
    "扫描中（>=1MB 的文件），请稍候……":
        "Scanning (files ≥ 1 MB), please wait...",
    "\n删除全部副本可释放：{0}":
        "\nDeleting all copies would free: {0}",
    "开机启动项管理（停用可随时恢复）":
        "Startup items (can be re-enabled any time)",
    "后台进程管理（仅显示当前用户的非系统关键进程）":
        "Background processes (only non-critical processes of the current user)",
    "{0:>3}  {1:>7}  {2:>9}  {3:>5}  名称":
        "{0:>3}  {1:>7}  {2:>9}  {3:>5}  Name",
    "\n⚠ 结束进程会丢失该程序未保存的数据；系统关键进程已自动隐藏。":
        "\n⚠ Ending a process loses any unsaved data in that program; critical system processes are hidden automatically.",
    "卸载不需要的程序（按占用空间从大到小）":
        "Uninstall programs you don't need (largest first)",
    "\n⚠ 请只卸载你确认不需要的软件；驱动、运行库(VC++/.NET)、安全软件请保留。":
        "\n⚠ Only uninstall software you are sure you don't need; keep drivers, runtimes (VC++/.NET) and security software.",
    "潜在风险扫描":
        "Potential risk scan",
    "\n---------- 扫描结果 ----------":
        "\n---------- Scan results ----------",
    "\n报告已保存：{0}":
        "\nReport saved: {0}",
    "说明：以上为启发式检测，“中危/提示”多数是需要你人工确认的项目，并不等于中毒；":
        "Note: these are heuristic checks. Most “Medium/Info” items need your manual confirmation and do not mean you are infected;",
    "      对“高危”项请先核实来源，再考虑处理（可在启动项菜单中停用，或断网后用杀毒软件深度查杀）。":
        "      for “High” items, verify the source first, then decide what to do (disable them in the Startup menu, or go offline and run a deep scan with antivirus software).",
    "一键体检（只检查，不做任何修改）":
        "Quick health check (read-only, changes nothing)",
    "可清理垃圾：约 {0}":
        "Reclaimable junk: about {0}",
    "开机启动项：{0} 个":
        "Startup items: {0}",
    "建议依次进入对应菜单处理。":
        "Open the matching menu to handle them one by one.",
    "\nFaster v{0} | 系统：{1} {2} | 权限：{3}":
        "\nFaster v{0} | System: {1} {2} | Privileges: {3}",
    "全部":
        "all",
    "   ✗ 已保护（钱包文件），不处理：{0}":
        "   ✗ Protected (wallet file), not touched: {0}",
    "没有发现可清理的垃圾文件。":
        "No junk files to clean.",
    "{0:>3}. {1:>10}  {2}  ({3} 个文件)\n       {4}":
        "{0:>3}. {1:>10}  {2}  ({3} files)\n       {4}",
    "输入要清理的编号（如 1,3 / all / 直接回车取消）：":
        "Enter the numbers to clean (e.g. 1,3 / all / press Enter to cancel): ",
    "是否清空回收站？":
        "Empty the Recycle Bin?",
    "提示：apt 缓存 / systemd 日志需 root，可手动执行 `sudo apt clean` 与 `sudo journalctl --vacuum-size=200M`":
        "Tip: the apt cache / systemd journal need root; run `sudo apt clean` and `sudo journalctl --vacuum-size=200M` manually",
    "目录不存在。":
        "Directory does not exist.",
    "输入要删除的编号（如 1,3,5-8 / all / 回车取消）：":
        "Enter the numbers to delete (e.g. 1,3,5-8 / all / Enter to cancel): ",
    "确认移动到 {0}？":
        "Move to {0}?",
    "没有找到符合条件的文件。":
        "No matching files found.",
    "{0:>3}. {1:>10}  {2:>4}天前修改  {3}":
        "{0:>3}. {1:>10}  modified {2:>4} days ago  {3}",
    "没有发现重复文件。":
        "No duplicate files found.",
    "\n[组{0}] 每个 {1}，保留：{2}":
        "\n[Group {0}] {1} each, keeping: {2}",
    "没有发现启动项。":
        "No startup items found.",
    "\n建议停用：更新检查器、云盘/聊天工具自启、各类“助手/管家”。杀毒软件、输入法、驱动相关请保留。":
        "\nSuggested to disable: updaters, cloud-drive/chat auto-start, various “helpers/managers”. Keep antivirus, input methods and drivers.",
    "是否查看/恢复已停用的启动项？":
        "View/restore disabled startup items?",
    "没有可恢复的项目。":
        "Nothing to restore.",
    "输入要恢复的编号：":
        "Enter the numbers to restore: ",
    "需要 psutil 库：请先执行  pip install psutil":
        "psutil is required: run  pip install psutil  first",
    "输入要结束的编号（回车跳过）：":
        "Enter the numbers to end (Enter to skip): ",
    "未获取到已安装程序列表。":
        "Could not get the list of installed programs.",
    "输入要卸载的编号（回车跳过）：":
        "Enter the numbers to uninstall (Enter to skip): ",
    "未安装 psutil，跳过进程与端口检查（pip install psutil）":
        "psutil is not installed; skipping process and port checks (pip install psutil)",
    "使用 Windows Defender 执行快速扫描？（可能需要几分钟）":
        "Run a Windows Defender quick scan? (may take a few minutes)",
    "ℹ 当前非管理员权限，部分检查（端口归属、系统级项目）可能不完整。":
        "ℹ Not running as administrator; some checks (port owners, system-level items) may be incomplete.",
    "运行中的进程与网络端口":
        "Running processes and network ports",
    "启动项 / 计划任务 / 持久化":
        "Startup items / scheduled tasks / persistence",
    "hosts 文件":
        "hosts file",
    "临时目录中的可执行文件":
        "Executables in temp folders",
    "系统安全防护状态":
        "System protection status",
    "→ 检查：{0} ……":
        "→ Checking: {0} ...",
    "未发现明显异常。":
        "No obvious problems found.",
    "内存使用：{0}%   磁盘使用：{1:.0f}% （剩余 {2}）":
        "Memory usage: {0}%   Disk usage: {1:.0f}% ({2} free)",
    "提示：安装 psutil 可解锁进程管理与端口检查（pip install psutil）":
        "Tip: install psutil to enable process management and port checks (pip install psutil)",
    "提示：未安装 send2trash，被删除的文件将移动到 {0}（可找回）":
        "Tip: send2trash is not installed; deleted files will be moved to {0} (recoverable)",
    "大文件列表（大→小，自选删除）":
        "Large files (largest first, choose what to delete)",
    "开机启动项管理":
        "Startup item management",
    "后台进程管理":
        "Background process management",
    "卸载不需要的程序":
        "Uninstall unneeded programs",
    "潜在风险扫描（病毒/后门迹象）":
        "Potential risk scan (virus / backdoor signs)",
    "一键体检（仅检查）":
        "Quick health check (read-only)",
    "  0. 退出":
        "  0. Exit",
    "是":
        "yes",
    "好":
        "ok",
    "   ✗ 无法处理 {0}: {1}":
        "   ✗ Cannot process {0}: {1}",
    "用户临时文件":
        "User temp files",
    "系统临时文件(需管理员)":
        "System temp files (admin required)",
    "Windows 更新下载缓存(需管理员)":
        "Windows Update download cache (admin required)",
    "IE/Edge 旧缓存":
        "Old IE/Edge cache",
    "Chrome 缓存":
        "Chrome cache",
    "Chrome 代码缓存":
        "Chrome code cache",
    "Edge 缓存":
        "Edge cache",
    "Edge 代码缓存":
        "Edge code cache",
    "崩溃转储":
        "Crash dumps",
    "确认清理选中的 {0} 项？":
        "Clean the {0} selected items?",
    "  {0:>3}. 副本：{1}":
        "  {0:>3}. Copy: {1}",
    "   ✗ 停用失败（可能需要管理员权限）：{0}":
        "   ✗ Could not disable (administrator rights may be needed): {0}",
    "输入要停用的编号（回车跳过）：":
        "Enter the numbers to disable (Enter to skip): ",
    "确认停用 {0} 个启动项？":
        "Disable {0} startup items?",
    "   ✔ 已恢复 {0}":
        "   ✔ Restored {0}",
    "确认结束 {0} 个进程？":
        "End {0} processes?",
    "   ✔ 已结束 {0}":
        "   ✔ Ended {0}",
    "卸载 {0}？":
        "Uninstall {0}?",
    "读取网络连接需要管理员/root 权限，已跳过端口检查（可用管理员身份重新运行）":
        "Reading network connections needs administrator/root rights; port check skipped (re-run as administrator)",
    "可疑启动项 [{0}]：{1}":
        "Suspicious startup item [{0}]: {1}",
    "Windows 防火墙有配置文件处于关闭状态":
        "A Windows Firewall profile is turned off",
    "扫描完成，可在“Windows 安全中心 -> 病毒和威胁防护”查看结果。":
        "Scan finished. See results under Windows Security → Virus & threat protection.",
    "用 ClamAV 扫描 {0}？":
        "Scan {0} with ClamAV?",
    "未找到杀毒引擎。建议：":
        "No antivirus engine found. Suggestions:",
    "管理员":
        "Administrator",
    "普通用户":
        "Standard user",
    "\n再见！":
        "\nGoodbye!",
    "用户应用缓存":
        "User app caches",
    "用户日志":
        "User logs",
    "废纸篓":
        "Trash",
    "用户缓存 ~/.cache":
        "User cache ~/.cache",
    "回收站信息":
        "Trash info",
    "缩略图缓存":
        "Thumbnail cache",
    "清空回收站失败：":
        "Failed to empty the Recycle Bin: ",
    "   ✗ 恢复失败：{0}":
        "   ✗ Restore failed: {0}",
    "   … {0} 未响应，未强制结束（可在任务管理器中手动处理）":
        "   … {0} did not respond and was not force-quit (handle it manually in Task Manager)",
    "   ✔ 已移入废纸篓（如有残留可清理 ~/Library/Application Support 中对应目录）":
        "   ✔ Moved to the Trash (leftovers can be removed from ~/Library/Application Support)",
    "   → 正在启动该软件自带的卸载程序，请在弹出的窗口中完成……":
        "   → Starting the program's own uninstaller; please finish in the window that appears...",
    "   将执行：{0}":
        "   Will run: {0}",
    "确认执行？":
        "Confirm to run?",
    "进程 {0} (PID {1}) 伪装成系统进程，实际路径：{2}":
        "Process {0} (PID {1}) is disguised as a system process; real path: {2}",
    "对外监听端口 {0}：{1} {2}":
        "Listening on external port {0}: {1} {2}",
    "{0} 中有 {1} 个 SSH 公钥可免密登录本机，请确认都是你自己的":
        "{0} contains {1} SSH public keys that allow passwordless login to this machine; make sure they are all yours",
    "/etc/ld.so.preload 存在（可被 rootkit 利用），请核对其内容":
        "/etc/ld.so.preload exists (can be abused by rootkits); please check its contents",
    "hosts 文件将 {0} 指向 {1}（可能被劫持，请确认是否为你自己设置）":
        "The hosts file points {0} to {1} (it may be hijacked; confirm you set this yourself)",
    "临时目录中的可执行/脚本文件：{0}":
        "Executable/script file in a temp folder: {0}",
    "Windows Defender 实时保护未开启（若已安装其它杀毒软件可忽略）":
        "Windows Defender real-time protection is off (ignore if you use other antivirus software)",
    "病毒库已 {0} 天未更新":
        "Virus definitions have not been updated for {0} days",
    "Gatekeeper 已被关闭，系统会运行未签名程序":
        "Gatekeeper is turned off; the system will run unsigned programs",
    "SIP（系统完整性保护）已关闭":
        "SIP (System Integrity Protection) is turned off",
    "macOS 防火墙未开启":
        "The macOS firewall is off",
    "  macOS 内置 XProtect 会自动运行；如需按需扫描可安装 ClamAV（brew install clamav）或 Malwarebytes。":
        "  macOS has built-in XProtect that runs automatically; for on-demand scans install ClamAV (brew install clamav) or Malwarebytes.",
    "  安装 ClamAV：sudo apt install clamav && sudo freshclam；rootkit 检测可用 rkhunter / chkrootkit。":
        "  Install ClamAV: sudo apt install clamav && sudo freshclam; use rkhunter / chkrootkit for rootkit detection.",
    "检查“{0}”时出错：{1}":
        "Error while checking “{0}”: {1}",
    "请选择：":
        "Choose: ",
    "扫描目录（回车=用户主目录 {0}）：":
        "Directory to scan (Enter = home folder {0}): ",
    "   ✔ 已停用 {0}":
        "   ✔ Disabled {0}",
    "未知":
        "Unknown",
    "进程 {0} (PID {1}) 从临时目录运行：{2}":
        "Process {0} (PID {1}) is running from a temp folder: {2}",
    "可疑计划任务 [{0}]：{1}":
        "Suspicious scheduled task [{0}]: {1}",
    "可疑 crontab 条目：{0}":
        "Suspicious crontab entry: {0}",
    "未检测到 ufw / firewalld 防火墙在运行":
        "No ufw / firewalld firewall detected running",
    "\n已取消。":
        "\nCancelled.",
    "出错：{0}":
        "Error: {0}",
    "只显示大于多少 MB 的文件？(默认 100) ":
        "Show only files larger than how many MB? (default 100) ",
    "最多显示多少个？(默认 50) ":
        "Show at most how many? (default 50) ",
    "进程 {0} (PID {1}) 的程序文件已被删除但仍在运行（常见于恶意程序）":
        "The program file of process {0} (PID {1}) was deleted but it is still running (common with malware)",
    "未知进程":
        "Unknown process",
    "{0} 中含可疑命令：{1}":
        "{0} contains a suspicious command: {1}",
    "ClamAV 扫描目录（回车=用户主目录）：":
        "Directory to scan with ClamAV (Enter = home folder): ",
    "(无法解析)":
        "(cannot parse)",
    "用户级 systemd 服务含可疑命令：{0}":
        "User-level systemd service contains a suspicious command: {0}",
    "可疑 LaunchDaemon：{0}":
        "Suspicious LaunchDaemon: {0}",
    "周一":
        "Mon",
    "周二":
        "Tue",
    "周三":
        "Wed",
    "周四":
        "Thu",
    "周五":
        "Fri",
    "周六":
        "Sat",
    "周日":
        "Sun",
    "每天":
        "Daily",
    "每周":
        "Weekly",
    "每月":
        "Monthly",
    "目录不存在":
        "Directory does not exist",
    "过于靠近根目录/主目录，已拒绝":
        "Too close to the root/home folder; refused",
    "本工具自身目录，已拒绝":
        "This tool's own folder; refused",
    "[试运行·不删除] ":
        "[Dry run · nothing deleted] ",
    "{0}开始自动清理 {1:%Y-%m-%d %H:%M:%S}":
        "{0}Auto-clean started {1:%Y-%m-%d %H:%M:%S}",
    "{0}合计{1} {2}":
        "{0}Total {1}: {2}",
    "释放 {0}":
        "Freed {0}",
    "合计释放 {0}":
        "Total freed {0}",
    "参考":
        "Ref",
    "路径无效":
        "Invalid path",
    "系统目录，已拒绝":
        "System folder; refused",
    "未找到 systemd 或 cron，无法创建定时任务":
        "systemd or cron not found; cannot create a scheduled task",
    "已移除定时任务":
        "Scheduled task removed",
    "{0}：释放 {1}":
        "{0}: freed {1}",
    "未找到 pkexec（polkit）。请安装 policykit-1，或在终端用 sudo 运行本程序。":
        "pkexec (polkit) not found. Install policykit-1, or run this program with sudo in a terminal.",
    "来源：{0}\n文件：{1}\n单词数：{2}（BIP39 英文词表固定为 2048 个，每个词对应 11 位）\nSHA-256：{3}\n校验：✓ 2048 个互不相同、按字母排序、前 4 个字母可唯一区分；✓ 通过 BIP39 官方测试向量\n官方来源：{4}":
        "Source: {0}\nFile: {1}\nWords: {2} (the BIP39 English list is fixed at 2048 words; each word encodes 11 bits)\nSHA-256: {3}\nVerification: ✓ 2048 distinct words, sorted alphabetically, first 4 letters unique; ✓ passes the official BIP39 test vectors\nOfficial source: {4}",
    "已扫描 {0} 个文件：高危 {1} · 中危 {2} · 提示 {3}。":
        "Scanned {0} files: High {1} · Medium {2} · Info {3}.",
    "处理中…":
        "Working...",
    "未找到 tkinter。Windows/macOS 请使用 python.org 的官方安装包；Linux 请执行：sudo apt install python3-tk":
        "tkinter not found. On Windows/macOS use the official installer from python.org; on Linux run: sudo apt install python3-tk",
    "  工具回收站中超过 {0} 天的文件：{1}":
        "  Files in the tool's trash older than {0} days: {1}",
    "  跳过文件夹 {0}：{1}":
        "  Skipping folder {0}: {1}",
    "  文件夹 {0}：{1} 个超过 {2} 天的文件，{3}{4}":
        "  Folder {0}: {1} files older than {2} days, {3}{4}",
    "  文件夹 {0}：已保护并跳过 {1} 个钱包文件":
        "  Folder {0}: protected and skipped {1} wallet files",
    "可释放":
        "reclaimable",
    "释放":
        "freed",
    "已移除计划任务":
        "Scheduled task removed",
    "系统临时文件":
        "System temp files",
    "Windows 更新下载缓存":
        "Windows Update download cache",
    "Windows 错误报告":
        "Windows error reports",
    "systemd 日志：已压缩到 200MB 以内":
        "systemd journal: reduced to under 200MB",
    "systemd 日志清理失败：{0}":
        "Failed to clean the systemd journal: {0}",
    "提示：系统级 LaunchAgent 需注销并重新登录后才完全生效":
        "Note: system-level LaunchAgents only take full effect after you log out and back in",
    "不支持的操作：{0}":
        "Unsupported action: {0}",
    "扫描":
        "Scan",
    "全选":
        "Select all",
    "清理选中项":
        "Clean selected",
    "🛡 管理员清理系统级垃圾":
        "🛡 Clean system-level junk (admin)",
    "扫描垃圾文件…":
        "Scanning junk files...",
    "清理中…":
        "Cleaning...",
    "等待管理员授权…":
        "Waiting for administrator authorization...",
    "确认":
        "Confirm",
    "清空回收站？此操作不可恢复。":
        "Empty the Recycle Bin? This cannot be undone.",
    "扫描（大→小）":
        "Scan (largest first)",
    "删除选中":
        "Delete selected",
    "扫描大文件…（目录较大时可能需要几分钟）":
        "Scanning large files... (large folders can take a few minutes)",
    "查找重复文件(≥1MB)":
        "Find duplicates (≥1MB)",
    "选中所有副本":
        "Select all copies",
    "查找重复文件…（会计算文件哈希，较慢）":
        "Finding duplicate files... (computing file hashes, slow)",
    "刷新":
        "Refresh",
    "停用选中":
        "Disable selected",
    "恢复已停用…":
        "Restore disabled...",
    "注册表":
        "Registry",
    "启动文件夹":
        "Startup folder",
    "自启动项":
        "Autostart item",
    "恢复已停用的启动项":
        "Restore disabled startup items",
    "结束选中进程":
        "End selected processes",
    "读取进程…":
        "Reading processes...",
    "刷新列表":
        "Refresh list",
    "卸载选中":
        "Uninstall selected",
    "读取已安装程序…":
        "Reading installed programs...",
    "开始扫描":
        "Start scan",
    "🛡 管理员权限扫描（更完整）":
        "🛡 Admin scan (more complete)",
    "杀毒引擎查杀（Defender / ClamAV）":
        "Antivirus engine scan (Defender / ClamAV)",
    "风险扫描中…（约 1-2 分钟）":
        "Running risk scan... (about 1–2 minutes)",
    "等待管理员授权并扫描…":
        "Waiting for administrator authorization, then scanning...",
    "扫描钱包文件":
        "Scan wallet files",
    "打开所在位置":
        "Show in folder",
    "发现 {0} 个钱包文件/目录，已全部受 Faster 保护。":
        "Found {0} wallet files/folders, all protected by Faster.",
    "查找钱包文件…（会遍历主目录，可能需要几分钟）":
        "Looking for wallet files... (walks your home folder, may take a few minutes)",
    "扫描区块链数据":
        "Scan blockchain data",
    "识别区块链数据目录…":
        "Identifying blockchain data folders...",
    "查看助记词表":
        "View word list",
    "下载并校验 BIP39 词表…":
        "Downloading and verifying the BIP39 word list...",
    "BIP39 英文助记词表":
        "BIP39 English word list",
    "扫描助记词/私钥…（文件多时需要几分钟）":
        "Scanning for mnemonics/private keys... (can take a few minutes for many files)",
    "（仅显示前 {0} 项，请用“显示”筛选）":
        "(showing only the first {0}; use the “Show” filter)",
    "  ⚠ 未加载 BIP39 词表，本次没有检测助记词。":
        "  ⚠ BIP39 word list not loaded; mnemonics were not checked this time.",
    "  建议：把资产转到新钱包（新助记词），抄写在纸上离线保存，并删除/加密这些明文文件。":
        "  Advice: move your assets to a new wallet (new mnemonic), write the mnemonic on paper and keep it offline, and delete/encrypt these plaintext files.",
    "开始检测（约 3 秒）":
        "Start detection (about 3 s)",
    "检测挖矿进程…":
        "Detecting miner processes...",
    "天数":
        "Days",
    "清理该文件夹内未修改超过多少天的文件？":
        "Clean files in this folder that have not been modified for how many days?",
    "定时任务":
        "Scheduled task",
    "定时任务：已启用":
        "Scheduled task: enabled",
    "定时任务：未启用":
        "Scheduled task: not enabled",
    "  |  上次运行 {0}（{1}）":
        "  |  Last run {0} ({1})",
    "  垃圾缓存 · {0}：{1} 个文件，{2}":
        "  Junk caches · {0}: {1} files, {2}",
    "  将清空回收站":
        "  The Recycle Bin will be emptied",
    "已创建 Windows 计划任务":
        "Windows scheduled task created",
    "创建失败：{0}":
        "Creation failed: {0}",
    "已创建 launchd 定时任务（电脑休眠错过时，唤醒后会补跑）":
        "launchd job created (if the Mac is asleep at the scheduled time, it runs after waking)",
    "加载失败：{0}":
        "Load failed: {0}",
    "已创建 systemd 用户定时器（错过的任务开机后会补跑）":
        "systemd user timer created (missed runs happen after the next boot)",
    "启用失败：{0}":
        "Enable failed: {0}",
    "已写入 crontab":
        "Written to crontab",
    "写入失败：{0}":
        "Write failed: {0}",
    "检查 {0} 出错：{1}":
        "Error while checking {0}: {1}",
    "系统级缓存 /Library/Caches":
        "System-level cache /Library/Caches",
    "诊断报告":
        "Diagnostic reports",
    "apt 软件包缓存":
        "apt package cache",
    "/var/tmp 超过7天的文件":
        "Files in /var/tmp older than 7 days",
    "systemd 核心转储":
        "systemd core dumps",
    "未获得管理员权限":
        "Administrator rights were not granted",
    "已将 {0} 移入废纸篓":
        "Moved {0} to the Trash",
    "已取消，或未获得管理员授权。":
        "Cancelled, or administrator authorization was not granted.",
    "请先在列表中选择项目（可按住 Ctrl/Shift 多选，或点“全选”）。":
        "Select items in the list first (hold Ctrl/Shift for multiple, or click “Select all”).",
    "磁盘":
        "Disk",
    "内存":
        "Memory",
    "未能获得管理员权限（授权被取消）。":
        "Could not get administrator rights (authorization cancelled).",
    "已用 {0} / 共 {1}（剩 {2}）":
        "{0} used of {1} ({2} free)",
    "清空回收站":
        "Empty Recycle Bin",
    "完成":
        "Done",
    "已释放约 {0}":
        "Freed about {0}",
    "Windows 系统临时文件、更新下载缓存、错误报告":
        "Windows system temp files, update download cache, error reports",
    "/Library/Caches 系统级缓存、诊断报告":
        "/Library/Caches system-level caches, diagnostic reports",
    "apt 软件包缓存、/var/tmp 旧文件、systemd 日志(压缩到200MB)":
        "apt package cache, old files in /var/tmp, systemd journal (trimmed to 200MB)",
    "管理员清理":
        "Admin cleanup",
    "将以管理员权限清理：\n{0}\n\n继续？（随后会弹出系统授权窗口）":
        "Will clean with administrator rights:\n{0}\n\nContinue? (a system authorization window will appear)",
    "回收站已清空":
        "Recycle Bin emptied",
    "这些文件无法自动判断是否有用（视频/虚拟机/安装包等），请自行甄别；删除后进回收站。钱包文件已被自动保护、不会出现在列表里。":
        "These files can't be judged automatically (videos/virtual machines/installers etc.); review them yourself. Deleted files go to the Recycle Bin. Wallet files are protected automatically and never appear in this list.",
    "错误":
        "Error",
    "将 {0} 个文件（{1}）移入回收站？":
        "Move {0} files ({1}) to the Recycle Bin?",
    "灰色“保留”为建议保留的一份（路径最短/最早），只会删除你选中的“副本”。":
        "The greyed-out “Keep” row is the copy suggested to keep (shortest/earliest path); only the “Copy” rows you select will be deleted.",
    "将 {0} 个副本（{1}）移入回收站？":
        "Move {0} copies ({1}) to the Recycle Bin?",
    "建议停用：更新检查器、云盘/聊天工具自启、各类“助手/管家”。杀毒、输入法、驱动相关请保留。停用可随时恢复。":
        "Suggested to disable: updaters, cloud-drive/chat auto-start, various “helpers/managers”. Keep antivirus, input methods and drivers. Disabled items can be restored any time.",
    "部分失败":
        "Partly failed",
    "需要管理员权限":
        "Administrator rights needed",
    "没有可恢复的启动项。":
        "Nothing to restore.",
    "仅显示当前用户的非系统关键进程（按内存排序）。结束进程会丢失该程序未保存的数据。":
        "Only non-critical processes of the current user (sorted by memory). Ending a process loses its unsaved data.",
    "请先安装 psutil：pip install psutil":
        "Please install psutil first: pip install psutil",
    "部分未结束":
        "Some were not ended",
    "按占用空间从大到小。请只卸载确认不需要的软件；驱动、运行库(VC++/.NET)、安全软件请保留。":
        "Largest first. Only uninstall software you are sure you don't need; keep drivers, runtimes (VC++/.NET) and security software.",
    "启发式检测：“中危/提示”多数需要你人工确认，并不等于中毒；扫不出结果也不代表一定安全。管理员扫描可看到全部进程的网络连接。":
        "Heuristic checks: most “Medium/Info” items need your manual confirmation and do not mean you are infected; finding nothing does not guarantee safety. The admin scan can see every process's network connections.",
    "高危 {0} · 中危 {1} · 提示 {2}（报告已保存到 {3}）":
        "High {0} · Medium {1} · Info {2} (report saved to {3})",
    "未发现明显异常":
        "No obvious problems found",
    "Defender 扫描中…":
        "Defender scan running...",
    "未找到杀毒引擎。\n\nmacOS：系统内置 XProtect 会自动运行；按需扫描可安装 ClamAV（brew install clamav）或 Malwarebytes。\nLinux：sudo apt install clamav && sudo freshclam；rootkit 检测可用 rkhunter / chkrootkit。":
        "No antivirus engine found.\n\nmacOS: the built-in XProtect runs automatically; for on-demand scans install ClamAV (brew install clamav) or Malwarebytes.\nLinux: sudo apt install clamav && sudo freshclam; use rkhunter / chkrootkit for rootkit detection.",
    "Faster 的清理 / 大文件 / 重复文件 / 自动清理 / 卸载废纸篓清空，都会自动跳过这些文件。点“扫描”查看。":
        "Faster's cleanup / large files / duplicates / auto clean / emptying the Trash all skip these files automatically. Click “Scan” to view them.",
    "  ⚠ 其中 {0} 个位于云同步目录（红色），云端可能有副本，建议迁出并确认已离线备份助记词。":
        "  ⚠ {0} of them are in cloud-synced folders (red); the cloud may hold a copy. Move them out and make sure the mnemonic is backed up offline.",
    "只识别和提示，Faster 不会自动删除这些数据。删除“可重新同步”的区块数据前请先关闭对应软件，重新同步可能需要数小时到数天。":
        "Detect and report only: Faster never deletes this data automatically. Close the matching software before deleting “re-syncable” block data; re-syncing can take hours to days.",
    "在文本/笔记/Office 文件里查找明文保存的助记词和私钥。结果只显示位置与类型，不回显任何内容，也不会上传。":
        "Looks for plaintext mnemonics and private keys in text/note/Office files. Results show only location and type, never the content, and nothing is uploaded.",
    "BIP39 词表":
        "BIP39 word list",
    "序号":
        "No.",
    "单词":
        "Word",
    "已复制":
        "Copied",
    "2048 个单词已复制到剪贴板（每行一个）。":
        "The 2048 words were copied to the clipboard (one per line).",
    "需要 BIP39 词表":
        "BIP39 word list needed",
    "没有找到 BIP39 助记词表，无法检测助记词（私钥仍可检测）。\n\n现在下载吗？约 13KB，来自 BIP39 官方仓库 bitcoin/bips，下载后会校验。\n\n是：下载后开始扫描\n否：跳过助记词检测，只检测私钥\n取消：不扫描":
        "The BIP39 mnemonic word list was not found, so mnemonics can't be detected (private keys still can).\n\nDownload it now? About 13KB, from the official BIP39 repo bitcoin/bips; it is verified after download.\n\nYes: download, then scan\nNo: skip mnemonic detection, check private keys only\nCancel: don't scan",
    "  未发现明文助记词/私钥。（图片/截图、便签数据库、PDF 不在扫描范围内）":
        "  No plaintext mnemonics/private keys found. (Images/screenshots, sticky-note databases and PDFs are not scanned)",
    "检查进程名/命令行里的挖矿特征、连接矿池端口、临时目录里的高 CPU 程序。启动项/计划任务里的挖矿命令会在“风险扫描”里一并检查。":
        "Checks process names/command lines for miner signatures, connections to mining-pool ports, and high-CPU programs in temp folders. Miner commands in startup items/scheduled tasks are checked by the “Risk scan” too.",
    "已结束。如确认是木马，请再用“风险扫描”找出并停用它的启动项，并用杀毒软件查杀。":
        "Ended. If you are sure it is a trojan, use the “Risk scan” to find and disable its startup item, then scan with antivirus software.",
    "（把你在钱包/交易所里看到的收款地址粘贴进来，核对是否被替换）":
        "(Paste the payee address shown in your wallet/exchange to check whether it was swapped)",
    "用法：开启监控 → 照常复制地址 → 粘贴到转账页面后，把页面上显示的地址再贴到上面校验。首尾相同、中间不同的地址是典型的剪贴板劫持/地址投毒。":
        "How to use: turn monitoring on → copy addresses as usual → after pasting into the transfer page, paste the address shown there into the box above to verify. Addresses with the same start and end but a different middle are the classic sign of clipboard hijacking / address poisoning.",
    "剪贴板监控已开启":
        "Clipboard monitoring turned on",
    "剪贴板监控已关闭":
        "Clipboard monitoring turned off",
    "校验：":
        "Check: ",
    "区块链数据":
        "Blockchain data",
    "密钥泄露扫描":
        "Key leak scan",
    "挖矿检测":
        "Miner detection",
    "剪贴板守护":
        "Clipboard guard",
    "① 执行计划":
        "① Schedule",
    "② 清理内容":
        "② What to clean",
    "③ 自定义文件夹：超过 N 天未修改的文件移入回收站（可找回）":
        "③ Custom folders: files not modified for N days go to the Recycle Bin (recoverable)",
    "文件夹":
        "Folder",
    "运行日志":
        "Run log",
    "选择要定期清理的文件夹":
        "Choose a folder to clean regularly",
    "不允许":
        "Not allowed",
    "就绪":
        "Ready",
    "概览":
        "Overview",
    "垃圾清理":
        "Junk cleanup",
    "大文件":
        "Large files",
    "重复文件":
        "Duplicates",
    "启动项":
        "Startup",
    "后台进程":
        "Processes",
    "卸载程序":
        "Uninstall",
    "风险扫描":
        "Risk scan",
    "钱包安全":
        "Wallet security",
    "自动清理":
        "Auto clean",
    "  已清空回收站":
        "  Recycle Bin emptied",
    "（已移入回收站，可找回）":
        " (moved to the Recycle Bin, recoverable)",
    "跳过 {0}：非系统级项目，无需管理员权限":
        "Skipped {0}: not a system-level item, no administrator rights needed",
    "拒绝：只允许移除 /Applications 下的 .app":
        "Refused: only .app bundles directly under /Applications may be removed",
    "执行出错：{0}":
        "Execution error: {0}",
    "已用 {0} / 共 {1}":
        "{0} used of {1}",
    "需要安装 psutil":
        "psutil is required",
    "项目":
        "Item",
    "文件数":
        "Files",
    "位置":
        "Location",
    "系统级清理结果":
        "System-level cleanup result",
    "大小":
        "Size",
    "最后修改":
        "Last modified",
    "路径":
        "Path",
    "共 {0} 个文件，合计 {1}":
        "{0} files, {1} in total",
    "组":
        "Group",
    "状态":
        "Status",
    "名称":
        "Name",
    "类型":
        "Type",
    "命令 / 路径":
        "Command / path",
    "停用 {0} 个启动项？（会自动备份，可恢复）":
        "Disable {0} startup items? (they are backed up automatically and can be restored)",
    "以下项目停用失败：\n":
        "These items could not be disabled:\n",
    "\n\n现在授权并重试？":
        "\n\nAuthorize now and retry?",
    "{0} 项恢复失败，可能需要管理员权限。\n现在授权并重试？":
        "{0} items failed to restore; administrator rights may be needed.\nAuthorize now and retry?",
    "需要安装 psutil 才能使用此功能：pip install psutil":
        "psutil is required for this feature: pip install psutil",
    "结束 {0} 个进程？未保存的数据会丢失。":
        "End {0} processes? Unsaved data will be lost.",
    "占用":
        "Disk use",
    "程序名称":
        "Program name",
    "确认卸载":
        "Confirm uninstall",
    "级别":
        "Level",
    "发现":
        "Finding",
    "执行 Defender 快速扫描？可能需要几分钟。":
        "Run a Defender quick scan? It may take a few minutes.",
    "云同步":
        "Cloud sync",
    "软件":
        "Software",
    "总大小":
        "Total size",
    "可重新同步的数据":
        "Re-syncable data",
    "钱包相关（勿删）":
        "Wallet-related (do not delete)",
    "说明":
        "Description",
    "高危+中危":
        "High+Medium",
    "仅高危":
        "High only",
    "词表：已就绪（助记词按校验和验证）":
        "Word list: ready (mnemonics are checked with the checksum)",
    "词表：未加载（将跳过助记词检测，点“查看助记词表”可下载）":
        "Word list: not loaded (mnemonic detection will be skipped; click “View word list” to download)",
    "显示 {0} / {1}":
        "Showing {0} / {1}",
    "  (第 {0} 行)":
        "  (line {0})",
    "进程":
        "Process",
    "需要安装 psutil 才能使用：pip install psutil":
        "psutil is required: pip install psutil",
    "结束 {0} 个进程？":
        "End {0} processes?",
    "时间":
        "Time",
    "记录":
        "Log",
    "{0}\n中超过 {1} 天未修改的文件将被定期移入回收站。\n确认添加？":
        "{0}\nFiles in it not modified for more than {1} days will be moved to the Recycle Bin regularly.\nAdd it?",
    "（暂无日志）":
        "(no log yet)",
    "  [管理员]":
        "  [Administrator]",
    "  清空回收站失败：{0}":
        "  Failed to empty the Recycle Bin: {0}",
    "  清空 {0}：{1}":
        "  Emptied {0}: {1}",
    "已恢复 ":
        "Restored ",
    "恢复失败 ":
        "Restore failed ",
    "目录：":
        "Folder: ",
    "浏览…":
        "Browse...",
    "版本 v{0} · {1} {2} · 当前：{3}权限":
        "Version v{0} · {1} {2} · Current: {3} privileges",
    "清理浏览器缓存后网页首次加载会稍慢，不会丢失密码/书签":
        "After clearing browser caches, pages load slightly slower the first time; passwords/bookmarks are not lost",
    "可释放合计 {0}":
        "Total reclaimable {0}",
    "没有发现可清理的垃圾":
        "No junk to clean",
    "MB  前":
        "MB, top",
    "个":
        "items",
    "{0} 天前":
        "{0} days ago",
    "保留":
        "Keep",
    "{0} 组重复文件，删除全部副本可释放 {1}":
        "{0} groups of duplicates; deleting all copies frees {1}",
    "没有发现重复文件":
        "No duplicate files found",
    "{0} 个系统级启动项需要管理员权限：\n":
        "{0} system-level startup items need administrator rights:\n",
    "恢复选中":
        "Restore selected",
    "{0}：未响应，未强制结束":
        "{0}: not responding, not force-quit",
    "{0}：{1}":
        "{0}: {1}",
    "结果":
        "Result",
    "已移入废纸篓":
        "Moved to the Trash",
    "普通权限无法移除该应用，是否授权后重试？":
        "Normal rights can't remove this app. Authorize and retry?",
    "已启动该软件自带的卸载程序，请在弹出的窗口中完成。":
        "The program's own uninstaller has been started; finish in the window that appears.",
    "Defender 扫描结果":
        "Defender scan result",
    "选择要用 ClamAV 扫描的目录":
        "Choose a folder to scan with ClamAV",
    "ClamAV 扫描中…":
        "ClamAV scan running...",
    "没有发现钱包文件。":
        "No wallet files found.",
    "发现 {0} 个区块链软件数据目录；其中可重新同步的数据共 {1}。":
        "Found {0} blockchain software data folders; {1} of it is re-syncable data.",
    "没有发现常见区块链软件的数据目录。":
        "No data folders of common blockchain software found.",
    "提示：":
        "Note: ",
    "同时扫描代码/配置文件（.py .js .sh .yml 等，仅报强证据）":
        "Also scan code/config files (.py .js .sh .yml etc.; only strong evidence is reported)",
    "   显示：":
        "   Show: ",
    "搜索（单词片段或序号）：":
        "Search (word fragment or number): ",
    "复制全部":
        "Copy all",
    "重新下载/更新":
        "Re-download/update",
    "CPU 占用靠前的进程（仅供参考）":
        "Top CPU processes (for reference only)",
    "发现 {0} 个可疑项，请核对。":
        "Found {0} suspicious items; please review.",
    "未发现挖矿迹象。（下方为 CPU 占用靠前的进程）":
        "No signs of mining found. (Below are the top CPU processes)",
    "启用剪贴板监控（只在内存里记录，不写入磁盘）":
        "Enable clipboard monitoring (kept in memory only, never written to disk)",
    "校验收款地址：":
        "Verify payee address: ",
    "校验":
        "Verify",
    "记录到 {0} 地址：{1}":
        "Recorded {0} address: {1}",
    "钱包安全：全部在本地运行，不上传任何内容，不接触你的私钥/助记词。":
        "Wallet security: everything runs locally, nothing is uploaded, and your private keys/mnemonics are never touched.",
    "时间：":
        "Time: ",
    "每周星期：":
        "Day of week (weekly): ",
    "每月几号：":
        "Day of month (monthly): ",
    "清理系统垃圾/缓存，仅清理未修改超过":
        "Clean system junk/caches, only files unmodified for more than",
    "天的文件（0 = 1 小时前）":
        "days (0 = 1 hour)",
    "清空系统回收站 / 废纸篓（不可恢复）":
        "Empty the system Recycle Bin / Trash (cannot be undone)",
    "彻底删除本工具回收站中超过":
        "Permanently delete files in this tool's trash older than",
    "天的文件（0 = 不处理）":
        "days (0 = leave alone)",
    "添加文件夹…":
        "Add folder...",
    "保存并启用定时任务":
        "Save and enable scheduled task",
    "停用定时任务":
        "Disable scheduled task",
    "试运行（只统计）":
        "Dry run (count only)",
    "立即清理一次":
        "Clean now",
    "刷新日志":
        "Refresh log",
    "出错":
        "Error",
    "已停用 ":
        "Disabled ",
    "停用失败 ":
        "Disable failed ",
    "副本":
        "Copy",
    "请在终端执行":
        "Run this in a terminal",
    "卸载中…":
        "Uninstalling...",
    "、":
        ", ",
    "现在下载并校验":
        "Download and verify now",
    "试运行结果":
        "Dry-run result",
    "清理结果":
        "Cleanup result",
    "🛡 以管理员身份重新启动（一次授权，全部功能可用）":
        "🛡 Restart as administrator (authorize once, all features available)",
    "也可不重启：需要管理员权限的功能会按提示单独授权":
        "You can also skip the restart: features that need administrator rights ask for authorization one by one",
    "需要管理员权限的功能会按提示弹出系统授权窗口（输入开机密码即可）":
        "Features that need administrator rights will show a system authorization window (enter your login password)",
    "未发现威胁。":
        "No threats found.",
    "ClamAV 扫描结果":
        "ClamAV scan result",
    "\n\n官方来源：{0}\n点下面的按钮可下载并校验（约 13KB）。":
        "\n\nOfficial source: {0}\nClick the button below to download and verify it (about 13KB).",
    "剪贴板地址异常":
        "Clipboard address alert",
    "词表还没有加载。\n\n程序会在下面这些位置查找 bip39_english.txt：\n":
        "The word list is not loaded yet.\n\nThe program looks for bip39_english.txt in these places:\n",
    "失败：{0}":
        "Failed: {0}",
    "编号":
        "No.",
    "当前语言：{0}":
        "Current language: {0}",
    "已保存，重新启动程序后生效。":
        "Saved. It takes effect after you restart the program.",
    "语言 / Language":
        "Language / 语言",
    "请选择语言编号（回车取消）：":
        "Choose a language number (Enter to cancel): ",
    "跟随系统":
        "Follow system",
    "语言已更改，需要重启程序才能完全生效。现在重启吗？":
        "The language was changed. The program must restart for it to take full effect. Restart now?",
    "语言 / Language：":
        "Language / 语言: ",
    "性能诊断":
        "Diagnostics",
    "健康分：{0} / 100":
        "Health score: {0} / 100",
    "回收站里已找不到该文件":
        "The file can no longer be found in the trash",
    "原路径无效":
        "Invalid original path",
    "性能诊断（只读）":
        "Performance diagnosis (read-only)",
    " (已还原)":
        " (restored)",
    "{0}（前）":
        "{0} (before)",
    "{0}（后）":
        "{0} (after)",
    "效果：{0}":
        "Effect: {0}",
    "停用启动项":
        "Disable startup items",
    "结束进程":
        "End processes",
    "诊断中…":
        "Diagnosing...",
    "评估启动影响":
        "Assess startup impact",
    "评估启动影响…":
        "Assessing startup impact...",
    "记录当前状态":
        "Record current state",
    "对比选中的两条":
        "Compare the two selected",
    "清空历史":
        "Clear history",
    "手动记录":
        "Manual record",
    "对比：{0}  →  {1}":
        "Comparison: {0}  →  {1}",
    "✓ 变好   ✗ 变差   = 没变化":
        "✓ better   ✗ worse   = unchanged",
    "前后对比":
        "Before/after",
    "清空全部历史记录？":
        "Clear all history records?",
    "还原选中":
        "Restore selected",
    "永久删除选中":
        "Delete selected permanently",
    "打开工具回收站":
        "Open tool trash",
    "打开系统回收站":
        "Open system trash",
    "清空工具回收站":
        "Empty tool trash",
    "永久清空工具回收站？此操作不可恢复。":
        "Permanently empty the tool trash? This cannot be undone.",
    "已处理 {0} 个文件（{1}）。文件现在在回收站里，清空回收站后才会真正释放磁盘空间；也可以到“还原中心”还原。":
        "Processed {0} files ({1}). They are now in the Recycle Bin; disk space is only really freed after you empty it. You can also restore them from the “Restore center”.",
    "建议":
        "Advice",
    "按“正在运行的进程”估算（内存 + 平均 CPU），不是精确的开机耗时；当前没在运行的项目无法评估。":
        "Estimated from the “running processes” (memory + average CPU); this is not an exact boot time, and items that are not currently running cannot be assessed.",
    "清理、停用启动项、结束进程时会自动记录“前/后”两条；选中任意两条可以对比。":
        "A “before/after” pair is recorded automatically when you clean, disable startup items or end processes; select any two entries to compare them.",
    "请选中恰好两条记录（按住 Ctrl/Shift 多选）。":
        "Select exactly two records (hold Ctrl/Shift for multiple).",
    "启动影响":
        "Startup impact",
    "这里列出被 Faster 移走/停用的东西。“垃圾清理”删除的缓存是永久删除的，不在此列。":
        "This lists things Faster moved away or disabled. Caches deleted by “Junk cleanup” are removed permanently and are not listed.",
    "{0} 条在系统回收站里，请点“打开系统回收站”自行还原。":
        "{0} entries are in the system trash; click “Open system trash” to restore them yourself.",
    "还原结果":
        "Restore result",
    "已永久删除，释放 {0}":
        "Permanently deleted, freed {0}",
    "取消":
        "Cancel",
    "还原中心":
        "Restore center",
    "已取消，下面只是已扫描到的 {0} 项部分结果。":
        "Cancelled; below are only the {0} partial results scanned so far.",
    "共 {0} 个启动项，其中 {1} 个影响较高。":
        "{0} startup items, {1} of them with high impact.",
    "永久删除选中的 {0} 项？此操作不可恢复。":
        "Permanently delete the {0} selected items? This cannot be undone.",
    "正在取消…":
        "Cancelling...",
    "清理垃圾":
        "Junk cleanup",
    "高":
        "High",
    "文件（工具回收站）":
        "File (tool trash)",
    "可还原":
        "Restorable",
    "文件（系统回收站）":
        "File (system trash)",
    "请在系统回收站还原":
        "Restore from the system trash",
    "中":
        "Medium",
    "运行中":
        "Running",
    "严重":
        "Critical",
    "注意":
        "Warning",
    "良好":
        "Good",
    "开机后 {0:.1f} 小时":
        "{0:.1f} h after boot",
    "磁盘剩余":
        "Disk free",
    "内存占用":
        "Memory used",
    "内存占用率":
        "Memory usage",
    "交换空间占用率":
        "Swap usage",
    "开机启动项":
        "Startup items",
    "进程数":
        "Processes",
    "诊断":
        "Diagnosis",
    "开机后 {0:.0f} 秒":
        "{0:.0f} s after boot",
    "开机后 {0:.0f} 分钟":
        "{0:.0f} min after boot",
    "低":
        "Low",
    "未运行":
        "Not running",
    "磁盘空间":
        "Disk space",
    "剩余 {0}（{1:.0f}%）":
        "{0} free ({1:.0f}%)",
    "清理垃圾、大文件和重复文件；卸载不用的大型程序。":
        "Clean junk, large files and duplicates; uninstall large programs you no longer use.",
    "已用 {0}（{1:.0f}%）":
        "{0} used ({1:.0f}%)",
    "关闭不用的程序和浏览器标签页；长期不够用就增加内存。":
        "Close programs and browser tabs you don't need; add more memory if it is never enough.",
    "交换空间":
        "Swap",
    "已用 {0:.0f}%":
        "{0:.0f}% used",
    "内存吃紧又在大量使用交换空间时电脑会明显变卡：关闭占内存大的程序，或增加内存。":
        "When memory is tight and swap is heavily used, the computer slows down noticeably: close memory-hungry programs or add more memory.",
    "内存 / CPU":
        "Memory / CPU",
    "无法读取":
        "Unavailable",
    "安装 psutil（pip install psutil）后才能诊断内存、CPU 和进程。":
        "Install psutil (pip install psutil) to diagnose memory, CPU and processes.",
    "共 {0} 个":
        "{0} in total",
    "到“启动影响”页按影响排序，停用不需要的启动项。":
        "On the “Startup impact” tab, sort by impact and disable the startup items you don't need.",
    "连续运行时间":
        "Uptime",
    "{0:.1f} 天":
        "{0:.1f} days",
    "重启一次可以释放内存，并让系统更新生效。":
        "Restart once to free memory and apply system updates.",
    "可清理的垃圾":
        "Reclaimable junk",
    "约 {0}":
        "about {0}",
    "到“垃圾清理”页清理。":
        "Clean it on the “Junk cleanup” tab.",
    "电源计划":
        "Power plan",
    "需要速度时，在“设置 → 系统 → 电源”里改成“平衡”或“最佳性能”。":
        "When you need speed, switch to “Balanced” or “Best performance” under Settings → System → Power.",
    "；占用最多：{0}":
        "; top memory users: {0}",
    "CPU":
        "CPU",
    "查看“后台进程”页，结束长期高占用且不需要的程序。":
        "Open the “Processes” tab and end programs that use a lot of CPU for a long time and that you don't need.",
    "节能":
        "Power saver",
    "平衡 / 高性能":
        "Balanced / High performance",
    "当前没有运行（可能是一次性任务，无法评估）":
        "Not running right now (possibly a one-off task; cannot be assessed)",
    "占用 {0:.0f}%":
        "{0:.0f}% in use",
    "无需处理":
        "Nothing to do",
    "；占用最高：{0}":
        "; top CPU users: {0}",
    "建议停用，需要时再手动打开":
        "Disable it and start it manually when needed",
    "可以考虑停用":
        "Consider disabling it",
    "影响很小":
        "Very little impact",
    "平均 CPU":
        "Avg CPU",
    "启动时间点":
        "Started",
    "影响":
        "Impact",
    "使用提示：\n  • 不知道从哪开始？点上面的“一键诊断”，按结果里的按钮处理即可。\n  • 所有删除/停用操作都会先让你确认；被删文件优先进回收站（或工具回收站，可找回）。\n  • “自动清理”页可设置每天/每周/每月定时清理，由系统计划任务执行，不需要保持本程序运行。\n  • “钱包安全”页：钱包文件自动受保护、助记词/私钥泄露扫描、挖矿检测、剪贴板劫持守护。\n  • 风险扫描为启发式检测，不能替代专业杀毒软件。":
        "Tips:\n  • Not sure where to start? Click “One-click diagnosis” above and use the buttons in the results.\n  • Every delete/disable action asks you to confirm first; deleted files go to the Recycle Bin (or the tool's own trash) and can be recovered.\n  • On the “Auto clean” tab you can schedule daily/weekly/monthly cleaning; it is run by the system scheduler, so this program doesn't need to stay open.\n  • “Wallet security” tab: automatic wallet-file protection, mnemonic/private-key leak scan, miner detection, clipboard-hijack guard.\n  • The risk scan is a heuristic check and cannot replace professional antivirus software.",
    "💡 建议操作（来自上次诊断）":
        "💡 Suggested actions (from the last diagnosis)",
    "只读检查，不会改动系统。点“开始诊断”，每个问题后面会有可以直接执行或跳转到对应页面的按钮。":
        "Read-only checks; nothing on your system is changed. Click “Start diagnosis”: every problem comes with buttons that run the fix directly or jump to the right page.",
    "{0}（{1} 项待处理）":
        "{0} ({1} to handle)",
    "{0}（正常）":
        "{0} (all good)",
    "全面诊断":
        "Full diagnosis",
    "这个系统没有对应的设置页面，请在系统设置里手动查找。":
        "This system has no matching settings page; please look for it in the system settings.",
    "结束进程 {0}？未保存的数据会丢失。":
        "End process {0}? Unsaved data will be lost.",
    "已结束 {0}":
        "Ended {0}",
    "没有影响较高的启动项。":
        "No startup items with high impact.",
    "🔍 一键诊断（性能 / 存储 / 安全 / 钱包）":
        "🔍 One-click diagnosis (performance / storage / security / wallet)",
    "只检查不改动；发现问题后每一项都有可以直接执行的按钮。":
        "Checks only, changes nothing; every problem found comes with buttons that run the fix directly.",
    "将清理 {0} 类垃圾，共约 {1}。继续？":
        "About to clean {0} kinds of junk, about {1} in total. Continue?",
    "🔍 开始诊断":
        "🔍 Start diagnosis",
    "深度诊断（较慢：大文件、重复文件、整个主目录的钱包与密钥扫描、深度风险扫描）":
        "Deep diagnosis (slower: large files, duplicates, wallet & key scan of the whole home folder, deep risk scan)",
    "显示正常项目":
        "Show items that are fine",
    "已取消，下面只是已完成部分的结果。":
        "Cancelled; below are only the results completed so far.",
    "诊断完成：{0} 项需要处理。点右侧按钮可以直接处理或跳转；对应页面顶部也会列出建议操作。":
        "Diagnosis finished: {0} items need attention. Use the buttons on the right to fix them directly or jump to the page; the matching pages also list the suggested actions at the top.",
    "还没有诊断。点上面的“开始诊断”。":
        "No diagnosis yet. Click “Start diagnosis” above.",
    "✓ 没有发现问题":
        "✓ No problems found",
    "已处理":
        "Done",
    "性能":
        "Performance",
    "存储":
        "Storage",
    "安全":
        "Security",
    "钱包":
        "Wallet",
    "打开 Windows 安全中心":
        "Open Windows Security",
    "打开防火墙设置":
        "Open firewall settings",
    "打开“隐私与安全性”":
        "Open “Privacy & Security”",
    "正在检查：性能与磁盘":
        "Checking: performance and disk",
    "确认里面没有需要的文件后清空。":
        "Empty it after making sure nothing you need is inside.",
    "打开系统安全设置，检查并开启。":
        "Open the system security settings, check it and turn it on.",
    "可以用 sudo ufw enable 启用防火墙。":
        "You can enable the firewall with sudo ufw enable.",
    "正在检查：挖矿木马":
        "Checking: mining trojans",
    "正在检查：内存与 CPU":
        "Checking: memory and CPU",
    "正在检查：{0}":
        "Checking: {0}",
    "查看占用内存的程序":
        "See which programs use the memory",
    "回收站里还有 {0}，清空后才会真正释放空间":
        "The trash still holds {0}; space is only really freed after you empty it",
    "占用 {0}":
        "Uses {0}",
    "工具回收站":
        "Tool trash",
    "Faster 的回收站占用 {0}":
        "Faster's own trash uses {0}",
    "到“还原中心”确认没有需要还原的文件后，再永久清空。":
        "Check the “Restore center” for files you may want back, then empty it permanently.",
    "正在查找重复文件…（较慢）":
        "Looking for duplicate files... (slow)",
    "系统防护":
        "System protection",
    "防火墙、杀毒、系统保护状态正常":
        "Firewall, antivirus and system protection look fine",
    "可疑启动项":
        "Suspicious startup item",
    "如果不是你安装的软件，请停用。":
        "If you did not install this software, disable it.",
    "另有 {0} 个":
        "{0} more",
    "到“启动项”页逐个确认。":
        "Review them one by one on the “Startup” tab.",
    "启动项安全":
        "Startup safety",
    "没有发现可疑的启动项":
        "No suspicious startup items found",
    "hosts 文件被改动":
        "The hosts file was modified",
    "确认这些条目是你自己添加的；不是的话请删除（需要管理员权限）。":
        "Make sure you added these entries yourself; if not, remove them (administrator rights needed).",
    "正在做深度风险扫描…":
        "Running the deep risk scan...",
    "深度风险扫描":
        "Deep risk scan",
    "高危 {0} · 中危 {1} · 提示 {2}":
        "High {0} · Medium {1} · Info {2}",
    "到“风险扫描”页查看每一项的详情。":
        "Open the “Risk scan” tab for details on every item.",
    "未加载，无法检测助记词":
        "Not loaded, so mnemonics can't be detected",
    "下载词表（约 13KB，来自 BIP39 官方仓库，下载后会校验）后才能检测助记词。":
        "Download the word list (about 13KB, from the official BIP39 repo, verified after download) to enable mnemonic detection.",
    "正在扫描主目录里的明文密钥…":
        "Scanning your home folder for plaintext keys...",
    "正在查找钱包文件…":
        "Looking for wallet files...",
    "结束 {0}":
        "End {0}",
    "查看占用 CPU 的程序":
        "See which programs use the CPU",
    "打开回收站查看":
        "Open the trash to look",
    "正在查找大文件…":
        "Looking for large files...",
    "有 {0} 个超过 500MB 的文件，共 {1}；最大的是 {2}（{3}）":
        "{0} files are larger than 500MB, {1} in total; the largest is {2} ({3})",
    "确认哪些不再需要，删除或移到外置硬盘。":
        "Decide which ones you no longer need, then delete them or move them to an external drive.",
    "没有超过 500MB 的文件":
        "No files larger than 500MB",
    "到挖矿检测页查看":
        "Open the miner detection tab",
    "疑似挖矿程序":
        "Suspected miner",
    "如果不是你自己运行的，请结束它并查杀。":
        "If you did not run it yourself, end it and scan your computer.",
    "未发现挖矿迹象":
        "No signs of mining found",
    "云同步目录里的明文密钥":
        "Plaintext keys in a cloud-synced folder",
    "在云同步目录里发现 {0} 处明文助记词/私钥":
        "Found {0} plaintext mnemonics/private keys in a cloud-synced folder",
    "云端会留有副本。建议把资产转到新钱包（新助记词），并删除这些明文文件。":
        "The cloud keeps a copy. Move your assets to a new wallet (new mnemonic) and delete these plaintext files.",
    "云同步目录里的钱包文件":
        "Wallet files in a cloud-synced folder",
    "在云同步目录里发现 {0} 个钱包文件":
        "Found {0} wallet files in a cloud-synced folder",
    "云端会留有副本。建议迁出这些文件，并确认助记词已离线备份。":
        "The cloud keeps a copy. Move these files out and make sure the mnemonic is backed up offline.",
    "云同步目录":
        "Cloud-synced folders",
    "云同步目录里没有发现钱包文件或明文密钥":
        "No wallet files or plaintext keys found in cloud-synced folders",
    "查找大文件":
        "Find large files",
    "停用影响高的启动项":
        "Disable startup items with high impact",
    "清理垃圾（约 {0}）":
        "Clean junk (about {0})",
    "打开电源设置":
        "Open power settings",
    "到还原中心查看":
        "Look in the Restore center",
    "永久清空":
        "Empty permanently",
    "发现 {0} 组重复文件，约浪费 {1}":
        "Found {0} groups of duplicate files, wasting about {1}",
    "保留一份，删除多余的副本。":
        "Keep one copy and delete the extra copies.",
    "没有发现明显浪费空间的重复文件":
        "No duplicate files that waste noticeable space",
    "停用":
        "Disable",
    "到启动项页查看":
        "Look at it on the Startup tab",
    "打开 hosts 所在文件夹":
        "Open the folder that holds hosts",
    "查看详情":
        "View details",
    "下载词表":
        "Download word list",
    "正在检查：云同步目录 {0}":
        "Checking: cloud-synced folder {0}",
    "明文助记词 / 私钥":
        "Plaintext mnemonics / private keys",
    "在主目录发现 {0} 处明文助记词/私钥":
        "Found {0} plaintext mnemonics/private keys in your home folder",
    "建议把资产转到新钱包（新助记词），助记词抄在纸上离线保存，并删除/加密这些明文文件。":
        "Move your assets to a new wallet (new mnemonic), write the mnemonic on paper and keep it offline, and delete/encrypt these plaintext files.",
    "主目录里没有发现明文助记词/私钥":
        "No plaintext mnemonics/private keys found in your home folder",
    "发现 {0} 个钱包文件（{1} 个在云同步目录里），已受 Faster 保护":
        "Found {0} wallet files ({1} of them in cloud-synced folders); Faster protects them",
    "这一项没有检查完：{0}":
        "This check did not finish: {0}",
    "查看大文件":
        "View large files",
    "查看并处理":
        "View and handle",
    "查看钱包文件":
        "View wallet files",
    "打开该文件夹":
        "Open the folder",
    "在云同步目录里的建议迁出，并确认助记词已离线备份。":
        "Move the ones in cloud-synced folders out, and make sure the mnemonic is backed up offline.",
    "确认助记词已离线备份。":
        "Make sure the mnemonic is backed up offline.",
    "查看重复文件":
        "View duplicate files",
    "视频":
        "Video",
    "图片":
        "Images",
    "音频":
        "Audio",
    "文档":
        "Documents",
    "压缩包":
        "Archives",
    "磁盘镜像 / 虚拟机":
        "Disk images / virtual machines",
    "已排除：{0}":
        "Excluded: {0}",
    "{0} 个文件夹":
        "{0} folders",
    "检查签名":
        "Check signatures",
    "停用选中的启动项":
        "Disable selected startup items",
    "结束选中的进程":
        "End selected processes",
    "复制 SHA-256":
        "Copy SHA-256",
    "验证程序签名…":
        "Verifying program signatures...",
    "设为基线":
        "Set as baseline",
    "对比当前":
        "Compare with now",
    "接受当前为新基线":
        "Accept current state as new baseline",
    "记录当前状态…":
        "Recording the current state...",
    "对比基线…":
        "Comparing with the baseline...",
    "检查":
        "Check",
    "执行选中项的修复":
        "Fix the selected item",
    "检查中…":
        "Checking...",
    "排除（这些不会被扫描）":
        "Exclude (these will not be scanned)",
    "选择要排除的文件夹":
        "Choose a folder to exclude",
    "检查开机自启的程序和从用户目录运行的程序有没有可信签名（Linux 上改查“是否属于某个软件包”）。无签名不等于有害，签名有效也不等于一定安全，请结合来源判断。":
        "Checks whether programs that start automatically, and programs running from user folders, carry a trusted signature (on Linux it checks whether the file belongs to an installed package). Unsigned does not mean harmful and a valid signature does not guarantee safety; judge by where the program came from.",
    "基线已建立。":
        "Baseline created.",
    "把当前状态接受为新基线？（说明这些变化是你自己做的）":
        "Accept the current state as the new baseline? (This says the changes were made by you.)",
    "检查系统更新、磁盘加密、远程登录、自动登录、屏幕锁、备份、对外开放的高风险端口等。需要管理员权限的修改，Faster 不会替你做：会打开对应的系统设置，或给出可复制的命令。":
        "Checks system updates, disk encryption, remote login, auto login, screen lock, backups, high-risk open ports and more. Faster never makes changes that need administrator rights for you: it opens the matching system settings or gives you a command to copy.",
    "程序签名":
        "Program signatures",
    "基线对比":
        "Baseline",
    "加固与更新":
        "Hardening & updates",
    "已复制到剪贴板。":
        "Copied to the clipboard.",
    "程序":
        "Program",
    "签名者 / 所属软件包":
        "Signer / owning package",
    "检查了 {0} 个程序，其中 {1} 个需要留意。":
        "Checked {0} programs; {1} need attention.",
    "读不了这个文件，或者文件太大。":
        "Cannot read this file, or it is too large.",
    "类别":
        "Category",
    "变化":
        "Change",
    "内容":
        "Content",
    "基线建立于 {0:%Y-%m-%d %H:%M}。点“对比当前”看多了什么、少了什么。":
        "Baseline created on {0:%Y-%m-%d %H:%M}. Click “Compare with now” to see what was added or removed.",
    "还没有建立基线。确认电脑目前是干净的，点“设为基线”；以后只会提醒你“多了什么”。":
        "No baseline yet. When you are sure the computer is clean, click “Set as baseline”; from then on you are only told what is new.",
    "已经有基线了，要用现在的状态覆盖它吗？":
        "A baseline already exists. Overwrite it with the current state?",
    "检查项":
        "Check",
    "现状":
        "Current state",
    "{0} 项需要处理。选中一行点“执行选中项的修复”。":
        "{0} items need attention. Select a row and click “Fix the selected item”.",
    "文件类型：":
        "File types: ",
    "其他扩展名（如 .psd .ai，用空格隔开）：":
        "Other extensions (such as .psd .ai, separated by spaces): ",
    "文件夹：":
        "Folders: ",
    "移除选中":
        "Remove selected",
    "检查所有运行中的程序（较慢）":
        "Check all running programs (slower)",
    "已复制。可以把它粘贴到 VirusTotal 等网站查询这个文件。":
        "Copied. You can paste it into a site such as VirusTotal to look this file up.",
    "和基线相比有 {0} 处新增。":
        "{0} new items compared with the baseline.",
    "和基线相比没有新增的东西。":
        "Nothing new compared with the baseline.",
    "包含联网检查（待安装的系统更新，较慢）":
        "Include online checks (pending system updates, slower)",
    "新增":
        "Added",
    "消失":
        "Removed",
    "打开 Windows 更新":
        "Open Windows Update",
    "打开远程桌面设置":
        "Open Remote Desktop settings",
    "打开 BitLocker 设置":
        "Open BitLocker settings",
    "打开“软件更新”":
        "Open “Software Update”",
    "打开 FileVault 设置":
        "Open FileVault settings",
    "打开“用户与群组”":
        "Open “Users & Groups”",
    "打开“共享”设置":
        "Open “Sharing” settings",
    "打开 Time Machine 设置":
        "Open Time Machine settings",
    "复制修复命令":
        "Copy the fix command",
    "正在检查：系统更新":
        "Checking: system updates",
    "正在检查：安全加固":
        "Checking: security hardening",
    "程序签名与基线":
        "Program signatures & baseline",
    "到程序签名页查看":
        "See it on the Program signatures tab",
    "如果不是你安装的软件，请停用或结束它；也可以复制文件的 SHA-256 去 VirusTotal 查询。":
        "If you did not install this software, disable or end it; you can also copy the file's SHA-256 and look it up on VirusTotal.",
    "来源可疑的程序":
        "Program from a dubious source",
    "到“程序签名”页逐个确认。":
        "Review them one by one on the “Program signatures” tab.",
    "检查了 {0} 个程序，没有发现签名问题":
        "Checked {0} programs; no signature problems found",
    "还没有建立基线":
        "No baseline yet",
    "在你确认电脑目前干净的时候，把现在的状态记为基线；以后只提醒你“多了什么”。":
        "When you are sure the computer is clean, record its current state as the baseline; from then on you are only told what is new.",
    "这些是我自己装的（接受为新基线）":
        "I installed these myself (accept as new baseline)",
    "查看变化":
        "View changes",
    "{0}有新增":
        "New {0}",
    "新增 {0} 项：{1}":
        "{0} new: {1}",
    "和基线相比多出来的东西。如果不是你做的，请重点核查。":
        "These appeared since the baseline. If you did not do it, check them carefully.",
    "和基线相比，没有新增的启动项、计划任务、端口、管理员账户":
        "Nothing new compared with the baseline: startup items, scheduled tasks, ports, administrator accounts",
    "命令已复制。请在终端 / 管理员 PowerShell 里粘贴运行。":
        "Command copied. Paste it into a terminal / administrator PowerShell and run it.",
    "签名被破坏的程序":
        "Program with a broken signature",
    "到卸载页处理":
        "Handle it on the Uninstall tab",
    "把现在的状态设为基线":
        "Set the current state as the baseline",
    "到基线页查看":
        "See it on the Baseline tab",
    "停用这些启动项":
        "Disable these startup items",
    "查看加固清单":
        "View the hardening checklist",
    "已验证":
        "Verified",
    "签名有效":
        "Signature valid",
    "无签名":
        "Unsigned",
    "不属于任何软件包":
        "Not owned by any package",
    "正在验证 {0} 个程序的签名…":
        "Verifying the signatures of {0} programs...",
    "签名无效":
        "Signature invalid",
    "文件不存在":
        "File missing",
    "无法判断":
        "Cannot tell",
    "计划任务":
        "Scheduled tasks",
    "对外监听端口":
        "Externally listening ports",
    "hosts 条目":
        "hosts entries",
    "管理员账户":
        "Administrator accounts",
    "SSH 授权密钥":
        "SSH authorized keys",
    "已安装程序":
        "Installed programs",
    "已停止维护的软件":
        "Software that is no longer maintained",
    "发现：{0}":
        "Found: {0}",
    "这些软件不再收到安全更新，建议卸载或换成新版。":
        "This software no longer receives security updates; uninstall it or switch to a newer version.",
    "系统更新":
        "System updates",
    "读不到补丁安装记录":
        "Cannot read the patch installation history",
    "打开 Windows 更新，手动检查一下。":
        "Open Windows Update and check by hand.",
    "最近一次补丁安装在 {0} 天前":
        "The last patch was installed {0} days ago",
    "很久没装补丁了：打开 Windows 更新，检查并安装更新。":
        "It has been a long time since the last patch: open Windows Update and install the updates.",
    "需要重启":
        "Restart needed",
    "更新已经安装，重启后才生效":
        "Updates are installed and only take effect after a restart",
    "保存好工作后重启电脑。":
        "Save your work, then restart the computer.",
    "待安装的更新":
        "Pending updates",
    "没能连上更新服务":
        "Could not reach the update service",
    "检查网络，或直接打开 Windows 更新。":
        "Check your network, or open Windows Update directly.",
    "自动检查更新已关闭":
        "Automatic update checking is off",
    "到“软件更新”里打开自动检查，安全更新才能及时装上。":
        "Turn on automatic checking in “Software Update” so security updates are installed in time.",
    "有 {0} 个更新没装：{1}":
        "{0} updates are not installed: {1}",
    "到 Windows 更新里安装。":
        "Install them in Windows Update.",
    "没有待安装的更新":
        "No pending updates",
    "没有开启“自动安装安全响应和系统文件”":
        "“Install security responses and system files automatically” is off",
    "建议在“软件更新”的高级选项里打开。":
        "Turn it on in the advanced options of “Software Update”.",
    "自动更新已开启":
        "Automatic updates are on",
    "没能查询更新":
        "Could not query updates",
    "打开“软件更新”手动检查。":
        "Open “Software Update” and check by hand.",
    "有 {0} 个软件包可更新，其中 {1} 个是安全更新":
        "{0} packages can be updated, {1} of them security updates",
    "尽快更新：复制命令，在终端里运行。":
        "Update soon: copy the command and run it in a terminal.",
    "软件包索引":
        "Package index",
    "已经 {0:.0f} 天没刷新":
        "Not refreshed for {0:.0f} days",
    "先刷新索引才能看到最新的更新。":
        "Refresh the index first to see the latest updates.",
    "有 {0} 个软件包可更新":
        "{0} packages can be updated",
    "复制命令，在终端里运行。":
        "Copy the command and run it in a terminal.",
    "到“软件更新”里安装。":
        "Install them in “Software Update”.",
    "已是最新（以本机的软件包索引为准）":
        "Up to date (according to this machine's package index)",
    "远程桌面":
        "Remote Desktop",
    "VNC / 屏幕共享":
        "VNC / screen sharing",
    "用户账户控制（UAC）":
        "User Account Control (UAC)",
    "已关闭":
        "Turned off",
    "UAC 是拦截程序偷偷提权的第一道门，建议开启。":
        "UAC is the first gate that stops programs from elevating themselves silently; turn it on.",
    "自动登录":
        "Automatic login",
    "开机不用输密码就进入系统":
        "The system is entered at startup without a password",
    "别人拿到电脑就能直接用，建议关闭自动登录。":
        "Anyone who gets the computer can use it directly; turn automatic login off.",
    "已开启":
        "Turned on",
    "不需要远程控制本机就关掉；要用请设置强密码并只在可信网络使用。":
        "Turn it off if you don't need to control this computer remotely; if you do, set a strong password and use it only on trusted networks.",
    "SMBv1 协议":
        "SMBv1 protocol",
    "SMBv1 有严重的已知漏洞（勒索病毒常用）。以管理员身份打开 PowerShell 运行命令关闭它。":
        "SMBv1 has serious known vulnerabilities (favoured by ransomware). Open PowerShell as administrator and run the command to turn it off.",
    "安全启动（Secure Boot）":
        "Secure Boot",
    "未开启":
        "Not turned on",
    "可在 BIOS/UEFI 里开启，能防止启动阶段被植入恶意程序。":
        "Turn it on in the BIOS/UEFI; it stops malware from being planted during startup.",
    "磁盘加密（BitLocker）":
        "Disk encryption (BitLocker)",
    "系统盘已加密":
        "The system drive is encrypted",
    "磁盘加密（FileVault）":
        "Disk encryption (FileVault)",
    "访客账户":
        "Guest account",
    "不需要就关掉。":
        "Turn it off if you don't need it.",
    "屏幕锁":
        "Screen lock",
    "唤醒屏幕时不要求输入密码":
        "No password is required when the screen wakes up",
    "建议开启：离开座位时别人无法直接使用。":
        "Turn it on: others cannot use the computer directly when you step away.",
    "备份（Time Machine）":
        "Backup (Time Machine)",
    "没有配置备份":
        "No backup configured",
    "硬盘坏了、被勒索病毒加密时，备份是唯一的退路。":
        "A backup is the only way back when the disk fails or ransomware encrypts your files.",
    "对外开放的高风险端口":
        "High-risk ports open to the network",
    "这些服务对整个局域网/互联网开放。不需要就关闭对应的服务；要用请设置强密码。":
        "These services are open to the whole LAN/Internet. Turn off the matching service if you don't need it; if you do, set a strong password.",
    "系统盘没有加密":
        "The system drive is not encrypted",
    "电脑丢失或被拆硬盘时，里面的数据可以被直接读取。家庭版 Windows 可能不支持 BitLocker，可看“设备加密”。":
        "If the computer is lost or its disk is removed, the data can be read directly. Windows Home may not support BitLocker; look for “Device encryption”.",
    "没有开启":
        "Not turned on",
    "电脑丢失时里面的数据可以被直接读取，建议开启。":
        "If the computer is lost, the data can be read directly; turn it on.",
    "已配置备份":
        "Backup configured",
    "磁盘加密":
        "Disk encryption",
    "检测到加密卷":
        "Encrypted volumes found",
    "没有检测到全盘加密（LUKS）":
        "No full-disk encryption (LUKS) detected",
    "新装系统时建议启用磁盘加密；已安装的系统很难事后补加。":
        "Enable disk encryption when installing the system; it is hard to add afterwards.",
    "SSH 服务":
        "SSH service",
    "允许 root 直接登录":
        "Root login is allowed",
    "在 /etc/ssh/sshd_config 里把 PermitRootLogin 改成 no，然后重启 sshd。":
        "Change PermitRootLogin to no in /etc/ssh/sshd_config, then restart sshd.",
    "自动安全更新":
        "Automatic security updates",
    "开启后安全补丁会自动安装。复制命令，在终端里运行。":
        "Once on, security patches install themselves. Copy the command and run it in a terminal.",
    "屏幕保护时不要求输入密码":
        "No password is required after the screen saver",
    "可在 BIOS/UEFI 里开启。":
        "Turn it on in the BIOS/UEFI.",
    "安全加固":
        "Security hardening",
    "允许用密码登录":
        "Password login is allowed",
    "改用密钥登录更安全：把 PasswordAuthentication 改成 no。":
        "Key-based login is safer: change PasswordAuthentication to no.",
    "正在运行（端口 22）":
        "Running (port 22)",
    "不需要远程登录的话请停用它。":
        "Stop it if you don't need remote login.",
    "健康分":
        "Health score",
    "让电脑更快、更安全":
        "Faster, safer computing",
    "扫描开发缓存":
        "Scan developer caches",
    "查找旧项目依赖":
        "Find old project dependencies",
    "清理选中":
        "Clean selected",
    "扫描开发缓存…":
        "Scanning developer caches...",
    "查找长期没动的项目依赖…":
        "Looking for project dependencies nobody has touched for a long time...",
    "分析空间占用…":
        "Analyzing disk usage...",
    "这些东西都能再生（重新下载 / 重新构建），清理是安全的，只是下次用会慢一些、要联网。缓存是永久删除；旧项目的依赖目录进回收站，可在“还原中心”还原。":
        "All of these can be regenerated (re-downloaded / rebuilt), so cleaning is safe; the next use is just a little slower and needs the network. Caches are deleted permanently; old project dependency folders go to the Recycle Bin and can be restored from the “Restore center”.",
    "{0} · {1} 天没动过":
        "{0} · untouched for {1} days",
    "清理选中的 {0} 项（约 {1}）？\n缓存会被永久删除，项目依赖目录会移到回收站。这些都能重新生成。":
        "Clean the {0} selected items (about {1})?\nCaches are deleted permanently and project dependency folders go to the Recycle Bin. All of them can be regenerated.",
    "将清理 {0} 个工具的缓存，共约 {1}。缓存会被永久删除，但都能重新生成。继续？":
        "About to clean the caches of {0} tools, about {1} in total. Caches are deleted permanently, but all of them can be regenerated. Continue?",
    "面积越大占的空间越多。点一块选中，双击进入文件夹；灰色的块是文件，浅灰色是许多小项的合计。":
        "The bigger the tile, the more space it uses. Click a tile to select it and double-click a folder to open it; grey tiles are files and light grey is the total of many small items.",
    "先点选一块要处理的文件或文件夹。":
        "Click a file or folder tile first.",
    "将“{0}”（{1}）移到回收站？可以在“还原中心”或系统回收站里找回。":
        "Move “{0}” ({1}) to the Recycle Bin? You can get it back from the “Restore center” or the system trash.",
    "开发者清理":
        "Developer cleanup",
    "空间分析":
        "Space analysis",
    "缓存":
        "Cache",
    "项目依赖":
        "Project deps",
    "共 {0} 项，约 {1}。选中后点“清理选中”。":
        "{0} items, about {1}. Select some and click “Clean selected”.",
    "没有发现可清理的开发缓存。":
        "No developer caches found to clean.",
    "已清理，释放约 {0}":
        "Cleaned, freed about {0}",
    "点“开始分析”，看看空间都被谁占了。":
        "Click “Start analysis” to see what is using your space.",
    "超过":
        "Older than",
    "天没动过":
        "days untouched",
    "清理开发缓存":
        "Clean developer caches",
    "开始分析":
        "Start analysis",
    "选择文件夹…":
        "Choose folder...",
    "上一级":
        "Up one level",
    "移到回收站":
        "Move to Recycle Bin",
    "{0}：共 {1}，{2} 项。双击文件夹进入，点一块选中。":
        "{0}: {1} in total, {2} items. Double-click a folder to open it, click a tile to select it.",
    "（已取消，只是部分结果）":
        "(cancelled, partial results only)",
    "正在检查：开发者缓存":
        "Checking: developer caches",
    "正在查找长期没动的项目依赖…":
        "Looking for project dependencies untouched for a long time...",
    "开发者缓存":
        "Developer caches",
    "{0} 个工具的缓存共约 {1}；最大的是 {2}（{3}）":
        "The caches of {0} tools use about {1}; the largest is {2} ({3})",
    "这些缓存都能重新生成，清理后第一次构建会慢一些。":
        "All of these caches can be regenerated; the first build after cleaning is a little slower.",
    "查看空间占用":
        "View space usage",
    "旧项目的依赖目录":
        "Dependency folders of old projects",
    "{0} 个超过 90 天没动过的项目里，依赖目录共约 {1}":
        "In {0} projects untouched for over 90 days, dependency folders use about {1}",
    "这些目录能用一条命令重新生成；清理后会进回收站，可以在“还原中心”还原。":
        "These folders can be regenerated with one command; after cleaning they go to the Recycle Bin and can be restored from the “Restore center”.",
    "清理开发缓存（约 {0}）":
        "Clean developer caches (about {0})",
    "查看明细":
        "View details",
    "查看并清理":
        "View and clean",
    "缓存，清理后会在需要时自动重新下载":
        "Cache; it is downloaded again automatically when needed",
    "构建缓存，清理后第一次构建会慢一些":
        "Build cache; the first build after cleaning is a little slower",
    "依赖缓存，清理后下次构建需要重新下载（要联网）":
        "Dependency cache; the next build must download it again (needs the network)",
    "Node.js 项目的依赖":
        "Dependencies of a Node.js project",
    "Rust 项目的编译产物":
        "Build output of a Rust project",
    "Python 虚拟环境":
        "Python virtual environment",
    "构建缓存":
        "build cache",
    "模块缓存":
        "module cache",
    "编译产物，Xcode 会自动重新生成":
        "Build output; Xcode regenerates it automatically",
    "调试用的设备支持文件，下次连接设备时会重新生成":
        "Device support files for debugging; regenerated the next time you connect a device",
    "Docker 的构建缓存，清理后重新构建会慢一些":
        "Docker's build cache; rebuilding is a little slower after cleaning",
    "没有被任何容器使用的镜像，需要时会重新拉取":
        "Images not used by any container; they are pulled again when needed",
    "未使用的镜像":
        "unused images",
    "其他 {0} 项":
        "{0} other items",
    "立即备份重要数据，并准备更换硬盘。":
        "Back up your important data right now and get ready to replace the drive.",
    "SMART 自检：通过":
        "SMART self-test: passed",
    "SMART 自检：失败":
        "SMART self-test: failed",
    "需要管理员权限才能读取 SMART":
        "Administrator rights are needed to read SMART",
    "健康状态：不健康":
        "Health status: unhealthy",
    "SMART 状态：即将故障":
        "SMART status: failing",
    "磁盘健康":
        "Disk health",
    "健康状态：{0}（{1}）":
        "Health status: {0} ({1})",
    "SMART 状态：正常":
        "SMART status: OK",
    "已磨损 {0}%":
        "{0}% worn",
    "温度 {0}℃":
        "Temperature {0}℃",
    "累计读写错误 {0} 次":
        "{0} read/write errors in total",
    "健康":
        "Healthy",
    "没有安装 smartmontools，读不到 SMART":
        "smartmontools is not installed, so SMART cannot be read",
    "安装后才能查看硬盘健康状态。":
        "Install it to see the drive's health status.",
}
