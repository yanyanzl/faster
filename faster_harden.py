# -*- coding: utf-8 -*-
"""
Faster · 安全加固检查（v0.4）

检查“系统有没有开着不该开的门、关着该开的锁”：磁盘加密、远程登录、自动登录、UAC、SMBv1、屏幕锁、备份、对外开放的高风险端口…
结果格式同 faster_patch：dict(key, level, title, detail, advice, fix)；只读检查，不改动任何设置。
fix 是“怎么修”：打开对应的系统设置，或给出可复制的命令（需要管理员权限的修改，Faster 不会替你做）。
"""
import os
import re
import socket
import shutil

try:
    import psutil
except ImportError:
    psutil = None

import faster as core
from faster_i18n import tr

IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC


def r(key, level, title, detail, advice="", fix=None):
    return dict(key=key, level=level, title=title, detail=detail, advice=advice, fix=fix)


def _reg(hive, path, name):
    try:
        import winreg
        h = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[hive]
        with winreg.OpenKey(h, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except Exception:
        return None


def _port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


RISKY_PORTS = {23: "Telnet", 21: "FTP", 3389: None, 5900: None, 5901: None}      # None → 用下面的本地化名称


def _risky_name(port):
    return {23: "Telnet", 21: "FTP", 3389: tr("远程桌面"), 5900: tr("VNC / 屏幕共享"), 5901: tr("VNC / 屏幕共享")}[port]


def risky_ports():
    """对外（非本机）监听的高风险端口 {端口: 名称}；读不到返回 {}"""
    found = {}
    if not psutil:
        return found
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port in RISKY_PORTS and c.laddr.ip not in ("127.0.0.1", "::1"):
                found[c.laddr.port] = _risky_name(c.laddr.port)
    except Exception:
        pass
    return found


def _windows():
    out = []
    uac = _reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "EnableLUA")
    if uac == 0:
        out.append(r("uac", "crit", tr("用户账户控制（UAC）"), tr("已关闭"), tr("UAC 是拦截程序偷偷提权的第一道门，建议开启。")))
    elif uac is not None:
        out.append(r("uac", "ok", tr("用户账户控制（UAC）"), tr("已开启"), ""))
    if str(_reg("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "AutoAdminLogon")) == "1":
        out.append(r("autologon", "warn", tr("自动登录"), tr("开机不用输密码就进入系统"), tr("别人拿到电脑就能直接用，建议关闭自动登录。")))
    if _reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Terminal Server", "fDenyTSConnections") == 0:
        out.append(r("rdp", "warn", tr("远程桌面"), tr("已开启"), tr("不需要远程控制本机就关掉；要用请设置强密码并只在可信网络使用。"), {"settings": "remote_desktop"}))
    if _reg("HKLM", r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "SMB1") == 1:
        out.append(r("smb1", "crit", tr("SMBv1 协议"), tr("已开启"), tr("SMBv1 有严重的已知漏洞（勒索病毒常用）。以管理员身份打开 PowerShell 运行命令关闭它。"),
                     {"command": "Set-SmbServerConfiguration -EnableSMB1Protocol $false"}))
    sb = _reg("HKLM", r"SYSTEM\CurrentControlSet\Control\SecureBoot\State", "UEFISecureBootEnabled")
    if sb == 0:
        out.append(r("secureboot", "info", tr("安全启动（Secure Boot）"), tr("未开启"), tr("可在 BIOS/UEFI 里开启，能防止启动阶段被植入恶意程序。")))
    _, txt, _ = core.run(["powershell", "-NoProfile", "-Command",
                          "(New-Object -ComObject Shell.Application).NameSpace($env:SystemDrive).Self.ExtendedProperty('System.Volume.BitLockerProtection')"],
                         timeout=30)
    v = txt.strip()
    if v == "1":
        out.append(r("bitlocker", "ok", tr("磁盘加密（BitLocker）"), tr("系统盘已加密"), ""))
    elif v == "0":
        out.append(r("bitlocker", "warn", tr("磁盘加密（BitLocker）"), tr("系统盘没有加密"),
                     tr("电脑丢失或被拆硬盘时，里面的数据可以被直接读取。家庭版 Windows 可能不支持 BitLocker，可看“设备加密”。"),
                     {"settings": "bitlocker"}))
    return out


def _mac():
    out = []
    _, txt, _ = core.run(["fdesetup", "status"])
    if "FileVault is On" in txt:
        out.append(r("filevault", "ok", tr("磁盘加密（FileVault）"), tr("已开启"), ""))
    elif "FileVault is Off" in txt:
        out.append(r("filevault", "warn", tr("磁盘加密（FileVault）"), tr("没有开启"), tr("电脑丢失时里面的数据可以被直接读取，建议开启。"),
                     {"settings": "mac_filevault"}))
    rc, txt, _ = core.run(["defaults", "read", "/Library/Preferences/com.apple.loginwindow", "autoLoginUser"])
    if rc == 0 and txt.strip():
        out.append(r("autologon", "warn", tr("自动登录"), tr("开机不用输密码就进入系统"), tr("别人拿到电脑就能直接用，建议关闭自动登录。"), {"settings": "mac_users"}))
    _, txt, _ = core.run(["defaults", "read", "/Library/Preferences/com.apple.loginwindow", "GuestEnabled"])
    if txt.strip() == "1":
        out.append(r("guest", "warn", tr("访客账户"), tr("已开启"), tr("不需要就关掉。"), {"settings": "mac_users"}))
    _, txt, _ = core.run(["defaults", "read", "com.apple.screensaver", "askForPassword"])
    if txt.strip() == "0":
        out.append(r("screenlock", "warn", tr("屏幕锁"), tr("唤醒屏幕时不要求输入密码"), tr("建议开启：离开座位时别人无法直接使用。"), {"settings": "mac_security"}))
    _, txt, _ = core.run(["tmutil", "destinationinfo"])
    if "No destinations configured" in txt:
        out.append(r("backup", "warn", tr("备份（Time Machine）"), tr("没有配置备份"), tr("硬盘坏了、被勒索病毒加密时，备份是唯一的退路。"), {"settings": "mac_backup"}))
    elif txt.strip():
        out.append(r("backup", "ok", tr("备份（Time Machine）"), tr("已配置备份"), ""))
    return out


def _linux():
    out = []
    _, txt, _ = core.run(["lsblk", "-o", "TYPE"])
    if txt.strip():
        out.append(r("luks", "ok", tr("磁盘加密"), tr("检测到加密卷"), "") if "crypt" in txt.split() else
                   r("luks", "info", tr("磁盘加密"), tr("没有检测到全盘加密（LUKS）"), tr("新装系统时建议启用磁盘加密；已安装的系统很难事后补加。")))
    if _port_open(22):
        cfg = ""
        for p in ["/etc/ssh/sshd_config"] + sorted(str(x) for x in __import__("pathlib").Path("/etc/ssh/sshd_config.d").glob("*.conf")) \
                if os.path.isdir("/etc/ssh") else []:
            try:
                cfg += open(p, errors="replace").read() + "\n"
            except OSError:
                pass
        if re.search(r"^\s*PermitRootLogin\s+yes", cfg, re.M | re.I):
            out.append(r("ssh_root", "crit", tr("SSH 服务"), tr("允许 root 直接登录"), tr("在 /etc/ssh/sshd_config 里把 PermitRootLogin 改成 no，然后重启 sshd。")))
        elif re.search(r"^\s*PasswordAuthentication\s+yes", cfg, re.M | re.I):
            out.append(r("ssh_pw", "info", tr("SSH 服务"), tr("允许用密码登录"), tr("改用密钥登录更安全：把 PasswordAuthentication 改成 no。")))
        else:
            out.append(r("ssh", "info", tr("SSH 服务"), tr("正在运行（端口 22）"), tr("不需要远程登录的话请停用它。")))
    if shutil.which("apt"):
        try:
            conf = open("/etc/apt/apt.conf.d/20auto-upgrades", errors="replace").read()
        except OSError:
            conf = ""
        if not re.search(r'Unattended-Upgrade\s+"1"', conf):
            out.append(r("unattended", "info", tr("自动安全更新"), tr("没有开启"), tr("开启后安全补丁会自动安装。复制命令，在终端里运行。"),
                         {"command": "sudo dpkg-reconfigure -plow unattended-upgrades"}))
    if shutil.which("gsettings") and os.environ.get("DISPLAY"):
        _, txt, _ = core.run(["gsettings", "get", "org.gnome.desktop.screensaver", "lock-enabled"])
        if txt.strip() == "false":
            out.append(r("screenlock", "warn", tr("屏幕锁"), tr("屏幕保护时不要求输入密码"), tr("建议开启：离开座位时别人无法直接使用。")))
    if shutil.which("mokutil"):
        _, txt, _ = core.run(["mokutil", "--sb-state"])
        if "disabled" in txt.lower():
            out.append(r("secureboot", "info", tr("安全启动（Secure Boot）"), tr("未开启"), tr("可在 BIOS/UEFI 里开启。")))
    return out


def check_all(deep=False):
    out = []
    try:
        out += _windows() if IS_WIN else _mac() if IS_MAC else _linux()
    except Exception as e:
        out.append(r("harden_err", "info", tr("安全加固"), tr("这一项没有检查完：{0}", e)))
    ports = risky_ports()
    if ports:
        out.append(r("risky_ports", "warn", tr("对外开放的高风险端口"), ", ".join(f"{p} ({n})" for p, n in sorted(ports.items())),
                     tr("这些服务对整个局域网/互联网开放。不需要就关闭对应的服务；要用请设置强密码。")))
    return out
