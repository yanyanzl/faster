# -*- coding: utf-8 -*-
"""
Faster · 性能诊断（v0.3）

  1. 瓶颈诊断：磁盘 / 内存 / 交换 / CPU / 启动项 / 运行时间 / 垃圾 / 电源计划 → 健康分 + 建议
  2. 启动影响评分：按“正在运行的进程”估算每个启动项的内存和平均 CPU 占用
  3. 前后对比：优化前后的状态快照（磁盘剩余、内存占用、启动项、进程数…）

原则：只读测量，不修改系统；估算值如实标注为“估算”，不做“加速”类的夸大宣传。
"""
import os
import re
import time
import json
import shutil
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

import faster as core
from faster_i18n import tr

HOME, APP_DIR, human = core.HOME, core.APP_DIR, core.human
IS_WIN = core.IS_WIN
SNAP_FILE = APP_DIR / "snapshots.json"
GB = 1024 ** 3

LV_CRIT, LV_WARN, LV_OK = tr("严重"), tr("注意"), tr("良好")
_LV_ORDER = {LV_CRIT: 0, LV_WARN: 1, LV_OK: 2}


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


# ============================================================ 瓶颈诊断
def sample_top(seconds=1.5, n=3):
    """采样 seconds 秒，返回内存/CPU 占用最高的进程"""
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
            mem.append((nm, p.info["memory_info"].rss))
            cpu.append((nm, p.cpu_percent(None)))
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


def diagnose(snap, junk_bytes=None, top=None, power=None):
    """根据快照给出诊断。返回 dict(score, findings, snapshot)；findings: dict(key,level,title,detail,advice,action)"""
    top = top or {}
    F = []

    def add(key, level, title, detail, advice, action=""):
        F.append(dict(key=key, level=level, title=title, detail=detail,
                      advice=advice if level != LV_OK else tr("无需处理"), action=action))

    total, free = snap.get("disk_total"), snap.get("disk_free")
    if total:
        pct = free / total * 100
        lv = LV_CRIT if (pct < 10 or free < 5 * GB) else LV_WARN if pct < 20 else LV_OK
        add("disk", lv, tr("磁盘空间"), tr("剩余 {0}（{1:.0f}%）", human(free), pct),
            tr("清理垃圾、大文件和重复文件；卸载不用的大型程序。"), "junk")
    if "mem_percent" in snap:
        p = snap["mem_percent"]
        lv = LV_CRIT if p >= 90 else LV_WARN if p >= 80 else LV_OK
        names = ", ".join(n for n, _ in top.get("mem", [])[:3])
        detail = tr("已用 {0}（{1:.0f}%）", human(snap["mem_used"]), p) + (tr("；占用最多：{0}", names) if names and lv != LV_OK else "")
        add("memory", lv, tr("内存"), detail, tr("关闭不用的程序和浏览器标签页；长期不够用就增加内存。"), "process")
        sp = snap.get("swap_percent", 0)
        lv = LV_WARN if (sp >= 50 and p >= 80) else LV_OK
        add("swap", lv, tr("交换空间"), tr("已用 {0:.0f}%", sp), tr("内存吃紧又在大量使用交换空间时电脑会明显变卡：关闭占内存大的程序，或增加内存。"), "process")
        cpu = top.get("cpu_total", snap.get("cpu_percent"))
        if cpu is not None:
            names = ", ".join(n for n, c in top.get("cpu", [])[:3] if c >= 10)
            lv = LV_WARN if cpu >= 85 else LV_OK
            add("cpu", lv, tr("CPU"), tr("占用 {0:.0f}%", cpu) + (tr("；占用最高：{0}", names) if names and lv != LV_OK else ""),
                tr("查看“后台进程”页，结束长期高占用且不需要的程序。"), "process")
    else:
        add("psutil", LV_WARN, tr("内存 / CPU"), tr("无法读取"), tr("安装 psutil（pip install psutil）后才能诊断内存、CPU 和进程。"))
    n = snap.get("startup")
    if n is not None:
        lv = LV_CRIT if n > 25 else LV_WARN if n > 12 else LV_OK
        add("startup", lv, tr("开机启动项"), tr("共 {0} 个", n), tr("到“启动影响”页按影响排序，停用不需要的启动项。"), "impact")
    if "uptime" in snap:
        d = snap["uptime"] / 86400
        add("uptime", LV_WARN if d > 14 else LV_OK, tr("连续运行时间"), tr("{0:.1f} 天", d),
            tr("重启一次可以释放内存，并让系统更新生效。"), "reboot")
    if junk_bytes is not None:
        lv = LV_CRIT if junk_bytes >= 10 * GB else LV_WARN if junk_bytes >= 2 * GB else LV_OK
        add("junk", lv, tr("可清理的垃圾"), tr("约 {0}", human(junk_bytes)), tr("到“垃圾清理”页清理。"), "junk")
    if power is None:
        power = win_power_scheme()
    if power:
        add("power", LV_WARN if power == "saver" else LV_OK, tr("电源计划"),
            tr("节能") if power == "saver" else tr("平衡 / 高性能"),
            tr("需要速度时，在“设置 → 系统 → 电源”里改成“平衡”或“最佳性能”。"))
    F.sort(key=lambda f: _LV_ORDER[f["level"]])
    crit = sum(1 for f in F if f["level"] == LV_CRIT)
    warn = sum(1 for f in F if f["level"] == LV_WARN)
    return dict(score=max(0, 100 - 25 * crit - 10 * warn), findings=F, snapshot=snap)


def run_diagnosis(task=None):
    """完整诊断（约 2~10 秒）：快照 + 垃圾体积 + 占用最高的进程"""
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
    return diagnose(snap, junk, sample_top())


# ============================================================ 启动影响评分
def parse_exe(cmd, kind=""):
    """从启动项命令里取出可执行文件路径"""
    c = (cmd or "").strip()
    if not c:
        return ""
    if kind == "desktop":
        c = re.sub(r"%[a-zA-Z]\b", "", c).strip()
    if c.startswith('"'):
        end = c.find('"', 1)
        exe = c[1:end] if end > 0 else c[1:]
    else:
        m = re.match(r"(.+?\.(?:exe|bat|cmd|com|scr))(?:\s|$)", c, re.I)
        exe = m.group(1) if m else c.split()[0]
    return os.path.expandvars(exe)


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
