# -*- coding: utf-8 -*-
"""v0.5：开发者缓存 / 旧项目依赖 / 空间树图 / 磁盘健康 的测试"""
import os
import sys
import json
import time
import tempfile
import subprocess
import unittest
from pathlib import Path

os.environ["FASTER_LANG"] = "zh"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import faster as core  # noqa: E402
import faster_dev as dev  # noqa: E402
import faster_space as space  # noqa: E402
import faster_disk as disk  # noqa: E402
import faster_diag as fd  # noqa: E402
from faster_task import Task  # noqa: E402

GB = 1024 ** 3


def run_in_home(code, home):
    env = dict(os.environ, HOME=home, USERPROFILE=home, FASTER_LANG="zh", PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               LOCALAPPDATA=os.path.join(home, "AppData", "Local"), APPDATA=os.path.join(home, "AppData", "Roaming"))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), env=env, timeout=90)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class Treemap(unittest.TestCase):
    def check_layout(self, values, w=800, h=500):
        rects = space.squarify(values, 0, 0, w, h)
        self.assertEqual(len(rects), len([v for v in values if v > 0]))
        self.assertAlmostEqual(sum(rw * rh for _, _, rw, rh in rects), w * h, delta=w * h * 1e-6)
        for x, y, rw, rh in rects:
            self.assertGreaterEqual(x, -1e-6); self.assertGreaterEqual(y, -1e-6)
            self.assertLessEqual(x + rw, w + 1e-6); self.assertLessEqual(y + rh, h + 1e-6)
            self.assertGreater(rw, 0); self.assertGreater(rh, 0)
        for i, (x1, y1, w1, h1) in enumerate(rects):                      # 两两不重叠
            for x2, y2, w2, h2 in rects[i + 1:]:
                ox = min(x1 + w1, x2 + w2) - max(x1, x2)
                oy = min(y1 + h1, y2 + h2) - max(y1, y2)
                self.assertFalse(ox > 1e-6 and oy > 1e-6, (rects[i], (x2, y2, w2, h2)))
        return rects

    def test_basic_and_proportional(self):
        rects = self.check_layout([60, 30, 10])
        areas = [rw * rh for _, _, rw, rh in rects]
        self.assertAlmostEqual(areas[0] / areas[1], 2.0, places=5)           # 面积与大小成正比
        self.assertAlmostEqual(areas[1] / areas[2], 3.0, places=5)

    def test_many_and_skewed_inputs(self):
        self.check_layout(sorted([i ** 2 + 1 for i in range(1, 60)], reverse=True))
        self.check_layout([10 ** 6, 5, 3, 2, 1, 1, 1], 300, 900)
        self.check_layout([5], 100, 100)
        self.check_layout([1, 1, 1, 1], 400, 400)

    def test_degenerate_inputs(self):
        self.assertEqual(space.squarify([], 0, 0, 10, 10), [])
        self.assertEqual(space.squarify([1, 2], 0, 0, 0, 10), [])
        self.assertEqual(space.squarify([0, 0], 0, 0, 10, 10), [])
        self.assertEqual(len(space.squarify([3, 0, 1], 0, 0, 10, 10)), 2)          # 0 大小的被忽略

    def test_reasonable_aspect_ratios(self):
        worst = max(max(w / h, h / w) for _, _, w, h in self.check_layout([50, 30, 20, 15, 10, 8, 5, 3, 2, 1]))
        self.assertLess(worst, 6)                                                    # 不会出现细长的“针”

    def test_group_small_and_colors(self):
        items = [dict(name=f"d{i}", path=f"/d{i}", size=s, is_dir=True) for i, s in enumerate([1000, 500, 5, 4, 3, 2])]
        g = space.group_small(items, min_frac=0.01)
        self.assertEqual([i["name"] for i in g[:2]], ["d0", "d1"])
        self.assertIsNone(g[-1]["path"])
        self.assertEqual(g[-1]["size"], 14)
        self.assertEqual(sum(i["size"] for i in g), sum(i["size"] for i in items))        # 合并后总量不变
        self.assertEqual(space.color_for(items[0]), space.color_for(dict(items[0])))
        self.assertEqual(space.color_for(g[-1]), "#d1d5db")
        self.assertEqual(space.color_for(dict(name="f", path="/f", size=1, is_dir=False)), "#94a3b8")


