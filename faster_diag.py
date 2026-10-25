# -*- coding: utf-8 -*-
"""
Faster · 诊断中心（v0.3.1）

  1. 全面诊断：性能 / 存储 / 安全 / 钱包 四大类；每个问题都带“可以采取的动作”（直接执行，或跳转到对应页面）
     → 健康分 + 建议 + 动作。动作只是数据（dict），由界面层执行；本模块不依赖界面
  2. 启动影响评分：按“正在运行的进程”估算每个启动项的内存和平均 CPU 占用
  3. 前后对比：优化前后的状态快照（磁盘剩余、内存占用、启动项、进程数…）

原则：只读测量，不修改系统；估算值如实标注为“估算”，不做“加速”类的夸大宣传。
"""
import os
import re
import heapq
import time
import json
import shutil
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

import faster as core
import faster_crypto as fc
import faster_sig as sig
import faster_baseline as bl
import faster_patch as patch
import faster_harden as harden
import faster_dev as dev
import faster_disk as disk
from faster_i18n import tr

HOME, APP_DIR, human = core.HOME, core.APP_DIR, core.human
IS_WIN = core.IS_WIN
SNAP_FILE = APP_DIR / "snapshots.json"
GB = 1024 ** 3

LV_CRIT, LV_WARN, LV_INFO, LV_OK = tr("严重"), tr("注意"), tr("提示"), tr("良好")
_LV_ORDER = {LV_CRIT: 0, LV_WARN: 1, LV_INFO: 2, LV_OK: 3}
CATEGORIES = (("perf", tr("性能")), ("storage", tr("存储")), ("security", tr("安全")), ("harden", tr("加固与更新")), ("wallet", tr("钱包")))


# ============================================================ 状态快照 / 前后对比
def take_snapshot(label="", sample_cpu=False):
    """读取当前状态（几毫秒，只读）。sample_cpu=True 会阻塞 1 秒测 CPU"""
    s = {"ts": time.time(), "label": label}
    try:
        du = shutil.disk_usage(HOME)
        s["disk_total"], s["disk_free"] = du.total, du.free
    except OSError:
        pass
    if psutil:
        try:
            vm = psutil.virtual_memory()
            s.update(mem_total=vm.total, mem_used=vm.total - vm.available, mem_percent=vm.percent,
                     swap_percent=psutil.swap_memory().percent, procs=len(psutil.pids()),
                     uptime=time.time() - psutil.boot_time(),
                     cpu_percent=psutil.cpu_percent(interval=1.0 if sample_cpu else None))
        except Exception:
            pass
    try:
        s["startup"] = len(core.get_startup_items())
    except Exception:
        pass
    return s


