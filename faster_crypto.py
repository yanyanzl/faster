# -*- coding: utf-8 -*-
"""
Faster · 钱包 / 区块链相关的本地安全功能（v0.2）

  1. 钱包文件识别与保护（is_wallet_path / find_wallet_files）
  2. 助记词 / 私钥泄露扫描（scan_secrets）
  3. 挖矿木马检测（detect_miners）
  4. 剪贴板地址劫持检测（ClipboardGuard）
  5. 区块链数据目录识别（known_chain_dirs）

原则：
  * 全部在本地运行、只读检测；除“下载 BIP39 词表”外不联网
  * 绝不索要、保存或上传私钥/助记词；扫描结果只给出位置与类型，不回显内容
  * 本模块只依赖标准库（psutil 可选）
"""
import os
import re
import sys
import time
import hashlib
import urllib.request
from pathlib import Path
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

HOME = Path.home()
APP_DIR = HOME / ".faster"
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{int(n)} B" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def _norm(path):
    return str(path).replace("\\", "/").lower()


def dir_size(path):
    total = 0
    for r, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                fp = os.path.join(r, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except OSError:
                pass
    return total


# ============================================================ 1. 钱包文件识别
_WALLET_NAME_RE = re.compile(
    r"^(wallet\.dat|seed\.seco|passphrase\.json|keystore\.json|default_wallet|"
    r".*\.wallet|.*\.keystore|.*\.keys|.*\.mpk|.*\.walletbackup|"
    r"utc--\d{4}-\d{2}-\d{2}t[\d\-\.]+z--[0-9a-f]{40})$", re.I)

# 路径片段（统一为小写、正斜杠、结尾补“/”后匹配，所以目录本身和其下所有文件都命中）
_WALLET_PATH_SUBSTR = (
    "/exodus/exodus.wallet/", "/.electrum/wallets/", "/electrum/wallets/",
    "/.bitcoin/wallets/", "/bitcoin/wallets/", "/.litecoin/wallets/", "/litecoin/wallets/",
    "/.dogecoin/wallets/", "/dogecoin/wallets/", "/keystore/",
)

# 浏览器钱包扩展 ID（出现在 Local Extension Settings / IndexedDB 路径中；仅供参考，不全）
_EXT_IDS = {
    "nkbihfbeogaeaoehlefnkodbefgpgknn": "MetaMask",
    "bfnaelmomeimhlpmgjnjophhpkkoljpa": "Phantom",
    "acmacodkjbdgmoleebolmdjonilkdbch": "Rabby",
    "egjidjbpglichdcondbcbdnbeeppgdph": "Trust Wallet",
    "hnfanknocfeofbddgcijnmhnfnkdnaad": "Coinbase Wallet",
    "dmkamcknogkgcdfhhbddcghachkejeap": "Keplr",
    "fhbohimaelbohpjbbldcngcnapndodjp": "Binance Wallet",
    "fnjhmkhhmkbjkkabndcnnogagogbneec": "Ronin Wallet",
    "mcohilncbfahbmgdjkbpemcciiolgcge": "OKX Wallet",
}


def is_wallet_path(path):
    """是否为钱包相关文件/目录（宁可多保护，不可漏保护）"""
    p = _norm(path)
    base = p.rsplit("/", 1)[-1]
    if _WALLET_NAME_RE.match(base):
        return True
    q = p + "/"
    for s in _WALLET_PATH_SUBSTR:
        if s in q:
            return True
    for i in _EXT_IDS:
        if i in p:
            return True
    return False


def wallet_kind(path):
    p = _norm(path)
    base = p.rsplit("/", 1)[-1]
    for i, name in _EXT_IDS.items():
        if i in p:
            return f"浏览器钱包扩展 · {name}"
    if "exodus" in p:
        return "Exodus 钱包"
    if "electrum" in p:
        return "Electrum 钱包"
    if "/keystore" in p or base.startswith("utc--") or base.endswith(".keystore") or base == "keystore.json":
        return "以太坊/EVM 密钥库"
    if base == "wallet.dat" or "/wallets/" in p:
        return "比特币系钱包"
    if base.endswith(".keys"):
        return "Monero 等钱包密钥文件"
    return "钱包文件"


_CLOUD_HINTS = (("onedrive", "OneDrive"), ("dropbox", "Dropbox"), ("mobile documents", "iCloud"),
                ("icloud drive", "iCloud"), ("iclouddrive", "iCloud"), ("google drive", "Google Drive"),
                ("googledrive", "Google Drive"), ("nutstore", "坚果云"), ("pcloud", "pCloud"),
                ("baidunetdisk", "百度网盘"), ("/mega/", "MEGA"))


def cloud_hint(path):
    p = _norm(path)
    for k, name in _CLOUD_HINTS:
        if k in p:
            return name
    return ""


_NOISE_DIRS = {"node_modules", ".git", "site-packages", "__pycache__", "$recycle.bin", "system volume information",
               "windows", "program files", "program files (x86)", "programdata", "cache", "code cache", "gpucache",
               "service worker", ".cache", ".npm", ".cargo", ".rustup", ".gradle", ".m2", ".venv", "venv", ".trash",
               ".faster", ".pc_optimizer"}


def find_wallet_files(root=None, limit=500, max_seconds=600):
    """扫描钱包文件/目录。目录型（钱包扩展、keystore 等）合并成一条"""
    root = Path(root or HOME)
    deadline, res = time.time() + max_seconds, []
    for r, dirs, files in os.walk(root, onerror=lambda e: None):
        if time.time() > deadline or len(res) >= limit:
            break
        if is_wallet_path(r):
            res.append(dict(path=r, kind=wallet_kind(r), size=dir_size(r), mtime=_mtime(r), cloud=cloud_hint(r), is_dir=True))
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d.lower() not in _NOISE_DIRS and not os.path.islink(os.path.join(r, d))
                   and not d.lower().endswith((".app", ".photoslibrary", ".framework"))]
        for f in files:
            fp = os.path.join(r, f)
            if _WALLET_NAME_RE.match(f):
                try:
                    res.append(dict(path=fp, kind=wallet_kind(fp), size=os.path.getsize(fp), mtime=_mtime(fp),
                                    cloud=cloud_hint(fp), is_dir=False))
                except OSError:
                    pass
    return res


