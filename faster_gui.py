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
import faster_crypto as fc  # noqa: E402
import faster_i18n as i18n  # noqa: E402
from faster_i18n import tr  # noqa: E402
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
TRASH_NAMES = {tr("废纸篓"), tr("回收站"), tr("回收站信息")}
WEEKDAYS_CN = [tr("周一"), tr("周二"), tr("周三"), tr("周四"), tr("周五"), tr("周六"), tr("周日")]
FREQ_CN = {"daily": tr("每天"), "weekly": tr("每周"), "monthly": tr("每月")}

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
        return tr("路径无效")
    if not p.is_dir():
        return tr("目录不存在")
    if p == HOME or p == Path(p.anchor) or len(p.parts) <= 2:
        return tr("过于靠近根目录/主目录，已拒绝")
    if IS_WIN:
        sysd = [os.environ.get(k) for k in ("WINDIR", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA")]
    else:
        sysd = ["/usr", "/etc", "/bin", "/sbin", "/lib", "/boot", "/System", "/Library", "/Applications",
                "/var", "/opt", "/dev", "/proc", "/sys", "/private/etc"]
    for s in sysd:
        if s and (p == Path(s) or Path(s) in p.parents):
            return tr("系统目录，已拒绝")
    if APP_DIR in (p, *p.parents):
        return tr("本工具自身目录，已拒绝")
    return None


def _has_wallet(child):
    if core.is_wallet_path(str(child)):
        return True
    if child.is_dir() and not child.is_symlink():
        for r, _, fs in os.walk(child):
            if core.is_wallet_path(r) or any(core.is_wallet_path(os.path.join(r, f)) for f in fs):
                return True
    return False


def empty_dir(p):
    freed = 0
    for child in Path(p).iterdir():
        try:
            if _has_wallet(child):
                continue                      # 钱包文件即使在废纸篓里也不自动清空
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
    tag = tr("[试运行·不删除] ") if dry_run else ""
    lines.append(tr("{0}开始自动清理 {1:%Y-%m-%d %H:%M:%S}", tag, datetime.datetime.now()))

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
                lines.append(tr("  垃圾缓存 · {0}：{1} 个文件，{2}", name, len(files), human(done)))
            freed += done

    # 2) 清空回收站 / 废纸篓
    if cfg["empty_trash"]:
        if IS_WIN:
            if not dry_run:
                try:
                    import ctypes
                    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
                    lines.append(tr("  已清空回收站"))
                except Exception as e:
                    lines.append(tr("  清空回收站失败：{0}", e))
            else:
                lines.append(tr("  将清空回收站"))
        else:
            for name, p in core.junk_targets():
                if name in TRASH_NAMES:
                    sz = core.dir_size(p)
                    if not dry_run:
                        sz = empty_dir(p)
                    if sz:
                        lines.append(tr("  清空 {0}：{1}", name, human(sz)))
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
            lines.append(tr("  工具回收站中超过 {0} 天的文件：{1}", pd, human(sz_total)))
            freed += sz_total

    # 4) 自定义文件夹规则：超过 N 天未修改的文件 → 移入回收站（可找回）
    for rule in cfg["folders"]:
        root, days = rule.get("path", ""), int(rule.get("days", 30))
        bad = danger_reason(root)
        if bad:
            lines.append(tr("  跳过文件夹 {0}：{1}", root, bad))
            continue
        cutoff, n, sz_total, skipped = time.time() - days * 86400, 0, 0, 0
        for r, dirs, files in os.walk(root, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(r, d))]
            for f in files:
                fp = os.path.join(r, f)
                try:
                    st = os.lstat(fp)
                    if st.st_mtime >= cutoff:
                        continue
                    if core.is_wallet_path(fp):
                        skipped += 1
                        continue
                    if dry_run or core.safe_remove(fp):
                        n += 1
                        sz_total += st.st_size
                except OSError:
                    pass
        if n:
            lines.append(tr("  文件夹 {0}：{1} 个超过 {2} 天的文件，{3}{4}", root, n, days, human(sz_total), '' if dry_run else tr("（已移入回收站，可找回）")))
        if skipped:
            lines.append(tr("  文件夹 {0}：已保护并跳过 {1} 个钱包文件", root, skipped))
        freed += sz_total

    lines.append(tr("{0}合计{1} {2}", tag, tr("可释放") if dry_run else tr("释放"), human(freed)))
    if not dry_run:
        cfg["last_run"] = f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
        cfg["last_result"] = tr("释放 {0}", human(freed))
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
            return rc == 0, tr("已创建 Windows 计划任务") if rc == 0 else tr("创建失败：{0}", err or out)
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
            return rc == 0, tr("已创建 launchd 定时任务（电脑休眠错过时，唤醒后会补跑）") if rc == 0 else tr("加载失败：{0}", err or out)
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
            return rc == 0, tr("已创建 systemd 用户定时器（错过的任务开机后会补跑）") if rc == 0 else tr("启用失败：{0}", err or out)
        if shutil.which("crontab"):
            _, cur, _ = sh(["crontab", "-l"])
            keep = [l for l in cur.splitlines() if CRON_TAG not in l]
            spec = {"daily": f"{m} {h} * * *", "weekly": f"{m} {h} * * {(wd + 1) % 7}",
                    "monthly": f"{m} {h} {md} * *"}[freq]
            keep.append(f"{spec} {_quoted(cmd)} {CRON_TAG}")
            rc, out, err = sh(["crontab", "-"], input_text="\n".join(keep) + "\n")
            return rc == 0, tr("已写入 crontab") if rc == 0 else tr("写入失败：{0}", err or out)
        return False, tr("未找到 systemd 或 cron，无法创建定时任务")
    except Exception as e:
        return False, tr("出错：{0}", e)


def remove_schedule():
    remove_legacy_schedule()
    try:
        if IS_WIN:
            rc, out, err = sh(["schtasks", "/Delete", "/TN", WIN_TASK, "/F"])
            return True, tr("已移除计划任务")
        if IS_MAC:
            plist = HOME / "Library/LaunchAgents" / f"{MAC_LABEL}.plist"
            sh(["launchctl", "unload", str(plist)])
            plist.unlink(missing_ok=True)
            return True, tr("已移除定时任务")
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
        return True, tr("已移除定时任务")
    except Exception as e:
        return False, tr("出错：{0}", e)


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


def scan_miners_core():
    for f in fc.detect_miners(2.0)["findings"]:
        core.add(f["level"], f["msg"])


def open_location(path):
    p = Path(path)
    try:
        if IS_WIN:
            subprocess.Popen(["explorer", f"/select,{p}"] if p.exists() else ["explorer", str(p.parent)])
        elif IS_MAC:
            subprocess.Popen(["open", "-R", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p if p.is_dir() else p.parent)])
    except Exception:
        pass


def run_all_scans():
    core.findings.clear()
    for fn in (core.scan_processes, core.scan_persistence, core.scan_hosts,
               core.scan_temp_executables, core.scan_security_posture, scan_miners_core):
        try:
            fn()
        except Exception as e:
            core.add(tr("提示"), tr("检查 {0} 出错：{1}", fn.__name__, e))
    order = {tr("高危"): 0, tr("中危"): 1, tr("提示"): 2}
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
        targets = [(tr("系统临时文件"), w / "Temp", 1, None),
                   (tr("Windows 更新下载缓存"), w / "SoftwareDistribution/Download", 1, None),
                   (tr("Windows 错误报告"), pd / "Microsoft/Windows/WER", 1, None)]
    elif IS_MAC:
        targets = [(tr("系统级缓存 /Library/Caches"), Path("/Library/Caches"), 24, None),
                   (tr("诊断报告"), Path("/Library/Logs/DiagnosticReports"), 24, None)]
    else:
        targets = [(tr("apt 软件包缓存"), Path("/var/cache/apt/archives"), 1, (".deb",)),
                   (tr("/var/tmp 超过7天的文件"), Path("/var/tmp"), 24 * 7, None),
                   (tr("systemd 核心转储"), Path("/var/lib/systemd/coredump"), 24, None)]
    lines, total = [], 0
    for name, p, h, suf in targets:
        n = _purge(p, h, suf)
        total += n
        lines.append(tr("{0}：释放 {1}", name, human(n)))
    if IS_LINUX and shutil.which("journalctl"):
        rc, _, err = sh(["journalctl", "--vacuum-size=200M"], timeout=120)
        lines.append(tr("systemd 日志：已压缩到 200MB 以内") if rc == 0 else tr("systemd 日志清理失败：{0}", err[:80]))
    lines.append(tr("合计释放 {0}", human(total)))
    return lines


