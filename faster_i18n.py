# -*- coding: utf-8 -*-
"""
Faster 多语言支持（i18n）

用法：代码里所有面向用户的文字都写成  tr("中文原文 {0}", 参数)
  * 中文界面：原样输出；其它语言：到 faster_i18n_<语言>.py 的 CATALOG 里按“中文原文”查译文，查不到就退回中文
  * 新增一种语言：1) 新建 faster_i18n_xx.py，写一个 CATALOG = {中文原文: 译文}（占位符 {0}{1} 必须一致）
                  2) 在本文件的 _CATALOGS / LANGUAGES 里各加一行  3) 运行 python -m unittest discover -s tests
  * 缺哪些译文：python tools/i18n_check.py

语言选择顺序：命令行 --lang xx  >  环境变量 FASTER_LANG  >  设置文件 ~/.faster/settings.json  >  系统语言
改变语言后需要重启程序才完全生效（界面里有“立即重启”）。
"""
import os
import sys
import json
from pathlib import Path

from faster_i18n_en import CATALOG as _EN

LANGUAGES = {"zh": "简体中文", "en": "English"}        # 语言代码 -> 该语言自己的名字（不翻译）
_CATALOGS = {"en": _EN}                                # zh 是源语言，不需要目录
SETTINGS = Path.home() / ".faster" / "settings.json"


def system_language():
    """根据系统界面语言猜：中文系统 → zh，其它 → en"""
    cands = [os.environ.get(v, "") for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")]
    try:
        if sys.platform.startswith("win"):
            import ctypes
            import locale
            cands.append(locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), ""))
        elif sys.platform == "darwin":
            import subprocess
            cands.append(subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True,
                                        text=True, timeout=2).stdout)
    except Exception:
        pass
    for c in cands:
        if "zh" in c.lower():
            return "zh"
    return "en"


def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def saved_language():
    """设置文件里保存的选择：'zh' / 'en' / 'auto'（跟随系统）"""
    v = load_settings().get("language", "auto")
    return v if v in LANGUAGES or v == "auto" else "auto"


def save_language(code):
    """保存语言选择（'auto' 表示跟随系统）；下次启动生效"""
    if code != "auto" and code not in LANGUAGES:
        raise ValueError(code)
    st = load_settings()
    st["language"] = code
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve():
    argv = sys.argv
    cand = argv[argv.index("--lang") + 1] if "--lang" in argv and argv.index("--lang") + 1 < len(argv) else None
    cand = cand or os.environ.get("FASTER_LANG") or saved_language()
    if cand == "auto" or cand not in LANGUAGES:
        cand = system_language()
    return cand


LANG = _resolve()
_CAT = _CATALOGS.get(LANG, {})


def get_language():
    return LANG


def tr(key, *args):
    """翻译。key 是中文原文（可含 {0}{1} 占位符）；args 是占位符参数。"""
    s = _CAT.get(key, key)
    if not args:
        return s
    try:
        return s.format(*args)
    except (IndexError, KeyError, ValueError):
        try:
            return key.format(*args)
        except Exception:
            return s