def _mtime(p):
    try:
        return os.stat(p).st_mtime
    except OSError:
        return 0


# ============================================================ 地址 / 编码工具
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {c: i for i, c in enumerate(_B58)}


def b58decode(s):
    n = 0
    for ch in s:
        if ch not in _B58_IDX:
            return None
        n = n * 58 + _B58_IDX[ch]
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def b58encode(b):
    n = int.from_bytes(b, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    return "1" * (len(b) - len(b.lstrip(b"\x00"))) + out


def _dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def b58check_encode(payload):
    return b58encode(payload + _dsha(payload)[:4])


def b58check_decode(s):
    raw = b58decode(s)
    if raw is None or len(raw) < 5:
        return None
    payload, chk = raw[:-4], raw[-4:]
    return payload if _dsha(payload)[:4] == chk else None


_BECH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech_polymod(values):
    gen = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= gen[i]
    return chk


def bech32_verify(s):
    """校验 bech32/bech32m，返回 (hrp, 类型) 或 None"""
    if s != s.lower() and s != s.upper():
        return None
    s = s.lower()
    pos = s.rfind("1")
    if pos < 1 or pos + 7 > len(s) or len(s) > 90:
        return None
    hrp, data = s[:pos], [_BECH.find(c) for c in s[pos + 1:]]
    if -1 in data:
        return None
    c = _bech_polymod([ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp] + data)
    return (hrp, "bech32") if c == 1 else (hrp, "bech32m") if c == 0x2bc830a3 else None


_B58_VERSIONS = {0x00: "BTC", 0x05: "BTC", 0x30: "LTC", 0x32: "LTC", 0x1e: "DOGE", 0x41: "TRON"}


def classify_address(text):
    """是有效的区块链地址就返回链名，否则 None（严格整串匹配并校验校验位）"""
    s = (text or "").strip()
    if not s or len(s) > 100 or any(c.isspace() for c in s):
        return None
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", s):
        return "ETH/EVM"
    r = bech32_verify(s)
    if r:
        return {"bc": "BTC", "ltc": "LTC"}.get(r[0])
    if s[0] in "13LMDT":
        payload = b58check_decode(s)
        if payload and len(payload) == 21:
            return _B58_VERSIONS.get(payload[0])
    if 32 <= len(s) <= 44 and all(c in _B58_IDX for c in s):
        raw = b58decode(s)
        if raw and len(raw) == 32:
            return "SOL"
    return None


def mask_addr(a):
    a = a.strip()
    return a if len(a) <= 12 else f"{a[:6]}…{a[-4:]}"


# ============================================================ 2. 助记词 / 私钥泄露扫描
_WORDLIST_URL = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
_VECTORS = (  # BIP39 官方测试向量（用来确认词表没被篡改/损坏）
    ("00000000000000000000000000000000", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"),
    ("7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f", "legal winner thank year wave sausage worth useful legal winner thank yellow"),
    ("80808080808080808080808080808080", "letter advice cage absurd amount doctor acoustic avoid letter advice cage above"),
    ("ffffffffffffffffffffffffffffffff", "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong"),
)


def entropy_to_mnemonic(ent, words):
    bits_n = len(ent) * 8
    cs = bits_n // 32
    bits = bin(int.from_bytes(ent, "big"))[2:].zfill(bits_n) + bin(hashlib.sha256(ent).digest()[0])[2:].zfill(8)[:cs]
    return [words[int(bits[i:i + 11], 2)] for i in range(0, len(bits), 11)]


def mnemonic_valid(tokens, index):
    n = len(tokens)
    if n not in (12, 15, 18, 21, 24):
        return False
    try:
        bits = "".join(format(index[t], "011b") for t in tokens)
    except KeyError:
        return False
    cs = n // 3
    ent_bits = len(bits) - cs
    ent = int(bits[:ent_bits], 2).to_bytes(ent_bits // 8, "big")
    return (hashlib.sha256(ent).digest()[0] >> (8 - cs)) == int(bits[ent_bits:], 2)


def validate_wordlist(words):
    """结构 + 官方测试向量双重校验：词表不对就拒绝使用（宁可降级为启发式，也不用错词表）"""
    try:
        if len(words) != 2048 or len(set(words)) != 2048 or words != sorted(words):
            return False
        if any(not re.fullmatch(r"[a-z]{3,8}", w) for w in words) or len({w[:4] for w in words}) != 2048:
            return False
        if words[0] != "abandon" or words[-1] != "zoo":
            return False
        return all(entropy_to_mnemonic(bytes.fromhex(e), words) == p.split() for e, p in _VECTORS)
    except Exception:
        return False


_WL_CACHE = {"tried": False, "val": None}


def wordlist_paths():
    return [Path(getattr(sys, "_MEIPASS", ".")) / "bip39_english.txt",
            Path(__file__).resolve().with_name("bip39_english.txt"),
            APP_DIR / "bip39_english.txt"]


def get_wordlist(force_reload=False):
    """返回 (words, index) 或 None（词表缺失/校验不通过）"""
    if _WL_CACHE["tried"] and not force_reload:
        return _WL_CACHE["val"]
    _WL_CACHE.update(tried=True, val=None)
    for p in wordlist_paths():
        try:
            words = p.read_text(encoding="utf-8").split()
        except OSError:
            continue
        if validate_wordlist(words):
            _WL_CACHE["val"] = (words, {w: i for i, w in enumerate(words)})
            break
    return _WL_CACHE["val"]


def download_wordlist():
    """从 BIP39 官方仓库下载英文词表并校验，保存到 ~/.faster/；返回 (ok, 说明)"""
    try:
        req = urllib.request.Request(_WORDLIST_URL, headers={"User-Agent": "Faster"})
        text = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    except Exception as e:
        return False, f"下载失败：{e}"
    if not validate_wordlist(text.split()):
        return False, "下载的词表未通过校验，已丢弃。"
    APP_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "bip39_english.txt").write_text(text, encoding="utf-8")
    get_wordlist(force_reload=True)
    return True, "BIP39 词表已就绪（校验通过）。"


KEY_CTX = re.compile(r"(private\s*key|priv[\s_\-]*key|secret\s*key|privkey|\bpk\b|私钥|密钥|signing\s*key)", re.I)
SEED_CTX = re.compile(r"(seed\s*phrase|seed\s*words?|seed|mnemonic|recovery\s*phrase|backup\s*phrase|secret\s*recovery|助记词|恢复短语|备份短语|种子)", re.I)
_HEX64 = re.compile(r"(?<![0-9A-Fa-f])(?:0x)?[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")
_B58_TOKEN = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{51,111}(?![1-9A-HJ-NP-Za-km-z])")
_SOL_ARRAY = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){63}\d{1,3}\s*\]")
_WORD = re.compile(r"[A-Za-z]+")
_HEUR_SEED = re.compile(r"[\s:：=\-\"'\[\(]*((?:\d{0,2}[.)、]?\s*[a-z]{3,8}[\s,，]+){11,23}[a-z]{3,8})", re.I)
_XPRV_VERS = {bytes.fromhex("0488ADE4"): "xprv", bytes.fromhex("049D7878"): "yprv", bytes.fromhex("04B2430C"): "zprv",
              bytes.fromhex("04358394"): "tprv"}
