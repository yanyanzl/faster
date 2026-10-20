# -*- coding: utf-8 -*-
"""
Faster · 程序签名验证（v0.4）

检查“会自动运行的程序”有没有可信的数字签名：开机启动项的程序 + 从用户目录运行的进程。
  * Windows：Authenticode（PowerShell Get-AuthenticodeSignature）
  * macOS：codesign（ad-hoc 签名视为“无签名”）
  * Linux：没有通用的程序签名，改查“文件是否属于某个已安装的软件包”（dpkg -S / rpm -qf）
只读检查，不修改任何东西。签名有效只说明“来源可追溯、没被篡改”，不等于一定安全；无签名也不等于一定有害。
"""
import os
import re
import sys
import json
import shutil
import hashlib
import tempfile

try:
    import psutil
except ImportError:
    psutil = None

import faster as core
from faster_i18n import tr

IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC
_RISK_ORDER = {"crit": 0, "warn": 1, "info": 2, "ok": 3}


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


def sha256_file(path, limit=200 * 1024 * 1024):
    """文件的 SHA-256（可以拿去 VirusTotal 之类的网站查询）；太大或读不了返回空串"""
    try:
        if os.path.getsize(path) > limit:
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _norm(p):
    """统一成小写 + 正斜杠，便于跨平台比较路径"""
    return str(p).replace("\\", "/").lower()


