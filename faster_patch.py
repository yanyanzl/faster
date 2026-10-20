# -*- coding: utf-8 -*-
"""
Faster · 补丁与更新检查（v0.4）

结果是 dict(key, level, title, detail, advice, fix) 的列表；level：crit / warn / info / ok；
fix：None，或 {"settings": 要打开的系统设置}，或 {"command": 可复制的修复命令}。
只读检查。快速模式只读本机信息（几秒）；deep=True 会联网向系统的更新服务查询“还有哪些更新没装”（可能要一两分钟）。
"""
import os
import re
import time
import shutil
import datetime

import faster as core
import faster_baseline as base
from faster_i18n import tr

IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC

EOL_RE = re.compile(r"(adobe flash|flash player|quicktime|silverlight|python 2\.|java\(tm\) se runtime environment [67]\b|"
                    r"\bjava [67]\b|jre ?1\.[67]|java\(tm\) 7)", re.I)


def r(key, level, title, detail, advice="", fix=None):
    return dict(key=key, level=level, title=title, detail=detail, advice=advice, fix=fix)


# ---------------------------------------------------------------- Windows
def win_last_hotfix_days():
    """最近一次补丁安装距今多少天；读不到返回 None"""
    _, txt, _ = core.run(["powershell", "-NoProfile", "-Command",
                          "(Get-HotFix | Where-Object {$_.InstalledOn} | Sort-Object InstalledOn -Descending | "
                          "Select-Object -First 1).InstalledOn.ToString('yyyy-MM-dd')"], timeout=60)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", txt or "")
    return (datetime.date.today() - datetime.date(*map(int, m.groups()))).days if m else None


def win_reboot_pending():
    import winreg
    for k in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"):
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, k))
            return True
        except OSError:
            pass
    return False


def win_pending_updates():
    """向 Windows 更新服务查询未安装的更新（需联网，较慢）：返回 (数量, [标题]) 或 None"""
    ps = ("$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.Encoding]::UTF8;try{"
          "$s=New-Object -ComObject Microsoft.Update.Session;"
          "$q=$s.CreateUpdateSearcher().Search(\"IsInstalled=0 and Type='Software' and IsHidden=0\");"
          "'COUNT='+$q.Updates.Count;$q.Updates|Select-Object -First 5|ForEach-Object{'T='+$_.Title}}catch{'ERR='+$_.Exception.Message}")
    _, txt, _ = core.run(["powershell", "-NoProfile", "-Command", ps], timeout=150)
    m = re.search(r"COUNT=(\d+)", txt or "")
    return (int(m.group(1)), re.findall(r"^T=(.+)$", txt, re.M)) if m else None


# ---------------------------------------------------------------- macOS / Linux
def mac_auto_update_flags():
    def flag(k):
        rc, out, _ = core.run(["defaults", "read", "/Library/Preferences/com.apple.SoftwareUpdate", k])
        return out.strip() if rc == 0 else None
    return dict(check=flag("AutomaticCheckEnabled"), critical=flag("CriticalUpdateInstall"))


def mac_pending_updates():
    _, txt, _ = core.run(["softwareupdate", "-l"], timeout=150)
    if re.search(r"No new software available", txt or "", re.I):
        return 0, []
    labels = re.findall(r"^\s*\*\s*(?:Label:\s*)?(.+)$", txt or "", re.M)
    return (len(labels), labels[:5]) if "Software Update found" in (txt or "") or labels else None


def apt_upgradable():
    """Debian/Ubuntu 系：(可更新总数, 其中安全更新数)；没有 apt 返回 None"""
    if not shutil.which("apt"):
        return None
    _, txt, _ = core.run(["apt", "list", "--upgradable"], timeout=60)
    lines = [l for l in (txt or "").splitlines() if "upgradable" in l]
    return len(lines), sum(1 for l in lines if "security" in l.lower())


def apt_index_age_days():
    p = "/var/lib/apt/periodic/update-success-stamp"
    try:
        return (time.time() - os.path.getmtime(p)) / 86400
    except OSError:
        return None


def dnf_updates():
    if not shutil.which("dnf"):
        return None
    rc, txt, _ = core.run(["dnf", "-q", "check-update"], timeout=120)
    return len([l for l in (txt or "").splitlines() if l.strip() and not l.startswith(" ")]) if rc == 100 else 0 if rc == 0 else None


# ---------------------------------------------------------------- 总入口
def eol_software():
    try:
        return sorted({n for n in base._programs() if EOL_RE.search(n)})
    except Exception:
        return []