_NAME_HINT = re.compile(r"(seed|mnemonic|助记词|私钥|privatekey|private[_\- ]key|recovery[_\- ]?phrase|wallet[_\- ]?backup)", re.I)


def _line(text, pos):
    return text.count("\n", 0, pos) + 1


def scan_text(text, wl=None):
    """在文本里找助记词/私钥。返回 [(类型, 级别, 说明, 行号)]；不返回任何敏感内容本身"""
    out = []
    # --- 明确格式的私钥：WIF / xprv / yprv / zprv（带校验位，几乎无误报）
    for m in _B58_TOKEN.finditer(text):
        tok = m.group()
        payload = b58check_decode(tok)
        if payload is None:
            if 86 <= len(tok) <= 90 and KEY_CTX.search(text[max(0, m.start() - 80):m.start()]):
                raw = b58decode(tok)
                if raw and len(raw) == 64:
                    out.append(("Solana 私钥", "高危", "Base58 编码的 64 字节密钥（附近有“私钥”字样）", _line(text, m.start())))
            continue
        if tok[0] in "5KL" and len(tok) in (51, 52) and payload[0] == 0x80 and len(payload) in (33, 34):
            out.append(("比特币私钥(WIF)", "高危", f"校验通过的 WIF 私钥，长度 {len(tok)}", _line(text, m.start())))
        elif len(payload) == 78 and payload[:4] in _XPRV_VERS:
            out.append(("HD 钱包扩展私钥", "高危", f"校验通过的 {_XPRV_VERS[payload[:4]]}（可推出该钱包全部私钥）", _line(text, m.start())))
    # --- Solana id.json：64 个 0~255 的整数数组
    for m in _SOL_ARRAY.finditer(text):
        nums = [int(x) for x in re.findall(r"\d+", m.group())]
        if len(nums) == 64 and max(nums) <= 255:
            out.append(("Solana 密钥文件", "高危", "64 个字节的数组（solana-keygen 生成的 id.json 格式）", _line(text, m.start())))
    # --- 64 位十六进制：必须附近出现“私钥/private key”之类字样才报，避免把哈希当私钥
    for m in _HEX64.finditer(text):
        ctx = text[max(0, m.start() - 60):m.start()] + text[m.end():m.end() + 20]
        if KEY_CTX.search(ctx):
            out.append(("疑似私钥(64位十六进制)", "高危", "64 位十六进制串，附近有“私钥/private key”字样", _line(text, m.start())))
    # --- 助记词
    if wl:
        out += _find_mnemonics_exact(text, wl)
    else:
        for m in SEED_CTX.finditer(text):
            h = _HEUR_SEED.match(text[m.end():m.end() + 400])
            if h:
                n = len(re.findall(r"[A-Za-z]{3,8}", h.group(1)))
                out.append(("疑似助记词", "中危", f"“助记词”字样后跟 {n} 个英文单词（未加载 BIP39 词表，未做校验）", _line(text, m.start())))
                break
    return out


