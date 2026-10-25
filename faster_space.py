# -*- coding: utf-8 -*-
"""
Faster · 磁盘空间分析（v0.5）

一次扫描，按“第一层子项”汇总大小，再用 squarified treemap（树图）排成一幅一眼看懂的“空间地图”：
面积越大，占的空间越多；点一块就能钻进去看里面。本模块只做数据和排版（不依赖界面），方便测试。
"""
import os
import time
import hashlib

import faster as core
from faster_i18n import tr

PALETTE = ("#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#2dd4bf", "#fb923c", "#f472b6", "#a3e635", "#38bdf8")


def scan_children(path, task=None, max_seconds=180):
    """返回 (子项列表, 总大小)。子项：dict(name, path, size, is_dir)，按大小从大到小；符号链接不跟进"""
    deadline, items = time.time() + max_seconds, []
    try:
        entries = list(os.scandir(path))
    except OSError:
        return [], 0
    for e in entries:
        if time.time() > deadline or (task is not None and not task.tick(e.path)):
            break
        try:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                size = core.dir_size(e.path, task)
                items.append(dict(name=e.name, path=e.path, size=size, is_dir=True))
            else:
                items.append(dict(name=e.name, path=e.path, size=e.stat(follow_symlinks=False).st_size, is_dir=False))
        except OSError:
            pass
    items = [i for i in items if i["size"] > 0]
    items.sort(key=lambda i: -i["size"])
    return items, sum(i["size"] for i in items)


def group_small(items, min_frac=0.012, max_tiles=40):
    """把占比太小的项合并成一块“其他 N 项”（path=None，不能点进去）"""
    total = sum(i["size"] for i in items) or 1
    big = [i for i in items if i["size"] / total >= min_frac][:max_tiles]
    rest = [i for i in items if i not in big]
    if rest:
        big.append(dict(name=tr("其他 {0} 项", len(rest)), path=None, size=sum(i["size"] for i in rest), is_dir=False))
    return big


def squarify(values, x, y, w, h):
    """Squarified treemap（Bruls 等）：values 为正数且从大到小 → 与之一一对应的矩形 [(x, y, w, h)]；总面积 = w*h"""
    values = [v for v in values if v > 0]
    total = sum(values)
    if not values or total <= 0 or w <= 0 or h <= 0:
        return []
    areas = [v * w * h / total for v in values]
    rects, i = [], 0

    def worst(row, side):
        s, mx, mn = sum(row), max(row), min(row)
        return max(side * side * mx / (s * s), (s * s) / (side * side * mn))

    while i < len(areas):
        side = min(w, h)
        row, j = [areas[i]], i + 1
        while j < len(areas) and worst(row + [areas[j]], side) <= worst(row, side):
            row.append(areas[j])
            j += 1
        s = sum(row)
        if w >= h:                                   # 在左边放一列
            cw, cy = s / h, y
            for a in row:
                ch = a / cw
                rects.append((x, cy, cw, ch))
                cy += ch
            x, w = x + cw, w - cw
        else:                                        # 在上边放一行
            rh, cx = s / w, x
            for a in row:
                cw2 = a / rh
                rects.append((cx, y, cw2, rh))
                cx += cw2
            y, h = y + rh, h - rh
        i = j
    return rects


def color_for(item):
    """给每一块一个稳定的颜色（同名同色）；文件用灰蓝，“其他”用浅灰"""
    if item["path"] is None:
        return "#d1d5db"
    if not item["is_dir"]:
        return "#94a3b8"
    return PALETTE[int(hashlib.md5(item["name"].encode("utf-8", "ignore")).hexdigest(), 16) % len(PALETTE)]