class ScanChildren(unittest.TestCase):
    def test_aggregates_first_level_and_sorts(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "big").mkdir(); (d / "big" / "a.bin").write_bytes(b"x" * 5000); (d / "big" / "sub").mkdir(); (d / "big" / "sub" / "b").write_bytes(b"x" * 3000)
            (d / "small").mkdir(); (d / "small" / "c").write_bytes(b"x" * 100)
            (d / "file.bin").write_bytes(b"x" * 1000)
            (d / "empty").mkdir()
            items, total = space.scan_children(d)
            self.assertEqual([(i["name"], i["size"], i["is_dir"]) for i in items],
                             [("big", 8000, True), ("file.bin", 1000, False), ("small", 100, True)])
            self.assertEqual(total, 9100)

    def test_symlinks_are_not_followed_and_cancel(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "real").mkdir(); (d / "real" / "x").write_bytes(b"x" * 100)
            try:
                os.symlink(d / "real", d / "link")
            except (OSError, NotImplementedError):
                self.skipTest("不能创建符号链接")
            items, _ = space.scan_children(d)
            self.assertEqual([i["name"] for i in items], ["real"])
            tk = Task(); tk.cancel()
            self.assertEqual(space.scan_children(d, tk), ([], 0))
        self.assertEqual(space.scan_children("/no/such/dir"), ([], 0))