def _find_mnemonics_exact(text, wl):
    words, index = wl
    toks = [(m.group().lower(), m.start(), m.end()) for m in _WORD.finditer(text)]
    out, i, n = [], 0, len(toks)
    while i < n:
        if toks[i][0] not in index:
            i += 1
            continue
        j = i + 1
        while j < n and toks[j][0] in index and toks[j][1] - toks[j - 1][2] <= 8:
            j += 1
        run = toks[i:j]
        L = len(run)
        if 12 <= L <= 48:            # 超长的是“词表本身”之类，不是助记词
            hit = None
            for size in (24, 21, 18, 15, 12):
                for s in range(0, L - size + 1):
                    if mnemonic_valid([t[0] for t in run[s:s + size]], index):
                        hit = (s, size)
                        break
                if hit:
                    break
            if hit:
                out.append(("助记词(BIP39)", "高危", f"校验通过的 {hit[1]} 个单词助记词（可恢复整个钱包）", _line(text, run[hit[0]][1])))
            elif L in (12, 15, 18, 21, 24) and SEED_CTX.search(text[max(0, run[0][1] - 200):run[0][1]]):
                out.append(("疑似助记词", "中危", f"“助记词”字样后跟 {L} 个 BIP39 单词，但校验未通过（可能抄错了某个词）", _line(text, run[0][1])))
        i = j
    return out