def helper_work(action, keys, path):
    if not core.is_admin():
        return dict(ok=False, lines=[tr("未获得管理员权限")])
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
                    lines.append(tr("跳过 {0}：非系统级项目，无需管理员权限", it['name']))
                else:
                    lines.append((tr("已停用 ") if core.disable_startup(it) else tr("停用失败 ")) + it["name"])
        if IS_MAC:
            lines.append(tr("提示：系统级 LaunchAgent 需注销并重新登录后才完全生效"))
        return dict(ok=True, lines=lines)
    if action == "restore-startup":
        m, lines = core.load_manifest(), []
        for e in m:
            if f"{e.get('ts')}|{e.get('name')}" in keys and not e.get("restored"):
                ok, msg = restore_entry(e)
                if ok:
                    e["restored"] = True
                lines.append((tr("已恢复 ") if ok else tr("恢复失败 ")) + f"{e.get('name')} {msg}")
        core.save_manifest(m)
        return dict(ok=True, lines=lines)
    if action == "remove-app" and IS_MAC:
        p = Path(path or "")
        if p.suffix != ".app" or p.is_symlink() or p.parent != Path("/Applications") or not p.exists():
            return dict(ok=False, lines=[tr("拒绝：只允许移除 /Applications 下的 .app")])
        dest = HOME / ".Trash" / f"{p.stem}_{int(time.time())}.app"
        dest.parent.mkdir(exist_ok=True)
        shutil.move(str(p), str(dest))
        return dict(ok=True, lines=[tr("已将 {0} 移入废纸篓", p.name)])
    return dict(ok=False, lines=[tr("不支持的操作：{0}", action)])


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
        res = dict(ok=False, lines=[tr("执行出错：{0}", e)])
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
        raise RuntimeError(tr("未找到 pkexec（polkit）。请安装 policykit-1，或在终端用 sudo 运行本程序。"))
    return ["pkexec", "env", f"HOME={HOME}"] + cmd


def run_elevated(action, keys=None, path=None, timeout=900):
    """以管理员权限执行白名单动作，返回结果 dict；用户取消授权则抛 RuntimeError"""
    if core.is_admin():
        return helper_work(action, keys, path)
    io = APP_DIR / f"elev_{os.getpid()}_{int(time.time() * 1000)}.json"
    res_file = Path(str(io) + ".res")
    io.write_text(json.dumps(dict(keys=keys or [], path=path), ensure_ascii=False), encoding="utf-8")
    cmd = script_cmd() + ["--elevated", action, "--home", str(HOME), "--io", str(io), "--lang", i18n.LANG]
    try:
        rc, out, err = sh(_elevation_argv(cmd), timeout=timeout)
        if not res_file.exists():
            raise RuntimeError(tr("已取消，或未获得管理员授权。") + (f"\n{(err or out).strip()[:200]}" if (err or out).strip() else ""))
        return json.loads(res_file.read_text(encoding="utf-8"))
    finally:
        for f in (io, res_file):
            try:
                f.unlink()
            except OSError:
                pass


