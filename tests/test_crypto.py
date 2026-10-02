# -*- coding: utf-8 -*-
"""v0.2 钱包功能单元测试：python -m unittest discover -s tests -v"""
import os, sys, hashlib, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import faster_crypto as fc


def fake_wordlist():
    """合成一个 2048 词的“假词表”，只用来测试算法逻辑（真实词表由 validate_wordlist 的官方向量把关）"""
    def w(i):
        s = ""
        for _ in range(4):
            s = chr(97 + i % 26) + s
            i //= 26
        return s
    words = sorted({w(i * 37 + 5) for i in range(2048)})
    assert len(words) == 2048
    return words, {x: i for i, x in enumerate(words)}


class T(unittest.TestCase):
    def test_base58_roundtrip(self):
        for b in (b"\x00\x00abc", b"\x80" + os.urandom(32), os.urandom(21)):
            self.assertEqual(fc.b58decode(fc.b58encode(b)), b)
        p = b"\x00" + os.urandom(20)
        self.assertEqual(fc.b58check_decode(fc.b58check_encode(p)), p)
        bad = fc.b58check_encode(p)[:-1] + ("1" if not fc.b58check_encode(p).endswith("1") else "2")
        self.assertIsNone(fc.b58check_decode(bad))

    def test_classify(self):
        self.assertEqual(fc.classify_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"), "BTC")
        self.assertEqual(fc.classify_address("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"), "BTC")
        self.assertEqual(fc.classify_address("0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"), "ETH/EVM")
        self.assertEqual(fc.classify_address("TLsV52sRDL79HXGGm9yzwKibb6BeruhUzy"), "TRON")
        self.assertEqual(fc.classify_address(fc.b58check_encode(b"\x1e" + os.urandom(20))), "DOGE")
        self.assertEqual(fc.classify_address(fc.b58check_encode(b"\x30" + os.urandom(20))), "LTC")
        self.assertIsNone(fc.classify_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb"))   # 校验位错
        self.assertIsNone(fc.classify_address("hello world"))
        self.assertIsNone(fc.classify_address("0x123"))

    def test_mnemonic_logic(self):
        words, index = fake_wordlist()
        for nbytes in (16, 20, 24, 28, 32):
            ent = os.urandom(nbytes)
            m = fc.entropy_to_mnemonic(ent, words)
            self.assertEqual(len(m), {16: 12, 20: 15, 24: 18, 28: 21, 32: 24}[nbytes])
            self.assertTrue(fc.mnemonic_valid(m, index))
        m = fc.entropy_to_mnemonic(os.urandom(16), words)
        bad = list(m)
        for cand in words:                       # 换一个词使校验失败
            bad[-1] = cand
            if not fc.mnemonic_valid(bad, index):
                break
        self.assertFalse(fc.mnemonic_valid(bad, index))

    def test_wordlist_validation_rejects_fake(self):
        self.assertFalse(fc.validate_wordlist(fake_wordlist()[0]))

    def test_scan_text_mnemonic(self):
        wl = fake_wordlist()
        m = " ".join(fc.entropy_to_mnemonic(os.urandom(16), wl[0]))
        hits = fc.scan_text(f"我的备忘\n助记词: {m}\n结束", wl)
        self.assertTrue(any(k == "助记词(BIP39)" and lv == "高危" for k, lv, _, _ in hits))
        for _, _, d, _ in hits:
            self.assertNotIn(m.split()[0] + " " + m.split()[1], d)     # 不回显内容
        # 词表本身（超长列表）不应报警
        self.assertEqual([h for h in fc.scan_text(" ".join(wl[0]), wl) if h[0] == "助记词(BIP39)"], [])
        # 普通文章不报警
        self.assertEqual(fc.scan_text("The quick brown fox jumps over the lazy dog. " * 20, wl), [])

    def test_scan_text_keys(self):
        wif = fc.b58check_encode(b"\x80" + os.urandom(32) + b"\x01")
        hits = fc.scan_text(f"backup\n{wif}\n", None)
        self.assertTrue(any(k == "比特币私钥(WIF)" for k, *_ in hits))
        xprv = "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi"
        self.assertTrue(any(k == "HD 钱包扩展私钥" for k, *_ in fc.scan_text(xprv, None)))
        h = os.urandom(32).hex()
        self.assertTrue(any(k.startswith("疑似私钥") for k, *_ in fc.scan_text(f"private key: {h}", None)))
        self.assertEqual(fc.scan_text(f"sha256: {h}", None), [])        # 哈希不当私钥
        sol = "[" + ",".join(str(i * 3 % 256) for i in range(64)) + "]"
        self.assertTrue(any(k == "Solana 密钥文件" for k, *_ in fc.scan_text(sol, None)))

    def test_heuristic_seed_without_wordlist(self):
        t = "seed phrase: " + " ".join(["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
                                          "india", "juliet", "kilo", "lima"])
        self.assertTrue(any(k == "疑似助记词" for k, *_ in fc.scan_text(t, None)))
        self.assertEqual(fc.scan_text("今天吃饭 seed 数据库迁移完成", None), [])

    def test_scan_secrets_tree(self):
        wl = fake_wordlist()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            m = " ".join(fc.entropy_to_mnemonic(os.urandom(32), wl[0]))
            (d / "notes.txt").write_text("recovery phrase\n" + m, encoding="utf-8")
            (d / "OneDrive").mkdir(); (d / "OneDrive" / "a.txt").write_text(m, encoding="utf-8")
            (d / "seed.txt").write_text("nothing here, just a hint by file name", encoding="utf-8")
            (d / "node_modules").mkdir(); (d / "node_modules" / "x.txt").write_text(m, encoding="utf-8")
            res, n = fc.scan_secrets(d, wl)
            paths = {Path(r["path"]).name + ":" + r["kind"] for r in res}
            self.assertIn("notes.txt:助记词(BIP39)", paths)
            self.assertIn("a.txt:助记词(BIP39)", paths)
            self.assertIn("seed.txt:文件名可疑", paths)
            self.assertFalse(any("node_modules" in r["path"] for r in res))
            self.assertTrue(any(r["cloud"] == "OneDrive" and r["level"] == "高危" for r in res))

    def test_wallet_paths(self):
        yes = ["C:\\Users\\a\\AppData\\Roaming\\Bitcoin\\wallet.dat", "/home/a/.bitcoin/wallets/w1/wallet.dat",
               "/home/a/.ethereum/keystore/UTC--2020-01-01T00-00-00.000Z--" + "a" * 40,
               "/Users/a/Library/Application Support/Exodus/exodus.wallet/seed.seco",
               "/home/a/.config/google-chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn/000003.log",
               "/home/a/.electrum/wallets/default_wallet", "/x/my.keystore", "/x/test.wallet",
               "/x/UTC--2016-03-22T12-57-55.920751759Z--7ef5a6135f1fd6a02593eedc869c6d41d934aef8"]
        no = ["/home/a/Documents/report.pdf", "/home/a/.cache/pip/x.whl", "/home/a/wallet.txt.png"]
        for p in yes:
            self.assertTrue(fc.is_wallet_path(p), p)
        for p in no:
            self.assertFalse(fc.is_wallet_path(p), p)

    def test_find_wallet_files(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / ".bitcoin" / "wallets" / "w").mkdir(parents=True)
            (d / ".bitcoin" / "wallets" / "w" / "wallet.dat").write_bytes(b"x" * 100)
            (d / "Dropbox").mkdir(); (d / "Dropbox" / "wallet.dat").write_bytes(b"y")
            (d / "doc.txt").write_text("hi")
            res = fc.find_wallet_files(d)
            self.assertEqual(len(res), 2)
            self.assertTrue(any(r["cloud"] == "Dropbox" for r in res))

    def test_clipboard_guard(self):
        g = fc.ClipboardGuard(window=15)
        a = "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"
        b = "0xde0B" + "1" * 28 + "cb697BAe"            # 合法格式、首尾相同
        c = "0x" + "9" * 40
        self.assertIsNone(g.feed("hello", 0))
        self.assertIsNone(g.feed(a, 100))
        self.assertIsNone(g.feed(a, 101))               # 同一个，不报警
        al = g.feed(b, 103)
        self.assertEqual(al["level"], "高危")
        al2 = g.feed(c, 105)
        self.assertEqual(al2["level"], "中危")
        self.assertIsNone(g.feed(a, 500))               # 超过窗口，不报警
        self.assertEqual(g.verify(a, 505)[0], "正常")
        self.assertEqual(g.verify(b, 505)[0], "高危")
        self.assertEqual(g.verify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", 505)[0], "提示")
        self.assertEqual(g.verify("garbage", 505)[0], "提示")

    def test_miner_regex(self):
        self.assertTrue(fc.MINER_CMD.search("xmrig -o stratum+tcp://pool.example:3333 -u x"))
        self.assertTrue(fc.MINER_CMD.search("./app --donate-level 1"))
        self.assertFalse(fc.MINER_CMD.search("python manage.py runserver"))

    def test_detect_miners_runs(self):
        r = fc.detect_miners(sample=0.3)
        self.assertIn("findings", r)

    def test_chain_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["HOME"] = os.environ["USERPROFILE"] = d
            import importlib; importlib.reload(fc)
            (Path(d) / ".bitcoin" / "blocks").mkdir(parents=True)
            (Path(d) / ".bitcoin" / "blocks" / "blk0.dat").write_bytes(b"0" * 5000)
            (Path(d) / ".bitcoin" / "wallet.dat").write_bytes(b"w" * 10)
            e = fc.known_chain_dirs()
            if sys.platform.startswith("linux"):
                self.assertEqual(e[0]["name"], "Bitcoin Core")
                self.assertEqual(e[0]["resync"][0], ("blocks", 5000))
                self.assertTrue(any(s == "wallet.dat" for s, _ in e[0]["wallet"]))


if __name__ == "__main__":
    unittest.main()