_TEXT_EXT = {".txt", ".md", ".json", ".csv", ".log", ".rtf", ".html", ".htm", ".xml", ".yml", ".yaml", ".ini", ".conf",
             ".cfg", ".env", ".js", ".ts", ".py", ".sh", ".bak", ".key", ".keys", ".backup", ".note", ".notes", ".text"}
_OFFICE_EXT = {".docx", ".xlsx", ".pptx"}
_SECRET_SKIP = {"node_modules", ".git", "site-packages", "__pycache__", "$recycle.bin", "system volume information",
                "windows", "program files", "program files (x86)", "programdata", "appdata", ".cache", "cache", "caches",
                ".npm", ".cargo", ".rustup", ".gradle", ".m2", ".venv", "venv", ".trash", ".faster", ".pc_optimizer"}


def _read_text(fp, ext, size):
    try:
        if ext in _OFFICE_EXT:
            import zipfile
            with zipfile.ZipFile(fp) as z:
                names = [n for n in z.namelist() if n in ("word/document.xml", "xl/sharedStrings.xml")
                         or n.startswith("ppt/slides/slide")]
                xml = " ".join(z.read(n)[:4_000_000].decode("utf-8", "ignore") for n in names[:30])
            return re.sub(r"<[^>]+>", " ", xml)
        with open(fp, "rb") as f:
            raw = f.read(2_000_000)
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return raw.decode("utf-16", "ignore")
        if b"\x00" in raw[:1024]:
            return None
        return raw.decode("utf-8", "ignore")
    except Exception:
        return None


def scan_secrets(root, wl="auto", max_seconds=900):
    """扫描 root 下的文本/Office 文件。返回 (findings, 已扫描文件数)；
    findings: dict(path, kind, level, detail, line, cloud)"""
    if wl == "auto":
        wl = get_wordlist()
    root, deadline = Path(root), time.time() + max_seconds
    res, scanned = [], 0
    for r, dirs, files in os.walk(root, onerror=lambda e: None):
        if time.time() > deadline:
            break
        if Path(r) == HOME / "Library":                 # macOS：只看 iCloud 云盘
            dirs[:] = [d for d in dirs if d == "Mobile Documents"]
        else:
            dirs[:] = [d for d in dirs if d.lower() not in _SECRET_SKIP and not os.path.islink(os.path.join(r, d))
                       and not d.lower().endswith((".app", ".photoslibrary", ".framework"))]
        for f in files:
            fp = os.path.join(r, f)
            ext = os.path.splitext(f)[1].lower()
            cloud = cloud_hint(fp)
            if _NAME_HINT.search(f):
                res.append(dict(path=fp, kind="文件名可疑", level="提示", detail="文件名暗示里面可能存放助记词/私钥",
                                line=0, cloud=cloud))
            if ext not in _TEXT_EXT and ext not in _OFFICE_EXT:
                continue
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            if size > (8_000_000 if ext in _OFFICE_EXT else 2_000_000) or size < 20:
                continue
            text = _read_text(fp, ext, size)
            scanned += 1
            if not text:
                continue
            for kind, level, detail, line in scan_text(text, wl):
                if cloud:
                    level, detail = "高危", detail + f"；位于 {cloud} 同步目录，云端可能已有副本"
                res.append(dict(path=fp, kind=kind, level=level, detail=detail, line=line, cloud=cloud))
    order = {"高危": 0, "中危": 1, "提示": 2}
    res.sort(key=lambda x: order[x["level"]])
    return res, scanned


# ============================================================ 3. 挖矿木马检测
MINER_NAMES = ("xmrig", "xmr-stak", "xmrstak", "minerd", "cpuminer", "cgminer", "bfgminer", "ethminer", "nbminer",
               "t-rex", "phoenixminer", "lolminer", "gminer", "nanominer", "teamredminer", "kawpowminer", "claymore",
               "ccminer", "srbminer", "minergate", "nicehash", "bzminer", "kdevtmpfsi", "kinsing")
