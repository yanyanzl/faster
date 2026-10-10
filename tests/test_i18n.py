# -*- coding: utf-8 -*-
"""多语言测试：python -m unittest discover -s tests -v"""
import os
import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def run_py(code, lang=None, home=None, argv=()):
    env = dict(os.environ)
    env.pop("FASTER_LANG", None)
    if lang:
        env["FASTER_LANG"] = lang
    if home:
        env["HOME"] = env["USERPROFILE"] = home
    r = subprocess.run([sys.executable, "-c", code, *argv], capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class I18n(unittest.TestCase):
    def test_catalog_complete_and_consistent(self):
        import i18n_check
        self.assertEqual(i18n_check.check(), [])

    def test_english_levels_and_kinds(self):
        out = run_py("import faster_crypto as fc, json;"
                     "h=fc.scan_text('private key: '+'ab'*32, None);"
                     "print(json.dumps([fc.wallet_kind('/x/my.keystore'), h[0][0], h[0][1], fc.tr('高危')], ensure_ascii=False))", "en")
        self.assertEqual(json.loads(out), ["Ethereum/EVM keystore", "Suspected private key (64 hex chars)", "High", "High"])

    def test_chinese_unchanged(self):
        out = run_py("import faster_crypto as fc; print(fc.wallet_kind('/x/my.keystore'), fc.tr('高危'))", "zh")
        self.assertEqual(out, "以太坊/EVM 密钥库 高危")

    def test_logic_consistent_in_english(self):
        """等级字符串被用作字典键/比较：英文下排序、过滤、剪贴板判断必须仍然正确"""
        out = run_py(
            "import faster_crypto as fc, faster as core, tempfile, os, json\n"
            "wl=None\n"
            "d=tempfile.mkdtemp(); open(d+'/seed.txt','w').write('x'*30)\n"
            "open(d+'/mnemonic backup.txt','w').write('hint only file name '*3)\n"
            "open(d+'/k.txt','w').write('private key: '+'cd'*32)\n"
            "res,_=fc.scan_secrets(d, None)\n"
            "g=fc.ClipboardGuard(); a='0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe'; b='0xde0B'+'1'*28+'cb697BAe'\n"
            "g.feed(a,100); al=g.feed(b,103)\n"
            "core.findings.clear(); core.add(core.tr('提示'),'b'); core.add(core.tr('高危'),'a')\n"
            "print(json.dumps([[r['level'] for r in res], al['level'], g.verify(b,105)[0], sorted(core.findings,key=lambda x:{core.tr('高危'):0,core.tr('提示'):2}[x[0]])[0][0]]))",
            "en")
        levels, alert, verdict, first = json.loads(out)
        self.assertEqual(levels, ["High", "Info"])
        self.assertEqual((alert, verdict, first), ("High", "High", "High"))

    def test_missing_key_falls_back_and_bad_format_is_safe(self):
        out = run_py("from faster_i18n import tr; print(tr('没有翻译的句子 {0}', 5), '|', tr('{0:>3}', 'x'), '|', tr('只有一个 {0}', ))", "en")
        self.assertEqual(out, "没有翻译的句子 5 |   x | 只有一个 {0}")

    def test_language_setting_precedence(self):
        with tempfile.TemporaryDirectory() as h:
            code = "import faster_i18n as i; print(i.LANG)"
            run_py("import faster_i18n as i; i.save_language('en')", "zh", h)
            self.assertEqual(run_py(code, None, h), "en")                       # 设置文件生效
            self.assertEqual(run_py(code, "zh", h), "zh")                       # 环境变量优先于设置文件
            self.assertEqual(run_py("import sys; sys.argv += ['--lang','en']; import faster_i18n as i; print(i.LANG)", "zh", h), "en")  # 命令行最优先
            run_py("import faster_i18n as i; i.save_language('zh')", None, h)
            self.assertEqual(run_py(code, None, h), "zh")
            run_py("import faster_i18n as i; i.save_language('auto')", None, h)
            self.assertIn(run_py(code, None, h), ("zh", "en"))
            with self.assertRaises(Exception):
                run_py("import faster_i18n as i; i.save_language('xx')", None, h)

    def test_system_language_detection(self):
        code = "import faster_i18n as i; print(i.system_language())"
        env_zh = run_py("import os; os.environ['LANG']='zh_CN.UTF-8'; os.environ.pop('LC_ALL',None); import faster_i18n as i; "
                        "print('zh' if 'zh' in os.environ['LANG'] else '?')", None)
        self.assertEqual(env_zh, "zh")
        self.assertIn(run_py(code, None), ("zh", "en"))

    def test_cli_and_auto_clean_in_english(self):
        with tempfile.TemporaryDirectory() as h:
            out = run_py("import sys; sys.argv=['x','--auto-clean','--dry-run']; import faster_gui as g; g.main()", "en", h)
            self.assertIn("Auto-clean started", out)
            self.assertIn("Total reclaimable", out)
            self.assertIn("Faster 0.2.2", run_py("import sys; sys.argv=['x','--version']; import faster_gui as g; g.main()", "en", h))

    def test_english_ui_has_no_chinese_for_translated_strings(self):
        """英文界面下，目录里的译文不应夹带中文（identity 项和系统输出匹配除外）"""
        import faster_i18n_en as en
        import re
        cjk = re.compile(r"[\u4e00-\u9fff]")
        allowed = {"语言 / Language", "语言 / Language："}          # 故意写成中英并列
        bad = [k for k, v in en.CATALOG.items() if cjk.search(v) and k not in allowed]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
