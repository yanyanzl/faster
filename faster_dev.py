# -*- coding: utf-8 -*-
"""
Faster · 开发者缓存清理（v0.5）

开发者的电脑上最大的“垃圾”往往不是系统缓存，而是各种包管理器 / 构建工具的缓存和旧项目里的依赖目录：
  * 包管理器与构建缓存：npm / Yarn / pnpm / pip / cargo / Go / Gradle / Maven / NuGet / Xcode / CocoaPods / Homebrew / Conda / JetBrains / VS Code / Docker
  * 长期没动的项目里的依赖目录：node_modules、Python 虚拟环境（venv）、Rust 的 target
这些东西都能再生（重新下载 / 重新构建），所以清理是安全的，只是下次用的时候会慢一些、需要联网。
缓存是永久删除；旧项目的依赖目录走回收站（可在“还原中心”还原）。钱包文件永远不碰。
"""
import os
import re
import time
import shutil
from pathlib import Path

import faster as core
import faster_crypto as fc
from faster_i18n import tr

IS_WIN, IS_MAC = core.IS_WIN, core.IS_MAC
HOME = core.HOME


def _env(name, default):
    return Path(os.environ[name]) if os.environ.get(name) else default


def cache_specs():
    """各工具的缓存目录（当前系统上可能存在的）：[dict(id, name, paths, note, cmd)]"""
    H = HOME
    local, roaming, lib = _env("LOCALAPPDATA", H / "AppData/Local"), _env("APPDATA", H / "AppData/Roaming"), H / "Library"

    def P(win, mac, linux):
        return win if IS_WIN else mac if IS_MAC else linux

    DL = tr("缓存，清理后会在需要时自动重新下载")
    BUILD = tr("构建缓存，清理后第一次构建会慢一些")
    DEP = tr("依赖缓存，清理后下次构建需要重新下载（要联网）")
    out = []

    def add(id_, name, paths, note, cmd=None):
        out.append(dict(id=id_, name=name, paths=[Path(p) for p in paths if p], note=note, cmd=cmd))

    add("npm", "npm", [P(local / "npm-cache", H / ".npm/_cacache", H / ".npm/_cacache")], DL)
    add("yarn", "Yarn", [P(local / "Yarn/Cache", lib / "Caches/Yarn", H / ".cache/yarn")], DL)
    add("pnpm", "pnpm", [P(local / "pnpm/store", lib / "pnpm/store", H / ".local/share/pnpm/store")], DEP)
    add("pip", "pip", [P(local / "pip/Cache", lib / "Caches/pip", H / ".cache/pip")], DL)
    add("cargo", "Rust (cargo)", [H / ".cargo/registry/cache", H / ".cargo/registry/src"], DEP)
    add("gobuild", "Go " + tr("构建缓存"), [P(local / "go-build", lib / "Caches/go-build", H / ".cache/go-build")], BUILD)
    add("gomod", "Go " + tr("模块缓存"), [H / "go/pkg/mod/cache"], DEP)
    add("gradle", "Gradle", [H / ".gradle/caches"], DEP)
    add("maven", "Maven", [H / ".m2/repository"], DEP)
    add("nuget", "NuGet", [H / ".nuget/packages"] + ([local / "NuGet/v3-cache"] if IS_WIN else []), DEP)
    if IS_MAC:
        add("xcode", "Xcode DerivedData", [lib / "Developer/Xcode/DerivedData"], tr("编译产物，Xcode 会自动重新生成"))
        add("xcode_dev", "Xcode iOS DeviceSupport", [lib / "Developer/Xcode/iOS DeviceSupport"], tr("调试用的设备支持文件，下次连接设备时会重新生成"))
        add("cocoapods", "CocoaPods", [lib / "Caches/CocoaPods"], DL)
    add("brew", "Homebrew", [P(None, lib / "Caches/Homebrew", H / ".cache/Homebrew")], DL)
    add("conda", "Conda", [H / d / "pkgs" for d in ("miniconda3", "anaconda3", "miniforge3", ".conda")], DL)
    add("jetbrains", "JetBrains IDE", [P(local / "JetBrains", lib / "Caches/JetBrains", H / ".cache/JetBrains")], BUILD)
    code = P(roaming / "Code", lib / "Application Support/Code", H / ".config/Code")
    add("vscode", "VS Code", [code / n for n in ("Cache", "CachedData", "Code Cache", "GPUCache", "CachedExtensionVSIXs")], DL)
    return out


def _parse_size(s):
    """'1.2GB' / '350kB' → 字节（Docker 用 1000 进制）"""
    m = re.match(r"\s*([\d.]+)\s*([kKMGT]?B)", s or "")
    if not m:
        return 0
    return int(float(m.group(1)) * {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}[m.group(2).upper()])


