#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Faster - 图形界面 + 定时自动清理   (Windows / macOS / Linux)

用法：
    python faster_gui.py                  启动图形界面
    python faster_gui.py --auto-clean     无界面执行一次自动清理（定时任务就是调用它）
    python faster_gui.py --auto-clean --dry-run   试运行：只统计，不删除

需与 faster.py 放在同一目录。可选依赖：pip install psutil send2trash
Linux 若提示缺少 tkinter：sudo apt install python3-tk
"""
import os
import sys
import json
import time
import queue
import shutil
import heapq
import locale
import shlex
import platform
import plistlib
import threading
import subprocess
import datetime
from pathlib import Path
from collections import defaultdict

FROZEN = getattr(sys, "frozen", False)      # 是否为 PyInstaller 打包后的程序
if sys.stdout is None:                      # 无控制台(--noconsole)时 print 会报错，重定向掉
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 提权后的辅助进程：必须沿用“原用户”的主目录，备份/配置才不会写到管理员账户下
if "--elevated" in sys.argv and "--home" in sys.argv:
    _h = sys.argv[sys.argv.index("--home") + 1]
    os.environ["HOME"] = _h
    os.environ["USERPROFILE"] = _h
import faster as core  # noqa: E402
from faster import human, HOME, APP_DIR, TRASH_DIR, IS_WIN, IS_MAC, IS_LINUX, __version__  # noqa: E402

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
except Exception:  # 无界面模式（定时任务）不需要 tkinter
    tk = None

try:
    import psutil
except ImportError:
    psutil = None

CONFIG = APP_DIR / "schedule.json"
LOG = APP_DIR / "auto_clean.log"
TRASH_NAMES = {"废纸篓", "回收站", "回收站信息"}
WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
FREQ_CN = {"daily": "每天", "weekly": "每周", "monthly": "每月"}

DEFAULT_CFG = dict(
    enabled=False, freq="weekly", time="12:30", weekday=0, monthday=1,
    junk=True, junk_min_age_days=1,       # 清理 N 天前的缓存/临时文件（0 = 1 小时前）
    empty_trash=False,                    # 清空系统回收站/废纸篓
    purge_own_trash_days=30,              # 本工具“回收站”里超过 N 天的文件彻底删除（0 = 不处理）
    folders=[],                           # 自定义文件夹规则：[{"path":..., "days":30}]
    last_run="", last_result="")


# ======================================================== 配置 / 日志 / 通用
def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
    except OSError:
        pass


def sh(args, input_text=None, timeout=60):
    """运行外部命令，返回 (returncode, stdout, stderr)；Windows 下不弹黑窗"""
    try:
        r = subprocess.run(args, input=input_text.encode() if input_text else None, capture_output=True,
                           timeout=timeout, creationflags=0x08000000 if IS_WIN else 0)
        enc = locale.getpreferredencoding(False)
        return r.returncode, r.stdout.decode(enc, errors="replace"), r.stderr.decode(enc, errors="replace")
    except Exception as e:
        return -1, "", str(e)


def danger_reason(p):
    """自定义清理目录的安全检查：拒绝系统目录、主目录本身、盘符根目录"""
    try:
        p = Path(p).resolve()
    except Exception:
        return "路径无效"
    if not p.is_dir():
        return "目录不存在"
    if p == HOME or p == Path(p.anchor) or len(p.parts) <= 2:
        return "过于靠近根目录/主目录，已拒绝"
    if IS_WIN:
        sysd = [os.environ.get(k) for k in ("WINDIR", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA")]
    else:
        sysd = ["/usr", "/etc", "/bin", "/sbin", "/lib", "/boot", "/System", "/Library", "/Applications",
                "/var", "/opt", "/dev", "/proc", "/sys", "/private/etc"]
    for s in sysd:
        if s and (p == Path(s) or Path(s) in p.parents):
            return "系统目录，已拒绝"
    if APP_DIR in (p, *p.parents):
        return "本工具自身目录，已拒绝"
    return None


def empty_dir(p):
    freed = 0
    for child in Path(p).iterdir():
        try:
            if child.is_dir() and not child.is_symlink():
                freed += core.dir_size(child)
                shutil.rmtree(child, ignore_errors=True)
            else:
                freed += child.lstat().st_size
                child.unlink()
        except OSError:
            pass
    return freed


# ================================================================ 自动清理
def auto_clean(dry_run=False):
    """按已保存的配置执行一次清理。返回 (释放字节数, 日志行列表)"""
    cfg = load_cfg()
    lines, freed = [], 0
    tag = "[试运行·不删除] " if dry_run else ""
    lines.append(f"{tag}开始自动清理 {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")

    # 1) 垃圾缓存（只删超过 N 天未修改的文件，避免误删正在使用的）
    if cfg["junk"]:
        days = int(cfg["junk_min_age_days"])
        age_h = days * 24 if days > 0 else 1
        for name, p in core.junk_targets():
            if name in TRASH_NAMES:
                continue
            files = core.list_files_in(p, age_h)
            size = sum(s for _, s in files)
            done = size
            if not dry_run:
                done = 0
                for fp, sz in files:
                    try:
                        os.remove(fp)
                        done += sz
                    except OSError:
                        pass
            if files:
                lines.append(f"  垃圾缓存 · {name}：{len(files)} 个文件，{human(done)}")
            freed += done

    # 2) 清空回收站 / 废纸篓
    if cfg["empty_trash"]:
        if IS_WIN:
            if not dry_run:
                try:
                    import ctypes
                    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
                    lines.append("  已清空回收站")
                except Exception as e:
                    lines.append(f"  清空回收站失败：{e}")
            else:
                lines.append("  将清空回收站")
        else:
            for name, p in core.junk_targets():
                if name in TRASH_NAMES:
                    sz = core.dir_size(p)
                    if not dry_run:
                        sz = empty_dir(p)
                    if sz:
                        lines.append(f"  清空 {name}：{human(sz)}")
                    freed += sz

    # 3) 本工具回收站里的旧文件彻底删除
    pd = int(cfg["purge_own_trash_days"])
    if pd > 0 and TRASH_DIR.is_dir():
        cutoff, sz_total = time.time() - pd * 86400, 0
        for child in TRASH_DIR.iterdir():
            try:
                ts = int(child.name.split("_", 1)[0])
            except ValueError:
                ts = int(child.stat().st_mtime)
            if ts < cutoff:
                sz = core.dir_size(child) if child.is_dir() else child.stat().st_size
                sz_total += sz
                if not dry_run:
                    shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
        if sz_total:
            lines.append(f"  工具回收站中超过 {pd} 天的文件：{human(sz_total)}")
            freed += sz_total

    # 4) 自定义文件夹规则：超过 N 天未修改的文件 → 移入回收站（可找回）
    for rule in cfg["folders"]:
        root, days = rule.get("path", ""), int(rule.get("days", 30))
        bad = danger_reason(root)
        if bad:
            lines.append(f"  跳过文件夹 {root}：{bad}")
            continue
        cutoff, n, sz_total = time.time() - days * 86400, 0, 0
        for r, dirs, files in os.walk(root, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(r, d))]
            for f in files:
                fp = os.path.join(r, f)
                try:
                    st = os.lstat(fp)
                    if st.st_mtime >= cutoff:
                        continue
                    if dry_run or core.safe_remove(fp):
                        n += 1
                        sz_total += st.st_size
                except OSError:
                    pass
        if n:
            lines.append(f"  文件夹 {root}：{n} 个超过 {days} 天的文件，{human(sz_total)}"
                         f"{'' if dry_run else '（已移入回收站，可找回）'}")
        freed += sz_total

    lines.append(f"{tag}合计{'可释放' if dry_run else '释放'} {human(freed)}")
    if not dry_run:
        cfg["last_run"] = f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
        cfg["last_result"] = f"释放 {human(freed)}"
        save_cfg(cfg)
        for ln in lines:
            log(ln)
    return freed, lines


# ============================================================= 定时任务安装
def script_cmd():
    """返回启动本程序的命令列表（源码运行 / 打包后均适用）"""
    if FROZEN:
        return [sys.executable]
    py = sys.executable
    if IS_WIN:
        pw = Path(py).with_name("pythonw.exe")
        if pw.exists():
            py = str(pw)  # 无窗口运行
    return [py, str(Path(__file__).resolve())]


def _quoted(cmd):
    return " ".join(f'"{c}"' for c in cmd) + " --auto-clean"


def _hm(cfg):
    h, m = cfg["time"].split(":")
    return int(h), int(m)


MAC_LABEL = "com.faster.autoclean"
WIN_TASK = "FasterAutoClean"
SD_DIR = HOME / ".config/systemd/user"
CRON_TAG = "# faster"


def _use_systemd():
    return bool(shutil.which("systemctl")) and sh(["systemctl", "--user", "show-environment"])[0] == 0


def remove_legacy_schedule():
    """清理 v0.1.0（旧名称 PCOptimizer）创建的定时任务，避免升级后重复运行"""
    try:
        if IS_WIN:
            sh(["schtasks", "/Delete", "/TN", "PCOptimizerAutoClean", "/F"])
        elif IS_MAC:
            pl = HOME / "Library/LaunchAgents/com.pcoptimizer.autoclean.plist"
            if pl.exists():
                sh(["launchctl", "unload", str(pl)])
                pl.unlink()
        else:
            if shutil.which("systemctl"):
                sh(["systemctl", "--user", "disable", "--now", "pc-optimizer.timer"])
            for n in ("pc-optimizer.timer", "pc-optimizer.service"):
                (SD_DIR / n).unlink(missing_ok=True)
            if shutil.which("crontab"):
                cur = sh(["crontab", "-l"])[1]
                if "# pc_optimizer" in cur:
                    keep = [l for l in cur.splitlines() if "# pc_optimizer" not in l]
                    sh(["crontab", "-"], input_text="\n".join(keep) + ("\n" if keep else ""))
    except Exception:
        pass


def install_schedule(cfg):
    remove_legacy_schedule()
    cmd = script_cmd()
    h, m = _hm(cfg)
    freq, wd, md = cfg["freq"], int(cfg["weekday"]), int(cfg["monthday"])
    try:
        if IS_WIN:
            args = ["schtasks", "/Create", "/TN", WIN_TASK, "/TR", _quoted(cmd),
                    "/ST", f"{h:02d}:{m:02d}", "/F"]
            if freq == "daily":
                args += ["/SC", "DAILY"]
            elif freq == "weekly":
                args += ["/SC", "WEEKLY", "/D", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][wd]]
            else:
                args += ["/SC", "MONTHLY", "/D", str(md)]
            rc, out, err = sh(args)
            return rc == 0, "已创建 Windows 计划任务" if rc == 0 else f"创建失败：{err or out}"
        if IS_MAC:
            cal = {"Hour": h, "Minute": m}
            if freq == "weekly":
                cal["Weekday"] = wd + 1          # launchd：1=周一 … 7=周日
            elif freq == "monthly":
                cal["Day"] = md
            plist = HOME / "Library/LaunchAgents" / f"{MAC_LABEL}.plist"
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_bytes(plistlib.dumps({
                "Label": MAC_LABEL, "ProgramArguments": cmd + ["--auto-clean"],
                "StartCalendarInterval": cal, "RunAtLoad": False,
                "StandardOutPath": str(APP_DIR / "launchd.out"), "StandardErrorPath": str(APP_DIR / "launchd.err")}))
            sh(["launchctl", "unload", str(plist)])
            rc, out, err = sh(["launchctl", "load", "-w", str(plist)])
            return rc == 0, "已创建 launchd 定时任务（电脑休眠错过时，唤醒后会补跑）" if rc == 0 else f"加载失败：{err or out}"
        # Linux
        if _use_systemd():
            SD_DIR.mkdir(parents=True, exist_ok=True)
            cal = {"daily": "*-*-* {h:02d}:{m:02d}:00",
                   "weekly": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][wd] + " *-*-* {h:02d}:{m:02d}:00",
                   "monthly": f"*-*-{md:02d} " + "{h:02d}:{m:02d}:00"}[freq].format(h=h, m=m)
            (SD_DIR / "faster.service").write_text(
                f'[Unit]\nDescription=Faster auto clean\n\n[Service]\nType=oneshot\n'
                f"ExecStart={_quoted(cmd)}\n")
            (SD_DIR / "faster.timer").write_text(
                f"[Unit]\nDescription=Faster schedule\n\n[Timer]\nOnCalendar={cal}\nPersistent=true\n\n"
                f"[Install]\nWantedBy=timers.target\n")
            sh(["systemctl", "--user", "daemon-reload"])
            rc, out, err = sh(["systemctl", "--user", "enable", "--now", "faster.timer"])
            return rc == 0, "已创建 systemd 用户定时器（错过的任务开机后会补跑）" if rc == 0 else f"启用失败：{err or out}"
        if shutil.which("crontab"):
            _, cur, _ = sh(["crontab", "-l"])
            keep = [l for l in cur.splitlines() if CRON_TAG not in l]
            spec = {"daily": f"{m} {h} * * *", "weekly": f"{m} {h} * * {(wd + 1) % 7}",
                    "monthly": f"{m} {h} {md} * *"}[freq]
            keep.append(f"{spec} {_quoted(cmd)} {CRON_TAG}")
            rc, out, err = sh(["crontab", "-"], input_text="\n".join(keep) + "\n")
            return rc == 0, "已写入 crontab" if rc == 0 else f"写入失败：{err or out}"
        return False, "未找到 systemd 或 cron，无法创建定时任务"
    except Exception as e:
        return False, f"出错：{e}"


def remove_schedule():
    remove_legacy_schedule()
    try:
        if IS_WIN:
            rc, out, err = sh(["schtasks", "/Delete", "/TN", WIN_TASK, "/F"])
            return True, "已移除计划任务"
        if IS_MAC:
            plist = HOME / "Library/LaunchAgents" / f"{MAC_LABEL}.plist"
            sh(["launchctl", "unload", str(plist)])
            plist.unlink(missing_ok=True)
            return True, "已移除定时任务"
        if _use_systemd():
            sh(["systemctl", "--user", "disable", "--now", "faster.timer"])
            for n in ("faster.timer", "faster.service"):
                (SD_DIR / n).unlink(missing_ok=True)
            sh(["systemctl", "--user", "daemon-reload"])
        if shutil.which("crontab"):
            _, cur, _ = sh(["crontab", "-l"])
            if CRON_TAG in cur:
                keep = [l for l in cur.splitlines() if CRON_TAG not in l]
                sh(["crontab", "-"], input_text="\n".join(keep) + ("\n" if keep else ""))
        return True, "已移除定时任务"
    except Exception as e:
        return False, f"出错：{e}"


def schedule_installed():
    if IS_WIN:
        return sh(["schtasks", "/Query", "/TN", WIN_TASK])[0] == 0
    if IS_MAC:
        return (HOME / "Library/LaunchAgents" / f"{MAC_LABEL}.plist").exists()
    if (SD_DIR / "faster.timer").exists():
        return True
    return CRON_TAG in sh(["crontab", "-l"])[1]


# ======================================================== 业务函数（后台线程）
def find_duplicates(root, min_mb=1):
    by_size = defaultdict(list)
    for fp, sz, mt in core.walk_user_files(root, int(min_mb * 1048576)):
        by_size[sz].append((fp, mt))
    groups = []
    for sz, lst in by_size.items():
        if len(lst) < 2:
            continue
        quick = defaultdict(list)
        for fp, mt in lst:
            h = core.sha256(fp, 65536)
            if h:
                quick[h].append((fp, mt))
        for q in quick.values():
            if len(q) < 2:
                continue
            full = defaultdict(list)
            for fp, mt in q:
                h = core.sha256(fp)
                if h:
                    full[h].append((fp, mt))
            groups += [(sz, sorted(g, key=lambda x: (len(x[0]), x[1]))) for g in full.values() if len(g) > 1]
    groups.sort(key=lambda x: -x[0] * (len(x[1]) - 1))
    return groups[:200]


def list_processes():
    prot = core.PROTECTED["win" if IS_WIN else "mac" if IS_MAC else "linux"]
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
            rows.append((p.pid, p.info["name"], p.info["memory_info"].rss, p.cpu_percent(None)))
        except Exception:
            pass
    rows.sort(key=lambda x: -x[2])
    return rows[:60]


def restore_entry(e):
    try:
        if e["type"] == "reg":
            import winreg
            hive = winreg.HKEY_CURRENT_USER if e["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            with winreg.OpenKey(hive, e["key"], 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, e["name"], 0, e["regtype"], e["cmd"])
        elif e["type"] == "file_moved":
            shutil.move(e["backup"], e["orig"])
            if e.get("launchd"):
                sh(["launchctl", "load", "-w", e["orig"]])
        elif e["type"] == "file_created":
            os.remove(e["path"])
        return True, ""
    except Exception as ex:
        return False, str(ex)


def run_all_scans():
    core.findings.clear()
    for fn in (core.scan_processes, core.scan_persistence, core.scan_hosts,
               core.scan_temp_executables, core.scan_security_posture):
        try:
            fn()
        except Exception as e:
            core.add("提示", f"检查 {fn.__name__} 出错：{e}")
    order = {"高危": 0, "中危": 1, "提示": 2}
    return sorted(core.findings, key=lambda x: order[x[0]])


# ============================================================ 管理员权限（按需提权）
# 思路：GUI 始终以普通用户运行；需要管理员权限的动作，由本程序以“--elevated 动作”再启动一个
# 无界面的辅助进程，经系统授权窗口（Windows UAC / macOS 密码框 / Linux polkit）提权后执行，
# 结果经 JSON 文件返回。辅助进程只接受下面白名单里的固定动作，不执行任意命令。
def is_system_startup(it):
    p = it.get("path", "")
    if it["kind"] == "reg":
        return it.get("hive") == "HKLM"
    if it["kind"] == "file":
        pd = os.environ.get("PROGRAMDATA", "")
        return bool(pd) and p.lower().startswith(pd.lower())
    if it["kind"] == "launchd":
        return p.startswith("/Library")
    return False


def startup_key(it):
    return "|".join([it["kind"], it["name"], it.get("hive", ""), it.get("key", ""), it.get("path", "")])


def _purge(path, hours=1, suffixes=None):
    freed = 0
    if not Path(path).is_dir():
        return 0
    for fp, sz in core.list_files_in(path, hours):
        if suffixes and not fp.endswith(suffixes):
            continue
        try:
            os.remove(fp)
            freed += sz
        except OSError:
            pass
    return freed


def clean_system():
    """系统级垃圾（需管理员）：只清理确认安全的目录"""
    if IS_WIN:
        w = Path(os.environ.get("WINDIR", "C:/Windows"))
        pd = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
        targets = [("系统临时文件", w / "Temp", 1, None),
                   ("Windows 更新下载缓存", w / "SoftwareDistribution/Download", 1, None),
                   ("Windows 错误报告", pd / "Microsoft/Windows/WER", 1, None)]
    elif IS_MAC:
        targets = [("系统级缓存 /Library/Caches", Path("/Library/Caches"), 24, None),
                   ("诊断报告", Path("/Library/Logs/DiagnosticReports"), 24, None)]
    else:
        targets = [("apt 软件包缓存", Path("/var/cache/apt/archives"), 1, (".deb",)),
                   ("/var/tmp 超过7天的文件", Path("/var/tmp"), 24 * 7, None),
                   ("systemd 核心转储", Path("/var/lib/systemd/coredump"), 24, None)]
    lines, total = [], 0
    for name, p, h, suf in targets:
        n = _purge(p, h, suf)
        total += n
        lines.append(f"{name}：释放 {human(n)}")
    if IS_LINUX and shutil.which("journalctl"):
        rc, _, err = sh(["journalctl", "--vacuum-size=200M"], timeout=120)
        lines.append("systemd 日志：已压缩到 200MB 以内" if rc == 0 else f"systemd 日志清理失败：{err[:80]}")
    lines.append(f"合计释放 {human(total)}")
    return lines


def helper_work(action, keys, path):
    if not core.is_admin():
        return dict(ok=False, lines=["未获得管理员权限"])
    keys = keys or []
    if action == "clean-system":
        return dict(ok=True, lines=clean_system())
    if action == "scan":
        return dict(ok=True, findings=run_all_scans())
    if action == "disable-startup":
        lines = []
        for it in core.get_startup_items():
            if startup_key(it) in keys:
                if not is_system_startup(it):
                    lines.append(f"跳过 {it['name']}：非系统级项目，无需管理员权限")
                else:
                    lines.append(("已停用 " if core.disable_startup(it) else "停用失败 ") + it["name"])
        if IS_MAC:
            lines.append("提示：系统级 LaunchAgent 需注销并重新登录后才完全生效")
        return dict(ok=True, lines=lines)
    if action == "restore-startup":
        m, lines = core.load_manifest(), []
        for e in m:
            if f"{e.get('ts')}|{e.get('name')}" in keys and not e.get("restored"):
                ok, msg = restore_entry(e)
                if ok:
                    e["restored"] = True
                lines.append(("已恢复 " if ok else "恢复失败 ") + f"{e.get('name')} {msg}")
        core.save_manifest(m)
        return dict(ok=True, lines=lines)
    if action == "remove-app" and IS_MAC:
        p = Path(path or "")
        if p.suffix != ".app" or p.is_symlink() or p.parent != Path("/Applications") or not p.exists():
            return dict(ok=False, lines=["拒绝：只允许移除 /Applications 下的 .app"])
        dest = HOME / ".Trash" / f"{p.stem}_{int(time.time())}.app"
        dest.parent.mkdir(exist_ok=True)
        shutil.move(str(p), str(dest))
        return dict(ok=True, lines=[f"已将 {p.name} 移入废纸篓"])
    return dict(ok=False, lines=[f"不支持的操作：{action}"])


def _fix_ownership():
    """root 辅助进程写过的文件，归还给原用户，避免普通权限下无法修改"""
    if IS_WIN or os.geteuid() != 0:
        return
    st = os.stat(HOME)
    for root, dirs, files in os.walk(APP_DIR):
        for n in [root] + [os.path.join(root, x) for x in dirs + files]:
            try:
                os.chown(n, st.st_uid, st.st_gid)
            except OSError:
                pass


def _argval(name):
    i = sys.argv.index(name) if name in sys.argv else -1
    return sys.argv[i + 1] if 0 <= i < len(sys.argv) - 1 else None


def elevated_main():
    io, action = _argval("--io"), _argval("--elevated")
    try:
        req = json.loads(Path(io).read_text(encoding="utf-8"))
        res = helper_work(action, req.get("keys"), req.get("path"))
    except Exception as e:
        res = dict(ok=False, lines=[f"执行出错：{e}"])
    Path(io + ".res").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    _fix_ownership()


def _elevation_argv(cmd):
    """生成各平台的“弹出系统授权窗口并以管理员运行 cmd”的命令行"""
    if IS_WIN:
        argstr = " ".join(f'"{a}"' for a in cmd[1:])
        psq = lambda t: "'" + t.replace("'", "''") + "'"  # noqa: E731
        return ["powershell", "-NoProfile", "-Command",
                f"Start-Process -FilePath {psq(cmd[0])} -ArgumentList {psq(argstr)} -Verb RunAs -Wait"]
    if IS_MAC:
        inner = "HOME=" + shlex.quote(str(HOME)) + " " + " ".join(shlex.quote(c) for c in cmd)
        inner = inner.replace("\\", "\\\\").replace('"', '\\"')
        return ["osascript", "-e", f'do shell script "{inner}" with administrator privileges']
    if not shutil.which("pkexec"):
        raise RuntimeError("未找到 pkexec（polkit）。请安装 policykit-1，或在终端用 sudo 运行本程序。")
    return ["pkexec", "env", f"HOME={HOME}"] + cmd


def run_elevated(action, keys=None, path=None, timeout=900):
    """以管理员权限执行白名单动作，返回结果 dict；用户取消授权则抛 RuntimeError"""
    if core.is_admin():
        return helper_work(action, keys, path)
    io = APP_DIR / f"elev_{os.getpid()}_{int(time.time() * 1000)}.json"
    res_file = Path(str(io) + ".res")
    io.write_text(json.dumps(dict(keys=keys or [], path=path), ensure_ascii=False), encoding="utf-8")
    cmd = script_cmd() + ["--elevated", action, "--home", str(HOME), "--io", str(io)]
    try:
        rc, out, err = sh(_elevation_argv(cmd), timeout=timeout)
        if not res_file.exists():
            raise RuntimeError("已取消，或未获得管理员授权。" + (f"\n{(err or out).strip()[:200]}" if (err or out).strip() else ""))
        return json.loads(res_file.read_text(encoding="utf-8"))
    finally:
        for f in (io, res_file):
            try:
                f.unlink()
            except OSError:
                pass


def relaunch_as_admin():
    """Windows：以管理员身份重新启动整个程序（一次授权，全部功能可用）"""
    if not IS_WIN:
        return False
    import ctypes
    cmd = script_cmd()
    params = " ".join(f'"{a}"' for a in cmd[1:])
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd[0], params, None, 1) > 32


# ================================================================ 图形界面
if tk:
    def show_text(parent, title, text):
        w = tk.Toplevel(parent)
        w.title(title)
        w.geometry("780x500")
        st = scrolledtext.ScrolledText(w, wrap="word")
        st.pack(fill="both", expand=True)
        st.insert("1.0", text)
        st.config(state="disabled")

    class ListTab(ttk.Frame):
        """带工具栏 + 多选表格的通用页面"""

        def __init__(self, app, columns):
            super().__init__(app.nb)
            self.app, self.data = app, {}
            self.top = ttk.Frame(self)
            self.top.pack(fill="x", padx=8, pady=6)
            self.info = ttk.Label(self, text="", foreground="#555")
            self.info.pack(side="bottom", fill="x", padx=8, pady=4)
            body = ttk.Frame(self)
            body.pack(fill="both", expand=True, padx=8, pady=2)
            self.tree = ttk.Treeview(body, columns=[c[0] for c in columns], show="headings", selectmode="extended")
            for cid, title, w, anc in columns:
                self.tree.heading(cid, text=title)
                self.tree.column(cid, width=w, anchor=anc, stretch=(cid == columns[-1][0]))
            vs = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=vs.set)
            self.tree.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")
            self.tree.tag_configure("keep", foreground="#999")
            self.tree.tag_configure("high", foreground="#c62828")
            self.tree.tag_configure("mid", foreground="#e65100")
            self.tree.tag_configure("note", foreground="#1565c0")

        def btn(self, text, cmd):
            b = ttk.Button(self.top, text=text, command=cmd)
            b.pack(side="left", padx=3)
            return b

        def clear(self):
            self.tree.delete(*self.tree.get_children())
            self.data.clear()

        def add(self, values, obj, tags=()):
            iid = self.tree.insert("", "end", values=values, tags=tags)
            self.data[iid] = obj
            return iid

        def selected(self):
            return [(i, self.data[i]) for i in self.tree.selection()]

        def select_all(self):
            self.tree.selection_set(self.tree.get_children())

        def need_selection(self):
            sel = self.selected()
            if not sel:
                messagebox.showinfo("提示", "请先在列表中选择项目（可按住 Ctrl/Shift 多选，或点“全选”）。")
            return sel

        def path_picker(self, default=None):
            self.root_var = tk.StringVar(value=str(default or HOME))
            ttk.Label(self.top, text="目录：").pack(side="left")
            ttk.Entry(self.top, textvariable=self.root_var, width=34).pack(side="left")
            ttk.Button(self.top, text="浏览…", command=lambda: self.root_var.set(
                filedialog.askdirectory(initialdir=self.root_var.get()) or self.root_var.get())).pack(side="left", padx=3)

    # ------------------------------------------------------------ 概览
    class HomeTab(ttk.Frame):
        def __init__(self, app):
            super().__init__(app.nb)
            self.app = app
            ttk.Label(self, text="Faster", font=("", 20, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
            ttk.Label(self, text=f"版本 v{__version__} · {platform.system()} {platform.release()} · "
                                 f"当前：{'管理员' if core.is_admin() else '普通用户'}权限").pack(anchor="w", padx=18)
            if not core.is_admin():
                row = ttk.Frame(self)
                row.pack(anchor="w", padx=18, pady=(6, 0))
                if IS_WIN:
                    ttk.Button(row, text="🛡 以管理员身份重新启动（一次授权，全部功能可用）",
                               command=self.relaunch).pack(side="left")
                ttk.Label(row, text="也可不重启：需要管理员权限的功能会按提示单独授权" if IS_WIN else
                          "需要管理员权限的功能会按提示弹出系统授权窗口（输入开机密码即可）",
                          foreground="#555").pack(side="left", padx=8)
            box = ttk.Frame(self)
            box.pack(fill="x", padx=18, pady=14)
            self.bars = {}
            for key, label in (("disk", "磁盘"), ("mem", "内存"), ("cpu", "CPU")):
                ttk.Label(box, text=label, width=6).grid(row=len(self.bars), column=0, sticky="w", pady=4)
                pb = ttk.Progressbar(box, length=420, maximum=100)
                pb.grid(row=len(self.bars), column=1, pady=4)
                lb = ttk.Label(box, text="…", width=34)
                lb.grid(row=len(self.bars), column=2, padx=8, sticky="w")
                self.bars[key] = (pb, lb)
            ttk.Button(self, text="一键体检（只检查，不修改）", command=self.check).pack(anchor="w", padx=18)
            self.result = ttk.Label(self, text="", justify="left")
            self.result.pack(anchor="w", padx=18, pady=10)
            tips = ("使用提示：\n"
                    "  • 所有删除/停用操作都会先让你确认；被删文件优先进回收站（或工具回收站，可找回）。\n"
                    "  • “自动清理”页可设置每天/每周/每月定时清理，由系统计划任务执行，不需要保持本程序运行。\n"
                    "  • 风险扫描为启发式检测，不能替代专业杀毒软件。")
            ttk.Label(self, text=tips, foreground="#555", justify="left").pack(anchor="w", padx=18, pady=10)
            self.refresh()

        def relaunch(self):
            if relaunch_as_admin():
                self.app.destroy()
            else:
                messagebox.showwarning("提示", "未能获得管理员权限（授权被取消）。")

        def refresh(self):
            du = shutil.disk_usage(HOME)
            self.bars["disk"][0]["value"] = du.used / du.total * 100
            self.bars["disk"][1].config(text=f"已用 {human(du.used)} / 共 {human(du.total)}（剩 {human(du.free)}）")
            if psutil:
                vm = psutil.virtual_memory()
                self.bars["mem"][0]["value"] = vm.percent
                self.bars["mem"][1].config(text=f"已用 {human(vm.used)} / 共 {human(vm.total)}")
                c = psutil.cpu_percent(None)
                self.bars["cpu"][0]["value"] = c
                self.bars["cpu"][1].config(text=f"{c:.0f}%")
            else:
                self.bars["mem"][1].config(text="需要安装 psutil")
                self.bars["cpu"][1].config(text="需要安装 psutil")
            self.after(4000, self.refresh)

        def check(self):
            def work():
                junk = sum(sum(s for _, s in core.list_files_in(p)) for _, p in core.junk_targets())
                return junk, len(core.get_startup_items())

            self.app.run_bg(work, lambda r: self.result.config(
                text=f"可清理垃圾：约 {human(r[0])}\n开机启动项：{r[1]} 个\n建议到对应页面处理。"), "体检中…")

    # ------------------------------------------------------------ 垃圾清理
    class JunkTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("name", "项目", 240, "w"), ("size", "可释放", 90, "e"),
                                   ("n", "文件数", 70, "e"), ("path", "位置", 420, "w")])
            self.btn("扫描", self.scan)
            self.btn("全选", self.select_all)
            self.btn("清理选中项", self.clean)
            self.btn("🛡 管理员清理系统级垃圾", self.clean_system)
            if IS_WIN:
                self.btn("清空回收站", self.empty_bin)
            ttk.Label(self.top, text="清理浏览器缓存后网页首次加载会稍慢，不会丢失密码/书签").pack(side="left", padx=10)

        def scan(self):
            def work():
                res = []
                for name, p in core.junk_targets():
                    files = core.list_files_in(p)
                    size = sum(s for _, s in files)
                    if size > 0:
                        res.append((name, p, files, size))
                return sorted(res, key=lambda x: -x[3])

            def done(res):
                self.clear()
                for r in res:
                    self.add((r[0], human(r[3]), len(r[2]), str(r[1])), r)
                self.info.config(text=f"可释放合计 {human(sum(r[3] for r in res))}" if res else "没有发现可清理的垃圾")

            self.app.run_bg(work, done, "扫描垃圾文件…")

        def clean(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno("确认", f"确认清理选中的 {len(sel)} 项？"):
                return

            def work():
                freed = 0
                for _, (name, p, files, size) in sel:
                    for fp, sz in files:
                        try:
                            os.remove(fp)
                            freed += sz
                        except OSError:
                            pass
                return freed

            def done(freed):
                messagebox.showinfo("完成", f"已释放约 {human(freed)}")
                self.scan()

            self.app.run_bg(work, done, "清理中…")

        def clean_system(self):
            what = {"win": "Windows 系统临时文件、更新下载缓存、错误报告",
                    "mac": "/Library/Caches 系统级缓存、诊断报告",
                    "linux": "apt 软件包缓存、/var/tmp 旧文件、systemd 日志(压缩到200MB)"}["win" if IS_WIN else "mac" if IS_MAC else "linux"]
            if not messagebox.askyesno("管理员清理", f"将以管理员权限清理：\n{what}\n\n继续？（随后会弹出系统授权窗口）"):
                return
            self.app.run_bg(lambda: run_elevated("clean-system"),
                            lambda r: show_text(self, "系统级清理结果", "\n".join(r.get("lines", []))),
                            "等待管理员授权…")

        def empty_bin(self):
            if messagebox.askyesno("确认", "清空回收站？此操作不可恢复。"):
                import ctypes
                ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
                messagebox.showinfo("完成", "回收站已清空")

    # ------------------------------------------------------------ 大文件
    class LargeTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("size", "大小", 90, "e"), ("age", "最后修改", 90, "e"), ("path", "路径", 700, "w")])
            self.path_picker()
            self.mb = tk.StringVar(value="100")
            self.topn = tk.StringVar(value="50")
            ttk.Label(self.top, text="≥").pack(side="left")
            ttk.Spinbox(self.top, from_=1, to=100000, width=6, textvariable=self.mb).pack(side="left")
            ttk.Label(self.top, text="MB  前").pack(side="left")
            ttk.Spinbox(self.top, from_=5, to=500, width=5, textvariable=self.topn).pack(side="left")
            ttk.Label(self.top, text="个").pack(side="left", padx=(0, 6))
            self.btn("扫描（大→小）", self.scan)
            self.btn("全选", self.select_all)
            self.btn("删除选中", self.delete)
            self.info.config(text="这些文件无法自动判断是否有用（视频/虚拟机/安装包等），请自行甄别；删除后进回收站。")

        def scan(self):
            root = Path(self.root_var.get())
            if not root.is_dir():
                return messagebox.showerror("错误", "目录不存在")
            try:
                mb, n = float(self.mb.get()), int(self.topn.get())
            except ValueError:
                mb, n = 100, 50

            def work():
                return heapq.nlargest(n, core.walk_user_files(root, int(mb * 1048576)), key=lambda x: x[1])

            def done(res):
                self.clear()
                now = time.time()
                for fp, sz, mt in res:
                    self.add((human(sz), f"{int((now - mt) / 86400)} 天前", fp), (fp, sz))
                self.info.config(text=f"共 {len(res)} 个文件，合计 {human(sum(r[1] for r in res))}")

            self.app.run_bg(work, done, "扫描大文件…（目录较大时可能需要几分钟）")

        def delete(self):
            sel = self.need_selection()
            if not sel:
                return
            total = sum(o[1] for _, o in sel)
            if not messagebox.askyesno("确认", f"将 {len(sel)} 个文件（{human(total)}）移入回收站？"):
                return

            def work():
                ok = []
                for iid, (fp, sz) in sel:
                    if core.safe_remove(fp):
                        ok.append((iid, sz))
                return ok

            def done(ok):
                for iid, _ in ok:
                    self.tree.delete(iid)
                    self.data.pop(iid, None)
                messagebox.showinfo("完成", f"已处理 {len(ok)} 个文件，释放约 {human(sum(s for _, s in ok))}")

            self.app.run_bg(work, done, "处理中…")

    # ------------------------------------------------------------ 重复文件
    class DupTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("g", "组", 50, "e"), ("size", "大小", 90, "e"),
                                   ("st", "状态", 70, "center"), ("path", "路径", 700, "w")])
            self.path_picker()
            self.btn("查找重复文件(≥1MB)", self.scan)
            self.btn("选中所有副本", self.select_copies)
            self.btn("删除选中", self.delete)
            self.info.config(text="灰色“保留”为建议保留的一份（路径最短/最早），只会删除你选中的“副本”。")

        def scan(self):
            root = Path(self.root_var.get())
            if not root.is_dir():
                return messagebox.showerror("错误", "目录不存在")

            def done(groups):
                self.clear()
                waste = 0
                for gi, (sz, g) in enumerate(groups, 1):
                    self.add((gi, human(sz), "保留", g[0][0]), dict(path=g[0][0], size=sz, keep=True), ("keep",))
                    for fp, _ in g[1:]:
                        self.add((gi, human(sz), "副本", fp), dict(path=fp, size=sz, keep=False))
                        waste += sz
                self.info.config(text=f"{len(groups)} 组重复文件，删除全部副本可释放 {human(waste)}" if groups else "没有发现重复文件")

            self.app.run_bg(lambda: find_duplicates(root), done, "查找重复文件…（会计算文件哈希，较慢）")

        def select_copies(self):
            self.tree.selection_set([i for i, o in self.data.items() if not o["keep"]])

        def delete(self):
            sel = [(i, o) for i, o in self.need_selection() or [] if not o["keep"]]
            if not sel:
                return
            total = sum(o["size"] for _, o in sel)
            if not messagebox.askyesno("确认", f"将 {len(sel)} 个副本（{human(total)}）移入回收站？"):
                return

            def work():
                return [(i, o["size"]) for i, o in sel if core.safe_remove(o["path"])]

            def done(ok):
                for iid, _ in ok:
                    self.tree.delete(iid)
                    self.data.pop(iid, None)
                messagebox.showinfo("完成", f"已处理 {len(ok)} 个文件，释放约 {human(sum(s for _, s in ok))}")

            self.app.run_bg(work, done, "处理中…")

    # ------------------------------------------------------------ 启动项
    class StartupTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("name", "名称", 220, "w"), ("kind", "类型", 110, "w"), ("cmd", "命令 / 路径", 640, "w")])
            self.btn("刷新", self.load)
            self.btn("全选", self.select_all)
            self.btn("停用选中", self.disable)
            self.btn("恢复已停用…", self.restore)
            self.info.config(text="建议停用：更新检查器、云盘/聊天工具自启、各类“助手/管家”。杀毒、输入法、驱动相关请保留。停用可随时恢复。")
            self.load()

        def load(self):
            self.clear()
            kinds = {"reg": "注册表", "file": "启动文件夹", "launchd": "LaunchAgent", "desktop": "自启动项"}
            for it in core.get_startup_items():
                if it["name"].startswith(("com.faster", "com.pcoptimizer")):
                    continue
                self.add((it["name"], kinds.get(it["kind"], it["kind"]), it["cmd"]), it)

        def disable(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno("确认", f"停用 {len(sel)} 个启动项？（会自动备份，可恢复）"):
                return
            failed = [o for _, o in sel if not core.disable_startup(o)]
            need = [o for o in failed if is_system_startup(o)]
            other = [o["name"] for o in failed if not is_system_startup(o)]
            if other:
                messagebox.showwarning("部分失败", "以下项目停用失败：\n" + "\n".join(other))
            if need and messagebox.askyesno("需要管理员权限", f"{len(need)} 个系统级启动项需要管理员权限：\n"
                                            + "\n".join(o["name"] for o in need) + "\n\n现在授权并重试？"):
                self.app.run_bg(lambda: run_elevated("disable-startup", [startup_key(o) for o in need]),
                                lambda r: (show_text(self, "结果", "\n".join(r.get("lines", []))), self.load()),
                                "等待管理员授权…")
            else:
                self.load()

        def restore(self):
            allm = core.load_manifest()
            m = [e for e in allm if not e.get("restored")]
            if not m:
                return messagebox.showinfo("提示", "没有可恢复的启动项。")
            w = tk.Toplevel(self)
            w.title("恢复已停用的启动项")
            w.geometry("520x360")
            lb = tk.Listbox(w, selectmode="extended")
            lb.pack(fill="both", expand=True, padx=8, pady=8)
            for e in m:
                lb.insert("end", f"{e.get('name')}   ({datetime.datetime.fromtimestamp(e['ts']):%Y-%m-%d %H:%M})")

            def do():
                failed = []
                for i in lb.curselection():
                    ok, msg = restore_entry(m[i])
                    if ok:
                        m[i]["restored"] = True
                    else:
                        failed.append(m[i])
                core.save_manifest(allm)
                w.destroy()
                if failed and messagebox.askyesno("需要管理员权限", f"{len(failed)} 项恢复失败，可能需要管理员权限。\n现在授权并重试？"):
                    keys = [f"{e['ts']}|{e.get('name')}" for e in failed]
                    self.app.run_bg(lambda: run_elevated("restore-startup", keys),
                                    lambda r: (show_text(self, "结果", "\n".join(r.get("lines", []))), self.load()),
                                    "等待管理员授权…")
                else:
                    self.load()

            ttk.Button(w, text="恢复选中", command=do).pack(pady=6)

    # ------------------------------------------------------------ 进程
    class ProcTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("pid", "PID", 70, "e"), ("name", "名称", 260, "w"),
                                   ("mem", "内存", 100, "e"), ("cpu", "CPU%", 70, "e")])
            self.btn("刷新", self.load)
            self.btn("结束选中进程", self.kill)
            self.info.config(text="仅显示当前用户的非系统关键进程（按内存排序）。结束进程会丢失该程序未保存的数据。")
            if not psutil:
                self.info.config(text="需要安装 psutil 才能使用此功能：pip install psutil")

        def load(self):
            if not psutil:
                return messagebox.showinfo("提示", "请先安装 psutil：pip install psutil")

            def done(rows):
                self.clear()
                for pid, name, mem, cpu in rows:
                    self.add((pid, name, human(mem), f"{cpu:.1f}"), (pid, name))

            self.app.run_bg(list_processes, done, "读取进程…")

        def kill(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno("确认", f"结束 {len(sel)} 个进程？未保存的数据会丢失。"):
                return
            fails = []
            for _, (pid, name) in sel:
                try:
                    p = psutil.Process(pid)
                    p.terminate()
                    p.wait(3)
                except psutil.TimeoutExpired:
                    fails.append(f"{name}：未响应，未强制结束")
                except Exception as e:
                    fails.append(f"{name}：{e}")
            if fails:
                messagebox.showwarning("部分未结束", "\n".join(fails))
            self.load()

    # ------------------------------------------------------------ 卸载
    class UninstallTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("size", "占用", 100, "e"), ("name", "程序名称", 700, "w")])
            self.btn("刷新列表", self.load)
            self.btn("卸载选中", self.uninstall)
            self.info.config(text="按占用空间从大到小。请只卸载确认不需要的软件；驱动、运行库(VC++/.NET)、安全软件请保留。")

        def load(self):
            def done(apps):
                self.clear()
                for a in apps[:150]:
                    self.add((human(a["size"]) if a["size"] else "未知", a["name"]), a)

            self.app.run_bg(core.installed_programs, done, "读取已安装程序…")

        def uninstall(self):
            sel = self.need_selection()
            if not sel:
                return
            for _, a in sel:
                if not messagebox.askyesno("确认卸载", f"卸载 {a['name']}？"):
                    continue
                if IS_MAC:
                    if core.safe_remove(a["path"]):
                        messagebox.showinfo("结果", "已移入废纸篓")
                    elif messagebox.askyesno("需要管理员权限", "普通权限无法移除该应用，是否授权后重试？"):
                        self.app.run_bg(lambda p=a["path"]: run_elevated("remove-app", path=p),
                                        lambda r: messagebox.showinfo("结果", "\n".join(r.get("lines", []))),
                                        "等待管理员授权…")
                elif IS_WIN:
                    subprocess.Popen(a["cmd"], shell=True)
                    messagebox.showinfo("提示", "已启动该软件自带的卸载程序，请在弹出的窗口中完成。")
                else:
                    cmd = a["cmd"]
                    if cmd.startswith("sudo ") and shutil.which("pkexec"):
                        cmd = "pkexec " + cmd[5:]
                    if cmd.startswith("sudo "):
                        show_text(self, "请在终端执行", cmd)
                    else:
                        self.app.run_bg(lambda c=cmd: sh(c.split(), timeout=600),
                                        lambda r: messagebox.showinfo("结果", "完成" if r[0] == 0 else f"失败：{r[2]}"),
                                        "卸载中…")

    # ------------------------------------------------------------ 安全扫描
    class SecurityTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("lv", "级别", 70, "center"), ("msg", "发现", 900, "w")])
            self.btn("开始扫描", self.scan)
            self.btn("🛡 管理员权限扫描（更完整）", self.scan_admin)
            self.btn("杀毒引擎查杀（Defender / ClamAV）", self.engine)
            self.info.config(text="启发式检测：“中危/提示”多数需要你人工确认，并不等于中毒；扫不出结果也不代表一定安全。"
                                  "管理员扫描可看到全部进程的网络连接。")

        def scan(self):
            self.app.run_bg(run_all_scans, self.fill, "风险扫描中…（约 1-2 分钟）")

        def scan_admin(self):
            self.app.run_bg(lambda: [tuple(x) for x in run_elevated("scan").get("findings", [])],
                            self.fill, "等待管理员授权并扫描…")

        def fill(self, res):
            self.clear()
            tagmap = {"高危": "high", "中危": "mid", "提示": "note"}
            for lv, msg in res:
                self.add((lv, msg), (lv, msg), (tagmap[lv],))
            if not res:
                self.add(("正常", "未发现明显异常"), None)
            cnt = {k: sum(1 for l, _ in res if l == k) for k in ("高危", "中危", "提示")}
            self.info.config(text=f"高危 {cnt['高危']} · 中危 {cnt['中危']} · 提示 {cnt['提示']}（报告已保存到 {core.REPORT_DIR}）")
            rp = core.REPORT_DIR / f"security_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
            rp.write_text("\n".join(f"[{l}] {m}" for l, m in res) or "未发现明显异常", encoding="utf-8")

        def engine(self):
            if IS_WIN:
                if not messagebox.askyesno("Windows Defender", "执行 Defender 快速扫描？可能需要几分钟。"):
                    return
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Update-MpSignature; Start-MpScan -ScanType QuickScan; Get-MpThreat | Format-List"]
                self.app.run_bg(lambda: sh(cmd, timeout=3600),
                                lambda r: show_text(self, "Defender 扫描结果",
                                                    (r[1].strip() or "未发现威胁。") + (f"\n\n{r[2]}" if r[2].strip() else "")),
                                "Defender 扫描中…")
            elif shutil.which("clamscan"):
                d = filedialog.askdirectory(initialdir=str(HOME), title="选择要用 ClamAV 扫描的目录")
                if d:
                    self.app.run_bg(lambda: sh(["clamscan", "-r", "-i", d], timeout=7200),
                                    lambda r: show_text(self, "ClamAV 扫描结果", r[1] or r[2]), "ClamAV 扫描中…")
            else:
                tip = ("未找到杀毒引擎。\n\nmacOS：系统内置 XProtect 会自动运行；按需扫描可安装 ClamAV（brew install clamav）或 Malwarebytes。\n"
                       "Linux：sudo apt install clamav && sudo freshclam；rootkit 检测可用 rkhunter / chkrootkit。")
                messagebox.showinfo("提示", tip)

    # ------------------------------------------------------------ 自动清理
    class ScheduleTab(ttk.Frame):
        def __init__(self, app):
            super().__init__(app.nb)
            self.app = app
            cfg = load_cfg()
            pad = dict(padx=10, pady=4)

            # 计划
            f1 = ttk.LabelFrame(self, text="① 执行计划")
            f1.pack(fill="x", padx=10, pady=(8, 4))
            self.freq = tk.StringVar(value=cfg["freq"])
            for i, (k, v) in enumerate(FREQ_CN.items()):
                ttk.Radiobutton(f1, text=v, value=k, variable=self.freq).grid(row=0, column=i, sticky="w", **pad)
            h, m = cfg["time"].split(":")
            self.hh, self.mm = tk.StringVar(value=h), tk.StringVar(value=m)
            ttk.Label(f1, text="时间：").grid(row=0, column=3, **pad)
            ttk.Spinbox(f1, from_=0, to=23, width=3, format="%02.0f", textvariable=self.hh).grid(row=0, column=4)
            ttk.Label(f1, text=":").grid(row=0, column=5)
            ttk.Spinbox(f1, from_=0, to=59, width=3, format="%02.0f", textvariable=self.mm).grid(row=0, column=6)
            ttk.Label(f1, text="每周星期：").grid(row=1, column=0, **pad)
            self.wd = ttk.Combobox(f1, values=WEEKDAYS_CN, width=6, state="readonly")
            self.wd.current(int(cfg["weekday"]))
            self.wd.grid(row=1, column=1, sticky="w")
            ttk.Label(f1, text="每月几号：").grid(row=1, column=2, **pad)
            self.md = tk.StringVar(value=str(cfg["monthday"]))
            ttk.Spinbox(f1, from_=1, to=28, width=4, textvariable=self.md).grid(row=1, column=3, sticky="w")

            # 内容
            f2 = ttk.LabelFrame(self, text="② 清理内容")
            f2.pack(fill="x", padx=10, pady=4)
            self.junk = tk.BooleanVar(value=cfg["junk"])
            self.age = tk.StringVar(value=str(cfg["junk_min_age_days"]))
            self.trash = tk.BooleanVar(value=cfg["empty_trash"])
            self.purge = tk.StringVar(value=str(cfg["purge_own_trash_days"]))
            ttk.Checkbutton(f2, text="清理系统垃圾/缓存，仅清理未修改超过", variable=self.junk).grid(row=0, column=0, sticky="w", **pad)
            ttk.Spinbox(f2, from_=0, to=90, width=4, textvariable=self.age).grid(row=0, column=1)
            ttk.Label(f2, text="天的文件（0 = 1 小时前）").grid(row=0, column=2, sticky="w")
            ttk.Checkbutton(f2, text="清空系统回收站 / 废纸篓（不可恢复）", variable=self.trash).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
            ttk.Label(f2, text="彻底删除本工具回收站中超过").grid(row=2, column=0, sticky="e", **pad)
            ttk.Spinbox(f2, from_=0, to=365, width=4, textvariable=self.purge).grid(row=2, column=1)
            ttk.Label(f2, text="天的文件（0 = 不处理）").grid(row=2, column=2, sticky="w")

            # 文件夹规则
            f3 = ttk.LabelFrame(self, text="③ 自定义文件夹：超过 N 天未修改的文件移入回收站（可找回）")
            f3.pack(fill="x", padx=10, pady=4)
            self.rules = ttk.Treeview(f3, columns=("path", "days"), show="headings", height=3)
            self.rules.heading("path", text="文件夹")
            self.rules.heading("days", text="天数")
            self.rules.column("path", width=560)
            self.rules.column("days", width=60, anchor="e")
            self.rules.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            bf = ttk.Frame(f3)
            bf.pack(side="left", padx=6)
            ttk.Button(bf, text="添加文件夹…", command=self.add_rule).pack(fill="x", pady=2)
            ttk.Button(bf, text="删除选中", command=lambda: [self.rules.delete(i) for i in self.rules.selection()]).pack(fill="x", pady=2)
            for r in cfg["folders"]:
                self.rules.insert("", "end", values=(r["path"], r["days"]))

            # 操作
            f4 = ttk.Frame(self)
            f4.pack(fill="x", padx=10, pady=6)
            ttk.Button(f4, text="保存并启用定时任务", command=self.enable).pack(side="left", padx=3)
            ttk.Button(f4, text="停用定时任务", command=self.disable).pack(side="left", padx=3)
            ttk.Button(f4, text="试运行（只统计）", command=lambda: self.run_now(True)).pack(side="left", padx=3)
            ttk.Button(f4, text="立即清理一次", command=lambda: self.run_now(False)).pack(side="left", padx=3)
            self.status = ttk.Label(f4, text="")
            self.status.pack(side="left", padx=12)

            f5 = ttk.LabelFrame(self, text="运行日志")
            f5.pack(fill="both", expand=True, padx=10, pady=(2, 8))
            self.logbox = scrolledtext.ScrolledText(f5, height=8, state="disabled")
            self.logbox.pack(fill="both", expand=True, padx=4, pady=4)
            ttk.Button(f5, text="刷新日志", command=self.refresh).pack(anchor="e", padx=4, pady=(0, 4))
            self.refresh()

        def add_rule(self):
            d = filedialog.askdirectory(initialdir=str(HOME), title="选择要定期清理的文件夹")
            if not d:
                return
            bad = danger_reason(d)
            if bad:
                return messagebox.showerror("不允许", bad)
            days = simpledialog.askinteger("天数", "清理该文件夹内未修改超过多少天的文件？", initialvalue=30,
                                           minvalue=1, maxvalue=3650, parent=self)
            if days:
                if not messagebox.askyesno("确认", f"{d}\n中超过 {days} 天未修改的文件将被定期移入回收站。\n确认添加？"):
                    return
                self.rules.insert("", "end", values=(d, days))

        def collect(self):
            def num(v, default, lo, hi):
                try:
                    return max(lo, min(hi, int(float(v.get()))))
                except ValueError:
                    return default
            cfg = load_cfg()
            cfg.update(freq=self.freq.get(), time=f"{num(self.hh, 12, 0, 23):02d}:{num(self.mm, 30, 0, 59):02d}",
                       weekday=self.wd.current(), monthday=num(self.md, 1, 1, 28), junk=self.junk.get(),
                       junk_min_age_days=num(self.age, 1, 0, 90), empty_trash=self.trash.get(),
                       purge_own_trash_days=num(self.purge, 30, 0, 365),
                       folders=[dict(path=self.rules.set(i, "path"), days=int(self.rules.set(i, "days")))
                                for i in self.rules.get_children()])
            return cfg

        def enable(self):
            cfg = self.collect()
            ok, msg = install_schedule(cfg)
            cfg["enabled"] = ok
            save_cfg(cfg)
            (messagebox.showinfo if ok else messagebox.showerror)("定时任务", msg)
            self.refresh()

        def disable(self):
            ok, msg = remove_schedule()
            cfg = load_cfg()
            cfg["enabled"] = False
            save_cfg(cfg)
            messagebox.showinfo("定时任务", msg)
            self.refresh()

        def run_now(self, dry):
            save_cfg(self.collect())
            self.app.run_bg(lambda: auto_clean(dry), lambda r: (show_text(self, "试运行结果" if dry else "清理结果", "\n".join(r[1])),
                                                                 self.refresh()), "清理中…")

        def refresh(self):
            cfg = load_cfg()
            on = schedule_installed()
            txt = "定时任务：已启用" if on else "定时任务：未启用"
            if cfg["last_run"]:
                txt += f"  |  上次运行 {cfg['last_run']}（{cfg['last_result']}）"
            self.status.config(text=txt, foreground="#2e7d32" if on else "#999")
            try:
                lines = LOG.read_text(encoding="utf-8").splitlines()[-200:]
            except OSError:
                lines = ["（暂无日志）"]
            self.logbox.config(state="normal")
            self.logbox.delete("1.0", "end")
            self.logbox.insert("1.0", "\n".join(lines))
            self.logbox.see("end")
            self.logbox.config(state="disabled")

    # ------------------------------------------------------------ 主窗口
    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"Faster v{__version__}" + ("  [管理员]" if core.is_admin() else ""))
            self.geometry("1040x700")
            self.minsize(880, 560)
            try:
                ttk.Style(self).theme_use("vista" if IS_WIN else "aqua" if IS_MAC else "clam")
            except tk.TclError:
                pass
            self.q, self.busy_n = queue.Queue(), 0
            bar = ttk.Frame(self)
            bar.pack(side="bottom", fill="x")
            self.status = ttk.Label(bar, text="就绪")
            self.status.pack(side="left", padx=8, pady=3)
            self.pb = ttk.Progressbar(bar, mode="indeterminate", length=160)
            self.pb.pack(side="right", padx=8)
            self.nb = ttk.Notebook(self)
            self.nb.pack(fill="both", expand=True)
            for title, cls in (("概览", HomeTab), ("垃圾清理", JunkTab), ("大文件", LargeTab), ("重复文件", DupTab),
                               ("启动项", StartupTab), ("后台进程", ProcTab), ("卸载程序", UninstallTab),
                               ("风险扫描", SecurityTab), ("自动清理", ScheduleTab)):
                self.nb.add(cls(self), text=title)
            self.after(100, self.poll)

        def run_bg(self, fn, done=None, msg="处理中…"):
            self.busy_n += 1
            self.status.config(text=msg)
            self.pb.start(12)

            def target():
                try:
                    res, err = fn(), None
                except Exception as e:
                    res, err = None, e
                self.q.put((done, res, err))

            threading.Thread(target=target, daemon=True).start()

        def poll(self):
            try:
                while True:
                    done, res, err = self.q.get_nowait()
                    self.busy_n -= 1
                    if self.busy_n <= 0:
                        self.busy_n = 0
                        self.pb.stop()
                        self.status.config(text="就绪")
                    if err:
                        messagebox.showerror("出错", str(err))
                    elif done:
                        done(res)
            except queue.Empty:
                pass
            self.after(100, self.poll)


def launch_gui():
    if tk is None:
        print("未找到 tkinter。Windows/macOS 请使用 python.org 的官方安装包；Linux 请执行：sudo apt install python3-tk")
        sys.exit(1)
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


def main():
    if "--version" in sys.argv:
        print(f"Faster {__version__}")
    elif "--elevated" in sys.argv:
        elevated_main()
    elif "--auto-clean" in sys.argv:
        _, lines = auto_clean(dry_run="--dry-run" in sys.argv)
        print("\n".join(lines))
    else:
        launch_gui()


if __name__ == "__main__":
    main()