def _system_prefixes():
    if IS_WIN:
        env = [os.environ.get(k) for k in ("WINDIR", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432")]
        return [_norm(x) for x in env if x]
    if IS_MAC:
        return ["/system", "/usr", "/bin", "/sbin", "/applications", "/library", "/opt", "/private/var/db"]
    return ["/usr", "/bin", "/sbin", "/lib", "/lib64", "/opt", "/snap", "/etc"]


def in_user_dir(path):
    """程序是否放在“用户可写”的位置（不在系统目录 / 程序安装目录里）"""
    n = _norm(path)
    return not any(n == p or n.startswith(p.rstrip("/") + "/") for p in _system_prefixes())


def in_temp_or_downloads(path):
    n = _norm(path)
    return any(k in n for k in ("/temp/", "/tmp/", "/var/tmp/", "/dev/shm/", "/downloads/", "/appdata/local/temp"))


# ---------------------------------------------------------------- 各平台验证
def _map_win(status):
    return {"valid": "valid", "notsigned": "unsigned", "notsupportedfileformat": "unknown"}.get(
        (status or "").lower(), "missing" if (status or "").lower() == "unknownerror" else "invalid")


def _verify_windows(paths):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(list(paths), tmp)
        tmp.close()
        ps = ("$ErrorActionPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
              "$p=@(Get-Content -Raw -Encoding UTF8 -LiteralPath '" + tmp.name.replace("'", "''") + "' | ConvertFrom-Json);"
              "$r=@();for($i=0;$i -lt $p.Count;$i++){$s=Get-AuthenticodeSignature -LiteralPath $p[$i];"
              "$r+=[pscustomobject]@{I=$i;Status=[string]$s.Status;Subject=[string]$s.SignerCertificate.Subject}};"
              "ConvertTo-Json -InputObject $r -Compress")
        rc, out, _ = core.run(["powershell", "-NoProfile", "-Command", ps], timeout=180)
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
        res = {}
        for d in data:
            m = re.search(r"CN=([^,]+)", d.get("Subject") or "")
            res[paths[int(d["I"])]] = dict(status=_map_win(d.get("Status")), signer=(m.group(1).strip('" ') if m else ""))
        return res
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _verify_mac(paths):
    res = {}
    for p in paths:
        rc, _, err = core.run(["codesign", "--verify", "--strict", p], timeout=20)
        if rc == 0:
            _, _, info = core.run(["codesign", "-dvv", p], timeout=20)
            if "Signature=adhoc" in info:
                res[p] = dict(status="unsigned", signer="ad-hoc")
                continue
            m = re.search(r"Authority=(.+)", info)
            auth = m.group(1).strip() if m else ""
            res[p] = dict(status="valid", signer="Apple" if "Apple" in auth and "Developer ID" not in auth else
                          re.sub(r"^Developer ID Application:\s*", "", auth))
        elif "not signed at all" in err:
            res[p] = dict(status="unsigned", signer="")
        else:
            res[p] = dict(status="invalid", signer="")
    return res


def _package_owner(path):
    """Linux：文件属于哪个软件包；不属于任何包返回 ''；没有包管理器返回 None"""
    rp = os.path.realpath(path)
    if shutil.which("dpkg"):
        rc, out, _ = core.run(["dpkg", "-S", rp], timeout=20)
        return out.split(":")[0].strip() if rc == 0 and out.strip() else ""
    if shutil.which("rpm"):
        rc, out, _ = core.run(["rpm", "-qf", rp], timeout=20)
        return out.strip() if rc == 0 and out.strip() else ""
    return None


def _verify_linux(paths):
    res = {}
    for p in paths:
        owner = _package_owner(p)
        res[p] = dict(status="unknown" if owner is None else "valid" if owner else "unsigned", signer=owner or "")
    return res


def verify(paths):
    """返回 {路径: dict(status, signer)}；status：valid / unsigned / invalid / unknown / missing"""
    paths = [p for p in dict.fromkeys(paths) if p]
    out = {p: dict(status="missing", signer="") for p in paths if not os.path.exists(p)}
    todo = [p for p in paths if p not in out]
    if todo:
        try:
            out.update(_verify_windows(todo) if IS_WIN else _verify_mac(todo) if IS_MAC else _verify_linux(todo))
        except Exception:
            pass
        for p in todo:
            out.setdefault(p, dict(status="unknown", signer=""))
    return out


def status_text(status):
    if status == "valid":
        return tr("已验证") if not (IS_WIN or IS_MAC) else tr("签名有效")
    if status == "unsigned":
        return tr("无签名") if (IS_WIN or IS_MAC) else tr("不属于任何软件包")
    return {"invalid": tr("签名无效"), "missing": tr("文件不存在"), "unknown": tr("无法判断")}.get(status, status)


# ---------------------------------------------------------------- 扫描
def candidates(deep=False):
    """要检查的程序：全部开机启动项 + 从用户目录运行的进程（deep：所有运行中的进程）"""
    rows, seen = [], set()
    for it in core.get_startup_items():
        exe = parse_exe(it.get("cmd", ""), it.get("kind", ""))
        if exe and _norm(exe) not in seen:
            seen.add(_norm(exe))
            rows.append(dict(kind="startup", name=it.get("name", ""), path=exe, item=it, pid=None))
    if psutil:
        me = {_norm(sys.executable)}
        limit, n = (200 if deep else 40), 0
        for p in psutil.process_iter(["pid", "name", "exe"]):
            try:
                exe = p.info.get("exe")
                if not exe or _norm(exe) in seen or _norm(exe) in me or p.pid == os.getpid():
                    continue
                if not deep and not in_user_dir(exe):
                    continue
                seen.add(_norm(exe))
                rows.append(dict(kind="process", name=p.info.get("name") or os.path.basename(exe), path=exe, item=None, pid=p.pid))
                n += 1
                if n >= limit:
                    break
            except Exception:
                pass
    return rows


def risk_of(r):
    """crit：签名被破坏 / 从临时目录运行的无签名进程；warn：无签名的启动项；info：用户目录里的无签名程序；ok：其余"""
    st = r["status"]
    if st == "invalid":
        return "crit"
    if st == "unsigned":
        if r["kind"] == "process" and r["temp"]:
            return "crit"
        if r["kind"] == "startup":
            return "warn"
        if r["user_dir"]:
            return "info"
    if st == "missing" and r["kind"] == "startup":
        return "info"
    return "ok"


def scan(task=None, deep=False):
    rows = candidates(deep)
    if task is not None:
        task.tick(tr("正在验证 {0} 个程序的签名…", len(rows)))
    res = verify([r["path"] for r in rows])
    for r in rows:
        v = res.get(r["path"], dict(status="unknown", signer=""))
        r.update(status=v["status"], signer=v["signer"], user_dir=in_user_dir(r["path"]), temp=in_temp_or_downloads(r["path"]))
        r["risk"] = risk_of(r)
    rows.sort(key=lambda r: (_RISK_ORDER[r["risk"]], r["name"].lower()))
    return rows