def restart_app():
    """重新启动本程序（切换语言后用）；成功返回 True"""
    try:
        subprocess.Popen(script_cmd(), close_fds=True)
        return True
    except Exception:
        return False


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

        def __init__(self, app, columns, parent=None):
            super().__init__(parent or app.nb)
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
                messagebox.showinfo(tr("提示"), tr("请先在列表中选择项目（可按住 Ctrl/Shift 多选，或点“全选”）。"))
            return sel

        def path_picker(self, default=None):
            self.root_var = tk.StringVar(value=str(default or HOME))
            ttk.Label(self.top, text=tr("目录：")).pack(side="left")
            ttk.Entry(self.top, textvariable=self.root_var, width=34).pack(side="left")
            ttk.Button(self.top, text=tr("浏览…"), command=lambda: self.root_var.set(
                filedialog.askdirectory(initialdir=self.root_var.get()) or self.root_var.get())).pack(side="left", padx=3)

    # ------------------------------------------------------------ 概览
    class HomeTab(ttk.Frame):
        def __init__(self, app):
            super().__init__(app.nb)
            self.app = app
            ttk.Label(self, text="Faster", font=("", 20, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
            ttk.Label(self, text=tr("版本 v{0} · {1} {2} · 当前：{3}权限", __version__, platform.system(), platform.release(), tr("管理员") if core.is_admin() else tr("普通用户"))).pack(anchor="w", padx=18)
            lrow = ttk.Frame(self)
            lrow.pack(anchor="w", padx=18, pady=(6, 0))
            ttk.Label(lrow, text=tr("语言 / Language：")).pack(side="left")
            self.lang_codes = ["auto"] + list(i18n.LANGUAGES)
            self.lang_box = ttk.Combobox(lrow, state="readonly", width=16, values=[
                tr("跟随系统") if c == "auto" else i18n.LANGUAGES[c] for c in self.lang_codes])
            self.lang_box.current(self.lang_codes.index(i18n.saved_language()))
            self.lang_box.pack(side="left", padx=6)
            self.lang_box.bind("<<ComboboxSelected>>", self.change_language)
            if not core.is_admin():
                row = ttk.Frame(self)
                row.pack(anchor="w", padx=18, pady=(6, 0))
                if IS_WIN:
                    ttk.Button(row, text=tr("🛡 以管理员身份重新启动（一次授权，全部功能可用）"),
                               command=self.relaunch).pack(side="left")
                ttk.Label(row, text=tr("也可不重启：需要管理员权限的功能会按提示单独授权") if IS_WIN else
                          tr("需要管理员权限的功能会按提示弹出系统授权窗口（输入开机密码即可）"),
                          foreground="#555").pack(side="left", padx=8)
            box = ttk.Frame(self)
            box.pack(fill="x", padx=18, pady=14)
            self.bars = {}
            for key, label in (("disk", tr("磁盘")), ("mem", tr("内存")), ("cpu", "CPU")):
                ttk.Label(box, text=label, width=6).grid(row=len(self.bars), column=0, sticky="w", pady=4)
                pb = ttk.Progressbar(box, length=420, maximum=100)
                pb.grid(row=len(self.bars), column=1, pady=4)
                lb = ttk.Label(box, text="…", width=34)
                lb.grid(row=len(self.bars), column=2, padx=8, sticky="w")
                self.bars[key] = (pb, lb)
            ttk.Button(self, text=tr("一键体检（只检查，不修改）"), command=self.check).pack(anchor="w", padx=18)
            self.result = ttk.Label(self, text="", justify="left")
            self.result.pack(anchor="w", padx=18, pady=10)
            tips = (tr("使用提示：\n  • 所有删除/停用操作都会先让你确认；被删文件优先进回收站（或工具回收站，可找回）。\n  • “自动清理”页可设置每天/每周/每月定时清理，由系统计划任务执行，不需要保持本程序运行。\n  • “钱包安全”页：钱包文件自动受保护、助记词/私钥泄露扫描、挖矿检测、剪贴板劫持守护。\n  • 风险扫描为启发式检测，不能替代专业杀毒软件。"))
            ttk.Label(self, text=tips, foreground="#555", justify="left").pack(anchor="w", padx=18, pady=10)
            self.refresh()

        def change_language(self, _e=None):
            code = self.lang_codes[self.lang_box.current()]
            if code == i18n.saved_language():
                return
            i18n.save_language(code)
            # 先保存，再问是否立即重启：重启后所有界面文字才会切换
            if messagebox.askyesno(tr("语言 / Language"), tr("语言已更改，需要重启程序才能完全生效。现在重启吗？")):
                if restart_app():
                    self.app.destroy()

        def relaunch(self):
            if relaunch_as_admin():
                self.app.destroy()
            else:
                messagebox.showwarning(tr("提示"), tr("未能获得管理员权限（授权被取消）。"))

        def refresh(self):
            du = shutil.disk_usage(HOME)
            self.bars["disk"][0]["value"] = du.used / du.total * 100
            self.bars["disk"][1].config(text=tr("已用 {0} / 共 {1}（剩 {2}）", human(du.used), human(du.total), human(du.free)))
            if psutil:
                vm = psutil.virtual_memory()
                self.bars["mem"][0]["value"] = vm.percent
                self.bars["mem"][1].config(text=tr("已用 {0} / 共 {1}", human(vm.used), human(vm.total)))
                c = psutil.cpu_percent(None)
                self.bars["cpu"][0]["value"] = c
                self.bars["cpu"][1].config(text=f"{c:.0f}%")
            else:
                self.bars["mem"][1].config(text=tr("需要安装 psutil"))
                self.bars["cpu"][1].config(text=tr("需要安装 psutil"))
            self.after(4000, self.refresh)

        def check(self):
            def work():
                junk = sum(sum(s for _, s in core.list_files_in(p)) for _, p in core.junk_targets())
                return junk, len(core.get_startup_items())

            self.app.run_bg(work, lambda r: self.result.config(
                text=tr("可清理垃圾：约 {0}\n开机启动项：{1} 个\n建议到对应页面处理。", human(r[0]), r[1])), tr("体检中…"))

    # ------------------------------------------------------------ 垃圾清理
    class JunkTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("name", tr("项目"), 240, "w"), ("size", tr("可释放"), 90, "e"),
                                   ("n", tr("文件数"), 70, "e"), ("path", tr("位置"), 420, "w")])
            self.btn(tr("扫描"), self.scan)
            self.btn(tr("全选"), self.select_all)
            self.btn(tr("清理选中项"), self.clean)
            self.btn(tr("🛡 管理员清理系统级垃圾"), self.clean_system)
            if IS_WIN:
                self.btn(tr("清空回收站"), self.empty_bin)
            ttk.Label(self.top, text=tr("清理浏览器缓存后网页首次加载会稍慢，不会丢失密码/书签")).pack(side="left", padx=10)

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
                self.info.config(text=tr("可释放合计 {0}", human(sum(r[3] for r in res))) if res else tr("没有发现可清理的垃圾"))

            self.app.run_bg(work, done, tr("扫描垃圾文件…"))

        def clean(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno(tr("确认"), tr("确认清理选中的 {0} 项？", len(sel))):
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
                messagebox.showinfo(tr("完成"), tr("已释放约 {0}", human(freed)))
                self.scan()

            self.app.run_bg(work, done, tr("清理中…"))

        def clean_system(self):
            what = {"win": tr("Windows 系统临时文件、更新下载缓存、错误报告"),
                    "mac": tr("/Library/Caches 系统级缓存、诊断报告"),
                    "linux": tr("apt 软件包缓存、/var/tmp 旧文件、systemd 日志(压缩到200MB)")}["win" if IS_WIN else "mac" if IS_MAC else "linux"]
            if not messagebox.askyesno(tr("管理员清理"), tr("将以管理员权限清理：\n{0}\n\n继续？（随后会弹出系统授权窗口）", what)):
                return
            self.app.run_bg(lambda: run_elevated("clean-system"),
                            lambda r: show_text(self, tr("系统级清理结果"), "\n".join(r.get("lines", []))),
                            tr("等待管理员授权…"))

        def empty_bin(self):
            if messagebox.askyesno(tr("确认"), tr("清空回收站？此操作不可恢复。")):
                import ctypes
                ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
                messagebox.showinfo(tr("完成"), tr("回收站已清空"))

    # ------------------------------------------------------------ 大文件
    class LargeTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("size", tr("大小"), 90, "e"), ("age", tr("最后修改"), 90, "e"), ("path", tr("路径"), 700, "w")])
            self.path_picker()
            self.mb = tk.StringVar(value="100")
            self.topn = tk.StringVar(value="50")
            ttk.Label(self.top, text="≥").pack(side="left")
            ttk.Spinbox(self.top, from_=1, to=100000, width=6, textvariable=self.mb).pack(side="left")
            ttk.Label(self.top, text=tr("MB  前")).pack(side="left")
            ttk.Spinbox(self.top, from_=5, to=500, width=5, textvariable=self.topn).pack(side="left")
            ttk.Label(self.top, text=tr("个")).pack(side="left", padx=(0, 6))
            self.btn(tr("扫描（大→小）"), self.scan)
            self.btn(tr("全选"), self.select_all)
            self.btn(tr("删除选中"), self.delete)
            self.info.config(text=tr("这些文件无法自动判断是否有用（视频/虚拟机/安装包等），请自行甄别；删除后进回收站。钱包文件已被自动保护、不会出现在列表里。"))

        def scan(self):
            root = Path(self.root_var.get())
            if not root.is_dir():
                return messagebox.showerror(tr("错误"), tr("目录不存在"))
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
                    self.add((human(sz), tr("{0} 天前", int((now - mt) / 86400)), fp), (fp, sz))
                self.info.config(text=tr("共 {0} 个文件，合计 {1}", len(res), human(sum(r[1] for r in res))))

            self.app.run_bg(work, done, tr("扫描大文件…（目录较大时可能需要几分钟）"))

        def delete(self):
            sel = self.need_selection()
            if not sel:
                return
            total = sum(o[1] for _, o in sel)
            if not messagebox.askyesno(tr("确认"), tr("将 {0} 个文件（{1}）移入回收站？", len(sel), human(total))):
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
                messagebox.showinfo(tr("完成"), tr("已处理 {0} 个文件，释放约 {1}", len(ok), human(sum(s for _, s in ok))))

            self.app.run_bg(work, done, tr("处理中…"))

    # ------------------------------------------------------------ 重复文件
    class DupTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("g", tr("组"), 50, "e"), ("size", tr("大小"), 90, "e"),
                                   ("st", tr("状态"), 70, "center"), ("path", tr("路径"), 700, "w")])
            self.path_picker()
            self.btn(tr("查找重复文件(≥1MB)"), self.scan)
            self.btn(tr("选中所有副本"), self.select_copies)
            self.btn(tr("删除选中"), self.delete)
            self.info.config(text=tr("灰色“保留”为建议保留的一份（路径最短/最早），只会删除你选中的“副本”。"))

        def scan(self):
            root = Path(self.root_var.get())
            if not root.is_dir():
                return messagebox.showerror(tr("错误"), tr("目录不存在"))

            def done(groups):
                self.clear()
                waste = 0
                for gi, (sz, g) in enumerate(groups, 1):
                    self.add((gi, human(sz), tr("保留"), g[0][0]), dict(path=g[0][0], size=sz, keep=True), ("keep",))
                    for fp, _ in g[1:]:
                        self.add((gi, human(sz), tr("副本"), fp), dict(path=fp, size=sz, keep=False))
                        waste += sz
                self.info.config(text=tr("{0} 组重复文件，删除全部副本可释放 {1}", len(groups), human(waste)) if groups else tr("没有发现重复文件"))

            self.app.run_bg(lambda: find_duplicates(root), done, tr("查找重复文件…（会计算文件哈希，较慢）"))

        def select_copies(self):
            self.tree.selection_set([i for i, o in self.data.items() if not o["keep"]])

        def delete(self):
            sel = [(i, o) for i, o in self.need_selection() or [] if not o["keep"]]
            if not sel:
                return
            total = sum(o["size"] for _, o in sel)
            if not messagebox.askyesno(tr("确认"), tr("将 {0} 个副本（{1}）移入回收站？", len(sel), human(total))):
                return

            def work():
                return [(i, o["size"]) for i, o in sel if core.safe_remove(o["path"])]

            def done(ok):
                for iid, _ in ok:
                    self.tree.delete(iid)
                    self.data.pop(iid, None)
                messagebox.showinfo(tr("完成"), tr("已处理 {0} 个文件，释放约 {1}", len(ok), human(sum(s for _, s in ok))))

            self.app.run_bg(work, done, tr("处理中…"))

    # ------------------------------------------------------------ 启动项
    class StartupTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("name", tr("名称"), 220, "w"), ("kind", tr("类型"), 110, "w"), ("cmd", tr("命令 / 路径"), 640, "w")])
            self.btn(tr("刷新"), self.load)
            self.btn(tr("全选"), self.select_all)
            self.btn(tr("停用选中"), self.disable)
            self.btn(tr("恢复已停用…"), self.restore)
            self.info.config(text=tr("建议停用：更新检查器、云盘/聊天工具自启、各类“助手/管家”。杀毒、输入法、驱动相关请保留。停用可随时恢复。"))
            self.load()

        def load(self):
            self.clear()
            kinds = {"reg": tr("注册表"), "file": tr("启动文件夹"), "launchd": "LaunchAgent", "desktop": tr("自启动项")}
            for it in core.get_startup_items():
                if it["name"].startswith(("com.faster", "com.pcoptimizer")):
                    continue
                self.add((it["name"], kinds.get(it["kind"], it["kind"]), it["cmd"]), it)

        def disable(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno(tr("确认"), tr("停用 {0} 个启动项？（会自动备份，可恢复）", len(sel))):
                return
            failed = [o for _, o in sel if not core.disable_startup(o)]
            need = [o for o in failed if is_system_startup(o)]
            other = [o["name"] for o in failed if not is_system_startup(o)]
            if other:
                messagebox.showwarning(tr("部分失败"), tr("以下项目停用失败：\n") + "\n".join(other))
            if need and messagebox.askyesno(tr("需要管理员权限"), tr("{0} 个系统级启动项需要管理员权限：\n", len(need))
                                            + "\n".join(o["name"] for o in need) + tr("\n\n现在授权并重试？")):
                self.app.run_bg(lambda: run_elevated("disable-startup", [startup_key(o) for o in need]),
                                lambda r: (show_text(self, tr("结果"), "\n".join(r.get("lines", []))), self.load()),
                                tr("等待管理员授权…"))
            else:
                self.load()

        def restore(self):
            allm = core.load_manifest()
            m = [e for e in allm if not e.get("restored")]
            if not m:
                return messagebox.showinfo(tr("提示"), tr("没有可恢复的启动项。"))
            w = tk.Toplevel(self)
            w.title(tr("恢复已停用的启动项"))
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
                if failed and messagebox.askyesno(tr("需要管理员权限"), tr("{0} 项恢复失败，可能需要管理员权限。\n现在授权并重试？", len(failed))):
                    keys = [f"{e['ts']}|{e.get('name')}" for e in failed]
                    self.app.run_bg(lambda: run_elevated("restore-startup", keys),
                                    lambda r: (show_text(self, tr("结果"), "\n".join(r.get("lines", []))), self.load()),
                                    tr("等待管理员授权…"))
                else:
                    self.load()

            ttk.Button(w, text=tr("恢复选中"), command=do).pack(pady=6)

    # ------------------------------------------------------------ 进程
    class ProcTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("pid", "PID", 70, "e"), ("name", tr("名称"), 260, "w"),
                                   ("mem", tr("内存"), 100, "e"), ("cpu", "CPU%", 70, "e")])
            self.btn(tr("刷新"), self.load)
            self.btn(tr("结束选中进程"), self.kill)
            self.info.config(text=tr("仅显示当前用户的非系统关键进程（按内存排序）。结束进程会丢失该程序未保存的数据。"))
            if not psutil:
                self.info.config(text=tr("需要安装 psutil 才能使用此功能：pip install psutil"))

        def load(self):
            if not psutil:
                return messagebox.showinfo(tr("提示"), tr("请先安装 psutil：pip install psutil"))

            def done(rows):
                self.clear()
                for pid, name, mem, cpu in rows:
                    self.add((pid, name, human(mem), f"{cpu:.1f}"), (pid, name))

            self.app.run_bg(list_processes, done, tr("读取进程…"))

        def kill(self):
            sel = self.need_selection()
            if not sel or not messagebox.askyesno(tr("确认"), tr("结束 {0} 个进程？未保存的数据会丢失。", len(sel))):
                return
            fails = []
            for _, (pid, name) in sel:
                try:
                    p = psutil.Process(pid)
                    p.terminate()
                    p.wait(3)
                except psutil.TimeoutExpired:
                    fails.append(tr("{0}：未响应，未强制结束", name))
                except Exception as e:
                    fails.append(tr("{0}：{1}", name, e))
            if fails:
                messagebox.showwarning(tr("部分未结束"), "\n".join(fails))
            self.load()

    # ------------------------------------------------------------ 卸载
    class UninstallTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("size", tr("占用"), 100, "e"), ("name", tr("程序名称"), 700, "w")])
            self.btn(tr("刷新列表"), self.load)
            self.btn(tr("卸载选中"), self.uninstall)
            self.info.config(text=tr("按占用空间从大到小。请只卸载确认不需要的软件；驱动、运行库(VC++/.NET)、安全软件请保留。"))

        def load(self):
            def done(apps):
                self.clear()
                for a in apps[:150]:
                    self.add((human(a["size"]) if a["size"] else tr("未知"), a["name"]), a)

            self.app.run_bg(core.installed_programs, done, tr("读取已安装程序…"))

        def uninstall(self):
            sel = self.need_selection()
            if not sel:
                return
            for _, a in sel:
                if not messagebox.askyesno(tr("确认卸载"), tr("卸载 {0}？", a['name'])):
                    continue
                if IS_MAC:
                    if core.safe_remove(a["path"]):
                        messagebox.showinfo(tr("结果"), tr("已移入废纸篓"))
                    elif messagebox.askyesno(tr("需要管理员权限"), tr("普通权限无法移除该应用，是否授权后重试？")):
                        self.app.run_bg(lambda p=a["path"]: run_elevated("remove-app", path=p),
                                        lambda r: messagebox.showinfo(tr("结果"), "\n".join(r.get("lines", []))),
                                        tr("等待管理员授权…"))
                elif IS_WIN:
                    subprocess.Popen(a["cmd"], shell=True)
                    messagebox.showinfo(tr("提示"), tr("已启动该软件自带的卸载程序，请在弹出的窗口中完成。"))
                else:
                    cmd = a["cmd"]
                    if cmd.startswith("sudo ") and shutil.which("pkexec"):
                        cmd = "pkexec " + cmd[5:]
                    if cmd.startswith("sudo "):
                        show_text(self, tr("请在终端执行"), cmd)
                    else:
                        self.app.run_bg(lambda c=cmd: sh(c.split(), timeout=600),
                                        lambda r: messagebox.showinfo(tr("结果"), tr("完成") if r[0] == 0 else tr("失败：{0}", r[2])),
                                        tr("卸载中…"))

    # ------------------------------------------------------------ 安全扫描
    class SecurityTab(ListTab):
        def __init__(self, app):
            super().__init__(app, [("lv", tr("级别"), 70, "center"), ("msg", tr("发现"), 900, "w")])
            self.btn(tr("开始扫描"), self.scan)
            self.btn(tr("🛡 管理员权限扫描（更完整）"), self.scan_admin)
            self.btn(tr("杀毒引擎查杀（Defender / ClamAV）"), self.engine)
            self.info.config(text=tr("启发式检测：“中危/提示”多数需要你人工确认，并不等于中毒；扫不出结果也不代表一定安全。管理员扫描可看到全部进程的网络连接。"))

        def scan(self):
            self.app.run_bg(run_all_scans, self.fill, tr("风险扫描中…（约 1-2 分钟）"))

        def scan_admin(self):
            self.app.run_bg(lambda: [tuple(x) for x in run_elevated("scan").get("findings", [])],
                            self.fill, tr("等待管理员授权并扫描…"))

        def fill(self, res):
            self.clear()
            tagmap = {tr("高危"): "high", tr("中危"): "mid", tr("提示"): "note"}
            for lv, msg in res:
                self.add((lv, msg), (lv, msg), (tagmap[lv],))
            if not res:
                self.add((tr("正常"), tr("未发现明显异常")), None)
            cnt = {k: sum(1 for l, _ in res if l == k) for k in (tr("高危"), tr("中危"), tr("提示"))}
            self.info.config(text=tr("高危 {0} · 中危 {1} · 提示 {2}（报告已保存到 {3}）", cnt[tr("高危")], cnt[tr("中危")], cnt[tr("提示")], core.REPORT_DIR))
            rp = core.REPORT_DIR / f"security_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
            rp.write_text("\n".join(f"[{l}] {m}" for l, m in res) or tr("未发现明显异常"), encoding="utf-8")

        def engine(self):
            if IS_WIN:
                if not messagebox.askyesno("Windows Defender", tr("执行 Defender 快速扫描？可能需要几分钟。")):
                    return
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Update-MpSignature; Start-MpScan -ScanType QuickScan; Get-MpThreat | Format-List"]
                self.app.run_bg(lambda: sh(cmd, timeout=3600),
                                lambda r: show_text(self, tr("Defender 扫描结果"),
                                                    (r[1].strip() or tr("未发现威胁。")) + (f"\n\n{r[2]}" if r[2].strip() else "")),
                                tr("Defender 扫描中…"))
            elif shutil.which("clamscan"):
                d = filedialog.askdirectory(initialdir=str(HOME), title=tr("选择要用 ClamAV 扫描的目录"))
                if d:
                    self.app.run_bg(lambda: sh(["clamscan", "-r", "-i", d], timeout=7200),
                                    lambda r: show_text(self, tr("ClamAV 扫描结果"), r[1] or r[2]), tr("ClamAV 扫描中…"))
            else:
                tip = (tr("未找到杀毒引擎。\n\nmacOS：系统内置 XProtect 会自动运行；按需扫描可安装 ClamAV（brew install clamav）或 Malwarebytes。\nLinux：sudo apt install clamav && sudo freshclam；rootkit 检测可用 rkhunter / chkrootkit。"))
                messagebox.showinfo(tr("提示"), tip)

    # ------------------------------------------------------------ 钱包安全（v0.2）
    LV_TAG = {tr("高危"): "high", tr("中危"): "mid", tr("提示"): "note", tr("正常"): "keep", tr("参考"): "keep"}

    class WalletFilesTab(ListTab):
        def __init__(self, app, parent):
            super().__init__(app, [("kind", tr("类型"), 190, "w"), ("size", tr("大小"), 80, "e"), ("mod", tr("最后修改"), 100, "center"),
                                   ("cloud", tr("云同步"), 90, "center"), ("path", tr("路径"), 620, "w")], parent)
            self.btn(tr("扫描钱包文件"), self.scan)
            self.btn(tr("打开所在位置"), self.reveal)
            self.info.config(text=tr("Faster 的清理 / 大文件 / 重复文件 / 自动清理 / 卸载废纸篓清空，都会自动跳过这些文件。点“扫描”查看。"))

        def scan(self):
            def done(res):
                self.clear()
                for r in res:
                    d = datetime.date.fromtimestamp(r["mtime"]).isoformat() if r["mtime"] else "-"
                    self.add((r["kind"], human(r["size"]), d, r["cloud"] or "-", r["path"]), r, ("high",) if r["cloud"] else ())
                cloud = sum(1 for r in res if r["cloud"])
                msg = tr("发现 {0} 个钱包文件/目录，已全部受 Faster 保护。", len(res))
                if cloud:
                    msg += tr("  ⚠ 其中 {0} 个位于云同步目录（红色），云端可能有副本，建议迁出并确认已离线备份助记词。", cloud)
                self.info.config(text=msg if res else tr("没有发现钱包文件。"))

            self.app.run_bg(lambda: fc.find_wallet_files(HOME), done, tr("查找钱包文件…（会遍历主目录，可能需要几分钟）"))

        def reveal(self):
            sel = self.need_selection()
            if sel:
                open_location(sel[0][1]["path"])

    class ChainDirsTab(ListTab):
        def __init__(self, app, parent):
            super().__init__(app, [("name", tr("软件"), 140, "w"), ("total", tr("总大小"), 90, "e"), ("resync", tr("可重新同步的数据"), 220, "w"),
                                   ("wallet", tr("钱包相关（勿删）"), 190, "w"), ("path", tr("位置"), 420, "w")], parent)
            self.btn(tr("扫描区块链数据"), self.scan)
            self.btn(tr("打开所在位置"), self.reveal)
            self.tree.bind("<<TreeviewSelect>>", self.on_select)
            self.info.config(text=tr("只识别和提示，Faster 不会自动删除这些数据。删除“可重新同步”的区块数据前请先关闭对应软件，重新同步可能需要数小时到数天。"))

        def scan(self):
            def done(res):
                self.clear()
                fmt = lambda xs: tr("、").join(f"{s} {human(z)}" for s, z in xs) or "—"  # noqa: E731
                for e in res:
                    self.add((e["name"], human(e["total"]), fmt(e["resync"]), fmt(e["wallet"]), e["path"]), e)
                free = sum(z for e in res for _, z in e["resync"])
                self.info.config(text=tr("发现 {0} 个区块链软件数据目录；其中可重新同步的数据共 {1}。", len(res), human(free)) if res
                                 else tr("没有发现常见区块链软件的数据目录。"))

            self.app.run_bg(lambda: fc.known_chain_dirs(), done, tr("识别区块链数据目录…"))

        def on_select(self, _e=None):
            sel = self.selected()
            if sel and sel[0][1]["note"]:
                self.info.config(text=tr("提示：") + sel[0][1]["note"])

        def reveal(self):
            sel = self.need_selection()
            if sel:
                open_location(sel[0][1]["path"])

    class SecretScanTab(ListTab):
        MAX_ROWS = 500

        def __init__(self, app, parent):
            super().__init__(app, [("lv", tr("级别"), 60, "center"), ("kind", tr("类型"), 150, "w"),
                                   ("detail", tr("说明"), 430, "w"), ("loc", tr("位置"), 400, "w")], parent)
            self.path_picker()
            self.btn(tr("开始扫描"), self.scan)
            self.btn(tr("查看助记词表"), self.show_wordlist)
            self.btn(tr("打开所在位置"), self.reveal)
            row2 = ttk.Frame(self)
            row2.pack(fill="x", padx=8, after=self.top)
            self.code = tk.BooleanVar(value=False)
            ttk.Checkbutton(row2, text=tr("同时扫描代码/配置文件（.py .js .sh .yml 等，仅报强证据）"), variable=self.code).pack(side="left")
            ttk.Label(row2, text=tr("   显示：")).pack(side="left")
            self.flt = ttk.Combobox(row2, values=[tr("全部"), tr("高危+中危"), tr("仅高危")], width=9, state="readonly")
            self.flt.current(0)
            self.flt.pack(side="left")
            self.flt.bind("<<ComboboxSelected>>", lambda e: self.render())
            self.wl = ttk.Label(row2, text="")
            self.wl.pack(side="left", padx=12)
            self.results, self.scanned = [], 0
            self.refresh_wl()
            self.info.config(text=tr("在文本/笔记/Office 文件里查找明文保存的助记词和私钥。结果只显示位置与类型，不回显任何内容，也不会上传。"))

        def refresh_wl(self):
            ok = fc.get_wordlist() is not None
            self.wl.config(text=tr("词表：已就绪（助记词按校验和验证）") if ok else tr("词表：未加载（将跳过助记词检测，点“查看助记词表”可下载）"),
                           foreground="#2e7d32" if ok else "#e65100")

        def get_wl(self, then=None):
            def done(r):
                (messagebox.showinfo if r[0] else messagebox.showwarning)(tr("BIP39 词表"), r[1])
                self.refresh_wl()
                if then:
                    then()
            self.app.run_bg(fc.download_wordlist, done, tr("下载并校验 BIP39 词表…"))

        # ---- 助记词表查看器
        def show_wordlist(self):
            info = fc.wordlist_info()
            w = tk.Toplevel(self)
            w.title(tr("BIP39 英文助记词表"))
            w.geometry("680x680")
            if not info["loaded"]:
                ttk.Label(w, justify="left", wraplength=640,
                          text=tr("词表还没有加载。\n\n程序会在下面这些位置查找 bip39_english.txt：\n") + "\n".join(info["searched"]) +
                               tr("\n\n官方来源：{0}\n点下面的按钮可下载并校验（约 13KB）。", info['url'])).pack(anchor="w", padx=12, pady=12)
                ttk.Button(w, text=tr("现在下载并校验"), command=lambda: (w.destroy(), self.get_wl())).pack(pady=8)
                return
            head = (tr("来源：{0}\n文件：{1}\n单词数：{2}（BIP39 英文词表固定为 2048 个，每个词对应 11 位）\nSHA-256：{3}\n校验：✓ 2048 个互不相同、按字母排序、前 4 个字母可唯一区分；✓ 通过 BIP39 官方测试向量\n官方来源：{4}", info['source'], info['path'], info['count'], info['sha256'], info['url']))
            ttk.Label(w, text=head, justify="left", wraplength=640).pack(anchor="w", padx=12, pady=8)
            bar = ttk.Frame(w)
            bar.pack(fill="x", padx=12)
            ttk.Label(bar, text=tr("搜索（单词片段或序号）：")).pack(side="left")
            q = tk.StringVar()
            ent = ttk.Entry(bar, textvariable=q, width=22)
            ent.pack(side="left", padx=4)
            cnt = ttk.Label(bar, text="")
            cnt.pack(side="left", padx=8)
            body = ttk.Frame(w)
            body.pack(fill="both", expand=True, padx=12, pady=6)
            tv = ttk.Treeview(body, columns=("n", "w"), show="headings")
            tv.heading("n", text=tr("序号"))
            tv.heading("w", text=tr("单词"))
            tv.column("n", width=90, anchor="e")
            tv.column("w", width=320)
            vs = ttk.Scrollbar(body, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=vs.set)
            tv.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")

            def fill(*_):
                key, k = q.get().strip().lower(), 0
                tv.delete(*tv.get_children())
                for n, wd in enumerate(info["words"], 1):
                    if not key or key in wd or key == str(n):
                        tv.insert("", "end", values=(n, wd))
                        k += 1
                cnt.config(text=tr("显示 {0} / {1}", k, info['count']))

            ent.bind("<KeyRelease>", fill)
            fill()

            def copy_all():
                self.clipboard_clear()
                self.clipboard_append("\n".join(info["words"]))
                messagebox.showinfo(tr("已复制"), tr("2048 个单词已复制到剪贴板（每行一个）。"))

            bf = ttk.Frame(w)
            bf.pack(fill="x", padx=12, pady=(0, 10))
            ttk.Button(bf, text=tr("复制全部"), command=copy_all).pack(side="left", padx=3)
            ttk.Button(bf, text=tr("打开所在位置"), command=lambda: open_location(info["path"])).pack(side="left", padx=3)
            ttk.Button(bf, text=tr("重新下载/更新"), command=lambda: (w.destroy(), self.get_wl())).pack(side="left", padx=3)

        # ---- 扫描
        def scan(self):
            root = Path(self.root_var.get())
            if not root.is_dir():
                return messagebox.showerror(tr("错误"), tr("目录不存在"))
            if fc.get_wordlist() is None:
                ans = messagebox.askyesnocancel(
                    tr("需要 BIP39 词表"),
                    tr("没有找到 BIP39 助记词表，无法检测助记词（私钥仍可检测）。\n\n现在下载吗？约 13KB，来自 BIP39 官方仓库 bitcoin/bips，下载后会校验。\n\n是：下载后开始扫描\n否：跳过助记词检测，只检测私钥\n取消：不扫描"))
                if ans is None:
                    return
                if ans:
                    return self.get_wl(then=lambda: self.do_scan(root))
            self.do_scan(root)

        def do_scan(self, root):
            inc = self.code.get()

            def done(r):
                self.results, self.scanned = r
                self.render()

            self.app.run_bg(lambda: fc.scan_secrets(root, "auto", include_code=inc), done,
                            tr("扫描助记词/私钥…（文件多时需要几分钟）"))

        def render(self):
            self.clear()
            idx = self.flt.current()
            keep = {0: (tr("高危"), tr("中危"), tr("提示")), 1: (tr("高危"), tr("中危")), 2: (tr("高危"),)}.get(idx, (tr("高危"), tr("中危"), tr("提示")))
            shown = [x for x in self.results if x["level"] in keep]
            for x in shown[:self.MAX_ROWS]:
                loc = x["path"] + (tr("  (第 {0} 行)", x['line']) if x["line"] else "")
                self.add((x["level"], x["kind"], x["detail"], loc), x, (LV_TAG[x["level"]],))
            cnt = {k: sum(1 for x in self.results if x["level"] == k) for k in (tr("高危"), tr("中危"), tr("提示"))}
            msg = tr("已扫描 {0} 个文件：高危 {1} · 中危 {2} · 提示 {3}。", self.scanned, cnt[tr("高危")], cnt[tr("中危")], cnt[tr("提示")])
            if len(shown) > self.MAX_ROWS:
                msg += tr("（仅显示前 {0} 项，请用“显示”筛选）", self.MAX_ROWS)
            if fc.get_wordlist() is None:
                msg += tr("  ⚠ 未加载 BIP39 词表，本次没有检测助记词。")
            if cnt[tr("高危")]:
                msg += tr("  建议：把资产转到新钱包（新助记词），抄写在纸上离线保存，并删除/加密这些明文文件。")
            elif not self.results:
                msg += tr("  未发现明文助记词/私钥。（图片/截图、便签数据库、PDF 不在扫描范围内）")
            self.info.config(text=msg)

        def reveal(self):
            sel = self.need_selection()
            if sel:
                open_location(sel[0][1]["path"])

    class MinerTab(ListTab):
        def __init__(self, app, parent):
            super().__init__(app, [("lv", tr("级别"), 60, "center"), ("pid", "PID", 70, "e"), ("name", tr("进程"), 180, "w"),
                                   ("cpu", "CPU", 60, "e"), ("detail", tr("说明"), 560, "w")], parent)
            self.btn(tr("开始检测（约 3 秒）"), self.scan)
            self.btn(tr("结束选中进程"), self.kill)
            self.info.config(text=tr("检查进程名/命令行里的挖矿特征、连接矿池端口、临时目录里的高 CPU 程序。启动项/计划任务里的挖矿命令会在“风险扫描”里一并检查。"))
            if not psutil:
                self.info.config(text=tr("需要安装 psutil 才能使用：pip install psutil"))

        def scan(self):
            def done(r):
                self.clear()
                for f in r["findings"]:
                    self.add((f["level"], f["pid"] or "-", f["name"], f"{f['cpu']:.0f}%", f["msg"]), f, (LV_TAG[f["level"]],))
                for pid, name, cpu in r["top"]:
                    self.add((tr("参考"), pid, name, f"{cpu:.0f}%", tr("CPU 占用靠前的进程（仅供参考）")), None, ("keep",))
                n = len([f for f in r["findings"] if f["level"] != tr("提示")])
                self.info.config(text=tr("发现 {0} 个可疑项，请核对。", n) if n else tr("未发现挖矿迹象。（下方为 CPU 占用靠前的进程）"))

            self.app.run_bg(lambda: fc.detect_miners(3.0), done, tr("检测挖矿进程…"))

        def kill(self):
            sel = [(i, o) for i, o in self.need_selection() or [] if o and o.get("pid")]
            if not sel or not psutil or not messagebox.askyesno(tr("确认"), tr("结束 {0} 个进程？", len(sel))):
                return
            fails = []
            for _, o in sel:
                try:
                    p = psutil.Process(o["pid"])
                    p.terminate()
                    p.wait(3)
                except Exception as e:
                    fails.append(tr("{0}：{1}", o['name'], e))
            messagebox.showwarning(tr("部分未结束"), "\n".join(fails)) if fails else messagebox.showinfo(
                tr("完成"), tr("已结束。如确认是木马，请再用“风险扫描”找出并停用它的启动项，并用杀毒软件查杀。"))
            self.scan()

    class ClipboardTab(ListTab):
        def __init__(self, app, parent):
            super().__init__(app, [("t", tr("时间"), 80, "center"), ("lv", tr("级别"), 60, "center"), ("msg", tr("记录"), 840, "w")], parent)
            self.guard, self.last_text = fc.ClipboardGuard(), None
            self.on = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.top, text=tr("启用剪贴板监控（只在内存里记录，不写入磁盘）"), variable=self.on,
                            command=self.toggle).pack(side="left", padx=4)
            vf = ttk.Frame(self)
            vf.pack(fill="x", padx=8, pady=2, after=self.top)
            ttk.Label(vf, text=tr("校验收款地址：")).pack(side="left")
            self.addr = tk.StringVar()
            ttk.Entry(vf, textvariable=self.addr, width=52).pack(side="left", padx=4)
            ttk.Button(vf, text=tr("校验"), command=self.verify).pack(side="left")
            self.res = ttk.Label(vf, text=tr("（把你在钱包/交易所里看到的收款地址粘贴进来，核对是否被替换）"))
            self.res.pack(side="left", padx=8)
            self.info.config(text=tr("用法：开启监控 → 照常复制地址 → 粘贴到转账页面后，把页面上显示的地址再贴到上面校验。首尾相同、中间不同的地址是典型的剪贴板劫持/地址投毒。"))
            self.after(800, self.poll)

        def log(self, lv, msg):
            self.add((time.strftime("%H:%M:%S"), lv, msg), None, (LV_TAG.get(lv, "note"),))
            self.tree.yview_moveto(1)

        def toggle(self):
            if self.on.get():
                self.guard = fc.ClipboardGuard()
                try:
                    self.last_text = self.clipboard_get()
                    self.guard.feed(self.last_text)
                except tk.TclError:
                    self.last_text = None
                self.log(tr("提示"), tr("剪贴板监控已开启"))
            else:
                self.log(tr("提示"), tr("剪贴板监控已关闭"))

        def poll(self):
            if self.on.get():
                try:
                    txt = self.clipboard_get()
                except tk.TclError:
                    txt = ""
                if txt and txt != self.last_text:
                    self.last_text = txt
                    kind = fc.classify_address(txt)
                    alert = self.guard.feed(txt)
                    if kind and not alert:
                        self.log(tr("提示"), tr("记录到 {0} 地址：{1}", kind, fc.mask_addr(txt.strip())))
                    if alert:
                        self.log(alert["level"], alert["msg"])
                        self.app.bell()
                        self.after(50, lambda m=alert["msg"]: messagebox.showwarning(tr("剪贴板地址异常"), m))
            self.after(800, self.poll)

        def verify(self):
            lv, msg = self.guard.verify(self.addr.get())
            self.res.config(text=f"[{lv}] {msg}", foreground={tr("高危"): "#c62828", tr("正常"): "#2e7d32"}.get(lv, "#e65100"))
            self.log(lv, tr("校验：") + msg)

    class WalletHub(ttk.Frame):
        def __init__(self, app):
            super().__init__(app.nb)
            ttk.Label(self, text=tr("钱包安全：全部在本地运行，不上传任何内容，不接触你的私钥/助记词。"),
                      foreground="#555").pack(anchor="w", padx=10, pady=(8, 0))
            nb = ttk.Notebook(self)
            nb.pack(fill="both", expand=True, padx=4, pady=4)
            for title, cls in ((tr("钱包文件"), WalletFilesTab), (tr("区块链数据"), ChainDirsTab), (tr("密钥泄露扫描"), SecretScanTab),
                               (tr("挖矿检测"), MinerTab), (tr("剪贴板守护"), ClipboardTab)):
                nb.add(cls(app, nb), text=title)

    # ------------------------------------------------------------ 自动清理
    class ScheduleTab(ttk.Frame):
        def __init__(self, app):
            super().__init__(app.nb)
            self.app = app
            cfg = load_cfg()
            pad = dict(padx=10, pady=4)

            # 计划
            f1 = ttk.LabelFrame(self, text=tr("① 执行计划"))
            f1.pack(fill="x", padx=10, pady=(8, 4))
            self.freq = tk.StringVar(value=cfg["freq"])
            for i, (k, v) in enumerate(FREQ_CN.items()):
                ttk.Radiobutton(f1, text=v, value=k, variable=self.freq).grid(row=0, column=i, sticky="w", **pad)
            h, m = cfg["time"].split(":")
            self.hh, self.mm = tk.StringVar(value=h), tk.StringVar(value=m)
            ttk.Label(f1, text=tr("时间：")).grid(row=0, column=3, **pad)
            ttk.Spinbox(f1, from_=0, to=23, width=3, format="%02.0f", textvariable=self.hh).grid(row=0, column=4)
            ttk.Label(f1, text=":").grid(row=0, column=5)
            ttk.Spinbox(f1, from_=0, to=59, width=3, format="%02.0f", textvariable=self.mm).grid(row=0, column=6)
            ttk.Label(f1, text=tr("每周星期：")).grid(row=1, column=0, **pad)
            self.wd = ttk.Combobox(f1, values=WEEKDAYS_CN, width=6, state="readonly")
            self.wd.current(int(cfg["weekday"]))
            self.wd.grid(row=1, column=1, sticky="w")
            ttk.Label(f1, text=tr("每月几号：")).grid(row=1, column=2, **pad)
            self.md = tk.StringVar(value=str(cfg["monthday"]))
            ttk.Spinbox(f1, from_=1, to=28, width=4, textvariable=self.md).grid(row=1, column=3, sticky="w")

            # 内容
            f2 = ttk.LabelFrame(self, text=tr("② 清理内容"))
            f2.pack(fill="x", padx=10, pady=4)
            self.junk = tk.BooleanVar(value=cfg["junk"])
            self.age = tk.StringVar(value=str(cfg["junk_min_age_days"]))
            self.trash = tk.BooleanVar(value=cfg["empty_trash"])
            self.purge = tk.StringVar(value=str(cfg["purge_own_trash_days"]))
            ttk.Checkbutton(f2, text=tr("清理系统垃圾/缓存，仅清理未修改超过"), variable=self.junk).grid(row=0, column=0, sticky="w", **pad)
            ttk.Spinbox(f2, from_=0, to=90, width=4, textvariable=self.age).grid(row=0, column=1)
            ttk.Label(f2, text=tr("天的文件（0 = 1 小时前）")).grid(row=0, column=2, sticky="w")
            ttk.Checkbutton(f2, text=tr("清空系统回收站 / 废纸篓（不可恢复）"), variable=self.trash).grid(row=1, column=0, columnspan=3, sticky="w", **pad)
            ttk.Label(f2, text=tr("彻底删除本工具回收站中超过")).grid(row=2, column=0, sticky="e", **pad)
            ttk.Spinbox(f2, from_=0, to=365, width=4, textvariable=self.purge).grid(row=2, column=1)
            ttk.Label(f2, text=tr("天的文件（0 = 不处理）")).grid(row=2, column=2, sticky="w")

            # 文件夹规则
            f3 = ttk.LabelFrame(self, text=tr("③ 自定义文件夹：超过 N 天未修改的文件移入回收站（可找回）"))
            f3.pack(fill="x", padx=10, pady=4)
            self.rules = ttk.Treeview(f3, columns=("path", "days"), show="headings", height=3)
            self.rules.heading("path", text=tr("文件夹"))
            self.rules.heading("days", text=tr("天数"))
            self.rules.column("path", width=560)
            self.rules.column("days", width=60, anchor="e")
            self.rules.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            bf = ttk.Frame(f3)
            bf.pack(side="left", padx=6)
            ttk.Button(bf, text=tr("添加文件夹…"), command=self.add_rule).pack(fill="x", pady=2)
            ttk.Button(bf, text=tr("删除选中"), command=lambda: [self.rules.delete(i) for i in self.rules.selection()]).pack(fill="x", pady=2)
            for r in cfg["folders"]:
                self.rules.insert("", "end", values=(r["path"], r["days"]))

            # 操作
            f4 = ttk.Frame(self)
            f4.pack(fill="x", padx=10, pady=6)
            ttk.Button(f4, text=tr("保存并启用定时任务"), command=self.enable).pack(side="left", padx=3)
            ttk.Button(f4, text=tr("停用定时任务"), command=self.disable).pack(side="left", padx=3)
            ttk.Button(f4, text=tr("试运行（只统计）"), command=lambda: self.run_now(True)).pack(side="left", padx=3)
            ttk.Button(f4, text=tr("立即清理一次"), command=lambda: self.run_now(False)).pack(side="left", padx=3)
            self.status = ttk.Label(f4, text="")
            self.status.pack(side="left", padx=12)

            f5 = ttk.LabelFrame(self, text=tr("运行日志"))
            f5.pack(fill="both", expand=True, padx=10, pady=(2, 8))
            self.logbox = scrolledtext.ScrolledText(f5, height=8, state="disabled")
            self.logbox.pack(fill="both", expand=True, padx=4, pady=4)
            ttk.Button(f5, text=tr("刷新日志"), command=self.refresh).pack(anchor="e", padx=4, pady=(0, 4))
            self.refresh()

        def add_rule(self):
            d = filedialog.askdirectory(initialdir=str(HOME), title=tr("选择要定期清理的文件夹"))
            if not d:
                return
            bad = danger_reason(d)
            if bad:
                return messagebox.showerror(tr("不允许"), bad)
            days = simpledialog.askinteger(tr("天数"), tr("清理该文件夹内未修改超过多少天的文件？"), initialvalue=30,
                                           minvalue=1, maxvalue=3650, parent=self)
            if days:
                if not messagebox.askyesno(tr("确认"), tr("{0}\n中超过 {1} 天未修改的文件将被定期移入回收站。\n确认添加？", d, days)):
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
            (messagebox.showinfo if ok else messagebox.showerror)(tr("定时任务"), msg)
            self.refresh()

        def disable(self):
            ok, msg = remove_schedule()
            cfg = load_cfg()
            cfg["enabled"] = False
            save_cfg(cfg)
            messagebox.showinfo(tr("定时任务"), msg)
            self.refresh()

        def run_now(self, dry):
            save_cfg(self.collect())
            self.app.run_bg(lambda: auto_clean(dry), lambda r: (show_text(self, tr("试运行结果") if dry else tr("清理结果"), "\n".join(r[1])),
                                                                 self.refresh()), tr("清理中…"))

        def refresh(self):
            cfg = load_cfg()
            on = schedule_installed()
            txt = tr("定时任务：已启用") if on else tr("定时任务：未启用")
            if cfg["last_run"]:
                txt += tr("  |  上次运行 {0}（{1}）", cfg['last_run'], cfg['last_result'])
            self.status.config(text=txt, foreground="#2e7d32" if on else "#999")
            try:
                lines = LOG.read_text(encoding="utf-8").splitlines()[-200:]
            except OSError:
                lines = [tr("（暂无日志）")]
            self.logbox.config(state="normal")
            self.logbox.delete("1.0", "end")
            self.logbox.insert("1.0", "\n".join(lines))
            self.logbox.see("end")
            self.logbox.config(state="disabled")

    # ------------------------------------------------------------ 主窗口
    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"Faster v{__version__}" + (tr("  [管理员]") if core.is_admin() else ""))
            self.geometry("1040x700")
            self.minsize(880, 560)
            try:
                ttk.Style(self).theme_use("vista" if IS_WIN else "aqua" if IS_MAC else "clam")
            except tk.TclError:
                pass
            self.q, self.busy_n = queue.Queue(), 0
            bar = ttk.Frame(self)
            bar.pack(side="bottom", fill="x")
            self.status = ttk.Label(bar, text=tr("就绪"))
            self.status.pack(side="left", padx=8, pady=3)
            self.pb = ttk.Progressbar(bar, mode="indeterminate", length=160)
            self.pb.pack(side="right", padx=8)
            self.nb = ttk.Notebook(self)
            self.nb.pack(fill="both", expand=True)
            for title, cls in ((tr("概览"), HomeTab), (tr("垃圾清理"), JunkTab), (tr("大文件"), LargeTab), (tr("重复文件"), DupTab),
                               (tr("启动项"), StartupTab), (tr("后台进程"), ProcTab), (tr("卸载程序"), UninstallTab),
                               (tr("风险扫描"), SecurityTab), (tr("钱包安全"), WalletHub), (tr("自动清理"), ScheduleTab)):
                self.nb.add(cls(self), text=title)
            self.after(100, self.poll)

        def run_bg(self, fn, done=None, msg=tr("处理中…")):
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
                        self.status.config(text=tr("就绪"))
                    if err:
                        messagebox.showerror(tr("出错"), str(err))
                    elif done:
                        done(res)
            except queue.Empty:
                pass
            self.after(100, self.poll)


def launch_gui():
    if tk is None:
        print(tr("未找到 tkinter。Windows/macOS 请使用 python.org 的官方安装包；Linux 请执行：sudo apt install python3-tk"))
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
