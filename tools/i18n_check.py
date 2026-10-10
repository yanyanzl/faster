# -*- coding: utf-8 -*-
"""检查多语言完整性：python tools/i18n_check.py   （退出码非 0 表示有问题）

检查三件事：
  1. 源码里每个 tr("中文原文") 在各语言目录里都有译文
  2. 译文的占位符 {0}{1}... 与原文一致
  3. 没有“漏包”的中文字符串（面向用户的中文必须写成 tr(...)；正则、文档字符串除外）
"""
import ast
import re
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FILES = ["faster.py", "faster_gui.py", "faster_crypto.py"]
CJK = re.compile(r"[\u4e00-\u9fff]")
SYSTEM_MATCH = {"要运行的任务", "任务名"}          # 用来匹配中文 Windows 的系统输出，故意不翻译


def _fields(s):
    return sorted({(f[1].split(".")[0].split("[")[0]) for f in string.Formatter().parse(s) if f[1] is not None})


def collect_keys():
    keys = {}
    for f in FILES:
        for n in ast.walk(ast.parse((ROOT / f).read_text(encoding="utf-8"))):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "tr" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                keys.setdefault(n.args[0].value, f"{f}:{n.lineno}")
    return keys


def unwrapped_cjk():
    bad = []
    for f in FILES:
        tree = ast.parse((ROOT / f).read_text(encoding="utf-8"))
        pm = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}

        def anc(n):
            while n in pm:
                n = pm[n]
                yield n

        for n in ast.walk(tree):
            if not (isinstance(n, ast.Constant) and isinstance(n.value, str) and CJK.search(n.value)):
                continue
            p = pm.get(n)
            if isinstance(p, (ast.Expr, ast.JoinedStr)) or n.value in SYSTEM_MATCH:
                continue
            if isinstance(p, ast.Call) and getattr(p.func, "id", None) == "tr" and p.args and n is p.args[0]:
                continue
            if any(isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and getattr(a.func.value, "id", "") == "re"
                   for a in anc(n)):
                continue
            bad.append(f"{f}:{n.lineno}  {n.value[:40]!r}")
    return bad


def check():
    import faster_i18n as i18n
    problems, keys = [], collect_keys()
    for lang, cat in i18n._CATALOGS.items():
        for k, where in keys.items():
            if k not in cat:
                problems.append(f"[{lang}] 缺少译文：{k[:50]!r}  ({where})")
            elif _fields(k) != _fields(cat[k]):
                problems.append(f"[{lang}] 占位符不一致：{k[:50]!r}")
        for k in cat:
            if k not in keys:
                problems.append(f"[{lang}] 多余译文（源码里已不存在）：{k[:50]!r}")
    problems += [f"漏包的中文字符串：{x}" for x in unwrapped_cjk()]
    return problems


if __name__ == "__main__":
    ps = check()
    print("\n".join(ps) if ps else "i18n 检查通过")
    sys.exit(1 if ps else 0)