MINER_CMD = re.compile(
    r"(stratum\+(tcp|ssl|tls)://|--donate-level|--algo[ =]|cryptonight|randomx|--coin[ =]|ethermine|nanopool|f2pool|"
    r"2miners|hashvault|supportxmr|minexmr|moneroocean|nicehash|unmineable|herominers|antpool|viabtc|poolin\.)", re.I)
MINER_PORTS = {3333, 4444, 5555, 7777, 14433, 14444, 45700}
_TMP_HINTS = ("/tmp/", "/var/tmp/", "/dev/shm/", "/appdata/local/temp/")


def detect_miners(sample=3.0):
    """返回 dict(findings=[{level,msg,pid,name,cpu}], top=[(pid,name,cpu)])"""
    if not psutil:
        return dict(findings=[dict(level="提示", msg="需要安装 psutil 才能检测挖矿进程（pip install psutil）", pid=None, name="", cpu=0)], top=[])
    procs = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            p.cpu_percent(None)
            procs.append(p)
        except Exception:
            pass
    time.sleep(sample)
    # 网络：pid -> 远端端口集合
    ports = {}
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_ESTABLISHED and c.raddr and c.pid:
                ports.setdefault(c.pid, set()).add(c.raddr.port)
    except Exception:
        pass
    findings, top = [], []
    for p in procs:
        try:
            cpu = p.cpu_percent(None)
            name = p.info["name"] or ""
            top.append((p.pid, name, cpu))
            try:
                cmd = " ".join(p.cmdline())
                exe = _norm(p.exe() or "")
            except Exception:
                cmd, exe = "", ""
            reasons = []
            if any(k in name.lower() for k in MINER_NAMES):
                reasons.append("进程名匹配已知挖矿程序")
            if MINER_CMD.search(cmd):
                reasons.append("命令行含矿池地址/挖矿参数")
            bad_ports = sorted(ports.get(p.pid, set()) & MINER_PORTS)
            if bad_ports:
                reasons.append(f"连接常见矿池端口 {bad_ports}")
            in_tmp = any(h in exe for h in _TMP_HINTS)
            if cpu >= 70 and in_tmp:
                reasons.append(f"CPU {cpu:.0f}% 且从临时目录运行")
            if not reasons:
                continue
            strong = (reasons[0].startswith(("进程名", "命令行"))) or (bad_ports and cpu >= 30)
            findings.append(dict(level="高危" if strong else "中危", pid=p.pid, name=name, cpu=cpu,
                                 msg="；".join(reasons) + ("（若是你自己运行的矿工可忽略）" if strong else "")))
        except Exception:
            pass
    top.sort(key=lambda x: -x[2])
    return dict(findings=findings, top=top[:8])


# ============================================================ 4. 剪贴板地址劫持检测
def lookalike(a, b):
    """首尾相同、中间不同：地址投毒 / 剪贴板劫持常用的“相似地址”"""
    a, b = a.strip(), b.strip()
    a2, b2 = (a[2:] if a.lower().startswith("0x") else a), (b[2:] if b.lower().startswith("0x") else b)
    return a != b and len(a2) >= 12 and len(b2) >= 12 and a2[:4].lower() == b2[:4].lower() and a2[-4:].lower() == b2[-4:].lower()


class ClipboardGuard:
    """只在内存里保存最近复制的地址（不写盘、不上传）"""

    def __init__(self, window=15.0, keep=20):
        self.window, self.last, self.recent = window, None, deque(maxlen=keep)
        self.suspect = set()          # 被判定为“疑似替换”的地址

    def feed(self, text, now=None):
        now = time.time() if now is None else now
        kind = classify_address(text)
        if not kind:
            return None
        s, alert = text.strip(), None
        if self.last and self.last[0] == s:
            return None
        if self.last and self.last[1] == kind and now - self.last[2] <= self.window:
            old = self.last[0]
            if lookalike(old, s):
                alert = dict(level="高危", old=old, new=s,
                             msg=f"剪贴板里的 {kind} 地址在 {now - self.last[2]:.0f} 秒内被换成了一个“首尾相同、中间不同”的地址"
                                 f"（{mask_addr(old)} → {mask_addr(s)}），极可能是剪贴板劫持！请勿转账，并立即查杀。")
            else:
                alert = dict(level="中危", old=old, new=s,
                             msg=f"剪贴板里的 {kind} 地址在 {now - self.last[2]:.0f} 秒内变成了另一个地址"
                                 f"（{mask_addr(old)} → {mask_addr(s)}）。如果这不是你自己的操作，请警惕。")
        if alert and alert["level"] == "高危":
            self.suspect.add(s)          # 疑似劫持的地址：不计入“你复制过的地址”，也不更新基准
            return alert
        self.recent.append((s, kind, now))
        self.last = (s, kind, now)
        return alert

    def verify(self, pasted, now=None, horizon=1800):
        """校验你在钱包/交易所里看到的收款地址，是否和你复制的一致"""
        now = time.time() if now is None else now
        s = (pasted or "").strip()
        kind = classify_address(s)
        if not kind:
            return "提示", "这不是有效的区块链地址（格式或校验位不对）——请检查是否复制完整。"
        if s in self.suspect:
            return "高危", "这个地址之前被判定为“疑似替换”的地址，请勿使用，并立即查杀电脑。"
        cand = [a for a, k, t in self.recent if k == kind and now - t <= horizon]
        if s in cand:
            return "正常", "与你最近复制的地址完全一致。"
        if any(lookalike(a, s) for a in cand):
            return "高危", "与你复制的地址首尾相同但中间不一致——疑似被替换（剪贴板劫持/地址投毒）。请重新复制并逐位核对。"
        return "提示", "该地址不在最近 30 分钟的复制记录里（监控未开启或已过期），无法比对。"


