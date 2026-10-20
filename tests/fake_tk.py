# -*- coding: utf-8 -*-
"""假 tkinter：不画任何界面，只让 faster_gui 的代码能跑起来，并记录所有传给控件/弹窗的文字。
用法：import fake_tk; fake_tk.install()  然后 import faster_gui。（CI 里没有显示器，用它做界面冒烟测试）"""
import sys
import types

SEEN, MESSAGES = [], []
_METHODS = set("""config configure pack pack_forget grid bind bind_all unbind_all heading column insert delete get_children
selection selection_set yview yview_moveto yview_scroll winfo_children destroy after title geometry minsize mainloop current
set get start stop create_window itemconfig bbox columnconfigure rowconfigure add select tag_configure clipboard_get
clipboard_clear clipboard_append bell state cget focus_set curselection theme_use see tag_bind invoke update_idletasks
option_add map lookup create_arc create_oval create_text create_rectangle coords itemconfigure tag_raise
withdraw protocol resizable lift focus_force grid_forget place selection_clear xview winfo_width item exists""".split())


def _rec(args, kw):
    for v in list(args) + list(kw.values()):
        if isinstance(v, str):
            SEEN.append(v)
        elif isinstance(v, (list, tuple)):
            SEEN.extend(x for x in v if isinstance(x, str))


class W:
    def __init__(self, *a, **k):
        _rec(a, k)

    def __getattr__(self, name):                    # 只有真实 Tk 方法才返回“记录器”，其余像真实对象一样 AttributeError
        if name not in _METHODS:
            raise AttributeError(name)

        def f(*a, **k):
            _rec(a, k)
            return W()
        return f

    def __iter__(self):
        return iter([])

    def __setitem__(self, k, v):
        pass

    def __getitem__(self, k):
        return None


class Var:
    def __init__(self, value=""):
        self.v = value

    def get(self):
        return self.v

    def set(self, v):
        self.v = v


def install(ask=True):
    """安装假的 tkinter 系列模块。ask：所有“是/否”确认框的回答"""
    tk, ttk = types.ModuleType("tkinter"), types.ModuleType("tkinter.ttk")
    for n in ("Tk", "Toplevel", "Listbox", "Frame", "Canvas", "Label"):
        setattr(tk, n, W)
    tk.StringVar = tk.BooleanVar = Var
    tk.TclError = Exception
    tk.ttk = ttk
    for n in ("Frame", "Label", "Button", "Entry", "Spinbox", "Combobox", "Notebook", "Treeview", "Scrollbar", "Progressbar",
              "Checkbutton", "Radiobutton", "LabelFrame", "Style"):
        setattr(ttk, n, W)
    font = types.ModuleType("tkinter.font")
    font.nametofont = lambda name: W()
    tk.font = font
    mb = types.ModuleType("tkinter.messagebox")
    for n in ("showinfo", "showwarning", "showerror"):
        setattr(mb, n, lambda *a, _n=n, **k: (_rec(a, k), MESSAGES.append((_n, a))))
    mb.askyesno = lambda *a, **k: (_rec(a, k), ask)[1]
    mb.askyesnocancel = lambda *a, **k: (_rec(a, k), ask)[1]
    fd, sd, st = (types.ModuleType("tkinter." + n) for n in ("filedialog", "simpledialog", "scrolledtext"))
    fd.askdirectory = lambda **k: ""
    sd.askinteger = lambda *a, **k: 30
    st.ScrolledText = W
    tk.messagebox, tk.filedialog, tk.simpledialog, tk.scrolledtext = mb, fd, sd, st
    for name, m in (("tkinter", tk), ("tkinter.ttk", ttk), ("tkinter.messagebox", mb), ("tkinter.filedialog", fd),
                    ("tkinter.simpledialog", sd), ("tkinter.scrolledtext", st), ("tkinter.font", font)):
        sys.modules[name] = m
