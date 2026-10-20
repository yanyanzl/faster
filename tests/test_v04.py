# -*- coding: utf-8 -*-
"""v0.4：排除设置 / 程序签名 / 基线对比 / 补丁与更新 / 安全加固 / 系统设置命令 / 外观 的测试"""
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
import faster as core  # noqa: E402
import faster_sig as sig  # noqa: E402
import faster_baseline as bl  # noqa: E402
import faster_patch as patch  # noqa: E402
import faster_harden as harden  # noqa: E402
import faster_diag as fd  # noqa: E402
import faster_theme as theme  # noqa: E402
from faster_task import Task  # noqa: E402


def run_in_home(code, home):
    env = dict(os.environ, HOME=home, USERPROFILE=home, FASTER_LANG="zh", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), env=env, timeout=90)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class Exclusions(unittest.TestCase):
    def make_tree(self, d):
        d = Path(d)
        for p in ("v/a.mp4", "v/b.MKV", "pics/c.jpg", "docs/d.bin", "skipme/e.bin", "skipme/deep/f.bin", "g.psd"):
            (d / p).parent.mkdir(parents=True, exist_ok=True)
            (d / p).write_bytes(b"x" * 2048)
        return d

    def names(self, d, ex):
        return sorted(os.path.relpath(fp, d).replace("\\", "/") for fp, _, _ in core.walk_user_files(d, 1, None, ex))

    def test_file_groups_and_extra_extensions(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.make_tree(t)
            self.assertEqual(len(self.names(d, None)), 7)
            self.assertEqual(self.names(d, core.Exclusions(["video", "image"])), ["docs/d.bin", "skipme/deep/f.bin", "skipme/e.bin"])
            self.assertEqual(self.names(d, core.Exclusions([], [".BIN", "psd"])), ["pics/c.jpg", "v/a.mp4", "v/b.MKV"])

    def test_excluded_folders_cover_subfolders(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.make_tree(t)
            ex = core.Exclusions([], [], [str(d / "skipme")])
            self.assertNotIn("skipme/e.bin", self.names(d, ex))
            self.assertNotIn("skipme/deep/f.bin", self.names(d, ex))
            self.assertEqual(len(self.names(d, ex)), 5)
            self.assertEqual(self.names(d, core.Exclusions([], [], [str(d)])), [])        # 把根目录本身排除 → 什么都不扫
            (d / "skipme2").mkdir(); (d / "skipme2" / "x.bin").write_bytes(b"x" * 2048)
            self.assertIn("skipme2/x.bin", self.names(d, ex))                                # 前缀相同的兄弟目录不受影响

    def test_exclusions_apply_to_duplicates_and_truthiness(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for n in ("a.mp4", "b.mp4", "c.txt", "d.txt"):
                (d / n).write_bytes(b"same" * (1 << 20))
            self.assertEqual(len(core.find_duplicates(d, 1)), 1)           # mp4 和 txt 内容相同 → 1 组（4 个文件）
            g = core.find_duplicates(d, 1, None, core.Exclusions(["video"]))
            self.assertEqual([len(x[1]) for x in g], [2])
            self.assertFalse(core.Exclusions())
            self.assertTrue(core.Exclusions(["video"]))

    def test_summary_text(self):
        ex = core.Exclusions(["video"], [".psd"], ["/a", "/b"])
        s = ex.summary()
        self.assertIn(core.FILE_GROUPS["video"][0], s)
        self.assertIn(".psd", s)
        self.assertIn("2", s)
        self.assertEqual(core.Exclusions().summary(), "")

    def test_settings_persist_per_page(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(
                "import faster as c, json\n"
                "c.exclusion_save('large', dict(groups=['video'], exts=['.psd'], folders=['/x']))\n"
                "c.exclusion_save('dup', dict(groups=['image'], exts=[], folders=[]))\n"
                "c.settings_update(other=1)\n"
                "print(json.dumps([c.exclusion_config('large'), c.exclusion_config('dup'), c.exclusion_config('none'),\n"
                "                  sorted(c.exclusions_for('large').exts)[:2], c.settings_load()['other']]))", h)
            large, dup, none, exts, other = json.loads(out.splitlines()[-1])
            self.assertEqual(large["groups"], ["video"])
            self.assertEqual(dup["groups"], ["image"])
            self.assertEqual(none, {})
            self.assertIn(".avi", exts)
            self.assertEqual(other, 1)                    # 保存排除设置不能冲掉别的设置（比如语言）

    def test_language_setting_survives_exclusion_save(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home("import faster_i18n as i, faster as c\ni.save_language('en')\n"
                              "c.exclusion_save('large', dict(groups=['video']))\nprint(i.saved_language())", h)
            self.assertEqual(out.splitlines()[-1], "en")

    def test_diagnosis_deep_scan_respects_saved_exclusions(self):
        with tempfile.TemporaryDirectory() as h:
            Path(h, "movies").mkdir()
            Path(h, "movies", "big.mp4").write_bytes(b"0" * 1024)
            out = run_in_home(
                "import faster as c, faster_diag as fd\nimport faster_diag\n"
                "c.exclusion_save('large', dict(groups=['video']))\n"
                "c.exclusion_save('dup', dict(groups=['image']))\n"
                "MB = 1 << 20\n"
                "seen = []\n"
                "orig = c.walk_user_files\n"
                "def spy(root, min_size, task=None, exclude=None): seen.append(bool(exclude)); return orig(root, min_size, task, exclude)\n"
                "c.walk_user_files = spy\n"
                "fd.storage_findings(None, True)\nprint(seen)", h)
            self.assertEqual(out.splitlines()[-1], "[True, True]")          # 大文件、重复文件各自带着自己页面里保存的排除设置


class Signatures(unittest.TestCase):
    def test_parse_exe(self):
        self.assertEqual(sig.parse_exe('"C:\\Program Files\\Foo\\foo.exe" --silent'), "C:\\Program Files\\Foo\\foo.exe")
        self.assertEqual(sig.parse_exe("/usr/bin/foo --x", "desktop"), "/usr/bin/foo")
        self.assertEqual(sig.parse_exe(""), "")

    def test_user_dir_and_temp_detection(self):
        self.assertTrue(sig.in_user_dir(str(Path.home() / "Downloads" / "x.exe")))
        self.assertFalse(sig.in_user_dir("/usr/bin/python3") if os.name != "nt" else sig.in_user_dir(os.environ["WINDIR"] + "\\notepad.exe"))
        self.assertTrue(sig.in_temp_or_downloads("C:\\Users\\a\\AppData\\Local\\Temp\\x.exe"))
        self.assertTrue(sig.in_temp_or_downloads("/tmp/evil"))
        self.assertTrue(sig.in_temp_or_downloads("/home/a/Downloads/setup"))
        self.assertFalse(sig.in_temp_or_downloads("/opt/app/bin"))

    def test_risk_rules(self):
        base = dict(kind="startup", user_dir=True, temp=False, path="x")
        self.assertEqual(sig.risk_of(dict(base, status="invalid")), "crit")
        self.assertEqual(sig.risk_of(dict(base, status="unsigned")), "warn")                       # 无签名的启动项
        self.assertEqual(sig.risk_of(dict(base, status="valid")), "ok")
        self.assertEqual(sig.risk_of(dict(base, status="missing")), "info")
        proc = dict(kind="process", user_dir=True, temp=False, path="x")
        self.assertEqual(sig.risk_of(dict(proc, status="unsigned")), "info")
        self.assertEqual(sig.risk_of(dict(proc, status="unsigned", temp=True)), "crit")            # 从临时目录运行的无签名进程
        self.assertEqual(sig.risk_of(dict(proc, status="unsigned", user_dir=False)), "ok")
        self.assertEqual(sig.risk_of(dict(proc, status="unknown")), "ok")

    def test_windows_status_mapping(self):
        self.assertEqual(sig._map_win("Valid"), "valid")
        self.assertEqual(sig._map_win("NotSigned"), "unsigned")
        self.assertEqual(sig._map_win("HashMismatch"), "invalid")
        self.assertEqual(sig._map_win("NotTrusted"), "invalid")
        self.assertEqual(sig._map_win("NotSupportedFileFormat"), "unknown")
        self.assertEqual(sig._map_win("UnknownError"), "missing")

    def test_missing_files_and_verify_never_raises(self):
        r = sig.verify(["/definitely/not/here.exe", "/definitely/not/here.exe"])
        self.assertEqual(r, {"/definitely/not/here.exe": dict(status="missing", signer="")})
        self.assertEqual(sig.verify([]), {})

    def test_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"abc")
        try:
            self.assertEqual(sig.sha256_file(f.name), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            self.assertEqual(sig.sha256_file(f.name, limit=1), "")
        finally:
            os.unlink(f.name)
        self.assertEqual(sig.sha256_file("/no/such/file"), "")

    def test_scan_with_mocked_verifier_orders_by_risk(self):
        real_cands, real_verify = sig.candidates, sig.verify
        try:
            sig.candidates = lambda deep=False: [
                dict(kind="startup", name="ok1", path="/opt/ok1", item={}, pid=None),
                dict(kind="startup", name="bad", path="/home/u/bad", item={}, pid=None),
                dict(kind="process", name="tmp", path="/tmp/x", item=None, pid=7),
                dict(kind="startup", name="broken", path="/home/u/broken", item={}, pid=None)]
            sig.verify = lambda paths: {"/opt/ok1": dict(status="valid", signer="Acme"), "/home/u/bad": dict(status="unsigned", signer=""),
                                        "/tmp/x": dict(status="unsigned", signer=""), "/home/u/broken": dict(status="invalid", signer="")}
            rows = sig.scan(Task(), False)
        finally:
            sig.candidates, sig.verify = real_cands, real_verify
        self.assertEqual([(r["name"], r["risk"]) for r in rows], [("broken", "crit"), ("tmp", "crit"), ("bad", "warn"), ("ok1", "ok")])

    def test_live_candidates_do_not_crash(self):
        rows = sig.candidates(False)
        self.assertIsInstance(rows, list)


class Baseline(unittest.TestCase):
    def test_diff(self):
        old = dict(startup=["a", "b"], ports=["80|nginx"], admins=["root"])
        new = dict(startup=["b", "c"], ports=["80|nginx"], admins=["root", "mallory"], programs=["x"])
        d = bl.diff(old, new)
        self.assertEqual(d["startup"], dict(added=["c"], removed=["a"]))
        self.assertEqual(d["admins"], dict(added=["mallory"], removed=[]))
        self.assertEqual(d["programs"], dict(added=["x"], removed=[]))
        self.assertNotIn("ports", d)
        self.assertEqual(bl.diff(new, new), {})

    def test_save_load_compare_roundtrip(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(
                "import faster_baseline as b, json\n"
                "assert b.load() is None and b.compare() is None\n"
                "d = b.save({'startup': ['x|a|cmd'], 'admins': ['root']})\n"
                "assert b.load()['items']['admins'] == ['root']\n"
                "orig = b.collect\n"
                "b.collect = lambda: {'startup': ['x|a|cmd', 'x|evil|curl'], 'admins': ['root', 'eve'], 'ports': ['4444|nc']}\n"
                "res = b.compare()\n"
                "print(json.dumps([sorted(res['diff']), res['diff']['admins']['added'], b.pretty('startup', 'x|evil|curl'), b.pretty('ports', '4444|nc')]))", h)
            cats, added, p1, p2 = json.loads(out.splitlines()[-1])
            self.assertEqual(cats, ["admins", "ports", "startup"])
            self.assertEqual(added, ["eve"])
            self.assertEqual(p1, "evil: curl")
            self.assertEqual(p2, "4444 (nc)")

    def test_collect_never_raises_and_has_all_categories(self):
        c = bl.collect()
        self.assertEqual(sorted(c), sorted(k for k, _ in bl.CATS))
        self.assertTrue(all(isinstance(v, list) for v in c.values()))

    def test_baseline_findings_levels_and_actions(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(
                "import faster_baseline as b, faster_diag as fd, faster as core, json\n"
                "none = fd.baseline_findings()\n"
                "b.save({'startup': [], 'tasks': [], 'ports': [], 'hosts': [], 'admins': ['root'], 'ssh_keys': [], 'programs': []})\n"
                "b.collect = lambda: {'startup': ['desktop|evil|sh -c x'], 'tasks': ['cron|* * * * * x'], 'ports': ['1|a','2|b','3|c','4|d'],\n"
                "                     'hosts': [], 'admins': ['root', 'eve'], 'ssh_keys': ['abc|me'], 'programs': ['NewApp']}\n"
                "core.get_startup_items = lambda: [dict(kind='desktop', name='evil', cmd='sh -c x')]\n"
                "F = {f['key']: f for f in fd.baseline_findings()}\n"
                "print(json.dumps([none[0]['key'], none[0]['level'], [a['op'] for a in none[0]['actions']],\n"
                "   {k: v['level'] for k, v in F.items()}, [a['op'] for a in F['baseline_startup']['actions']], [a['op'] for a in F['baseline_admins']['actions']]]))", h)
            key, lv, ops, levels, startup_ops, admin_ops = json.loads(out.splitlines()[-1])
            self.assertEqual((key, lv), ("baseline_none", "提示"))
            self.assertEqual(ops, ["set_baseline", "goto"])
            self.assertEqual(levels, {"baseline_startup": "注意", "baseline_tasks": "注意", "baseline_ports": "注意",
                                      "baseline_admins": "严重", "baseline_ssh_keys": "严重", "baseline_programs": "提示"})
            self.assertEqual(startup_ops, ["disable_startup", "accept_baseline", "goto"])
            self.assertEqual(admin_ops, ["accept_baseline", "goto"])


class PatchAndHarden(unittest.TestCase):
    def test_result_shape(self):
        for x in patch.check(False) + harden.check_all(False):
            self.assertEqual(set(x), {"key", "level", "title", "detail", "advice", "fix"})
            self.assertIn(x["level"], ("crit", "warn", "info", "ok"))
            if x["fix"]:
                self.assertTrue(set(x["fix"]) <= {"settings", "command"})

    def test_eol_regex(self):
        for n in ("Adobe Flash Player 32 NPAPI", "QuickTime 7", "Microsoft Silverlight", "Python 2.7.18", "Java 7 Update 80",
                  "Java(TM) SE Runtime Environment 6"):
            self.assertTrue(patch.EOL_RE.search(n), n)
        for n in ("Python 3.12.1", "Java 17", "Adobe Acrobat", "Visual Studio Code"):
            self.assertFalse(patch.EOL_RE.search(n), n)

    def test_apt_levels_with_mocks(self):
        saved = (patch.IS_WIN, patch.IS_MAC, patch.apt_upgradable, patch.apt_index_age_days, patch.eol_software, os.path.exists)
        try:
            patch.IS_WIN = patch.IS_MAC = False
            patch.eol_software = lambda: []
            patch.apt_index_age_days = lambda: 30
            for upg, level in (((0, 0), "ok"), ((5, 0), "warn"), ((9, 2), "crit")):
                patch.apt_upgradable = lambda u=upg: u
                items = {x["key"]: x for x in patch.check(False)}
                self.assertEqual(items["apt"]["level"], level)
                self.assertEqual(items["apt_index"]["level"], "info")
                if level != "ok":
                    self.assertEqual(items["apt"]["fix"]["command"], "sudo apt update && sudo apt upgrade")
        finally:
            patch.IS_WIN, patch.IS_MAC, patch.apt_upgradable, patch.apt_index_age_days, patch.eol_software = saved[:5]

    def test_windows_hotfix_age_levels(self):
        saved = (patch.IS_WIN, patch.win_last_hotfix_days, patch.win_reboot_pending, patch.eol_software)
        try:
            patch.IS_WIN = True
            patch.win_reboot_pending = lambda: False
            patch.eol_software = lambda: []
            for days, level in ((10, "ok"), (90, "warn"), (200, "crit"), (None, "info")):
                patch.win_last_hotfix_days = lambda d=days: d
                x = {i["key"]: i for i in patch.check(False)}["hotfix"]
                self.assertEqual(x["level"], level)
                self.assertEqual(x["fix"], {"settings": "windows_update"})
            patch.win_reboot_pending = lambda: True
            self.assertIn("reboot", {i["key"] for i in patch.check(False)})
        finally:
            patch.IS_WIN, patch.win_last_hotfix_days, patch.win_reboot_pending, patch.eol_software = saved

    def test_risky_ports_filter(self):
        class C:
            def __init__(self, port, ip, status="LISTEN"):
                self.status = status
                self.laddr = type("A", (), dict(port=port, ip=ip))
        class P:
            CONN_LISTEN = "LISTEN"
            @staticmethod
            def net_connections(kind):
                return [C(23, "0.0.0.0"), C(5900, "127.0.0.1"), C(8080, "0.0.0.0"), C(3389, "::")]
        saved = harden.psutil
        harden.psutil = P
        try:
            ports = harden.risky_ports()
        finally:
            harden.psutil = saved
        self.assertEqual(sorted(ports), [23, 3389])

    def test_diag_converts_fixes_to_actions(self):
        saved = (patch.check, harden.check_all)
        try:
            patch.check = lambda deep=False: [
                dict(key="hotfix", level="crit", title="t", detail="d", advice="a", fix={"settings": "windows_update"}),
                dict(key="apt", level="warn", title="t2", detail="d2", advice="a2", fix={"command": "sudo apt upgrade"}),
                dict(key="eol", level="warn", title="t3", detail="d3", advice="a3", fix=None),
                dict(key="auto", level="ok", title="t4", detail="d4", advice="", fix={"settings": "windows_update"})]
            harden.check_all = lambda deep=False: []
            F = {f["key"]: f for f in fd.harden_findings()}
        finally:
            patch.check, harden.check_all = saved
        self.assertEqual([a["op"] for a in F["h_hotfix"]["actions"]], ["open_settings", "goto"])
        self.assertEqual(F["h_hotfix"]["actions"][0]["args"]["what"], "windows_update")
        self.assertEqual(F["h_apt"]["actions"][0]["op"], "copy_text")
        self.assertEqual(F["h_apt"]["actions"][0]["args"]["text"], "sudo apt upgrade")
        self.assertEqual([a["op"] for a in F["h_eol"]["actions"]], ["goto"])
        self.assertEqual(F["h_eol"]["actions"][0]["args"]["tab"], "uninstall")
        self.assertEqual(F["h_auto"]["actions"], [])               # 正常项没有动作
        self.assertTrue(all(f["cat"] == "harden" for f in F.values()))

    def test_trust_findings_actions(self):
        real = sig.scan
        try:
            sig.scan = lambda task=None, deep=False: [
                dict(kind="startup", name="evil", path=__file__, item=dict(kind="reg", name="evil", cmd="x"), pid=None, status="unsigned", signer="", risk="warn", user_dir=True, temp=False),
                dict(kind="process", name="tmp", path=__file__, item=None, pid=999999, status="unsigned", signer="", risk="crit", user_dir=True, temp=True)]
            F = fd.trust_findings(None, False)
        finally:
            sig.scan = real
        evil = [f for f in F if f["title"] == fd.tr("来源可疑的程序") and "evil" in f["detail"]][0]
        self.assertEqual([a["op"] for a in evil["actions"]], ["disable_startup", "copy_text", "goto"])
        tmp = [f for f in F if "tmp" in f["detail"]][0]
        self.assertEqual(tmp["level"], fd.LV_CRIT)
        self.assertEqual(tmp["actions"][0]["op"], "kill_pid")
        self.assertEqual(len(evil["actions"][1]["args"]["text"]), 64)          # 复制的是 SHA-256


class SettingsCommands(unittest.TestCase):
    def test_every_settings_label_has_a_command_on_some_os(self):
        import faster_gui as g
        for what in fd.SETTINGS_LABEL:
            self.assertIn(what, g._SETTINGS, what)
            self.assertTrue(g._SETTINGS[what])
        for what, per_os in g._SETTINGS.items():
            self.assertIn(what, fd.SETTINGS_LABEL)
            for os_key, cmd in per_os.items():
                self.assertIn(os_key, ("win", "mac", "linux"))
                self.assertIsInstance(cmd, list)

    def test_every_fix_target_used_by_modules_is_known(self):
        import re
        import faster_gui as g
        used = set()
        for f in ("faster_patch.py", "faster_harden.py"):
            used |= set(re.findall(r'"settings":\s*"([a-z_]+)"', (ROOT / f).read_text(encoding="utf-8")))
        self.assertTrue(used)
        for what in used:
            self.assertIn(what, g._SETTINGS)
            self.assertIn(what, fd.SETTINGS_LABEL)


class Theme(unittest.TestCase):
    def test_palette_and_score_colors(self):
        self.assertEqual(theme.score_color(95), theme.PALETTE["ok"])
        self.assertEqual(theme.score_color(60), theme.PALETTE["warn"])
        self.assertEqual(theme.score_color(10), theme.PALETTE["crit"])
        for k in ("bg", "card", "text", "muted", "line", "stripe", "header", "primary"):
            self.assertRegex(theme.PALETTE[k], r"^#[0-9a-f]{6}$")
        self.assertEqual(set(theme.LEVEL_COLOR), {"crit", "warn", "info", "ok"})

    def test_apply_never_raises_without_a_display(self):
        class Root:
            def configure(self, **k): raise RuntimeError("boom")
            def option_add(self, *a): raise RuntimeError("boom")
        sys.modules.pop("tkinter", None)
        try:
            theme.apply(Root())                       # 没有 tkinter / 出错时必须静默
        except Exception as e:                        # pragma: no cover
            self.fail(f"theme.apply raised {e!r}")


if __name__ == "__main__":
    unittest.main()