# ============================================================ 5. 区块链数据目录识别
def known_chain_dirs():
    """扫描常见区块链软件的数据目录；返回 [dict(name,path,total,resync,wallet,note)]"""
    H = HOME
    appdata = Path(os.environ.get("APPDATA", H / "AppData/Roaming"))
    local = Path(os.environ.get("LOCALAPPDATA", H / "AppData/Local"))
    pdata = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
    sup = H / "Library/Application Support"

    def P(win, mac, linux):
        return win if IS_WIN else mac if IS_MAC else linux

    specs = [
        ("Bitcoin Core", P(appdata / "Bitcoin", sup / "Bitcoin", H / ".bitcoin"), ["blocks", "chainstate", "indexes"], ["wallets", "wallet.dat"], ""),
        ("Litecoin Core", P(appdata / "Litecoin", sup / "Litecoin", H / ".litecoin"), ["blocks", "chainstate"], ["wallets", "wallet.dat"], ""),
        ("Dogecoin Core", P(appdata / "DogeCoin", sup / "Dogecoin", H / ".dogecoin"), ["blocks", "chainstate"], ["wallets", "wallet.dat"], ""),
        ("Ethereum (geth)", P(local / "Ethereum", H / "Library/Ethereum", H / ".ethereum"), ["geth/chaindata", "geth/lightchaindata", "geth/ethash"], ["keystore"], ""),
        ("Monero", P(pdata / "bitmonero", H / ".bitmonero", H / ".bitmonero"), ["lmdb"], [], "钱包文件通常在别处，请先在 Monero 软件里确认钱包位置"),
        ("IPFS (Kubo)", H / ".ipfs", ["blocks"], ["keystore", "config"], "blocks 里可能有只存在于本机的固定内容，删除前请确认"),
        ("Reth", None if IS_WIN else P(None, sup / "reth", H / ".local/share/reth"), ["db", "static_files"], [], ""),
        ("Erigon", None if IS_WIN else P(None, sup / "erigon", H / ".local/share/erigon"), ["chaindata", "snapshots"], ["nodekey"], ""),
        ("Lighthouse", None if IS_WIN else H / ".lighthouse", ["mainnet/beacon"], ["validators", "secrets"], "validators/secrets 含验证者密钥，切勿删除"),
        ("Electrum", P(appdata / "Electrum", H / ".electrum", H / ".electrum"), [], ["wallets"], "只有钱包，没有区块数据"),
        ("Exodus", P(appdata / "Exodus", sup / "Exodus", H / ".config/Exodus"), [], ["exodus.wallet"], "只有钱包，没有区块数据"),
    ]
    out = []
    for name, path, resync, wallet, note in specs:
        if not path or not Path(path).is_dir():
            continue
        path = Path(path)
        rs = [(s, dir_size(path / s)) for s in resync if (path / s).exists()]
        ws = [(s, dir_size(path / s) if (path / s).is_dir() else _size(path / s)) for s in wallet if (path / s).exists()]
        out.append(dict(name=name, path=str(path), total=dir_size(path), resync=rs, wallet=ws, note=note))
    out.sort(key=lambda e: -e["total"])
    return out


def _size(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return 0
