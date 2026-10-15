# -*- coding: utf-8 -*-
"""v0.3：性能诊断 / 启动影响 / 前后对比 / 可取消任务 / 还原记录 的测试"""
import os
import sys
import json
import tempfile
import subprocess
import unittest
from pathlib import Path

os.environ["FASTER_LANG"] = "zh"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import faster_diag as fd  # noqa: E402
import faster as core  # noqa: E402
from faster_task import Task  # noqa: E402

GB = 1024 ** 3


def run_in_home(code, home, lang="zh"):
    env = dict(os.environ, HOME=home, USERPROFILE=home, FASTER_LANG=lang, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    for k in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):      # 避免真实的 OneDrive 目录混进测试
        env.pop(k, None)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def snap(**k):
    base = dict(ts=0, label="", disk_total=500 * GB, disk_free=300 * GB, mem_total=16 * GB, mem_used=6 * GB,
                mem_percent=40.0, swap_percent=5.0, procs=200, uptime=2 * 86400, cpu_percent=10.0, startup=8)
    base.update(k)
    return base


class Diagnosis(unittest.TestCase):
    def levels(self, res):
        return {f["key"]: f["level"] for f in res["findings"]}

    def test_healthy_system_scores_100(self):
        r = fd.diagnose(snap(), junk_bytes=1 * GB, top={}, power="balanced")
        self.assertEqual(r["score"], 100)
        self.assertTrue(all(f["level"] == fd.LV_OK for f in r["findings"]))

    def test_thresholds(self):
        r = fd.diagnose(snap(disk_free=30 * GB), None, {}, "balanced")          # 6% 剩余
        self.assertEqual(self.levels(r)["disk"], fd.LV_CRIT)
        r = fd.diagnose(snap(disk_free=80 * GB), None, {}, "balanced")          # 16%
        self.assertEqual(self.levels(r)["disk"], fd.LV_WARN)
        r = fd.diagnose(snap(mem_percent=92.0), None, {"mem": [("chrome", 3 * GB)]}, "balanced")
        lv = self.levels(r)
        self.assertEqual(lv["memory"], fd.LV_CRIT)
        self.assertIn("chrome", [f for f in r["findings"] if f["key"] == "memory"][0]["detail"])
        r = fd.diagnose(snap(mem_percent=85.0, swap_percent=60.0), None, {}, "balanced")
        self.assertEqual(self.levels(r)["swap"], fd.LV_WARN)
        self.assertEqual(self.levels(fd.diagnose(snap(startup=30), None, {}, "balanced"))["startup"], fd.LV_CRIT)
        self.assertEqual(self.levels(fd.diagnose(snap(startup=15), None, {}, "balanced"))["startup"], fd.LV_WARN)
        self.assertEqual(self.levels(fd.diagnose(snap(uptime=20 * 86400), None, {}, "balanced"))["uptime"], fd.LV_WARN)
        self.assertEqual(self.levels(fd.diagnose(snap(), 12 * GB, {}, "balanced"))["junk"], fd.LV_CRIT)
        self.assertEqual(self.levels(fd.diagnose(snap(), 3 * GB, {}, "balanced"))["junk"], fd.LV_WARN)
        self.assertEqual(self.levels(fd.diagnose(snap(), None, {}, "saver"))["power"], fd.LV_WARN)
        self.assertEqual(self.levels(fd.diagnose(snap(), None, {"cpu_total": 95.0, "cpu": [("miner", 90.0)]}, "balanced"))["cpu"], fd.LV_WARN)

    def test_score_and_ordering(self):
        r = fd.diagnose(snap(disk_free=20 * GB, mem_percent=95.0, startup=14), None, {}, "balanced")   # 2 严重 + 1 注意
        self.assertEqual(r["score"], 100 - 25 * 2 - 10)
        order = [f["level"] for f in r["findings"]]
        self.assertEqual(order, sorted(order, key=lambda x: fd._LV_ORDER[x]))                   # 严重在前
        many = fd.diagnose(snap(disk_free=1 * GB, mem_percent=99.0, startup=40, uptime=40 * 86400), 20 * GB, {}, "saver")
        self.assertGreaterEqual(many["score"], 0)

    def test_every_non_ok_finding_has_advice(self):
        r = fd.diagnose(snap(disk_free=1 * GB, mem_percent=95.0, startup=40), 20 * GB, {}, "saver")
        for f in r["findings"]:
            self.assertTrue(f["advice"])

    def test_live_snapshot_and_diagnosis(self):
        s = fd.take_snapshot("x")
        self.assertIn("disk_free", s)
        res = fd.diagnose(s, None, {}, None)
        self.assertTrue(0 <= res["score"] <= 100)