class DevCaches(unittest.TestCase):
    def test_specs_are_well_formed(self):
        specs = dev.cache_specs()
        ids = [s["id"] for s in specs]
        self.assertEqual(len(ids), len(set(ids)))
        for s in specs:
            self.assertTrue(s["name"] and s["note"])
            self.assertTrue(all(isinstance(p, Path) for p in s["paths"]))
        self.assertTrue({"npm", "pip", "gradle", "maven", "vscode"} <= set(ids))

    def test_scan_and_clean_real_directories(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_in_home(
                "import faster_dev as dev, json, os\n"
                "specs = {s['id']: s for s in dev.cache_specs()}\n"
                "npm = specs['npm']['paths'][0]; pip = specs['pip']['paths'][0]\n"
                "for p, n in ((npm, 4000), (pip, 3000)):\n"
                "    os.makedirs(p / 'sub', exist_ok=True); (p / 'a.bin').write_bytes(b'x' * n); (p / 'sub' / 'b.bin').write_bytes(b'x' * 10)\n"
                "(pip / 'wallet.dat').write_bytes(b'w')                    # 钱包文件即使混进缓存目录也不能删\n"
                "rows = {r['id']: r for r in dev.scan_caches(None, 20, False)}\n"
                "freed = dev.clean(rows['npm'])\n"
                "freed2 = dev.clean(rows['pip'])\n"
                "print(json.dumps([sorted(rows), rows['npm']['size'], freed, os.path.isdir(npm), os.listdir(npm), freed2, os.path.exists(pip / 'wallet.dat')]))", h)
            ids, size, freed, still_dir, left, freed2, wallet = json.loads(out.splitlines()[-1])
            self.assertEqual(ids, ["npm", "pip"])
            self.assertEqual(size, 4010)
            self.assertEqual(freed, 4010)
            self.assertTrue(still_dir)
            self.assertEqual(left, [])                       # 内容清空，目录本身还在
            self.assertTrue(wallet)                          # 钱包文件还在
            self.assertEqual(freed2, 3010)

    def test_parse_size(self):
        self.assertEqual(dev._parse_size("1.5GB"), 1500000000)
        self.assertEqual(dev._parse_size("350kB"), 350000)
        self.assertEqual(dev._parse_size("12B"), 12)
        self.assertEqual(dev._parse_size("garbage"), 0)

    def test_docker_rows_with_mocked_cli(self):
        real = (dev.shutil.which, dev.core.run)
        try:
            dev.shutil.which = lambda n: "/usr/bin/docker"
            dev.core.run = lambda cmd, timeout=60: (0, "Images|3GB|2.4GB (80%)\nContainers|10MB|0B (0%)\nLocal Volumes|1GB|1GB (100%)\n"
                                                      "Build Cache|500MB|450MB\n", "")
            rows = {r["id"]: r for r in dev.docker_rows()}
            self.assertEqual(sorted(rows), ["docker_build", "docker_images"])
            self.assertEqual(rows["docker_build"]["size"], 450000000)
            self.assertEqual(rows["docker_build"]["cmd"], ["docker", "builder", "prune", "-f"])
            self.assertEqual(rows["docker_images"]["cmd"], ["docker", "image", "prune", "-a", "-f"])
            dev.core.run = lambda cmd, timeout=60: (0, "Deleted build cache objects:\nxyz\nTotal reclaimed space: 1.25GB\n", "")
            self.assertEqual(dev.clean(rows["docker_build"]), 1250000000)
            dev.core.run = lambda cmd, timeout=60: (1, "", "daemon not running")
            self.assertEqual(dev.docker_rows(), [])
            self.assertEqual(dev.clean(rows["docker_build"]), 0)
        finally:
            dev.shutil.which, dev.core.run = real

    def make_projects(self, d):
        d = Path(d)
        old = time.time() - 200 * 86400
        for name, marker, dep in (("old_node", "package.json", "node_modules"), ("old_rust", "Cargo.toml", "target"),
                                  ("new_node", "package.json", "node_modules")):
            (d / name / dep / "pkg").mkdir(parents=True)
            (d / name / dep / "pkg" / "f.js").write_bytes(b"x" * 2000)
            (d / name / marker).write_text("{}")
            if name.startswith("old"):
                for p in (d / name / marker, d / name):
                    os.utime(p, (old, old))
        (d / "old_py" / ".venv").mkdir(parents=True)
        (d / "old_py" / ".venv" / "pyvenv.cfg").write_text("home = /usr")
        (d / "old_py" / ".venv" / "lib.bin").write_bytes(b"x" * 500)
        (d / "old_py" / "main.py").write_text("print()")
        for p in (d / "old_py" / "main.py", d / "old_py"):
            os.utime(p, (old, old))
        (d / "plain" / "node_modules").mkdir(parents=True)                       # 没有 package.json → 不是项目依赖
        (d / "plain" / "node_modules" / "x").write_bytes(b"x" * 100)
        return d

    def test_stale_projects(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.make_projects(t)
            rows = dev.stale_projects(d, 90)
            names = sorted(r["name"] for r in rows)
            self.assertEqual(names, ["old_node/node_modules", "old_py/.venv", "old_rust/target"])
            by = {r["name"]: r for r in rows}
            self.assertEqual(by["old_node/node_modules"]["size"], 2000)
            self.assertGreaterEqual(by["old_node/node_modules"]["days"], 199)
            self.assertEqual([r["size"] for r in rows], sorted((r["size"] for r in rows), reverse=True))       # 大的在前
            self.assertEqual(len(dev.stale_projects(d, 400)), 0)                 # 阈值提高后都不算旧
            self.assertEqual(len(dev.stale_projects(d, 0)), 4)                   # 阈值为 0：连新项目也算（但 plain 不算）
            ex = core.Exclusions([], [], [str(d / "old_node")])
            self.assertNotIn("old_node/node_modules", [r["name"] for r in dev.stale_projects(d, 90, None, ex)])
            tk = Task(); tk.cancel()
            self.assertEqual(dev.stale_projects(d, 90, tk), [])

    def test_project_removal_goes_to_restorable_trash(self):
        with tempfile.TemporaryDirectory() as h:
            Path(h, "proj", "node_modules").mkdir(parents=True)
            Path(h, "proj", "node_modules", "f").write_bytes(b"x" * 10)
            Path(h, "proj", "package.json").write_text("{}")
            out = run_in_home(
                "import faster as c, faster_dev as dev, os\nc.send2trash = None\n"
                "p = os.path.expanduser('~/proj/node_modules')\n"
                "assert c.safe_remove(p) and not os.path.exists(p)\n"
                "e = c.ledger_load()[0]; ok, dest = c.restore_from_trash(e)\n"
                "print(ok, os.path.isfile(os.path.join(p, 'f')))", h)
            self.assertEqual(out.splitlines()[-1], "True True")


class DiskHealth(unittest.TestCase):
    def test_windows_parse(self):
        disks = json.dumps([
            dict(DeviceId="0", FriendlyName="Samsung SSD", HealthStatus="Healthy", OperationalStatus="OK", MediaType="SSD"),
            dict(DeviceId="1", FriendlyName="Old HDD", HealthStatus="Unhealthy", OperationalStatus="Degraded", MediaType="HDD"),
            dict(DeviceId="2", FriendlyName="Flaky", HealthStatus="Warning", OperationalStatus="Predictive Failure", MediaType="HDD"),
            dict(DeviceId="3", FriendlyName="Worn SSD", HealthStatus="Healthy", OperationalStatus="OK", MediaType="SSD")])
        wear = json.dumps([dict(DeviceId="0", Wear=3, Temperature=40, ReadErrorsTotal=0, WriteErrorsTotal=0),
                           dict(DeviceId="3", Wear=97, Temperature=70, ReadErrorsTotal=2, WriteErrorsTotal=1)])
        by = {x["key"]: x for x in disk.parse_windows(disks, wear)}
        self.assertEqual(by["disk_0"]["level"], "ok")
        self.assertEqual(by["disk_1"]["level"], "crit")
        self.assertEqual(by["disk_2"]["level"], "warn")
        self.assertEqual(by["disk_3"]["level"], "crit")                    # 磨损 ≥95%
        self.assertIn("97", by["disk_3"]["detail"])
        self.assertTrue(by["disk_1"]["advice"])
        self.assertEqual(disk.parse_windows("", ""), [])
        self.assertEqual(disk.parse_windows("not json", ""), [])
        one = disk.parse_windows(json.dumps(dict(DeviceId="9", FriendlyName="Solo", HealthStatus="Healthy", OperationalStatus="OK")), "")
        self.assertEqual([x["level"] for x in one], ["ok"])                # 只有一块盘时 PowerShell 返回的是对象不是数组

    def test_windows_moderate_wear_and_temperature(self):
        d = json.dumps([dict(DeviceId="0", FriendlyName="S", HealthStatus="Healthy", OperationalStatus="OK")])
        self.assertEqual(disk.parse_windows(d, json.dumps([dict(DeviceId="0", Wear=85, Temperature=30)]))[0]["level"], "warn")
        self.assertEqual(disk.parse_windows(d, json.dumps([dict(DeviceId="0", Wear=10, Temperature=70)]))[0]["level"], "warn")

    def test_diskutil_parse(self):
        txt = ("   Device Identifier:         disk0\n   Device / Media Name:       APPLE SSD\n   SMART Status:              Verified\n\n"
               "   Device Identifier:         disk1\n   Device / Media Name:       Old Drive\n   SMART Status:              Failing\n\n"
               "   Device Identifier:         disk2\n   Device / Media Name:       Virtual\n   SMART Status:              Not Supported\n")
        by = {x["key"]: x["level"] for x in disk.parse_diskutil(txt)}
        self.assertEqual(by, {"disk_APPLE SSD": "ok", "disk_Old Drive": "crit"})

    def test_smartctl_parse(self):
        self.assertEqual(disk.parse_smartctl("sda", 0, "SMART overall-health self-assessment test result: PASSED")["level"], "ok")
        self.assertEqual(disk.parse_smartctl("sda", 0, "SMART overall-health self-assessment test result: FAILED!")["level"], "crit")
        r = disk.parse_smartctl("sda", 2, "Smartctl open device: /dev/sda failed: Permission denied")
        self.assertEqual((r["level"], r["fix"]["command"]), ("info", "sudo smartctl -H /dev/sda"))
        self.assertIsNone(disk.parse_smartctl("sda", 0, "nothing useful"))
        self.assertIsNone(disk.parse_smartctl("sda", 2, "Smartctl open device: /dev/sdz failed: No such device"))   # 不能把“打不开设备”当成硬盘故障

    def test_check_never_raises(self):
        for x in disk.check():
            self.assertEqual(set(x), {"key", "level", "title", "detail", "advice", "fix"})


class TabBar(unittest.TestCase):
    def test_english_tab_titles_are_short_and_complete(self):
        import re
        import faster_gui as g
        src = (ROOT / "faster_gui.py").read_text(encoding="utf-8")
        keys = re.findall(r'\("([a-z]+)", tr\("[^"]+"\), [A-Za-z]+(?:Tab|Hub)\)', src)
        top = [k for k in keys if k in g.SHORT_TITLES]
        self.assertEqual(sorted(g.SHORT_TITLES), sorted(set(top)))               # 每个顶层标签页都有短标题
        for t in g.SHORT_TITLES.values():
            self.assertTrue(t.isascii() and len(t) <= 12, t)
        self.assertLessEqual(sum(len(t) for t in g.SHORT_TITLES.values()), 110)  # 总字数控制在窗口放得下的范围内


class DiagIntegration(unittest.TestCase):
    def test_storage_findings_include_dev_caches_and_disk_health(self):
        saved = (dev.scan_caches, disk.check, fd.system_trash_size)
        try:
            dev.scan_caches = lambda task=None, max_seconds=25, with_docker=True: [
                dict(kind="cache", id="npm", name="npm", paths=["/x"], size=3 * GB, note="n", cmd=None),
                dict(kind="cache", id="pip", name="pip", paths=["/y"], size=1 * GB, note="n", cmd=None)]
            disk.check = lambda: [dict(key="disk_0", level="crit", title="Old HDD", detail="unhealthy", advice="back up", fix=None),
                                  dict(key="smartctl", level="info", title="磁盘健康", detail="x", advice="y", fix={"command": "sudo apt install smartmontools"})]
            fd.system_trash_size = lambda: 0
            F = {f["key"]: f for f in fd.storage_findings(None, False)}
        finally:
            dev.scan_caches, disk.check, fd.system_trash_size = saved
        dc = F["devcache"]
        self.assertEqual(dc["level"], fd.LV_WARN)                                        # 4GB ≥ 2GB
        self.assertEqual([a["op"] for a in dc["actions"]], ["clean_dev", "goto"])
        self.assertEqual(dc["actions"][0]["page"], "dev")
        self.assertEqual(dc["actions"][1]["args"]["tab"], "dev")
        self.assertEqual(F["disk_0"]["level"], fd.LV_CRIT)
        self.assertEqual(F["smartctl"]["actions"][0]["op"], "copy_text")
        self.assertEqual(F["smartctl"]["actions"][0]["args"]["text"], "sudo apt install smartmontools")

    def test_dev_caches_levels(self):
        saved = dev.scan_caches
        try:
            for size, level in ((1 * GB, fd.LV_OK), (3 * GB, fd.LV_WARN), (25 * GB, fd.LV_CRIT)):
                dev.scan_caches = lambda task=None, max_seconds=25, with_docker=True, s=size: [
                    dict(kind="cache", id="npm", name="npm", paths=["/x"], size=s, note="n", cmd=None)]
                f = [x for x in fd.storage_findings(None, False) if x["key"] == "devcache"][0]
                self.assertEqual(f["level"], level)
            dev.scan_caches = lambda task=None, max_seconds=25, with_docker=True: []
            self.assertNotIn("devcache", [x["key"] for x in fd.storage_findings(None, False)])         # 没装开发工具就不出现
        finally:
            dev.scan_caches = saved

    def test_deep_stale_projects_finding(self):
        saved = dev.stale_projects
        try:
            dev.stale_projects = lambda root=None, min_days=90, task=None, exclude=None, max_seconds=180: [
                dict(kind="project", name="a/node_modules", path="/a", size=3 * GB, days=200, note="n", paths=["/a"], cmd=None)]
            f = [x for x in fd.storage_findings(None, True) if x["key"] == "stale_projects"][0]
        finally:
            dev.stale_projects = saved
        self.assertEqual(f["level"], fd.LV_WARN)
        self.assertEqual(f["actions"][0]["args"]["auto"], "scan_projects")

    def test_disk_finding_links_to_space_analysis(self):
        snap = dict(ts=0, label="", disk_total=500 * GB, disk_free=20 * GB)
        f = [x for x in fd.diagnose(snap)["findings"] if x["key"] == "disk"][0]
        self.assertIn("space", [a["args"].get("tab") for a in f["actions"] if a["op"] == "goto"])


if __name__ == "__main__":
    unittest.main()
