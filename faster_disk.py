# -*- coding: utf-8 -*-
"""
Faster · 磁盘健康（v0.5）

硬盘“快坏了”比清理垃圾重要得多：读取系统给出的健康状态（SMART），只读检查。
  * Windows：Get-PhysicalDisk 的健康状态 + （读得到时）磨损 / 温度 / 读写错误
  * macOS：diskutil 的 SMART 状态
  * Linux：smartctl -H（需要安装 smartmontools，通常还需要管理员权限）
结果格式同 faster_patch：dict(key, level, title, detail, advice, fix)，level：crit / warn / info / ok。
"""
import re
import json
import shutil

import faster as core
from faster_i18n import tr

IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC
BACKUP_ADVICE = tr("立即备份重要数据，并准备更换硬盘。")


def r(key, level, title, detail, advice="", fix=None):
    return dict(key=key, level=level, title=title, detail=detail, advice=advice, fix=fix)


def parse_windows(json_text, wear_text=""):
    """解析 Get-PhysicalDisk 的 JSON（可选再加磨损信息）→ 结果列表"""
    out = []
    try:
        data = json.loads(json_text) if json_text.strip() else []
    except ValueError:
        return out
    data = [data] if isinstance(data, dict) else data
    wear = {}
    try:
        w = json.loads(wear_text) if wear_text.strip() else []
        for x in ([w] if isinstance(w, dict) else w):
            wear[str(x.get("DeviceId"))] = x
    except ValueError:
        pass
    for d in data:
        name = d.get("FriendlyName") or tr("磁盘")
        health, oper = str(d.get("HealthStatus", "")), str(d.get("OperationalStatus", ""))
        key = "disk_" + str(d.get("DeviceId", name))
        wr = wear.get(str(d.get("DeviceId")), {})
        if health.lower() == "unhealthy":
            out.append(r(key, "crit", name, tr("健康状态：不健康"), BACKUP_ADVICE))
        elif health.lower() == "warning" or (oper and oper.lower() not in ("ok", "")):
            out.append(r(key, "warn", name, tr("健康状态：{0}（{1}）", health or "?", oper or "?"), BACKUP_ADVICE))
        else:
            extra = []
            lv = "ok"
            try:
                if wr.get("Wear") is not None and int(wr["Wear"]) >= 80:
                    extra.append(tr("已磨损 {0}%", int(wr["Wear"])))
                    lv = "crit" if int(wr["Wear"]) >= 95 else "warn"
                if wr.get("Temperature") is not None and int(wr["Temperature"]) >= 65:
                    extra.append(tr("温度 {0}℃", int(wr["Temperature"])))
                    lv = "warn" if lv == "ok" else lv
                errs = int(wr.get("ReadErrorsTotal") or 0) + int(wr.get("WriteErrorsTotal") or 0)
                if errs > 0:
                    extra.append(tr("累计读写错误 {0} 次", errs))
                    lv = "warn" if lv == "ok" else lv
            except (TypeError, ValueError):
                pass
            out.append(r(key, lv, name, "; ".join(extra) if extra else tr("健康"), BACKUP_ADVICE if lv != "ok" else ""))
    return out


def parse_diskutil(text):
    """解析 `diskutil info -all`：每块物理盘的 SMART 状态"""
    out = []
    for block in re.split(r"\n\s*\n|\*{5,}", text or ""):
        m = re.search(r"SMART Status:\s*(.+)", block)
        if not m:
            continue
        name = (re.search(r"Device / Media Name:\s*(.+)", block) or re.search(r"Media Name:\s*(.+)", block))
        name = name.group(1).strip() if name else (re.search(r"Device Identifier:\s*(\S+)", block).group(1) if re.search(r"Device Identifier:\s*(\S+)", block) else tr("磁盘"))
        st = m.group(1).strip()
        if st.lower().startswith("failing"):
            out.append(r("disk_" + name, "crit", name, tr("SMART 状态：即将故障"), BACKUP_ADVICE))
        elif st.lower().startswith("verified"):
            out.append(r("disk_" + name, "ok", name, tr("SMART 状态：正常"), ""))
    return out


def parse_smartctl(device, rc, text):
    """解析 smartctl -H 的结果；看不出来返回 None"""
    low = (text or "").lower()
    if "permission denied" in low or "operation not permitted" in low:
        return r("disk_" + device, "info", device, tr("需要管理员权限才能读取 SMART"), tr("复制命令，在终端里运行。"),
                 {"command": f"sudo smartctl -H /dev/{device}"})
    if "passed" in low or re.search(r"health status:\s*ok", low):
        return r("disk_" + device, "ok", device, tr("SMART 自检：通过"), "")
    if re.search(r"test result:\s*failed|failed!", low):
        return r("disk_" + device, "crit", device, tr("SMART 自检：失败"), BACKUP_ADVICE)
    return None


def check():
    out = []
    try:
        if IS_WIN:
            _, a, _ = core.run(["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
                                "ConvertTo-Json -Compress -InputObject @(Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,"
                                "HealthStatus,OperationalStatus,MediaType)"], timeout=60)
            _, b, _ = core.run(["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
                                "ConvertTo-Json -Compress -InputObject @(Get-PhysicalDisk | Get-StorageReliabilityCounter | "
                                "Select-Object DeviceId,Wear,Temperature,ReadErrorsTotal,WriteErrorsTotal)"], timeout=60)
            out += parse_windows(a, b)
        elif IS_MAC:
            _, txt, _ = core.run(["diskutil", "info", "-all"], timeout=60)
            out += parse_diskutil(txt)
        else:
            if not shutil.which("lsblk"):
                return out
            _, lsb, _ = core.run(["lsblk", "-dno", "NAME,TYPE"])
            disks = [ln.split()[0] for ln in lsb.splitlines() if len(ln.split()) >= 2 and ln.split()[1] == "disk"]
            if disks and not shutil.which("smartctl"):
                out.append(r("smartctl", "info", tr("磁盘健康"), tr("没有安装 smartmontools，读不到 SMART"), tr("安装后才能查看硬盘健康状态。"),
                             {"command": "sudo apt install smartmontools"}))
            elif disks:
                for dev in disks:
                    rc, txt, err = core.run(["smartctl", "-H", f"/dev/{dev}"], timeout=30)
                    res = parse_smartctl(dev, rc, txt + "\n" + err)
                    if res:
                        out.append(res)
    except Exception as e:
        out.append(r("disk_err", "info", tr("磁盘健康"), tr("这一项没有检查完：{0}", e)))
    return out
