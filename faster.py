#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Faster Faster  (Windows / macOS / Linux)

功能：
  1. 存储空间优化：清理垃圾缓存、大文件列表（大->小，用户勾选）、重复文件
  2. 运行速度优化：开机启动项管理（可恢复）、后台进程结束、卸载程序
  3. 潜在风险扫描：可疑进程/端口/持久化/hosts/计划任务/临时目录可执行文件，
                    并可调用系统自带杀毒引擎（Defender / ClamAV）

设计原则（安全第一）：
  * 所有删除/停用操作都要用户确认；不确定的内容只“列出建议”，由用户选择
  * 文件删除优先进回收站；没有 send2trash 时移动到 ~/.faster/trash（可找回）
  * 启动项停用前自动备份，可在菜单中恢复
  * 不触碰系统关键进程和系统目录
  * 安全扫描是启发式检测，不能替代专业杀毒软件

依赖：Python 3.8+。可选：pip install psutil send2trash
"""
__version__ = "0.2.0"

import os
import sys
import re
import csv
import json
import time
import shutil
import heapq
import hashlib
import platform
import subprocess
import datetime
from pathlib import Path
from collections import defaultdict

try:
    import psutil
except ImportError:
    psutil = None
try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

SYSTEM = platform.system()
IS_WIN, IS_MAC, IS_LINUX = SYSTEM == "Windows", SYSTEM == "Darwin", SYSTEM == "Linux"
HOME = Path.home()
APP_DIR = HOME / ".faster"
BACKUP_DIR = APP_DIR / "backup"
TRASH_DIR = APP_DIR / "trash"
REPORT_DIR = APP_DIR / "reports"
MANIFEST = BACKUP_DIR / "manifest.json"
# 从 v0.1.0（旧名称 PC Optimizer）升级：迁移数据目录，并修正备份清单里的路径
_OLD_APP_DIR = HOME / ".pc_optimizer"
if _OLD_APP_DIR.exists() and not APP_DIR.exists():
    try:
        _OLD_APP_DIR.rename(APP_DIR)
        _mf = APP_DIR / "backup" / "manifest.json"
        if _mf.exists():
            _mf.write_text(_mf.read_text(encoding="utf-8").replace(".pc_optimizer", ".faster"), encoding="utf-8")
    except OSError:
        pass
for d in (BACKUP_DIR, TRASH_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------- 通用工具
# 钱包文件保护：清理 / 大文件 / 重复文件 / 自动清理一律跳过，safe_remove 也会拒绝
try:
    from faster_crypto import is_wallet_path
except Exception:  # 保护模块缺失时退化为不保护（不影响其余功能）
    def is_wallet_path(path):
        return False


def human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024


def confirm(msg, default=False):
    s = input(f"{msg} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    return default if not s else s in ("y", "yes", "是", "好")


def parse_selection(s, n):
    """'1,3,5-8' / 'all' -> 0-based 下标集合"""
    s = s.strip().lower()
    if s in ("all", "a", "全部"):
        return list(range(n))
    out = set()
    for tok in re.split(r"[,\s，]+", s):
        if not tok:
            continue
        try:
            if "-" in tok:
                a, b = tok.split("-", 1)
                out.update(range(int(a) - 1, int(b)))
            else:
                out.add(int(tok) - 1)
        except ValueError:
            pass
    return sorted(i for i in out if 0 <= i < n)


def run(cmd, timeout=60, shell=False):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, shell=shell,
                           creationflags=0x08000000 if IS_WIN else 0)  # Windows 下不弹黑窗
        return r.returncode, r.stdout.decode(errors="replace"), r.stderr.decode(errors="replace")
    except Exception as e:
        return -1, "", str(e)


def is_admin():
    try:
        if IS_WIN:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def safe_remove(path):
    """进回收站；失败则移动到 ~/.faster/trash（可找回）。钱包文件一律拒绝"""
    path = str(path)
    if is_wallet_path(path):
        print(f"   ✗ 已保护（钱包文件），不处理：{path}")
        return False
    try:
        if send2trash:
            send2trash(path)
            return True
        dest = TRASH_DIR / f"{int(time.time())}_{os.urandom(2).hex()}_{os.path.basename(path)}"
        shutil.move(path, dest)
        return True
    except Exception as e:
        print(f"   ✗ 无法处理 {path}: {e}")
        return False


def header(t):
    print("\n" + "=" * 62 + f"\n  {t}\n" + "=" * 62)


# ------------------------------------------------------------ 1. 存储空间
def junk_targets():
    t = []
    if IS_WIN:
        local = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData/Local"))
        t += [("用户临时文件", Path(os.environ.get("TEMP", local / "Temp"))),
              ("系统临时文件(需管理员)", Path(os.environ.get("WINDIR", "C:/Windows")) / "Temp"),
              ("Windows 更新下载缓存(需管理员)", Path(os.environ.get("WINDIR", "C:/Windows")) / "SoftwareDistribution/Download"),
              ("IE/Edge 旧缓存", local / "Microsoft/Windows/INetCache"),
              ("Chrome 缓存", local / "Google/Chrome/User Data/Default/Cache"),
              ("Chrome 代码缓存", local / "Google/Chrome/User Data/Default/Code Cache"),
              ("Edge 缓存", local / "Microsoft/Edge/User Data/Default/Cache"),
              ("Edge 代码缓存", local / "Microsoft/Edge/User Data/Default/Code Cache"),
              ("崩溃转储", local / "CrashDumps")]
    elif IS_MAC:
        t += [("用户应用缓存", HOME / "Library/Caches"),
              ("用户日志", HOME / "Library/Logs"),
              ("废纸篓", HOME / ".Trash")]
    else:
        t += [("用户缓存 ~/.cache", HOME / ".cache"),
              ("回收站", HOME / ".local/share/Trash/files"),
              ("回收站信息", HOME / ".local/share/Trash/info"),
              ("缩略图缓存", HOME / ".thumbnails")]
    return [(n, p) for n, p in t if p.exists()]


def list_files_in(path, min_age_hours=1):
    """列出目录下（1 小时内未被修改，避免删除正在使用的）文件"""
    now, res = time.time(), []
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            fp = os.path.join(root, f)
            if is_wallet_path(fp):
                continue
            try:
                st = os.lstat(fp)
                if now - st.st_mtime >= min_age_hours * 3600:
                    res.append((fp, st.st_size))
            except OSError:
                pass
    return res


def clean_junk():
    header("清理系统垃圾 / 缓存")
    targets = junk_targets()
    scanned = []
    for name, p in targets:
        files = list_files_in(p)
        size = sum(s for _, s in files)
        scanned.append((name, p, files, size))
    scanned = [x for x in scanned if x[3] > 0]
    if not scanned:
        print("没有发现可清理的垃圾文件。")
        return
    scanned.sort(key=lambda x: -x[3])
    for i, (name, p, files, size) in enumerate(scanned, 1):
        print(f"{i:>3}. {human(size):>10}  {name}  ({len(files)} 个文件)\n       {p}")
    print(f"\n合计可释放：{human(sum(x[3] for x in scanned))}")
    print("提示：清理浏览器缓存会让网页首次加载稍慢，但不会删除密码/书签。")
    sel = parse_selection(input("输入要清理的编号（如 1,3 / all / 直接回车取消）："), len(scanned))
    if not sel or not confirm(f"确认清理选中的 {len(sel)} 项？"):
        return
    freed = 0
    for i in sel:
        for fp, sz in scanned[i][2]:
            try:
                os.remove(fp)
                freed += sz
            except OSError:
                pass  # 正在使用/无权限，跳过
    if IS_WIN and confirm("是否清空回收站？"):
        try:
            import ctypes
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
        except Exception as e:
            print("清空回收站失败：", e)
    print(f"✔ 已释放约 {human(freed)}")
    if IS_LINUX:
        print("提示：apt 缓存 / systemd 日志需 root，可手动执行 `sudo apt clean` 与 `sudo journalctl --vacuum-size=200M`")


SKIP_DIR_NAMES = {"$recycle.bin", "system volume information", "windows", "program files",
                  "program files (x86)", "programdata", "appdata", ".git", "node_modules",
                  "proc", "sys", "dev", "system", "usr", "bin", "sbin", "etc", "var", "lib",
                  "snap", "library", "site-packages", ".faster"}
SKIP_DIR_SUFFIX = (".app", ".photoslibrary", ".framework", ".bundle")
SKIP_FILE_EXT = {".dll", ".sys", ".so", ".dylib", ".plist", ".kext", ".drv", ".msi"}


def walk_user_files(root, min_size):
    for r, dirs, files in os.walk(root, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_NAMES
                   and not d.lower().endswith(SKIP_DIR_SUFFIX)
                   and not os.path.islink(os.path.join(r, d))]
        for f in files:
            if os.path.splitext(f)[1].lower() in SKIP_FILE_EXT:
                continue
            fp = os.path.join(r, f)
            if is_wallet_path(fp):
                continue
            try:
                if os.path.islink(fp):
                    continue
                st = os.stat(fp)
                if st.st_size >= min_size:
                    yield fp, st.st_size, st.st_mtime
            except OSError:
                pass


def ask_root():
    s = input(f"扫描目录（回车=用户主目录 {HOME}）：").strip().strip('"')
    p = Path(s) if s else HOME
    if not p.is_dir():
        print("目录不存在。")
        return None
    return p


def delete_selected(items):
    """items: [(path,size,...)]"""
    sel = parse_selection(input("输入要删除的编号（如 1,3,5-8 / all / 回车取消）："), len(items))
    if not sel:
        return
    total = sum(items[i][1] for i in sel)
    print(f"将处理 {len(sel)} 个文件，共 {human(total)}")
    where = "回收站" if send2trash else f"{TRASH_DIR}（可手动找回）"
    if not confirm(f"确认移动到 {where}？"):
        return
    freed = 0
    for i in sel:
        if safe_remove(items[i][0]):
            freed += items[i][1]
    print(f"✔ 已处理，释放约 {human(freed)}")


def large_files():
    header("大文件列表（从大到小，由你决定是否删除）")
    root = ask_root()
    if not root:
        return
    try:
        mb = float(input("只显示大于多少 MB 的文件？(默认 100) ").strip() or 100)
        top = int(input("最多显示多少个？(默认 50) ").strip() or 50)
    except ValueError:
        mb, top = 100, 50
    print("扫描中，请稍候……")
    heap = heapq.nlargest(top, walk_user_files(root, int(mb * 1024 * 1024)), key=lambda x: x[1])
    if not heap:
        print("没有找到符合条件的文件。")
        return
    now = time.time()
    for i, (fp, sz, mt) in enumerate(heap, 1):
        age = int((now - mt) / 86400)
        print(f"{i:>3}. {human(sz):>10}  {age:>4}天前修改  {fp}")
    print("\n⚠ 这些文件无法自动判断是否有用（可能是视频、虚拟机、安装包等），请自行甄别。")
    delete_selected(heap)


def sha256(path, limit=None):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(limit) if limit else b"")
            if not limit:
                f.seek(0)
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def duplicate_files():
    header("重复文件查找")
    root = ask_root()
    if not root:
        return
    print("扫描中（>=1MB 的文件），请稍候……")
    by_size = defaultdict(list)
    for fp, sz, mt in walk_user_files(root, 1024 * 1024):
        by_size[sz].append((fp, mt))
    groups = []
    for sz, lst in by_size.items():
        if len(lst) < 2:
            continue
        quick = defaultdict(list)
        for fp, mt in lst:
            h = sha256(fp, 65536)
            if h:
                quick[h].append((fp, mt))
        for q in quick.values():
            if len(q) < 2:
                continue
            full = defaultdict(list)
            for fp, mt in q:
                h = sha256(fp)
                if h:
                    full[h].append((fp, mt))
            groups += [(sz, g) for g in full.values() if len(g) > 1]
    if not groups:
        print("没有发现重复文件。")
        return
    groups.sort(key=lambda x: -x[0] * (len(x[1]) - 1))
    candidates = []
    for gi, (sz, g) in enumerate(groups[:40], 1):
        g.sort(key=lambda x: (len(x[0]), x[1]))  # 保留路径最短/最早的一个
        print(f"\n[组{gi}] 每个 {human(sz)}，保留：{g[0][0]}")
        for fp, _ in g[1:]:
            candidates.append((fp, sz))
            print(f"  {len(candidates):>3}. 副本：{fp}")
    print(f"\n删除全部副本可释放：{human(sum(s for _, s in candidates))}")
    delete_selected(candidates)


# ------------------------------------------------------------ 2. 运行速度
def load_manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_manifest(m):
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def get_startup_items():
    items = []
    if IS_WIN:
        import winreg
        targets = [(winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                   (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
                   (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")]
        for hive, hn, key in targets:
            try:
                with winreg.OpenKey(hive, key) as k:
                    i = 0
                    while True:
                        try:
                            name, val, typ = winreg.EnumValue(k, i)
                        except OSError:
                            break
                        items.append(dict(kind="reg", name=name, cmd=str(val), hive=hn, key=key, regtype=typ))
                        i += 1
            except OSError:
                pass
        for d in (Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup",
                  Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs/StartUp"):
            if d.is_dir():
                for f in d.iterdir():
                    if f.name.lower() != "desktop.ini":
                        items.append(dict(kind="file", name=f.name, cmd=str(f), path=str(f)))
    elif IS_MAC:
        import plistlib
        for d in (HOME / "Library/LaunchAgents", Path("/Library/LaunchAgents")):
            if d.is_dir():
                for f in d.glob("*.plist"):
                    if f.name.startswith("com.apple."):
                        continue
                    try:
                        pl = plistlib.loads(f.read_bytes())
                        cmd = pl.get("Program") or " ".join(pl.get("ProgramArguments", []))
                    except Exception:
                        cmd = "(无法解析)"
                    items.append(dict(kind="launchd", name=f.stem, cmd=cmd, path=str(f)))
    else:
        for d, own in ((HOME / ".config/autostart", True), (Path("/etc/xdg/autostart"), False)):
            if d.is_dir():
                for f in d.glob("*.desktop"):
                    if not own and (HOME / ".config/autostart" / f.name).exists():
                        continue
                    cmd = ""
                    try:
                        for line in f.read_text(errors="replace").splitlines():
                            if line.startswith("Exec="):
                                cmd = line[5:]
                    except OSError:
                        pass
                    items.append(dict(kind="desktop", name=f.stem, cmd=cmd, path=str(f), own=own))
    return items


def disable_startup(it):
    m = load_manifest()
    ts = int(time.time())
    try:
        if it["kind"] == "reg":
            import winreg
            hive = winreg.HKEY_CURRENT_USER if it["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            with winreg.OpenKey(hive, it["key"], 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, it["name"])
            m.append(dict(type="reg", **{x: it[x] for x in ("hive", "key", "name", "cmd", "regtype")}, ts=ts))
        elif it["kind"] in ("file", "launchd", "desktop"):
            src = Path(it["path"])
            if it["kind"] == "launchd":
                run(["launchctl", "unload", "-w", str(src)])
            if it["kind"] == "desktop" and not it.get("own", True):
                dst = HOME / ".config/autostart" / src.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text("[Desktop Entry]\nHidden=true\n")
                m.append(dict(type="file_created", path=str(dst), name=it["name"], ts=ts))
            else:
                dst = BACKUP_DIR / f"{ts}_{src.name}"
                shutil.move(str(src), dst)
                m.append(dict(type="file_moved", orig=str(src), backup=str(dst), name=it["name"],
                              launchd=it["kind"] == "launchd", ts=ts))
        save_manifest(m)
        return True
    except Exception as e:
        print(f"   ✗ 停用失败（可能需要管理员权限）：{e}")
        return False


def startup_manager():
    header("开机启动项管理（停用可随时恢复）")
    items = get_startup_items()
    if not items:
        print("没有发现启动项。")
    else:
        for i, it in enumerate(items, 1):
            print(f"{i:>3}. {it['name']}\n       {it['cmd'][:110]}")
        print("\n建议停用：更新检查器、云盘/聊天工具自启、各类“助手/管家”。杀毒软件、输入法、驱动相关请保留。")
        sel = parse_selection(input("输入要停用的编号（回车跳过）："), len(items))
        if sel and confirm(f"确认停用 {len(sel)} 个启动项？"):
            for i in sel:
                if disable_startup(items[i]):
                    print(f"   ✔ 已停用 {items[i]['name']}")
    if load_manifest() and confirm("是否查看/恢复已停用的启动项？"):
        restore_startup()


def restore_startup():
    m = load_manifest()
    active = [e for e in m if not e.get("restored")]
    if not active:
        print("没有可恢复的项目。")
        return
    for i, e in enumerate(active, 1):
        print(f"{i:>3}. {e.get('name')}  ({datetime.datetime.fromtimestamp(e['ts']):%Y-%m-%d %H:%M})")
    for i in parse_selection(input("输入要恢复的编号："), len(active)):
        e = active[i]
        try:
            if e["type"] == "reg":
                import winreg
                hive = winreg.HKEY_CURRENT_USER if e["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
                with winreg.OpenKey(hive, e["key"], 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, e["name"], 0, e["regtype"], e["cmd"])
            elif e["type"] == "file_moved":
                shutil.move(e["backup"], e["orig"])
                if e.get("launchd"):
                    run(["launchctl", "load", "-w", e["orig"]])
            elif e["type"] == "file_created":
                os.remove(e["path"])
            e["restored"] = True
            print(f"   ✔ 已恢复 {e['name']}")
        except Exception as ex:
            print(f"   ✗ 恢复失败：{ex}")
    save_manifest(m)


PROTECTED = {
    "win": {"system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
            "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe", "sihost.exe",
            "taskhostw.exe", "ctfmon.exe", "searchhost.exe", "runtimebroker.exe", "startmenuexperiencehost.exe",
            "shellexperiencehost.exe", "audiodg.exe", "msmpeng.exe", "securityhealthservice.exe", "python.exe",
            "conhost.exe", "wudfhost.exe", "spoolsv.exe", "dllhost.exe", "textinputhost.exe"},
    "mac": {"kernel_task", "launchd", "windowserver", "finder", "dock", "systemuiserver", "loginwindow",
            "coreaudiod", "mds", "mds_stores", "cfprefsd", "distnoted", "notificationcenter", "controlcenter",
            "python", "python3", "terminal", "iterm2"},
    "linux": {"systemd", "init", "xorg", "xwayland", "gnome-shell", "kwin_x11", "kwin_wayland", "plasmashell",
              "dbus-daemon", "pipewire", "pulseaudio", "networkmanager", "sshd", "python", "python3", "bash",
              "zsh", "gdm", "sddm", "lightdm", "gnome-session-b"},
}


def process_manager():
    header("后台进程管理（仅显示当前用户的非系统关键进程）")
    if not psutil:
        print("需要 psutil 库：请先执行  pip install psutil")
        return
    prot = PROTECTED["win" if IS_WIN else "mac" if IS_MAC else "linux"]
    me, my_pid = psutil.Process().username(), os.getpid()
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "memory_info"]):
        try:
            p.cpu_percent(None)
            procs.append(p)
        except Exception:
            pass
    time.sleep(1)
    rows = []
    for p in procs:
        try:
            nm = (p.info["name"] or "").lower()
            if p.info["username"] != me or p.pid in (my_pid, os.getppid()) or nm in prot:
                continue
            rows.append((p, p.info["memory_info"].rss, p.cpu_percent(None)))
        except Exception:
            pass
    rows.sort(key=lambda x: -x[1])
    rows = rows[:30]
    print(f"{'编号':>3}  {'PID':>7}  {'内存':>9}  {'CPU%':>5}  名称")
    for i, (p, mem, cpu) in enumerate(rows, 1):
        print(f"{i:>3}  {p.pid:>7}  {human(mem):>9}  {cpu:>5.1f}  {p.info['name']}")
    print("\n⚠ 结束进程会丢失该程序未保存的数据；系统关键进程已自动隐藏。")
    sel = parse_selection(input("输入要结束的编号（回车跳过）："), len(rows))
    if not sel or not confirm(f"确认结束 {len(sel)} 个进程？"):
        return
    for i in sel:
        p = rows[i][0]
        try:
            p.terminate()
            p.wait(3)
            print(f"   ✔ 已结束 {p.info['name']}")
        except psutil.TimeoutExpired:
            print(f"   … {p.info['name']} 未响应，未强制结束（可在任务管理器中手动处理）")
        except Exception as e:
            print(f"   ✗ {p.info['name']}: {e}")


def installed_programs():
    apps = []
    if IS_WIN:
        import winreg
        roots = [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                 (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                 (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]
        seen = set()
        for hive, key in roots:
            try:
                with winreg.OpenKey(hive, key) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            with winreg.OpenKey(k, winreg.EnumKey(k, i)) as sk:
                                def g(n):
                                    try:
                                        return winreg.QueryValueEx(sk, n)[0]
                                    except OSError:
                                        return None
                                name, cmd = g("DisplayName"), g("UninstallString")
                                if not name or not cmd or g("SystemComponent") == 1 or g("ParentKeyName") or name in seen:
                                    continue
                                seen.add(name)
                                apps.append(dict(name=name, size=(g("EstimatedSize") or 0) * 1024, cmd=cmd))
                        except OSError:
                            pass
            except OSError:
                pass
    elif IS_MAC:
        for f in Path("/Applications").glob("*.app"):
            apps.append(dict(name=f.stem, size=dir_size(f), path=str(f)))
    else:
        if shutil.which("dpkg-query"):
            _, out, _ = run(["dpkg-query", "-W", "-f=${Installed-Size}\t${Package}\n"])
            mgr = "sudo apt-get remove"
            for line in out.splitlines():
                try:
                    sz, nm = line.split("\t")
                    if not nm.startswith(("lib", "linux-", "systemd", "firmware", "base-", "python3", "gcc", "grub",
                                          "ubuntu-", "xserver", "xorg", "gnome-shell", "network-manager")):
                        apps.append(dict(name=nm, size=int(sz or 0) * 1024, cmd=f"{mgr} {nm}"))
                except ValueError:
                    pass
        elif shutil.which("rpm"):
            _, out, _ = run(["rpm", "-qa", "--qf", "%{SIZE}\t%{NAME}\n"])
            for line in out.splitlines():
                try:
                    sz, nm = line.split("\t")
                    if not nm.startswith(("lib", "kernel", "systemd", "glibc", "bash", "python3")):
                        apps.append(dict(name=nm, size=int(sz), cmd=f"sudo dnf remove {nm}"))
                except ValueError:
                    pass
        if shutil.which("flatpak"):
            _, out, _ = run(["flatpak", "list", "--app", "--columns=application,name"])
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    apps.append(dict(name=parts[1], size=0, cmd=f"flatpak uninstall {parts[0]}"))
    return sorted(apps, key=lambda a: -a["size"])


def uninstall_programs():
    header("卸载不需要的程序（按占用空间从大到小）")
    apps = installed_programs()
    if not apps:
        print("未获取到已安装程序列表。")
        return
    apps = apps[:80]
    for i, a in enumerate(apps, 1):
        print(f"{i:>3}. {human(a['size']) if a['size'] else '未知':>10}  {a['name']}")
    print("\n⚠ 请只卸载你确认不需要的软件；驱动、运行库(VC++/.NET)、安全软件请保留。")
    sel = parse_selection(input("输入要卸载的编号（回车跳过）："), len(apps))
    for i in sel:
        a = apps[i]
        if not confirm(f"卸载 {a['name']}？"):
            continue
        if IS_MAC:
            if safe_remove(a["path"]):
                print("   ✔ 已移入废纸篓（如有残留可清理 ~/Library/Application Support 中对应目录）")
        elif IS_WIN:
            print("   → 正在启动该软件自带的卸载程序，请在弹出的窗口中完成……")
            subprocess.Popen(a["cmd"], shell=True)
        else:
            print(f"   将执行：{a['cmd']}")
            if confirm("确认执行？"):
                subprocess.call(a["cmd"], shell=True)


# ---------------------------------------------------------- 3. 风险扫描
SUSP_CMD = re.compile(
    r"(powershell[^\n]*\s-(enc|e|encodedcommand)\s|frombase64string|curl[^|\n]*\|\s*(ba)?sh|wget[^|\n]*\|\s*(ba)?sh|"
    r"\bnc(at)?\s+-\w*e\b|/dev/tcp/|mshta|regsvr32[^\n]*http|bitsadmin|certutil[^\n]*-urlcache|"
    r"[\\/]temp[\\/]|/tmp/|/var/tmp/|/dev/shm|base64\s+-d|\.onion|"
    r"stratum\+(tcp|ssl)://|xmrig|minerd|--donate-level|cryptonight|kdevtmpfsi|kinsing)", re.I)
SUSP_DIRS = [r"\temp\\", r"\appdata\local\temp", "/tmp/", "/var/tmp/", "/dev/shm/", "/downloads/", r"\downloads\\"]
BAD_PORTS = {4444, 31337, 1337, 5555, 6667, 12345, 54321, 9001, 2222, 8888}
EXEC_EXT = {".exe", ".dll", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar", ".sh", ".elf", ".command", ".app"}
WIN_SYSTEM_PROCS = {"svchost.exe", "lsass.exe", "csrss.exe", "winlogon.exe", "services.exe", "smss.exe", "wininit.exe"}

findings = []


def add(level, msg):
    findings.append((level, msg))


def scan_processes():
    if not psutil:
        add("提示", "未安装 psutil，跳过进程与端口检查（pip install psutil）")
        return
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            exe = (p.info["exe"] or "")
            nm = (p.info["name"] or "").lower()
            low = exe.lower().replace("/", "\\") if IS_WIN else exe.lower()
            if IS_WIN and nm in WIN_SYSTEM_PROCS and exe and not low.startswith(r"c:\windows\system32"):
                add("高危", f"进程 {nm} (PID {p.pid}) 伪装成系统进程，实际路径：{exe}")
            elif any(d in exe.lower() for d in SUSP_DIRS[:4]) and exe:
                add("中危", f"进程 {nm} (PID {p.pid}) 从临时目录运行：{exe}")
            elif IS_LINUX and "(deleted)" in exe:
                add("高危", f"进程 {nm} (PID {p.pid}) 的程序文件已被删除但仍在运行（常见于恶意程序）")
        except Exception:
            pass
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.ip not in ("127.0.0.1", "::1"):
                name = exe = ""
                try:
                    pr = psutil.Process(c.pid)
                    name, exe = pr.name(), pr.exe()
                except Exception:
                    pass
                lvl = "高危" if c.laddr.port in BAD_PORTS else "提示"
                add(lvl, f"对外监听端口 {c.laddr.port}：{name or '未知进程'} {exe}")
    except (psutil.AccessDenied, PermissionError):
        add("提示", "读取网络连接需要管理员/root 权限，已跳过端口检查（可用管理员身份重新运行）")


def scan_persistence():
    for it in get_startup_items():
        if SUSP_CMD.search(it["cmd"]):
            add("高危", f"可疑启动项 [{it['name']}]：{it['cmd'][:140]}")
    if IS_WIN:
        rc, out, _ = run(["schtasks", "/query", "/fo", "csv", "/v"], timeout=90)
        if rc == 0:
            for row in csv.DictReader(out.splitlines()):
                cmd = row.get("Task To Run") or row.get("要运行的任务") or ""
                if cmd and SUSP_CMD.search(cmd):
                    add("中危", f"可疑计划任务 [{row.get('TaskName') or row.get('任务名')}]：{cmd[:140]}")
    else:
        rc, out, _ = run(["crontab", "-l"])
        if rc == 0:
            for ln in out.splitlines():
                if not ln.strip().startswith("#") and SUSP_CMD.search(ln):
                    add("高危", f"可疑 crontab 条目：{ln.strip()[:140]}")
        for f in (HOME / ".bashrc", HOME / ".zshrc", HOME / ".profile", HOME / ".bash_profile", HOME / ".zprofile"):
            try:
                for ln in f.read_text(errors="replace").splitlines():
                    if not ln.strip().startswith("#") and SUSP_CMD.search(ln):
                        add("中危", f"{f.name} 中含可疑命令：{ln.strip()[:140]}")
            except OSError:
                pass
        ak = HOME / ".ssh/authorized_keys"
        if ak.exists():
            n = sum(1 for l in ak.read_text(errors="replace").splitlines() if l.strip() and not l.startswith("#"))
            if n:
                add("提示", f"{ak} 中有 {n} 个 SSH 公钥可免密登录本机，请确认都是你自己的")
        if IS_LINUX:
            if Path("/etc/ld.so.preload").exists():
                add("高危", "/etc/ld.so.preload 存在（可被 rootkit 利用），请核对其内容")
            for d in (HOME / ".config/systemd/user",):
                if d.is_dir():
                    for f in d.glob("*.service"):
                        if SUSP_CMD.search(f.read_text(errors="replace")):
                            add("中危", f"用户级 systemd 服务含可疑命令：{f}")
        if IS_MAC:
            d = Path("/Library/LaunchDaemons")
            if d.is_dir():
                for f in d.glob("*.plist"):
                    if not f.name.startswith("com.apple."):
                        try:
                            if SUSP_CMD.search(f.read_text(errors="replace")):
                                add("中危", f"可疑 LaunchDaemon：{f}")
                        except OSError:
                            pass


def scan_hosts():
    hosts = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/drivers/etc/hosts" if IS_WIN else Path("/etc/hosts")
    try:
        for ln in hosts.read_text(errors="replace").splitlines():
            ln = ln.split("#")[0].strip()
            parts = ln.split()
            if len(parts) >= 2 and parts[0] not in ("127.0.0.1", "::1", "0.0.0.0", "255.255.255.255", "::",
                                                     "fe80::1%lo0", "ff02::1", "ff02::2"):
                add("中危", f"hosts 文件将 {parts[1]} 指向 {parts[0]}（可能被劫持，请确认是否为你自己设置）")
    except OSError:
        pass


def scan_temp_executables():
    dirs = [Path(os.environ.get("TEMP", ""))] if IS_WIN else [Path("/tmp"), Path("/var/tmp"), Path("/dev/shm")]
    if IS_MAC:
        dirs.append(Path(os.environ.get("TMPDIR", "/tmp")))
    cutoff, hits = time.time() - 30 * 86400, 0
    for d in dirs:
        if not d.is_dir():
            continue
        for fp, _, mt in walk_user_files_any(d):
            if os.path.splitext(fp)[1].lower() in EXEC_EXT and mt > cutoff:
                add("中危", f"临时目录中的可执行/脚本文件：{fp}")
                hits += 1
                if hits >= 30:
                    return


def walk_user_files_any(root):
    for r, _, files in os.walk(root, onerror=lambda e: None):
        for f in files:
            fp = os.path.join(r, f)
            try:
                yield fp, 0, os.stat(fp).st_mtime
            except OSError:
                pass


def scan_security_posture():
    if IS_WIN:
        rc, out, _ = run(["powershell", "-NoProfile", "-Command",
                          "Get-MpComputerStatus | Select AntivirusEnabled,RealTimeProtectionEnabled,"
                          "AntivirusSignatureAge | Format-List"], timeout=30)
        if rc == 0 and out.strip():
            if re.search(r"RealTimeProtectionEnabled\s*:\s*False", out):
                add("中危", "Windows Defender 实时保护未开启（若已安装其它杀毒软件可忽略）")
            m = re.search(r"AntivirusSignatureAge\s*:\s*(\d+)", out)
            if m and int(m.group(1)) > 7:
                add("中危", f"病毒库已 {m.group(1)} 天未更新")
        rc, out, _ = run(["netsh", "advfirewall", "show", "allprofiles", "state"])
        if re.search(r"OFF|关闭", out):
            add("中危", "Windows 防火墙有配置文件处于关闭状态")
    elif IS_MAC:
        _, out, _ = run(["spctl", "--status"])
        if "disabled" in out:
            add("高危", "Gatekeeper 已被关闭，系统会运行未签名程序")
        _, out, _ = run(["csrutil", "status"])
        if "disabled" in out:
            add("中危", "SIP（系统完整性保护）已关闭")
        _, out, _ = run(["defaults", "read", "/Library/Preferences/com.apple.alf", "globalstate"])
        if out.strip() == "0":
            add("提示", "macOS 防火墙未开启")
    else:
        if shutil.which("systemctl"):
            _, out, _ = run(["systemctl", "is-active", "ufw"])
            _, out2, _ = run(["systemctl", "is-active", "firewalld"])
            if "active" not in (out.strip(), out2.strip()) and "active\n" not in (out + out2):
                add("提示", "未检测到 ufw / firewalld 防火墙在运行")


def av_engine_scan():
    if IS_WIN:
        if confirm("使用 Windows Defender 执行快速扫描？（可能需要几分钟）", True):
            subprocess.call(["powershell", "-NoProfile", "-Command", "Update-MpSignature; Start-MpScan -ScanType QuickScan"])
            print("扫描完成，可在“Windows 安全中心 -> 病毒和威胁防护”查看结果。")
    elif shutil.which("clamscan"):
        s = input("ClamAV 扫描目录（回车=用户主目录）：").strip() or str(HOME)
        if confirm(f"用 ClamAV 扫描 {s}？"):
            subprocess.call(["clamscan", "-r", "-i", s])
    else:
        print("未找到杀毒引擎。建议：")
        if IS_MAC:
            print("  macOS 内置 XProtect 会自动运行；如需按需扫描可安装 ClamAV（brew install clamav）或 Malwarebytes。")
        else:
            print("  安装 ClamAV：sudo apt install clamav && sudo freshclam；rootkit 检测可用 rkhunter / chkrootkit。")


def security_scan():
    header("潜在风险扫描")
    if not is_admin():
        print("ℹ 当前非管理员权限，部分检查（端口归属、系统级项目）可能不完整。")
    findings.clear()
    steps = [("运行中的进程与网络端口", scan_processes), ("启动项 / 计划任务 / 持久化", scan_persistence),
             ("hosts 文件", scan_hosts), ("临时目录中的可执行文件", scan_temp_executables),
             ("系统安全防护状态", scan_security_posture)]
    for label, fn in steps:
        print(f"→ 检查：{label} ……")
        try:
            fn()
        except Exception as e:
            add("提示", f"检查“{label}”时出错：{e}")
    order = {"高危": 0, "中危": 1, "提示": 2}
    findings.sort(key=lambda x: order[x[0]])
    lines = [f"[{lv}] {msg}" for lv, msg in findings] or ["未发现明显异常。"]
    print("\n---------- 扫描结果 ----------")
    print("\n".join(lines))
    rp = REPORT_DIR / f"security_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
    rp.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已保存：{rp}")
    print("说明：以上为启发式检测，“中危/提示”多数是需要你人工确认的项目，并不等于中毒；")
    print("      对“高危”项请先核实来源，再考虑处理（可在启动项菜单中停用，或断网后用杀毒软件深度查杀）。")
    av_engine_scan()


# ------------------------------------------------------------------ 主程序
def health_check():
    header("一键体检（只检查，不做任何修改）")
    total = sum(sum(s for _, s in list_files_in(p)) for _, p in junk_targets())
    print(f"可清理垃圾：约 {human(total)}")
    print(f"开机启动项：{len(get_startup_items())} 个")
    if psutil:
        vm = psutil.virtual_memory()
        du = shutil.disk_usage(HOME)
        print(f"内存使用：{vm.percent}%   磁盘使用：{du.used / du.total * 100:.0f}% （剩余 {human(du.free)}）")
    print("建议依次进入对应菜单处理。")


def menu():
    print(f"\nFaster v{__version__} | 系统：{SYSTEM} {platform.release()} | 权限：{'管理员' if is_admin() else '普通用户'}")
    if not psutil:
        print("提示：安装 psutil 可解锁进程管理与端口检查（pip install psutil）")
    if not send2trash:
        print(f"提示：未安装 send2trash，被删除的文件将移动到 {TRASH_DIR}（可找回）")
    actions = {
        "1": ("清理系统垃圾 / 缓存", clean_junk),
        "2": ("大文件列表（大→小，自选删除）", large_files),
        "3": ("重复文件查找", duplicate_files),
        "4": ("开机启动项管理", startup_manager),
        "5": ("后台进程管理", process_manager),
        "6": ("卸载不需要的程序", uninstall_programs),
        "7": ("潜在风险扫描（病毒/后门迹象）", security_scan),
        "8": ("一键体检（仅检查）", health_check),
    }
    while True:
        print("\n" + "-" * 40)
        for k, (n, _) in actions.items():
            print(f"  {k}. {n}")
        print("  0. 退出")
        c = input("请选择：").strip()
        if c == "0":
            break
        if c in actions:
            try:
                actions[c][1]()
            except KeyboardInterrupt:
                print("\n已取消。")
            except Exception as e:
                print(f"出错：{e}")


if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\n再见！")
