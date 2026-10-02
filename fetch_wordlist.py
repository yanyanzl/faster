"""打包前下载并校验 BIP39 英文词表（用于助记词校验）。失败时退出码非 0。"""
import sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import faster_crypto as fc

URL = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
try:
    text = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Faster"}), timeout=30).read().decode("utf-8")
except Exception as e:
    sys.exit(f"下载 BIP39 词表失败：{e}")
if not fc.validate_wordlist(text.split()):
    sys.exit("BIP39 词表未通过校验（结构/官方测试向量），已放弃。")
Path(__file__).resolve().with_name("bip39_english.txt").write_text(text, encoding="utf-8")
print("BIP39 词表已就绪（校验通过）")