def docker_rows():
    """Docker 里可回收的空间（没装 Docker / 没启动就返回空）"""
    if not shutil.which("docker"):
        return []
    rc, out, _ = core.run(["docker", "system", "df", "--format", "{{.Type}}|{{.Size}}|{{.Reclaimable}}"], timeout=30)
    if rc != 0:
        return []
    rows = []
    for line in out.splitlines():
        parts = (line.split("|") + ["", "", ""])[:3]
        rec = _parse_size(parts[2].split("(")[0])
        if rec <= 0:
            continue
        if parts[0].strip() == "Build Cache":
            rows.append(dict(kind="docker", id="docker_build", name="Docker " + tr("构建缓存"), paths=[], size=rec,
                             note=tr("Docker 的构建缓存，清理后重新构建会慢一些"), cmd=["docker", "builder", "prune", "-f"]))
        elif parts[0].strip() == "Images":
            rows.append(dict(kind="docker", id="docker_images", name="Docker " + tr("未使用的镜像"), paths=[], size=rec,
                             note=tr("没有被任何容器使用的镜像，需要时会重新拉取"), cmd=["docker", "image", "prune", "-a", "-f"]))
    return rows


def scan_caches(task=None, max_seconds=40, with_docker=True):
    """扫描开发缓存，返回 [dict(kind, id, name, paths, size, note, cmd)]，大的在前"""
    rows, deadline = [], time.time() + max_seconds
    for spec in cache_specs():
        paths = [p for p in spec["paths"] if p.exists()]
        if not paths:
            continue
        if time.time() > deadline or (task is not None and not task.tick(spec["name"])):
            break
        size = sum(fc.dir_size(p, task) for p in paths)
        if size > 0:
            rows.append(dict(kind="cache", id=spec["id"], name=spec["name"], paths=[str(p) for p in paths], size=size,
                             note=spec["note"], cmd=spec["cmd"]))
    if with_docker and not (task is not None and task.cancelled):
        rows += docker_rows()
    rows.sort(key=lambda r: -r["size"])
    return rows


def _empty_children(path):
    freed = 0
    try:
        children = list(Path(path).iterdir())
    except OSError:
        return 0
    for c in children:
        if core.is_wallet_path(str(c)):
            continue
        try:
            size = core._size_of(c)
            shutil.rmtree(c) if c.is_dir() and not c.is_symlink() else c.unlink()
            freed += size
        except OSError:
            pass
    return freed


def clean(row):
    """清理一项缓存，返回释放的字节数。目录缓存：清空其中的内容（目录本身保留）；Docker：运行官方清理命令"""
    if row["kind"] == "docker":
        rc, out, _ = core.run(row["cmd"], timeout=900)
        m = re.search(r"reclaimed space:\s*([\d.]+\s*[kKMGT]?B)", out or "", re.I)
        return _parse_size(m.group(1)) if rc == 0 and m else 0
    return sum(_empty_children(p) for p in row["paths"])


# ---------------------------------------------------------------- 旧项目的依赖目录
def _dep_kind(files, d, full):
    if d == "node_modules" and "package.json" in files:
        return tr("Node.js 项目的依赖")
    if d == "target" and "Cargo.toml" in files:
        return tr("Rust 项目的编译产物")
    if d in (".venv", "venv", "env") and os.path.isfile(os.path.join(full, "pyvenv.cfg")):
        return tr("Python 虚拟环境")
    return None


def _last_touch(parent, dep):
    """项目最近一次被动过的时间：项目根目录里（不含依赖目录）最新的修改时间"""
    latest = 0.0
    try:
        with os.scandir(parent) as it:
            for n, e in enumerate(it):
                if e.name != dep:
                    latest = max(latest, e.stat(follow_symlinks=False).st_mtime)
                if n > 300:
                    break
    except OSError:
        pass
    return latest or os.stat(parent).st_mtime


def stale_projects(root=None, min_days=90, task=None, exclude=None, max_seconds=180):
    """找出超过 min_days 天没动过的项目里的依赖目录。返回 [dict(kind='project', name, path, size, days, note)]"""
    root, now = Path(root or HOME), time.time()
    deadline, rows = now + max_seconds, []
    for r, dirs, files in os.walk(root, onerror=lambda e: None):
        if time.time() > deadline or (task is not None and not task.tick(r)):
            break
        keep = []
        for d in dirs:
            full = os.path.join(r, d)
            if os.path.islink(full) or (exclude and exclude.skip_dir(full)):
                continue
            note = _dep_kind(files, d, full)
            if note:
                days = (now - _last_touch(r, d)) / 86400
                if days >= min_days:
                    rows.append(dict(kind="project", id="proj", name=f"{os.path.basename(r)}/{d}", path=full,
                                     size=fc.dir_size(full, task), days=int(days), note=note, paths=[full], cmd=None))
                continue                                    # 不再往依赖目录里面走
            if d.lower() in core.SKIP_DIR_NAMES or d.endswith(core.SKIP_DIR_SUFFIX):
                continue
            keep.append(d)
        dirs[:] = keep
    rows.sort(key=lambda r: -r["size"])
    return rows