def check(deep=False):
    out = []
    try:
        if IS_WIN:
            days = win_last_hotfix_days()
            fix = {"settings": "windows_update"}
            if days is None:
                out.append(r("hotfix", "info", tr("系统更新"), tr("读不到补丁安装记录"), tr("打开 Windows 更新，手动检查一下。"), fix))
            else:
                lv = "crit" if days > 120 else "warn" if days > 60 else "ok"
                out.append(r("hotfix", lv, tr("系统更新"), tr("最近一次补丁安装在 {0} 天前", days),
                             tr("很久没装补丁了：打开 Windows 更新，检查并安装更新。"), fix))
            if win_reboot_pending():
                out.append(r("reboot", "warn", tr("需要重启"), tr("更新已经安装，重启后才生效"), tr("保存好工作后重启电脑。")))
            if deep:
                pend = win_pending_updates()
                if pend is None:
                    out.append(r("wua", "info", tr("待安装的更新"), tr("没能连上更新服务"), tr("检查网络，或直接打开 Windows 更新。"), fix))
                elif pend[0]:
                    out.append(r("wua", "warn", tr("待安装的更新"), tr("有 {0} 个更新没装：{1}", pend[0], "; ".join(pend[1])[:150]),
                                 tr("到 Windows 更新里安装。"), fix))
                else:
                    out.append(r("wua", "ok", tr("待安装的更新"), tr("没有待安装的更新"), ""))
        elif IS_MAC:
            fl = mac_auto_update_flags()
            fix = {"settings": "mac_update"}
            if fl["check"] == "0":
                out.append(r("auto_check", "warn", tr("系统更新"), tr("自动检查更新已关闭"), tr("到“软件更新”里打开自动检查，安全更新才能及时装上。"), fix))
            elif fl["critical"] == "0":
                out.append(r("auto_critical", "info", tr("系统更新"), tr("没有开启“自动安装安全响应和系统文件”"), tr("建议在“软件更新”的高级选项里打开。"), fix))
            else:
                out.append(r("auto_update", "ok", tr("系统更新"), tr("自动更新已开启"), ""))
            if deep:
                pend = mac_pending_updates()
                if pend is None:
                    out.append(r("softwareupdate", "info", tr("待安装的更新"), tr("没能查询更新"), tr("打开“软件更新”手动检查。"), fix))
                elif pend[0]:
                    out.append(r("softwareupdate", "warn", tr("待安装的更新"), tr("有 {0} 个更新没装：{1}", pend[0], "; ".join(pend[1])[:150]),
                                 tr("到“软件更新”里安装。"), fix))
                else:
                    out.append(r("softwareupdate", "ok", tr("待安装的更新"), tr("没有待安装的更新"), ""))
        else:
            if os.path.exists("/var/run/reboot-required"):
                out.append(r("reboot", "warn", tr("需要重启"), tr("更新已经安装，重启后才生效"), tr("保存好工作后重启电脑。")))
            apt = apt_upgradable()
            cmd = {"command": "sudo apt update && sudo apt upgrade"}
            if apt is not None:
                total, sec = apt
                age = apt_index_age_days()
                if sec:
                    out.append(r("apt", "crit", tr("系统更新"), tr("有 {0} 个软件包可更新，其中 {1} 个是安全更新", total, sec),
                                 tr("尽快更新：复制命令，在终端里运行。"), cmd))
                elif total:
                    out.append(r("apt", "warn", tr("系统更新"), tr("有 {0} 个软件包可更新", total), tr("复制命令，在终端里运行。"), cmd))
                else:
                    out.append(r("apt", "ok", tr("系统更新"), tr("已是最新（以本机的软件包索引为准）"), ""))
                if age is not None and age > 7:
                    out.append(r("apt_index", "info", tr("软件包索引"), tr("已经 {0:.0f} 天没刷新", age),
                                 tr("先刷新索引才能看到最新的更新。"), cmd))
            if deep:
                n = dnf_updates()
                if n:
                    out.append(r("dnf", "warn", tr("系统更新"), tr("有 {0} 个软件包可更新", n), tr("复制命令，在终端里运行。"),
                                 {"command": "sudo dnf upgrade"}))
    except Exception as e:
        out.append(r("patch_err", "info", tr("系统更新"), tr("这一项没有检查完：{0}", e)))
    eol = eol_software()
    if eol:
        out.append(r("eol", "warn", tr("已停止维护的软件"), tr("发现：{0}", ", ".join(eol[:5])),
                     tr("这些软件不再收到安全更新，建议卸载或换成新版。")))
    return out