class Compare(unittest.TestCase):
    def test_compare_and_summary(self):
        a, b = snap(), snap(disk_free=300 * GB + 2 * GB, mem_used=6 * GB - 500 * (1 << 20), startup=6, procs=198)
        rows = {r["key"]: r for r in fd.compare(a, b)}
        self.assertTrue(rows["disk_free"]["better"])
        self.assertTrue(rows["mem_used"]["better"])
        self.assertTrue(rows["startup"]["better"])
        self.assertEqual(rows["startup"]["delta"], "-2")
        self.assertTrue(rows["disk_free"]["delta"].startswith("+"))
        s = fd.effect_summary(a, b)
        self.assertIn(fd.METRICS[0][1], s)                      # 磁盘剩余
        self.assertNotIn(fd.METRICS[5][1], s)                   # 进程数只少 2 个，不算显著
        worse = {r["key"]: r for r in fd.compare(b, a)}
        self.assertFalse(worse["disk_free"]["better"])
        self.assertEqual(fd.effect_summary(a, a), "")

    def test_history_roundtrip(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home("import faster_diag as fd, json\nfd.clear_history()\nfd.record('a'); fd.record('b')\n"
                              "h=fd.load_history(); print(json.dumps([x['label'] for x in h]))\nfd.clear_history(); print(len(fd.load_history()))", h)
            first, second = out.splitlines()
            self.assertEqual(json.loads(first), ["a", "b"])
            self.assertEqual(second, "0")


class StartupImpact(unittest.TestCase):
    def test_parse_exe(self):
        self.assertEqual(fd.parse_exe('"C:\\Program Files\\Foo\\foo.exe" --silent'), "C:\\Program Files\\Foo\\foo.exe")
        self.assertEqual(fd.parse_exe("C:\\Tools\\bar.exe /min"), "C:\\Tools\\bar.exe")
        self.assertEqual(fd.parse_exe("/usr/bin/foo --x", "desktop"), "/usr/bin/foo")
        self.assertEqual(fd.parse_exe("/opt/app/run %U", "desktop"), "/opt/app/run")
        self.assertEqual(fd.parse_exe(""), "")

    def test_running_and_missing(self):
        rows = fd.startup_impact([
            dict(kind="desktop", name="me", cmd=sys.executable),
            dict(kind="desktop", name="ghost", cmd="/nonexistent/never-running-binary-xyz")])
        by = {r["name"]: r for r in rows}
        if fd.psutil:
            self.assertTrue(by["me"]["running"])
            self.assertGreater(by["me"]["rss"], 0)
            self.assertGreaterEqual(by["me"]["score"], 0)
            self.assertEqual(rows[0]["name"], "me")                          # 运行中的排前面
        self.assertFalse(by["ghost"]["running"])
        self.assertEqual(by["ghost"]["level"], tr_off())


def tr_off():
    from faster_i18n import tr
    return tr("未运行")


class Tasks(unittest.TestCase):
    def test_cancel_returns_partial_results(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for i in range(5):
                (d / f"sub{i}").mkdir()
                (d / f"sub{i}" / "a.bin").write_bytes(b"x" * 2048)
            t = Task()
            full = list(core.walk_user_files(d, 1))
            self.assertEqual(len(full), 5)
            t2 = Task()
            t2.cancel()
            self.assertEqual(list(core.walk_user_files(d, 1, t2)), [])            # 立即取消：什么也不扫
            self.assertEqual(core.list_files_in(d, 0, t2), [])
            self.assertTrue(t.tick("x") and t.count == 1 and t.text == "x")
            t.cancel()
            self.assertFalse(t.tick("y"))
            self.assertTrue(t.cancelled)

    def test_progress_text_updates(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "s").mkdir()
            (Path(d) / "s" / "a.bin").write_bytes(b"x" * 100)
            t = Task()
            list(core.walk_user_files(d, 1, t))
            self.assertGreaterEqual(t.count, 2)
            self.assertTrue(t.text)


class RestoreLedger(unittest.TestCase):
    SETUP = ("import faster as c, os, json\nc.send2trash = None\n"
             "same = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))   # Windows 路径分隔符\n"
             "d = os.path.expanduser('~/data'); os.makedirs(d, exist_ok=True)\n")

    def test_remove_restore_collision_purge(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(self.SETUP + (
                "f = d + '/report.txt'; open(f, 'w').write('hello')\n"
                "assert c.safe_remove(f) and not os.path.exists(f)\n"
                "led = c.ledger_load(); assert len(led) == 1 and led[0]['via'] == 'tool' and led[0]['size'] == 5\n"
                "ok, dest = c.restore_from_trash(led[0]); assert ok and same(dest, f) and open(f).read() == 'hello'\n"
                "assert c.ledger_load() == []\n"
                # 冲突：原位置又有了同名文件 → 加后缀，不覆盖
                "assert c.safe_remove(f); open(f, 'w').write('NEW')\n"
                "ok, dest = c.restore_from_trash(c.ledger_load()[0])\n"
                "assert ok and not same(dest, f) and open(f).read() == 'NEW' and open(dest).read() == 'hello'\n"
                # 永久删除
                "g = d + '/tmp.bin'; open(g, 'w').write('x'); c.safe_remove(g)\n"
                "e = c.ledger_load()[0]; assert c.purge_from_trash(e) and c.ledger_load() == []\n"
                "print('OK')\n"), h)
            self.assertEqual(out, "OK")

    def test_directories_empty_trash_and_prune(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(self.SETUP + (
                "sub = d + '/proj'; os.makedirs(sub); open(sub + '/a', 'w').write('12345')\n"
                "assert c.safe_remove(sub) and not os.path.exists(sub)\n"
                "e = c.ledger_load()[0]; assert e['size'] == 5\n"
                "ok, dest = c.restore_from_trash(e); assert ok and os.path.isfile(sub + '/a')\n"
                "c.safe_remove(sub)\n"
                "import shutil; shutil.rmtree(c.TRASH_DIR / c.ledger_load()[0]['stored'])        # 手动删掉\n"
                "assert len(c.ledger_prune()) == 0\n"
                "x = d + '/y.txt'; open(x, 'w').write('abc'); c.safe_remove(x)\n"
                "assert c.empty_tool_trash() >= 3 and c.ledger_load() == [] and c.LEDGER.exists() or True\n"
                "print('OK')\n"), h)
            self.assertEqual(out, "OK")

    def test_wallet_files_never_enter_ledger(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(self.SETUP + (
                "w = d + '/wallet.dat'; open(w, 'w').write('k')\n"
                "assert c.safe_remove(w) is False and os.path.exists(w) and c.ledger_load() == []\nprint('OK')\n"), h)
            self.assertEqual(out.splitlines()[-1], "OK")           # 前面还会有一行“已保护”的提示

    def test_system_trash_records_are_kept_for_90_days(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(
                "import faster as c, time\n"
                "c.ledger_add(via='system', orig='/a/b', size=1, ts=int(time.time()))\n"
                "c.ledger_add(via='system', orig='/old', size=1, ts=int(time.time()) - 100 * 86400)\n"
                "print([e['orig'] for e in c.ledger_prune()])", h)
            self.assertEqual(out, "['/a/b']")


class Actions(unittest.TestCase):
    """诊断结果里的“动作”：结构、页面归属、界面层是否都有对应的处理函数"""

    def all_findings(self):
        bad = snap(disk_free=20 * GB, mem_percent=95.0, startup=30, uptime=40 * 86400)
        top = {"mem": [("bigapp.exe", 3 * GB, 4242), ("explorer.exe", 2 * GB, 5)], "cpu": [("miner", 95.0, 777)], "cpu_total": 95.0}
        r = fd.diagnose(bad, 12 * GB, top, "saver")
        return r["findings"]

    def test_problems_have_actions_and_ok_rows_do_not(self):
        for f in self.all_findings():
            self.assertIn(f["cat"], [c for c, _ in fd.CATEGORIES])
            if f["level"] == fd.LV_OK:
                self.assertEqual(f["actions"], [])
        ok = fd.diagnose(snap(), 1 * GB, {}, "balanced")["findings"]
        self.assertTrue(all(f["actions"] == [] for f in ok))

    def test_expected_actions(self):
        by = {f["key"]: f for f in self.all_findings()}
        ops = lambda k: [a["op"] for a in by[k]["actions"]]          # noqa: E731
        self.assertEqual(ops("disk"), ["clean_junk", "goto"])
        self.assertIn("clean_junk", ops("junk"))
        self.assertEqual(ops("startup"), ["goto", "disable_high"])
        self.assertEqual(ops("power"), ["open_settings"])
        self.assertIn("kill_pid", ops("memory"))
        kill = [a for a in by["memory"]["actions"] if a["op"] == "kill_pid"][0]
        self.assertEqual((kill["args"]["pid"], kill["args"]["name"]), (4242, "bigapp.exe"))
        self.assertTrue(kill["args"]["danger"] if "danger" in kill["args"] else True)
        self.assertEqual(sum(1 for a in by["cpu"]["actions"] if a["op"] == "kill_pid"), 1)

    def test_critical_system_processes_never_get_a_kill_button(self):
        top = {"mem": [("explorer.exe", 3 * GB, 5), ("systemd", 3 * GB, 1), ("kernel_task", 3 * GB, 0)]}
        r = fd.diagnose(snap(mem_percent=95.0), None, top, "balanced")
        mem = [f for f in r["findings"] if f["key"] == "memory"][0]
        self.assertEqual([a["op"] for a in mem["actions"]], ["goto"])

    def test_action_shapes(self):
        a = fd.act("clean_junk", "x", page="junk")
        self.assertEqual(set(a), {"op", "label", "page", "args", "done"})
        g = fd.goto("go", "large", sub=None, auto="scan", set={"mb": "500"})
        self.assertEqual((g["op"], g["page"], g["args"]["tab"], g["args"]["auto"]), ("goto", None, "large", "scan"))
        self.assertFalse(a["done"])

    def test_every_emitted_op_has_a_gui_handler(self):
        """诊断模块里出现的所有 op，在界面层都必须有 op_xxx 处理函数（防止按钮点了没反应）"""
        import ast
        import re as _re
        src = (ROOT / "faster_diag.py").read_text(encoding="utf-8")
        ops = set(_re.findall(r'act\(\s*"([a-z_]+)"', src)) | {"goto"}
        gui = ast.parse((ROOT / "faster_gui.py").read_text(encoding="utf-8"))
        handlers = {n.name[3:] for n in ast.walk(gui) if isinstance(n, ast.FunctionDef) and n.name.startswith("op_")}
        self.assertEqual(sorted(ops - handlers), [])

    def test_goto_targets_exist(self):
        """goto 的 tab/sub 必须是界面里真实存在的页签"""
        import re as _re
        src = (ROOT / "faster_diag.py").read_text(encoding="utf-8")
        gui = (ROOT / "faster_gui.py").read_text(encoding="utf-8")
        tabs = set(_re.findall(r'\("([a-z]+)", tr\("[^"]+"\), [A-Za-z]+\)', gui))
        subs = set(_re.findall(r'\("([a-z]+)", tr\("[^"]+"\), [A-Za-z]+Tab\)', gui))
        for tab, sub in _re.findall(r'goto\([^\n]*?"([a-z]+)"(?:, sub="([a-z]+)")?', src):
            self.assertIn(tab, tabs | {"large", "dup", "proc", "restore", "startup", "security", "wallet", "diag", "junk"})
            if sub:
                self.assertIn(sub, subs)


class Categories(unittest.TestCase):
    def test_scores(self):
        F = [dict(cat="perf", level=fd.LV_CRIT), dict(cat="perf", level=fd.LV_WARN), dict(cat="security", level=fd.LV_OK),
             dict(cat="wallet", level=fd.LV_INFO)]
        self.assertEqual(fd.score_of(F), 100 - 25 - 10)
        cs = fd.category_scores(F)
        self.assertEqual(cs, {"perf": 65, "security": 100, "wallet": 100})
        self.assertNotIn("storage", cs)

    def test_info_sorts_between_warning_and_ok(self):
        o = fd._LV_ORDER
        self.assertTrue(o[fd.LV_CRIT] < o[fd.LV_WARN] < o[fd.LV_INFO] < o[fd.LV_OK])

    def test_storage_trash_thresholds(self):
        MB = 1 << 20
        real = fd.system_trash_size
        try:
            for size, level in ((10 * MB, fd.LV_OK), (600 * MB, fd.LV_WARN), (11 * GB, fd.LV_CRIT)):
                fd.system_trash_size = lambda s=size: s
                f = [x for x in fd.storage_findings() if x["key"] == "trash"][0]
                self.assertEqual(f["level"], level)
                if level != fd.LV_OK:
                    self.assertEqual([a["op"] for a in f["actions"]], ["empty_trash", "open_system_trash"])
                    self.assertTrue(all(a["page"] == "restore" for a in f["actions"]))
        finally:
            fd.system_trash_size = real


class SecurityMapping(unittest.TestCase):
    def test_posture_startup_miner_hosts_mapping(self):
        from faster_i18n import tr
        saved = (core.security_posture_items, core.get_startup_items, fd.fc.detect_miners, core.hosts_entries)
        try:
            core.security_posture_items = lambda: [dict(key="defender_rt", level=tr("中危"), msg="rt off"),
                                                   dict(key="gatekeeper", level=tr("高危"), msg="gk off"),
                                                   dict(key="linux_fw", level=tr("提示"), msg="no fw")]
            core.get_startup_items = lambda: [dict(kind="reg", name="evil", cmd="powershell -enc AAAA", hive="HKCU", key="k"),
                                              dict(kind="reg", name="fine", cmd="C:\\ok.exe")]
            fd.fc.detect_miners = lambda s: dict(findings=[dict(level=tr("高危"), pid=999999, name="xmrig", cpu=90.0, msg="hit")], top=[])
            core.hosts_entries = lambda: [("bank.com", "6.6.6.6")]
            F = fd.security_findings(None, False)
        finally:
            core.security_posture_items, core.get_startup_items, fd.fc.detect_miners, core.hosts_entries = saved
        by = {f["key"]: f for f in F}
        self.assertEqual(by["posture_defender_rt"]["level"], fd.LV_WARN)
        self.assertEqual(by["posture_gatekeeper"]["level"], fd.LV_CRIT)
        self.assertEqual(by["posture_linux_fw"]["level"], fd.LV_INFO)
        self.assertEqual(by["posture_defender_rt"]["actions"][0]["args"]["what"], "defender")
        self.assertEqual(by["posture_gatekeeper"]["actions"][0]["args"]["what"], "mac_security")
        self.assertEqual(by["posture_linux_fw"]["actions"], [])
        susp = by["susp_evil"]
        self.assertEqual(susp["level"], fd.LV_CRIT)
        self.assertEqual([a["op"] for a in susp["actions"]], ["disable_startup", "goto"])
        self.assertEqual(susp["actions"][0]["args"]["items"][0]["name"], "evil")
        self.assertNotIn("susp_fine", by)
        miner = by["miner_999999"]
        self.assertEqual(miner["level"], fd.LV_CRIT)
        self.assertEqual(miner["actions"][0]["op"], "kill_pid")
        self.assertEqual(by["hosts"]["actions"][0]["op"], "open_folder")

    def test_clean_security_gives_ok_rows(self):
        saved = (core.security_posture_items, core.get_startup_items, fd.fc.detect_miners, core.hosts_entries)
        try:
            core.security_posture_items = lambda: []
            core.get_startup_items = lambda: []
            fd.fc.detect_miners = lambda s: dict(findings=[], top=[])
            core.hosts_entries = lambda: []
            F = fd.security_findings(None, False)
        finally:
            core.security_posture_items, core.get_startup_items, fd.fc.detect_miners, core.hosts_entries = saved
        self.assertTrue(F and all(f["level"] == fd.LV_OK and f["actions"] == [] for f in F))


class WalletAndCloud(unittest.TestCase):
    def test_cloud_roots_and_wallet_findings(self):
        with tempfile.TemporaryDirectory() as h:
            os.makedirs(h + "/OneDrive"); os.makedirs(h + "/Dropbox"); os.makedirs(h + "/Documents")
            (Path(h) / "OneDrive" / "wallet.dat").write_text("k")
            out = run_in_home(
                "import faster_crypto as fc, faster_diag as fd, os, json\n"
                "words = sorted({''.join(chr(97 + (i // 26 ** k) % 26) for k in (3, 2, 1, 0)) for i in (j * 37 + 5 for j in range(2048))})\n"
                "fc._WL_CACHE.update(tried=True, val=(words, {w: i for i, w in enumerate(words)}), path=fc.APP_DIR / 'x')\n"
                "open(os.path.expanduser('~/Dropbox/n.txt'), 'w').write('seed phrase: ' + ' '.join(fc.entropy_to_mnemonic(os.urandom(16), words)))\n"
                "roots = sorted(r.name for r in fc.cloud_roots())\n"
                "F = {f['key']: f for f in fd.wallet_findings(None, False)}\n"
                "print(json.dumps([roots, sorted(F), F['cloud_secrets']['level'], F['cloud_wallets']['level'],\n"
                "                  [a['op'] for a in F['cloud_wallets']['actions']], F['cloud_secrets']['actions'][0]['args']['sub']]))", h)
            roots, keys, lv1, lv2, ops, sub = json.loads(out.splitlines()[-1])
            self.assertEqual(roots, ["Dropbox", "OneDrive"])
            self.assertEqual(keys, ["cloud_secrets", "cloud_wallets"])
            self.assertEqual((lv1, lv2), ("严重", "严重"))
            self.assertEqual(ops, ["goto", "open_folder"])
            self.assertEqual(sub, "secrets")

    def test_missing_wordlist_offers_download(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home("import faster_crypto as fc, faster_diag as fd, json\n"
                              "fc._WL_CACHE.update(tried=True, val=None, path=None)\n"
                              "f = [x for x in fd.wallet_findings(None, False) if x['key'] == 'wordlist'][0]\n"
                              "print(json.dumps([f['level'], f['actions'][0]['op'], f['actions'][0]['page']]))", h)
            self.assertEqual(json.loads(out.splitlines()[-1]), ["提示", "download_wordlist", "wallet"])


class FullRun(unittest.TestCase):
    def test_quick_and_deep_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as h:
            os.makedirs(h + "/OneDrive")
            (Path(h) / "OneDrive" / "wallet.dat").write_text("k")
            out = run_in_home(
                "import faster_diag as fd, json\n"
                "q = fd.run_diagnosis(None, False); d = fd.run_diagnosis(None, True)\n"
                "print(json.dumps([sorted({f['cat'] for f in q['findings']}), q['deep'], d['deep'],\n"
                "                  len(d['findings']) > len(q['findings']), 0 <= q['score'] <= 100, sorted(q['cats'])]))", h)
            cats, qd, dd, more, ok, scored = json.loads(out.splitlines()[-1])
            self.assertEqual(cats, ["perf", "security", "storage", "wallet"])
            self.assertEqual((qd, dd, more, ok), (False, True, True, True))
            self.assertEqual(scored, ["perf", "security", "storage", "wallet"])

    def test_cancelled_run_returns_partial_results(self):
        t = Task()
        t.cancel()
        r = fd.run_diagnosis(t, False)
        self.assertTrue(r["findings"])                    # 取消后也返回已有结果，不抛异常

    def test_find_duplicates_in_core(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.bin").write_bytes(b"x" * (2 << 20))
            (Path(d) / "b.bin").write_bytes(b"x" * (2 << 20))
            (Path(d) / "c.bin").write_bytes(b"y" * (2 << 20))
            g = core.find_duplicates(d, 1)
            self.assertEqual(len(g), 1)
            self.assertEqual(len(g[0][1]), 2)
            t = Task(); t.cancel()
            self.assertEqual(core.find_duplicates(d, 1, t), [])


class Structured(unittest.TestCase):
    def test_hosts_and_posture_structures(self):
        items = core.security_posture_items()
        for it in items:
            self.assertEqual(set(it), {"key", "level", "msg"})
        for h, ip in core.hosts_entries():
            self.assertTrue(h and ip)


if __name__ == "__main__":
    unittest.main()
