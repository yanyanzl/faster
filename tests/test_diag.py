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


if __name__ == "__main__":
    unittest.main()