def load_history():
    try:
        return json.loads(SNAP_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_snapshot(s):
    h = load_history()
    h.append(s)
    try:
        SNAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAP_FILE.write_text(json.dumps(h[-100:], ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return s


def clear_history():
    try:
        SNAP_FILE.unlink()
    except OSError:
        pass


def record(label, sample_cpu=False):
    return save_snapshot(take_snapshot(label, sample_cpu))


METRICS = (  # 键, 标题, 类型, 是否“越小越好”
    ("disk_free", tr("磁盘剩余"), "bytes", False),
    ("mem_used", tr("内存占用"), "bytes", True),
    ("mem_percent", tr("内存占用率"), "pct", True),
    ("swap_percent", tr("交换空间占用率"), "pct", True),
    ("startup", tr("开机启动项"), "int", True),
    ("procs", tr("进程数"), "int", True),
)


def _fmt(kind, v, delta=False):
    if kind == "bytes":
        return (("+" if v > 0 else "-" if v < 0 else "") + human(abs(v))) if delta else human(v)
    if kind == "pct":
        return f"{v:+.0f}%" if delta else f"{v:.0f}%"
    return f"{int(v):+d}" if delta else str(int(v))


def compare(a, b):
    """比较两个快照（a 为之前，b 为之后）→ [dict(key,title,before,after,delta,better,raw)]；better=True 表示变好"""
    rows = []
    for key, title, kind, lower_better in METRICS:
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            continue
        d = y - x
        better = None if d == 0 else ((d < 0) == lower_better)
        rows.append(dict(key=key, title=title, before=_fmt(kind, x), after=_fmt(kind, y), delta=_fmt(kind, d, True),
                         better=better, raw=d))
    return rows


def effect_summary(before, after):
    """一句话概括优化效果，只列有意义的变化（磁盘 ≥1MB、内存 ≥50MB、启动项、进程数 ≥3）"""
    thr = {"disk_free": 1 << 20, "mem_used": 50 << 20, "startup": 1, "procs": 3}
    parts = []
    for r in compare(before, after):
        if r["key"] in thr and abs(r["raw"]) >= thr[r["key"]]:
            parts.append(f"{r['title']} {r['delta']}")
    return " · ".join(parts)


# ============================================================ 诊断中心
# 动作 act(op, label, page, **args)：
#   op     —— 要做什么（clean_junk / empty_trash / kill_pid / open_settings / disable_startup / goto …，由界面层实现）
#   page   —— 这个动作属于哪个页面（该页面顶部会同样列出它）；None 表示只出现在诊断结果里（如“跳转”类）
#   danger —— 需要二次确认的危险动作
def act(op, label, page=None, **args):
    return dict(op=op, label=label, page=page, args=args, done=False)


def goto(label, tab, sub=None, auto=None, set=None):
    """跳转到某页（可选：切到子页、预先填值 set、并自动开始 auto 指定的操作）"""
    return act("goto", label, None, tab=tab, sub=sub, auto=auto, set=set or {})


def _f(key, cat, level, title, detail, advice, actions=None):
    return dict(key=key, cat=cat, level=level, title=title, detail=detail,
                advice=advice if level != LV_OK else tr("无需处理"), actions=(actions or []) if level != LV_OK else [])


def score_of(findings):
    crit = sum(1 for f in findings if f["level"] == LV_CRIT)
    warn = sum(1 for f in findings if f["level"] == LV_WARN)
    return max(0, 100 - 25 * crit - 10 * warn)


def category_scores(findings):
    return {c: score_of([f for f in findings if f["cat"] == c]) for c, _ in CATEGORIES if any(f["cat"] == c for f in findings)}


def sample_top(seconds=1.5, n=3):
    """采样 seconds 秒，返回内存/CPU 占用最高的进程 [(名称, 数值, pid)]"""
    if not psutil:
        return {}
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            p.cpu_percent(None)
            procs.append(p)
        except Exception:
            pass
    time.sleep(seconds)
    mem, cpu = [], []
    for p in procs:
        try:
            nm = p.info["name"] or "?"
            mem.append((nm, p.info["memory_info"].rss, p.pid))
            cpu.append((nm, p.cpu_percent(None), p.pid))
        except Exception:
            pass
    mem.sort(key=lambda x: -x[1])
    cpu.sort(key=lambda x: -x[1])
    return dict(mem=mem[:n], cpu=cpu[:n], cpu_total=psutil.cpu_percent(None))


_POWER = {"a1841308-3541-4fab-bc81-f71556f20b4a": "saver", "381b4222-f694-41f0-9685-ff5bb260df2e": "balanced",
          "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "high"}


def win_power_scheme():
    """Windows 当前电源计划：'saver' / 'balanced' / 'high' / None（用 GUID 判断，不受界面语言影响）"""
    if not IS_WIN:
        return None
    _, out, _ = core.run(["powercfg", "/getactivescheme"], timeout=10)
    m = re.search(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", out or "")
    return _POWER.get(m.group(0).lower()) if m else None


def _killable(name, pid):
    """能给“结束进程”按钮的进程：已知 pid、不是系统关键进程、不是 Faster 自己"""
    prot = set().union(*core.PROTECTED.values())
    return bool(pid) and pid not in (os.getpid(), os.getppid()) and (name or "").lower() not in prot


def diagnose(snap, junk_bytes=None, top=None, power=None):
    """性能 + 磁盘/垃圾 诊断。返回 dict(score, cats, findings, snapshot)；
    finding: dict(key, cat, level, title, detail, advice, actions)"""
    top = top or {}
    F = []
    total, free = snap.get("disk_total"), snap.get("disk_free")
    if total:
        pct = free / total * 100
        lv = LV_CRIT if (pct < 10 or free < 5 * GB) else LV_WARN if pct < 20 else LV_OK
        F.append(_f("disk", "storage", lv, tr("磁盘空间"), tr("剩余 {0}（{1:.0f}%）", human(free), pct),
                    tr("清理垃圾、大文件和重复文件；卸载不用的大型程序。"),
                    [act("clean_junk", tr("清理垃圾"), page="junk"), goto(tr("查找大文件"), "large", auto="scan"),
                     goto(tr("查看空间占用"), "space", auto="scan")]))
    if "mem_percent" in snap:
        p = snap["mem_percent"]
        lv = LV_CRIT if p >= 90 else LV_WARN if p >= 80 else LV_OK
        names = ", ".join(t[0] for t in top.get("mem", [])[:3])
        detail = tr("已用 {0}（{1:.0f}%）", human(snap["mem_used"]), p) + (tr("；占用最多：{0}", names) if names and lv != LV_OK else "")
        acts = [goto(tr("查看占用内存的程序"), "proc", auto="load")]
        big = [t for t in top.get("mem", []) if len(t) > 2 and t[1] >= 800 * (1 << 20) and _killable(t[0], t[2])]
        if big:
            acts.append(act("kill_pid", tr("结束 {0}", big[0][0]), page="proc", pid=big[0][2], name=big[0][0], danger=True))
        F.append(_f("memory", "perf", lv, tr("内存"), detail, tr("关闭不用的程序和浏览器标签页；长期不够用就增加内存。"), acts))
        sp = snap.get("swap_percent", 0)
        F.append(_f("swap", "perf", LV_WARN if (sp >= 50 and p >= 80) else LV_OK, tr("交换空间"), tr("已用 {0:.0f}%", sp),
                    tr("内存吃紧又在大量使用交换空间时电脑会明显变卡：关闭占内存大的程序，或增加内存。"),
                    [goto(tr("查看占用内存的程序"), "proc", auto="load")]))
        cpu = top.get("cpu_total", snap.get("cpu_percent"))
        if cpu is not None:
            hot = [t for t in top.get("cpu", []) if t[1] >= 10]
            names = ", ".join(t[0] for t in hot[:3])
            lv = LV_WARN if cpu >= 85 else LV_OK
            acts = [goto(tr("查看占用 CPU 的程序"), "proc", auto="load")]
            if hot and len(hot[0]) > 2 and hot[0][1] >= 80 and _killable(hot[0][0], hot[0][2]):
                acts.append(act("kill_pid", tr("结束 {0}", hot[0][0]), page="proc", pid=hot[0][2], name=hot[0][0], danger=True))
            F.append(_f("cpu", "perf", lv, tr("CPU"), tr("占用 {0:.0f}%", cpu) + (tr("；占用最高：{0}", names) if names and lv != LV_OK else ""),
                        tr("查看“后台进程”页，结束长期高占用且不需要的程序。"), acts))
    else:
        F.append(_f("psutil", "perf", LV_WARN, tr("内存 / CPU"), tr("无法读取"), tr("安装 psutil（pip install psutil）后才能诊断内存、CPU 和进程。")))
    n = snap.get("startup")
    if n is not None:
        lv = LV_CRIT if n > 25 else LV_WARN if n > 12 else LV_OK
        F.append(_f("startup", "perf", lv, tr("开机启动项"), tr("共 {0} 个", n), tr("到“启动影响”页按影响排序，停用不需要的启动项。"),
                    [goto(tr("评估启动影响"), "diag", sub="impact", auto="scan"),
                     act("disable_high", tr("停用影响高的启动项"), page="impact")]))
    if "uptime" in snap:
        d = snap["uptime"] / 86400
        F.append(_f("uptime", "perf", LV_WARN if d > 14 else LV_OK, tr("连续运行时间"), tr("{0:.1f} 天", d),
                    tr("重启一次可以释放内存，并让系统更新生效。")))
    if junk_bytes is not None:
        lv = LV_CRIT if junk_bytes >= 10 * GB else LV_WARN if junk_bytes >= 2 * GB else LV_OK
        F.append(_f("junk", "storage", lv, tr("可清理的垃圾"), tr("约 {0}", human(junk_bytes)), tr("到“垃圾清理”页清理。"),
                    [act("clean_junk", tr("清理垃圾（约 {0}）", human(junk_bytes)), page="junk")]))
    if power is None:
        power = win_power_scheme()
    if power:
        F.append(_f("power", "perf", LV_WARN if power == "saver" else LV_OK, tr("电源计划"),
                    tr("节能") if power == "saver" else tr("平衡 / 高性能"),
                    tr("需要速度时，在“设置 → 系统 → 电源”里改成“平衡”或“最佳性能”。"),
                    [act("open_settings", tr("打开电源设置"), what="power")]))
    F.sort(key=lambda f: _LV_ORDER[f["level"]])
    return dict(score=score_of(F), cats=category_scores(F), findings=F, snapshot=snap)


# ---------------------------------------------------------------- 存储
def system_trash_size():
    """系统回收站（Windows 回收站 / macOS 废纸篓 / Linux 回收站）当前占用的字节数"""
    try:
        if IS_WIN:
            import ctypes

            class SHQUERYRBINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]
            info = SHQUERYRBINFO()
            info.cbSize = ctypes.sizeof(info)
            return info.i64Size if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0 else 0
        p = HOME / (".Trash" if core.IS_MAC else ".local/share/Trash/files")
        return core.dir_size(p) if p.exists() else 0
    except Exception:
        return 0


def storage_findings(task=None, deep=False):
    F, MB = [], 1 << 20
    sysz = system_trash_size()
    lv = LV_CRIT if sysz >= 10 * GB else LV_WARN if sysz >= 500 * MB else LV_OK
    F.append(_f("trash", "storage", lv, tr("回收站"),
                tr("回收站里还有 {0}，清空后才会真正释放空间", human(sysz)) if lv != LV_OK else tr("占用 {0}", human(sysz)),
                tr("确认里面没有需要的文件后清空。"),
                [act("empty_trash", tr("清空回收站"), page="restore"), act("open_system_trash", tr("打开回收站查看"), page="restore")]))
    toolsz = core.dir_size(core.TRASH_DIR) if core.TRASH_DIR.exists() else 0
    if toolsz >= 500 * MB:
        F.append(_f("tooltrash", "storage", LV_WARN, tr("工具回收站"), tr("Faster 的回收站占用 {0}", human(toolsz)),
                    tr("到“还原中心”确认没有需要还原的文件后，再永久清空。"),
                    [goto(tr("到还原中心查看"), "restore"), act("empty_tool_trash", tr("永久清空"), page="restore")]))
    # 开发者缓存（只在这台电脑上装了开发工具时才会出现）
    if task is None or task.tick(tr("正在检查：开发者缓存")):
        rows = dev.scan_caches(task, max_seconds=25)
        if rows:
            total = sum(r["size"] for r in rows)
            lv = LV_CRIT if total >= 20 * GB else LV_WARN if total >= 2 * GB else LV_OK
            F.append(_f("devcache", "storage", lv, tr("开发者缓存"),
                        tr("{0} 个工具的缓存共约 {1}；最大的是 {2}（{3}）", len(rows), human(total), rows[0]["name"], human(rows[0]["size"])),
                        tr("这些缓存都能重新生成，清理后第一次构建会慢一些。"),
                        [act("clean_dev", tr("清理开发缓存（约 {0}）", human(total)), page="dev"),
                         goto(tr("查看明细"), "dev", auto="scan")]))
    # 磁盘健康（SMART）
    for x in disk.check():
        F.append(_f(x["key"], "storage", _LV_RAW[x["level"]], x["title"], x["detail"], x["advice"], _fix_actions(x["fix"], None)))
    if deep:
        if task is None or task.tick(tr("正在查找长期没动的项目依赖…")):
            projs = dev.stale_projects(HOME, 90, task, core.exclusions_for("large"))
            if projs:
                total = sum(r["size"] for r in projs)
                F.append(_f("stale_projects", "storage", LV_WARN if total >= 2 * GB else LV_INFO, tr("旧项目的依赖目录"),
                            tr("{0} 个超过 90 天没动过的项目里，依赖目录共约 {1}", len(projs), human(total)),
                            tr("这些目录能用一条命令重新生成；清理后会进回收站，可以在“还原中心”还原。"),
                            [goto(tr("查看并清理"), "dev", auto="scan_projects")]))
        if task is not None and not task.tick(tr("正在查找大文件…")):
            return F
        big = list(core.walk_user_files(HOME, 500 * MB, task, core.exclusions_for("large")))
        if big:
            big.sort(key=lambda x: -x[1])
            F.append(_f("bigfiles", "storage", LV_WARN, tr("大文件"),
                        tr("有 {0} 个超过 500MB 的文件，共 {1}；最大的是 {2}（{3}）", len(big), human(sum(b[1] for b in big)),
                           os.path.basename(big[0][0]), human(big[0][1])),
                        tr("确认哪些不再需要，删除或移到外置硬盘。"),
                        [goto(tr("查看大文件"), "large", auto="scan", set={"mb": "500", "root_var": str(HOME)})]))
        else:
            F.append(_f("bigfiles", "storage", LV_OK, tr("大文件"), tr("没有超过 500MB 的文件"), ""))
        if task is None or task.tick(tr("正在查找重复文件…（较慢）")):
            groups = core.find_duplicates(HOME, 5, task, core.exclusions_for("dup"))
            waste = sum(sz * (len(g) - 1) for sz, g in groups)
            if groups and waste >= 500 * MB:
                F.append(_f("dups", "storage", LV_WARN, tr("重复文件"), tr("发现 {0} 组重复文件，约浪费 {1}", len(groups), human(waste)),
                            tr("保留一份，删除多余的副本。"),
                            [goto(tr("查看重复文件"), "dup", auto="scan", set={"root_var": str(HOME)})]))
            else:
                F.append(_f("dups", "storage", LV_OK, tr("重复文件"), tr("没有发现明显浪费空间的重复文件"), ""))
    return F


# ---------------------------------------------------------------- 安全
_SETTINGS_FOR = {"defender_rt": "defender", "defender_old": "defender", "firewall": "firewall",
                 "gatekeeper": "mac_security", "sip": "mac_security", "mac_fw": "mac_security"}
SETTINGS_LABEL = {
    "defender": lambda: tr("打开 Windows 安全中心"), "firewall": lambda: tr("打开防火墙设置"),
    "mac_security": lambda: tr("打开“隐私与安全性”"), "windows_update": lambda: tr("打开 Windows 更新"),
    "remote_desktop": lambda: tr("打开远程桌面设置"), "bitlocker": lambda: tr("打开 BitLocker 设置"),
    "mac_update": lambda: tr("打开“软件更新”"), "mac_filevault": lambda: tr("打开 FileVault 设置"),
    "mac_users": lambda: tr("打开“用户与群组”"), "mac_sharing": lambda: tr("打开“共享”设置"),
    "mac_backup": lambda: tr("打开 Time Machine 设置"), "power": lambda: tr("打开电源设置"),
}
_SETTINGS_LABEL = SETTINGS_LABEL


def security_findings(task=None, deep=False):
    F = []
    lvmap = {tr("高危"): LV_CRIT, tr("中危"): LV_WARN, tr("提示"): LV_INFO}
    # 1) 系统防护
    items = core.security_posture_items()
    for it in items:
        what = _SETTINGS_FOR.get(it["key"])
        advice = tr("打开系统安全设置，检查并开启。") if what else tr("可以用 sudo ufw enable 启用防火墙。")
        F.append(_f("posture_" + it["key"], "security", lvmap.get(it["level"], LV_INFO), tr("系统防护"), it["msg"], advice,
                    [act("open_settings", _SETTINGS_LABEL[what](), page="security", what=what)] if what else []))
    if not items:
        F.append(_f("posture", "security", LV_OK, tr("系统防护"), tr("防火墙、杀毒、系统保护状态正常"), ""))
    # 2) 可疑启动项
    bad = [it for it in core.get_startup_items() if core.SUSP_CMD.search(it.get("cmd", ""))]
    for it in bad[:5]:
        F.append(_f("susp_" + it["name"], "security", LV_CRIT, tr("可疑启动项"), f"{it['name']}: {it['cmd'][:90]}",
                    tr("如果不是你安装的软件，请停用。"),
                    [act("disable_startup", tr("停用"), page="startup", items=[it]), goto(tr("到启动项页查看"), "startup")]))
    if len(bad) > 5:
        F.append(_f("susp_more", "security", LV_WARN, tr("可疑启动项"), tr("另有 {0} 个", len(bad) - 5), tr("到“启动项”页逐个确认。"),
                    [goto(tr("到启动项页查看"), "startup")]))
    if not bad:
        F.append(_f("susp", "security", LV_OK, tr("启动项安全"), tr("没有发现可疑的启动项"), ""))
    # 3) 挖矿
    if task is None or task.tick(tr("正在检查：挖矿木马")):
        mined = [m for m in fc.detect_miners(2.0)["findings"] if m["level"] in (tr("高危"), tr("中危"))]
        for m in mined[:3]:
            acts = [goto(tr("到挖矿检测页查看"), "wallet", sub="miner", auto="scan")]
            if m.get("pid") and _killable(m["name"], m["pid"]):
                acts.insert(0, act("kill_pid", tr("结束 {0}", m["name"]), page="wallet", pid=m["pid"], name=m["name"], danger=True))
            F.append(_f(f"miner_{m.get('pid')}", "security", lvmap.get(m["level"], LV_WARN), tr("疑似挖矿程序"),
                        f"{m['name']} (PID {m.get('pid')}): {m['msg']}", tr("如果不是你自己运行的，请结束它并查杀。"), acts))
        if not mined:
            F.append(_f("miner", "security", LV_OK, tr("挖矿检测"), tr("未发现挖矿迹象"), ""))
    # 4) hosts
    ents = core.hosts_entries()
    if ents:
        F.append(_f("hosts", "security", LV_WARN, tr("hosts 文件被改动"),
                    "; ".join(f"{h} → {ip}" for h, ip in ents[:3]) + (" …" if len(ents) > 3 else ""),
                    tr("确认这些条目是你自己添加的；不是的话请删除（需要管理员权限）。"),
                    [act("open_folder", tr("打开 hosts 所在文件夹"), page="security", path=str(core.hosts_file().parent))]))
    # 5) 深度：进程/端口、持久化、临时目录
    if deep and (task is None or task.tick(tr("正在做深度风险扫描…"))):
        core.findings.clear()
        for fn in (core.scan_processes, core.scan_persistence, core.scan_temp_executables):
            try:
                fn()
            except Exception:
                pass
        fs = list(core.findings)
        hi, mid, info = (sum(1 for lv, _ in fs if lv == w) for w in (tr("高危"), tr("中危"), tr("提示")))
        lv = LV_CRIT if hi else LV_WARN if mid else LV_OK
        F.append(_f("deepscan", "security", lv, tr("深度风险扫描"), tr("高危 {0} · 中危 {1} · 提示 {2}", hi, mid, info),
                    tr("到“风险扫描”页查看每一项的详情。"), [goto(tr("查看详情"), "security", auto="scan")]))
    return F


# ---------------------------------------------------------------- 程序签名 + 基线（安全）
def trust_findings(task=None, deep=False):
    F = []
    rows = sig.scan(task, deep)
    probs = [r for r in rows if r["risk"] in ("crit", "warn")]
    for r in probs[:8]:
        acts = []
        if r["kind"] == "startup":
            acts.append(act("disable_startup", tr("停用"), page="sig", items=[r["item"]]))
        elif r["pid"] and _killable(r["name"], r["pid"]):
            acts.append(act("kill_pid", tr("结束 {0}", r["name"]), page="sig", pid=r["pid"], name=r["name"], danger=True))
        h = sig.sha256_file(r["path"])
        if h:
            acts.append(act("copy_text", tr("复制 SHA-256"), text=h, note=tr("已复制。可以把它粘贴到 VirusTotal 等网站查询这个文件。")))
        acts.append(goto(tr("到程序签名页查看"), "diag", sub="sig", auto="scan"))
        F.append(_f("sig_" + r["path"], "security", LV_CRIT if r["risk"] == "crit" else LV_WARN,
                    tr("签名被破坏的程序") if r["status"] == "invalid" else tr("来源可疑的程序"),
                    f"{r['name']} ({sig.status_text(r['status'])}) · {r['path'][:80]}",
                    tr("如果不是你安装的软件，请停用或结束它；也可以复制文件的 SHA-256 去 VirusTotal 查询。"), acts))
    if len(probs) > 8:
        F.append(_f("sig_more", "security", LV_WARN, tr("来源可疑的程序"), tr("另有 {0} 个", len(probs) - 8), tr("到“程序签名”页逐个确认。"),
                    [goto(tr("到程序签名页查看"), "diag", sub="sig", auto="scan")]))
    if not probs:
        F.append(_f("sig", "security", LV_OK, tr("程序签名"), tr("检查了 {0} 个程序，没有发现签名问题", len(rows)), ""))
    F += baseline_findings(task)
    return F


def baseline_findings(task=None):
    base = bl.load()
    if not base:
        return [_f("baseline_none", "security", LV_INFO, tr("基线对比"), tr("还没有建立基线"),
                   tr("在你确认电脑目前干净的时候，把现在的状态记为基线；以后只提醒你“多了什么”。"),
                   [act("set_baseline", tr("把现在的状态设为基线"), page="baseline"), goto(tr("到基线页查看"), "diag", sub="baseline")])]
    d = bl.diff(base["items"], bl.collect())
    startup_objs = {f"{it['kind']}|{it['name']}|{it.get('cmd', '')}": it for it in core.get_startup_items()}
    level = {"admins": LV_CRIT, "ssh_keys": LV_CRIT, "startup": LV_WARN, "tasks": LV_WARN, "hosts": LV_WARN,
             "ports": LV_INFO, "programs": LV_INFO}
    F = []
    for key, name in bl.CATS:
        e = d.get(key)
        if not e or not e["added"]:
            continue
        added = e["added"]
        lv = LV_WARN if (key == "ports" and len(added) > 3) else level[key]
        acts = []
        if key == "startup":
            items = [startup_objs[x] for x in added if x in startup_objs]
            if items:
                acts.append(act("disable_startup", tr("停用这些启动项"), page="startup", items=items))
        acts += [act("accept_baseline", tr("这些是我自己装的（接受为新基线）"), page="baseline"),
                 goto(tr("查看变化"), "diag", sub="baseline", auto="compare")]
        F.append(_f("baseline_" + key, "security", lv, tr("{0}有新增", name),
                    tr("新增 {0} 项：{1}", len(added), "; ".join(bl.pretty(key, x) for x in added[:3]) + (" …" if len(added) > 3 else "")),
                    tr("和基线相比多出来的东西。如果不是你做的，请重点核查。"), acts))
    if not F:
        F.append(_f("baseline", "security", LV_OK, tr("基线对比"), tr("和基线相比，没有新增的启动项、计划任务、端口、管理员账户"), ""))
    return F


# ---------------------------------------------------------------- 加固与更新
_LV_RAW = {"crit": LV_CRIT, "warn": LV_WARN, "info": LV_INFO, "ok": LV_OK}


def _fix_actions(fix, page):
    if not fix:
        return []
    if "settings" in fix:
        what = fix["settings"]
        return [act("open_settings", SETTINGS_LABEL[what](), page=page, what=what)]
    return [act("copy_text", tr("复制修复命令"), page=page, text=fix["command"],
                note=tr("命令已复制。请在终端 / 管理员 PowerShell 里粘贴运行。"))]


def harden_findings(task=None, deep=False):
    F = []
    if task is not None:
        task.tick(tr("正在检查：系统更新"))
    raw = patch.check(deep)
    if task is None or task.tick(tr("正在检查：安全加固")):
        raw += harden.check_all(deep)
    for x in raw:
        acts = _fix_actions(x["fix"], "harden")
        if x["key"] == "eol":
            acts = [goto(tr("到卸载页处理"), "uninstall", auto="load")]
        elif x["level"] != "ok":
            acts.append(goto(tr("查看加固清单"), "diag", sub="harden", auto="scan"))
        F.append(_f("h_" + x["key"], "harden", _LV_RAW[x["level"]], x["title"], x["detail"], x["advice"], acts))
    return F


# ---------------------------------------------------------------- 钱包
def wallet_findings(task=None, deep=False):
    F = []
    wl = fc.get_wordlist()
    if wl is None:
        F.append(_f("wordlist", "wallet", LV_INFO, tr("BIP39 词表"), tr("未加载，无法检测助记词"),
                    tr("下载词表（约 13KB，来自 BIP39 官方仓库，下载后会校验）后才能检测助记词。"),
                    [act("download_wordlist", tr("下载词表"), page="wallet")]))
    hi_word = tr("提示")
    roots = fc.cloud_roots()
    if roots:
        nfiles = nsecret = 0
        first = None
        for r in roots:
            if task is not None and not task.tick(tr("正在检查：云同步目录 {0}", r.name)):
                break
            files = fc.find_wallet_files(r, limit=50, max_seconds=15, task=task)
            res, _ = fc.scan_secrets(r, wl, max_seconds=20, task=task)
            bad = [x for x in res if x["level"] != hi_word]
            nfiles, nsecret = nfiles + len(files), nsecret + len(bad)
            if (files or bad) and first is None:
                first = r
        if nsecret:
            F.append(_f("cloud_secrets", "wallet", LV_CRIT, tr("云同步目录里的明文密钥"),
                        tr("在云同步目录里发现 {0} 处明文助记词/私钥", nsecret),
                        tr("云端会留有副本。建议把资产转到新钱包（新助记词），并删除这些明文文件。"),
                        [goto(tr("查看并处理"), "wallet", sub="secrets", auto="scan", set={"root_var": str(first)})]))
        if nfiles:
            F.append(_f("cloud_wallets", "wallet", LV_CRIT, tr("云同步目录里的钱包文件"),
                        tr("在云同步目录里发现 {0} 个钱包文件", nfiles),
                        tr("云端会留有副本。建议迁出这些文件，并确认助记词已离线备份。"),
                        [goto(tr("查看钱包文件"), "wallet", sub="files", auto="scan"),
                         act("open_folder", tr("打开该文件夹"), page=None, path=str(first))]))
        if not nsecret and not nfiles:
            F.append(_f("cloud", "wallet", LV_OK, tr("云同步目录"), tr("云同步目录里没有发现钱包文件或明文密钥"), ""))
    if deep:
        if task is None or task.tick(tr("正在扫描主目录里的明文密钥…")):
            res, n = fc.scan_secrets(HOME, wl, max_seconds=300, task=task)
            nbad = sum(1 for x in res if x["level"] == tr("高危"))
            if nbad:
                F.append(_f("home_secrets", "wallet", LV_CRIT, tr("明文助记词 / 私钥"), tr("在主目录发现 {0} 处明文助记词/私钥", nbad),
                            tr("建议把资产转到新钱包（新助记词），助记词抄在纸上离线保存，并删除/加密这些明文文件。"),
                            [goto(tr("查看并处理"), "wallet", sub="secrets", auto="scan", set={"root_var": str(HOME)})]))
            else:
                F.append(_f("home_secrets", "wallet", LV_OK, tr("明文助记词 / 私钥"), tr("主目录里没有发现明文助记词/私钥"), ""))
        if task is None or task.tick(tr("正在查找钱包文件…")):
            files = fc.find_wallet_files(HOME, max_seconds=120, task=task)
            if files:
                incloud = sum(1 for f in files if f["cloud"])
                F.append(_f("wallet_files", "wallet", LV_CRIT if incloud else LV_INFO, tr("钱包文件"),
                            tr("发现 {0} 个钱包文件（{1} 个在云同步目录里），已受 Faster 保护", len(files), incloud),
                            tr("在云同步目录里的建议迁出，并确认助记词已离线备份。") if incloud else tr("确认助记词已离线备份。"),
                            [goto(tr("查看钱包文件"), "wallet", sub="files", auto="scan")]))
    return F


# ---------------------------------------------------------------- 总入口
def run_diagnosis(task=None, deep=False):
    """全面诊断。快速模式约 10~30 秒；deep=True 另做大文件 / 重复文件 / 全主目录钱包与密钥 / 深度风险扫描（可能几分钟）。
    返回 dict(score, cats, findings, snapshot, deep)；task 可取消并显示进度"""
    def stage(text):
        return task is None or task.tick(text)

    stage(tr("正在检查：性能与磁盘"))
    snap = take_snapshot(tr("诊断"))
    junk = None
    try:
        junk = 0
        for _, p in core.junk_targets():
            junk += sum(s for _, s in core.list_files_in(p, 1, task))
            if task is not None and task.cancelled:
                break
    except Exception:
        junk = None
    top = sample_top() if stage(tr("正在检查：内存与 CPU")) else {}
    res = diagnose(snap, junk, top)
    F = res["findings"]
    for label, fn, cat in ((tr("存储"), storage_findings, "storage"), (tr("安全"), security_findings, "security"),
                           (tr("程序签名与基线"), trust_findings, "security"), (tr("加固与更新"), harden_findings, "harden"),
                           (tr("钱包"), wallet_findings, "wallet")):
        if task is not None and task.cancelled:
            break
        stage(tr("正在检查：{0}", label))
        try:
            F += fn(task, deep)
        except Exception as e:
            F.append(_f("err_" + cat + label, cat, LV_INFO, label, tr("这一项没有检查完：{0}", e), ""))
    F.sort(key=lambda f: _LV_ORDER[f["level"]])
    return dict(score=score_of(F), cats=category_scores(F), findings=F, snapshot=snap, deep=deep)


# ============================================================ 启动影响评分
parse_exe = sig.parse_exe          # 已移到 faster_sig.py，这里保留名字


def _running_index():
    byexe, byname = {}, {}
    now = time.time()
    for p in psutil.process_iter(["name", "exe", "memory_info", "cpu_times", "create_time"]):
        try:
            i = p.info
            rec = dict(rss=i["memory_info"].rss if i.get("memory_info") else 0,
                       cpu=(i["cpu_times"].user + i["cpu_times"].system) if i.get("cpu_times") else 0.0,
                       ct=i.get("create_time") or now)
            if i.get("exe"):
                byexe.setdefault(i["exe"].lower(), []).append(rec)
            if i.get("name"):
                byname.setdefault(i["name"].lower(), []).append(rec)
        except Exception:
            pass
    return byexe, byname


def _after_boot_text(sec):
    if sec < 0:
        return "-"
    if sec < 120:
        return tr("开机后 {0:.0f} 秒", sec)
    if sec < 7200:
        return tr("开机后 {0:.0f} 分钟", sec / 60)
    return tr("开机后 {0:.1f} 小时", sec / 3600)


def startup_impact(items=None):
    """估算每个启动项的占用：内存（每 20MB 得 1 分，上限 50）+ 平均 CPU（每 1% 得 5 分，上限 50）。
    返回按分数从高到低排序的 [dict(item,name,cmd,running,rss,cpu_pct,when,score,level,advice)]，未运行的排最后。"""
    items = core.get_startup_items() if items is None else items
    HIGH, MID, LOW, OFF = tr("高"), tr("中"), tr("低"), tr("未运行")
    idx = _running_index() if psutil else ({}, {})
    boot, now = (psutil.boot_time() if psutil else 0), time.time()
    out = []
    for it in items:
        exe = parse_exe(it.get("cmd", ""), it.get("kind", ""))
        recs = idx[0].get(exe.lower()) or (idx[1].get(os.path.basename(exe).lower(), []) if exe else [])
        row = dict(item=it, name=it.get("name", ""), cmd=it.get("cmd", ""), running=bool(recs), rss=0, cpu_pct=0.0,
                   when="-", score=0.0, level=OFF, advice=tr("当前没有运行（可能是一次性任务，无法评估）"))
        if recs:
            rss, cpu = sum(r["rss"] for r in recs), sum(r["cpu"] for r in recs)
            ct = min(r["ct"] for r in recs)
            avg = cpu / max(now - ct, 1.0) * 100
            score = min(50.0, rss / 1048576 / 20.0) + min(50.0, avg * 5)
            row.update(rss=rss, cpu_pct=avg, when=_after_boot_text(ct - boot), score=score,
                       level=HIGH if score >= 60 else MID if score >= 25 else LOW,
                       advice=tr("建议停用，需要时再手动打开") if score >= 60 else
                       tr("可以考虑停用") if score >= 25 else tr("影响很小"))
        out.append(row)
    out.sort(key=lambda r: (not r["running"], -r["score"]))
    return out
