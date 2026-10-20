# -*- coding: utf-8 -*-
"""
Faster · 外观（v0.4）：统一的配色、字体和控件样式。

设计原则：只“增强”，不依赖——任何一步失败（主题不存在、系统不支持某个样式选项……）都静默跳过，
最坏的情况是退回 tkinter 的默认外观，程序照常可用。macOS 保持原生（aqua）主题，只调整字体和卡片颜色。
"""
import sys

PALETTE = dict(
    bg="#f4f6fb",          # 窗口背景
    card="#ffffff",        # 卡片背景
    text="#1f2937",
    muted="#6b7280",
    line="#e5e7eb",        # 分隔线 / 卡片边框
    stripe="#f8fafc",      # 表格斑马纹
    header="#1e3a8a",      # 顶部横幅
    primary="#2563eb", primary_dark="#1d4ed8",
    ok="#16a34a", warn="#d97706", crit="#dc2626", info="#2563eb",
)
LEVEL_COLOR = {"crit": PALETTE["crit"], "warn": PALETTE["warn"], "info": PALETTE["info"], "ok": PALETTE["ok"]}


def score_color(score):
    return PALETTE["ok"] if score >= 80 else PALETTE["warn"] if score >= 55 else PALETTE["crit"]


def font_family():
    return {"win32": "Segoe UI"}.get(sys.platform, "" if sys.platform == "darwin" else "Noto Sans")


def apply(root):
    """给整个程序套上主题。返回 True 表示至少主题本身设置成功"""
    try:
        import tkinter as tk
        from tkinter import ttk, font as tkfont
    except Exception:
        return False
    P, native = PALETTE, sys.platform == "darwin"
    style = ttk.Style(root)

    def cfg(name, **kw):
        try:
            style.configure(name, **kw)
        except Exception:
            pass

    def mp(name, **kw):
        try:
            style.map(name, **kw)
        except Exception:
            pass

    ok = True
    if not native:
        try:
            style.theme_use("clam")
        except Exception:
            ok = False
    fam = font_family()
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            f = tkfont.nametofont(name)
            if fam and name != "TkFixedFont":
                f.configure(family=fam)
            f.configure(size=10 if not native else 12)
        except Exception:
            pass
    try:
        root.configure(background=P["bg"])
        root.option_add("*Listbox.background", "#ffffff")
        root.option_add("*Listbox.relief", "flat")
        root.option_add("*Listbox.highlightThickness", 1)
        root.option_add("*Listbox.highlightColor", P["line"])
    except Exception:
        pass
    if native:                                    # macOS：保持原生控件，不覆盖颜色
        cfg("Treeview", rowheight=26)
        return ok
    cfg(".", background=P["bg"], foreground=P["text"], bordercolor=P["line"], focuscolor=P["primary"])
    cfg("TFrame", background=P["bg"])
    cfg("TLabel", background=P["bg"], foreground=P["text"])
    cfg("Muted.TLabel", foreground=P["muted"])
    cfg("TLabelframe", background=P["bg"], bordercolor=P["line"], relief="solid", borderwidth=1)
    cfg("TLabelframe.Label", background=P["bg"], foreground=P["muted"])
    cfg("TCheckbutton", background=P["bg"])
    cfg("TRadiobutton", background=P["bg"])
    cfg("TButton", padding=(12, 6), background="#ffffff", foreground=P["text"], bordercolor=P["line"], relief="solid", borderwidth=1)
    mp("TButton", background=[("active", "#eef2ff"), ("pressed", "#e0e7ff"), ("disabled", "#f3f4f6")],
       foreground=[("disabled", "#9ca3af")])
    cfg("Accent.TButton", padding=(16, 8), background=P["primary"], foreground="#ffffff", bordercolor=P["primary"], borderwidth=1)
    mp("Accent.TButton", background=[("active", P["primary_dark"]), ("pressed", P["primary_dark"]), ("disabled", "#93c5fd")],
       foreground=[("disabled", "#ffffff")], bordercolor=[("active", P["primary_dark"])])
    cfg("Danger.TButton", padding=(12, 6), background=P["crit"], foreground="#ffffff", bordercolor=P["crit"], borderwidth=1)
    mp("Danger.TButton", background=[("active", "#b91c1c"), ("pressed", "#b91c1c")])
    cfg("TNotebook", background=P["bg"], borderwidth=0, tabmargins=(10, 8, 10, 0))
    cfg("TNotebook.Tab", padding=(14, 8), background="#e3e8f2", foreground=P["muted"], borderwidth=0)
    mp("TNotebook.Tab", background=[("selected", P["card"]), ("active", "#eef2ff")],
       foreground=[("selected", P["primary"])], expand=[("selected", (0, 0, 0, 2))])
    cfg("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=P["text"], rowheight=28,
        bordercolor=P["line"], borderwidth=1)
    cfg("Treeview.Heading", background="#eef2f7", foreground=P["text"], padding=(8, 7), relief="flat",
        font=(fam or "TkDefaultFont", 10, "bold") if fam else None)
    mp("Treeview", background=[("selected", P["primary"])], foreground=[("selected", "#ffffff")])
    mp("Treeview.Heading", background=[("active", "#e2e8f0")])
    cfg("Horizontal.TProgressbar", troughcolor="#e5e7eb", background=P["primary"], bordercolor="#e5e7eb", thickness=10)
    cfg("TEntry", fieldbackground="#ffffff", padding=4)
    cfg("TCombobox", fieldbackground="#ffffff", padding=4)
    cfg("TSpinbox", fieldbackground="#ffffff", padding=4)
    cfg("Vertical.TScrollbar", background="#d1d5db", troughcolor=P["bg"], bordercolor=P["bg"], arrowcolor=P["muted"])
    return ok
