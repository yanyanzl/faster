# -*- coding: utf-8 -*-
"""
Faster · 基线对比（v0.4）

给“安全相关的状态”拍一张快照作为基线：启动项、计划任务、对外监听端口、hosts 条目、管理员账户、SSH 授权密钥、已安装程序。
之后每次只告诉你“和基线相比多了什么 / 少了什么”——被偷偷加上的后门，比一次次全量报告更容易发现。
建议在你确认电脑目前是干净的时候建立基线；正常装了新软件后，点“接受变化”更新基线即可。
"""
import os
import csv
import time
import json
import hashlib
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

import faster as core
from faster_i18n import tr

BASE_FILE = core.APP_DIR / "baseline.json"
IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC
CATS = (("startup", tr("开机启动项")), ("tasks", tr("计划任务")), ("ports", tr("对外监听端口")), ("hosts", tr("hosts 条目")),
        ("admins", tr("管理员账户")), ("ssh_keys", tr("SSH 授权密钥")), ("programs", tr("已安装程序")))
CAT_NAME = dict(CATS)


def _startup():
    return sorted({f"{it['kind']}|{it['name']}|{it.get('cmd', '')}" for it in core.get_startup_items()})


def _tasks():
    out = set()
    if IS_WIN:
        _, txt, _ = core.run(["schtasks", "/query", "/fo", "csv", "/nh"], timeout=60)
        for row in csv.reader(txt.splitlines()):
            if row and row[0].strip() and not row[0].strip().lower().startswith("\\microsoft\\windows\\"):
                out.add(row[0].strip())
        return sorted(out)
    rc, txt, _ = core.run(["crontab", "-l"])
    if rc == 0:
        out.update("cron|" + ln.strip() for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith("#"))
    dirs = ([Path("/Library/LaunchDaemons"), Path("/Library/LaunchAgents"), core.HOME / "Library/LaunchAgents"] if IS_MAC
            else [Path("/etc/cron.d"), core.HOME / ".config/systemd/user"])
    for d in dirs:
        try:
            out.update(f"{d.name}|{f.name}" for f in d.iterdir() if f.is_file() and not f.name.startswith("com.apple."))
        except OSError:
            pass
    return sorted(out)


def _ports():
    if not psutil:
        return []
    out = set()
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.ip not in ("127.0.0.1", "::1"):
                name = ""
                try:
                    name = psutil.Process(c.pid).name() if c.pid else ""
                except Exception:
                    pass
                out.add(f"{c.laddr.port}|{name}")
    except Exception:
        pass
    return sorted(out)


def _hosts():
    return sorted(f"{h} {ip}" for h, ip in core.hosts_entries())


def _admins():
    members = set()
    if IS_WIN:
        _, txt, _ = core.run(["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
                              "Get-LocalGroupMember -SID S-1-5-32-544 | ForEach-Object { $_.Name }"], timeout=30)
        members.update(l.strip() for l in txt.splitlines() if l.strip())
    elif IS_MAC:
        _, txt, _ = core.run(["dscl", ".", "-read", "/Groups/admin", "GroupMembership"])
        if ":" in txt:
            members.update(txt.split(":", 1)[1].split())
    else:
        for g in ("sudo", "wheel", "admin"):
            _, txt, _ = core.run(["getent", "group", g])
            parts = txt.strip().split(":")
            if len(parts) >= 4:
                members.update(x for x in parts[3].split(",") if x)
    return sorted(members)


def _ssh_keys():
    out = []
    try:
        for ln in (core.HOME / ".ssh/authorized_keys").read_text(errors="replace").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.append(hashlib.sha256(ln.encode()).hexdigest()[:12] + "|" + ln.split()[-1][:40])
    except OSError:
        pass
    return sorted(out)


def _programs():
    if IS_MAC:
        try:
            return sorted(p.stem for p in Path("/Applications").glob("*.app"))
        except OSError:
            return []
    return sorted({a["name"] for a in core.installed_programs()})


def collect():
    """采集当前状态：{类别: [字符串, ...]}（某一类采集失败就是空列表，不影响其它类）"""
    items = {}
    for key, fn in (("startup", _startup), ("tasks", _tasks), ("ports", _ports), ("hosts", _hosts), ("admins", _admins),
                    ("ssh_keys", _ssh_keys), ("programs", _programs)):
        try:
            items[key] = fn()
        except Exception:
            items[key] = []
    return items


def load():
    try:
        d = json.loads(BASE_FILE.read_text(encoding="utf-8"))
        return d if "items" in d else None
    except Exception:
        return None


def save(items=None):
    d = dict(ts=time.time(), items=collect() if items is None else items)
    BASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASE_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def diff(old_items, new_items):
    """{类别: dict(added=[...], removed=[...])}，只包含有变化的类别"""
    out = {}
    for key, _ in CATS:
        a, b = set(old_items.get(key, [])), set(new_items.get(key, []))
        if a != b:
            out[key] = dict(added=sorted(b - a), removed=sorted(a - b))
    return out


def compare():
    """和基线对比；还没有基线返回 None"""
    base = load()
    if not base:
        return None
    cur = collect()
    return dict(ts=base["ts"], diff=diff(base["items"], cur), current=cur)


def pretty(key, entry):
    """把存储用的字符串变成给人看的文字"""
    if key == "startup":
        kind, name, cmd = (entry.split("|", 2) + ["", ""])[:3]
        return f"{name}: {cmd}"[:120]
    if key == "ports":
        port, name = (entry.split("|", 1) + [""])[:2]
        return f"{port} ({name or '?'})"
    if key == "ssh_keys":
        return entry.replace("|", "  ")
    return entry
