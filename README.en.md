# Faster v0.5.0 · Usage & build guide

[中文](README.md) | **English**

Faster is a cross-platform (Windows / macOS / Linux) PC cleaner and wallet-safety helper: it frees disk space, speeds up your computer, scans for risks, and protects crypto wallets. It has a GUI, a CLI, and scheduled auto-cleaning.

Deliverables:
- Windows: `Faster-0.5.0.exe` (single file, double-click to run)
- macOS: `Faster-0.5.0.dmg` (open it and drag Faster into “Applications”)

PyInstaller cannot cross-compile — **build the Windows version on Windows and the Mac version on a Mac**. Pick either way:

## Option A: one-click cloud build on GitHub (recommended, no local setup)
1. Create a new GitHub repository and upload **everything** in this folder (including the hidden `.github` directory).
2. Open **Actions → Build Faster → Run workflow** in the repository.
3. After about 3–5 minutes, download `Faster-<version>-windows` and `Faster-<version>-macos` from **Artifacts** at the bottom of the run page.
   (To publish a Release: create a tag, e.g. `git tag v1.0.0 && git push --tags`; a download page is generated automatically.)

## Option B: build on your own computer
- **Windows**: install Python 3.9+ (tick “Add to PATH”) → double-click `build_windows.bat` → `dist\Faster-<version>.exe`
- **macOS**: run `bash build_mac.sh` in Terminal → `dist/Faster-<version>.dmg`. The script creates a virtual environment automatically (so you won't hit the externally-managed-environment error).
  If tkinter is missing: Homebrew users run `brew install python-tk`, or install the official Python from python.org.

## System warnings on first run (expected while the app is not code-signed)
- **Windows SmartScreen**: click “More info” → “Run anyway”. Some antivirus programs may flag PyInstaller apps; add Faster to the allow list yourself.
  To remove the warning completely you need a code-signing certificate to sign the exe.
- **macOS**: if you see “cannot verify the developer / is damaged”, **right-click → Open** in “Applications”; if that is not enough, run in Terminal:
  `xattr -cr /Applications/Faster.app`. (Public distribution needs an Apple Developer account for signing + notarization.)
- **Intel Macs**: `macos-latest` produces an Apple-silicon build. For an Intel build, use Option B on an Intel Mac.

## Notes
- The scheduled auto-clean task records the program's location. **Do not move or rename the program after enabling the scheduled task**; if you did, click “Save and enable scheduled task” again.
- On macOS, to auto-clean folders such as Documents/Downloads, add Faster under System Settings → Privacy & Security → Full Disk Access.
- Run one clean-up without the GUI: `Faster.exe --auto-clean` (add `--dry-run` for a dry run).

## Versioning (v0.1.0 is the baseline)
- Change the version only in `__version__` at the top of `faster.py`; the window title, `--version`, the dmg/exe file names and the Mac app info follow automatically.
- To release a new version, commit and push a tag; GitHub then builds and publishes automatically (for the current version):
  ```
  git add . && git commit -m "v0.5.0"
  git tag v0.5.0 && git push origin main v0.5.0
  ```
- Changes for every version are recorded in `CHANGELOG.md`.

## How administrator rights work
The program normally runs as a standard user (safer) and elevates **only when needed**. Buttons and prompts marked 🛡 guide you:

| Feature that needs administrator rights | How it is triggered |
|---|---|
| System-level junk cleaning (Windows system temp / update cache, macOS /Library/Caches, Linux apt cache / logs) | Junk cleanup tab → 🛡 Clean system-level junk (admin) |
| Disable / restore system-level startup items (HKLM, /Library/LaunchAgents) | Click “Disable selected” as usual; on failure you are asked “authorize and retry?” |
| Complete port / process scan | Risk scan tab → 🛡 Admin scan (more complete) |
| Remove apps in macOS /Applications | If uninstalling fails you are asked to authorize and retry |

Authorization window: UAC prompt on Windows, the system password box on macOS, a polkit window on Linux (needs pkexec).
**Windows, to authorize everything at once**: on the Overview tab click “Restart as administrator”.
Elevation only runs built-in fixed actions, never arbitrary commands. Scheduled auto-clean still only cleans user-level content and needs no administrator rights.

## v0.2 Wallet security (the “Wallet security” tab)
| Sub-tab | What it does | Notes |
|---|---|---|
| Wallet files | Finds wallet files on this machine and flags cloud-sync risk | These files are skipped automatically by every cleaning feature |
| Blockchain data | Identifies node / wallet data folders and how much can be re-synced | Reports only, never deletes automatically |
| Key leak scan | Finds mnemonics / private keys saved in plaintext | Never echoes content; code/config files are not read by default (opt-in); images/screenshots, sticky-note databases and PDFs are out of scope |
| Miner detection | Finds mining trojans | Miners you run yourself are flagged too (the High entry says so) |
| Clipboard guard | Detects swapped addresses; verifies payee addresses | Must be turned on manually; records only in memory |

**BIP39 word list**: the checksum check for mnemonics needs the official English word list. Packaged builds download and bundle it at build time (`fetch_wordlist.py`; after download it is verified by structure + the official test vectors, and rejected if it fails).
When running from source, you are asked before scanning whether to download it (or click “View word list” on the “Key leak scan” sub-tab). **Without the word list, mnemonics are not detected** (no more keyword guessing); only private keys are checked.

**Run the tests**: `python -m unittest discover -s tests -v`

**Important**: Faster will never ask you for a mnemonic or private key. If a scan finds a plaintext mnemonic/private key, the safest course is to move your assets to a freshly generated wallet, write the new mnemonic on paper and keep it offline, then delete or encrypt the old plaintext files. “Delete” on an SSD does not guarantee the data cannot be recovered.

## v0.5 Developer cleanup, space analysis, disk health
**Developer cleanup** (the “Developer cleanup” tab): on a developer's machine the biggest “junk” is usually the caches of package managers and build tools, plus the dependency folders of old projects.
- **Caches**: npm, Yarn, pnpm, pip, cargo, Go (build / module caches), Gradle, Maven, NuGet, Xcode (DerivedData / DeviceSupport), CocoaPods, Homebrew, Conda, JetBrains IDEs, VS Code, and Docker's reclaimable build cache and unused images. Only what actually exists on this computer is listed.
- **Old project dependencies**: click “Find old project dependencies” to find `node_modules`, Python virtual environments (`venv` / `.venv`) and Rust `target` folders in projects untouched for more than N days (90 by default, adjustable). It honours the excluded folders set on the “Large files” tab.
- All of this can be **regenerated** (re-downloaded / rebuilt), so cleaning is safe; the next use is just a bit slower and needs the network. **Caches are deleted permanently**; **old project dependency folders go to the Recycle Bin** and can be restored from the “Restore center”. Wallet files are never touched.
- When the diagnosis finds large developer caches, a “Clean developer caches” button appears there, and at the top of this tab.

**Space analysis** (the “Space analysis” tab): draws disk usage as a **treemap** — the bigger the tile, the more space it uses. Click a tile to select it, **double-click a folder to open it**, “Up one level” to go back; you can “Move to Recycle Bin” or “Show in folder” for the selected item. Grey tiles are files and light grey is the total of many small items. When the diagnosis finds low disk space it offers a “View space usage” button that brings you here.

**Disk health** (the “Storage” category of the diagnosis): reads the health status the system reports, read-only — Windows' Get-PhysicalDisk health (plus wear, temperature and read/write errors when available); macOS SMART status; Linux `smartctl -H` (needs smartmontools and usually administrator rights; a command to copy is provided). If a drive shows “unhealthy / failing”, **back up your important data right away**.

## v0.4 Updates & hardening, program signatures, baseline, exclusions, new look
All of these checks live under “Diagnosis”: “One-click diagnosis” runs them together, and the sub-tabs of the “Diagnosis” tab let you look at and handle each one on its own.

**Hardening & updates** (sub-tab): lists system updates, disk encryption, remote login, auto login, screen lock, backups, high-risk open ports and more. Select a row and click “Fix the selected item”: Faster **opens the matching system settings** or gives you a **command to copy**. Changes that need administrator rights (for example turning SMBv1 off) are never made for you. Tick “Include online checks” to ask the system's update service which updates are still not installed (slower).

**Program signatures** (sub-tab): checks whether programs that start automatically, and programs running from user folders, carry a trusted signature (Windows: Authenticode; macOS: codesign, ad-hoc signatures count as unsigned; Linux has no general signing, so it checks whether the file belongs to an installed package). You can disable a startup item, end a process, or copy a file's SHA-256 (paste it into a site such as VirusTotal). Unsigned does not mean harmful and a valid signature does not guarantee safety; judge by where the program came from.

**Baseline comparison** (sub-tab): when you are sure the computer is clean, click “Set as baseline” (it records startup items, scheduled tasks, externally listening ports, hosts entries, administrator accounts, SSH authorized keys and installed programs). From then on you are only told **what is new**; a new administrator account or SSH key is flagged “Critical”. If you installed something yourself, click “Accept current state as new baseline”.

**Exclusions** (top of the “Large files” and “Duplicates” tabs): tick the **file types** you do not want scanned (video, images, audio, documents, archives, disk images / virtual machines, or add other extensions such as `.psd`) and use the **folder picker** to add **folders** you do not want scanned (subfolders included). Each page keeps its own settings, saved for next time; the deep diagnosis honours them too.

**New look**: consistent colors and fonts, a banner and resource cards on the Overview tab, a health-score gauge and colored cards on the Diagnosis tab, zebra-striped tables and highlighted primary buttons. If the styling cannot be applied it silently falls back to the system default look and everything still works; macOS keeps its native controls.

## Diagnosis center: one click, then fix with buttons (v0.5.0)
**How to use**: on the Overview tab click **🔍 One-click diagnosis** (or open the “Diagnosis” tab and click “Start diagnosis”). It is read-only and changes nothing; a quick diagnosis takes about 10–30 seconds and can be cancelled any time with the “Cancel” button at the bottom.

**Four categories are checked**
| Category | What is checked |
|---|---|
| Performance | Memory, swap, CPU, number of startup items, uptime, Windows power plan |
| Storage | Free disk space, reclaimable junk, Recycle Bin size, **developer caches** (npm / pip / Gradle / Xcode / Docker…), **disk health** (SMART); (deep) large files, duplicate files, dependency folders of long-untouched projects |
| Security | System protection (firewall / Defender / Gatekeeper / SIP), suspicious startup items, mining trojans, modified hosts file, **program signatures** (do auto-start programs and programs running from user folders carry a trusted signature?), **baseline comparison** (what is new compared with the “clean state” you recorded); (deep) processes and ports, scheduled tasks, executables in temp folders |
| Hardening & updates | **System updates** (Windows patch age / restart pending; macOS automatic-update switches; Linux upgradable packages and security updates), software that is no longer maintained (Flash, QuickTime, Python 2, Java 6/7…), **security hardening** (disk encryption, auto login, Remote Desktop / SSH, UAC, SMBv1, screen lock, backups, high-risk open ports); (deep, online) which updates are still not installed |
| Wallet | Wallet files and plaintext mnemonics/private keys in cloud-synced folders, whether the BIP39 word list is ready; (deep) wallet files and plaintext keys in your whole home folder |

**Reading the result**: at the top you see the overall **health score** and one score per category (starts at 100; −25 per “Critical”, −10 per “Warning”; “Info” costs nothing). Every problem is a card: level (Critical / Warning / Info / Good), current state, advice, and **action buttons** on the right. Only problems are shown by default; tick “Show items that are fine” to see everything.

**Two kinds of buttons**
- **Run directly**: clean junk, empty the Recycle Bin, disable suspicious startup items, disable high-impact startup items, end a heavy program, open the system security / firewall / power settings, download the BIP39 word list… Every button that changes something **asks you to confirm first**, and the card then shows “✓ Done”.
- **Jump**: takes you to the matching page and starts the scan automatically (for example “View large files” immediately starts a large-file scan).

**The target pages list the suggested actions too**: after a diagnosis, the matching pages show a “💡 Suggested actions (from the last diagnosis)” panel at the top with the actions you can run right there — Junk cleanup (clean junk), Restore center (empty the Recycle Bin), Startup / Startup impact (disable), Processes (end a process), Risk scan (open system security settings), Wallet security (end a miner process, download the word list). The panel hides itself when there is nothing to suggest.

**Deep diagnosis**: tick “Deep diagnosis” to also check large files, duplicates, wallet files and plaintext keys across the whole home folder, and run a deep risk scan; this can take a few minutes.

The “Diagnosis” tab has two more sub-tabs: **Startup impact** (estimates each startup item's memory and average CPU, sorted by impact, with a disable button; it is based on the *running* process and is not an exact boot time) and **Before/after** (every clean-up, startup-item disable or process kill records a “before” and “after” state automatically; compare any two entries).

## Cancel, progress & Restore center (v0.3)
**Cancel & progress**: for long operations (junk scan, large files, duplicates, wallet files, blockchain data, key leak scan, diagnostics) the status bar shows the current progress and a “Cancel” button; after cancelling, the partial results scanned so far are kept.

**Restore center** (one place to see and undo what Faster moved away or disabled):
- **Files in the tool's trash**: restored to their original location; if a file with the same name already exists there, a “(restored)” suffix is added — **nothing is ever overwritten**. You can also delete them permanently or empty the trash.
- **Files in the system trash**: only a record is kept (90 days); click “Open system trash” to restore them yourself.
- **Disabled startup items**: can be restored (system-level ones ask for authorization).
- Caches deleted by “Junk cleanup” are **deleted permanently** and not listed here; wallet files are never moved.
- Note: moving a file to the trash **does not free disk space immediately** — space is only freed after you empty the trash.

CLI menu `10`: performance diagnosis (read-only).

## Interface language (中文 / English)
- By default it follows the system language. Switch in any of these ways:
  - GUI: the **语言 / Language** drop-down at the top of the Overview tab (Follow system / 简体中文 / English); choose one and restart when prompted;
  - CLI menu: choose `9`;
  - Command-line option: `--lang en` or `--lang zh` (this run only); environment variable `FASTER_LANG=en`;
  - Settings file: `"language"` in `~/.faster/settings.json` (`zh` / `en` / `auto`).
- Scheduled auto-clean and the administrator helper process use the same language setting; logs and reports are written in the current language.
- The console output of the build scripts (`build_*.bat/.sh`, `fetch_wordlist.py`) is currently Chinese only.
- **To add a new language**: copy `faster_i18n_en.py` to `faster_i18n_xx.py` and fill in `CATALOG` (the key is the Chinese source text; keep the `{0}` `{1}` placeholders); add one line each in `LANGUAGES` and `_CATALOGS` in `faster_i18n.py`; run `python tools/i18n_check.py` to find gaps.
- **Development rule**: write every user-facing string as `tr("中文原文 {0}", args)` instead of a bare Chinese string (regular expressions excepted); `tests/test_i18n.py` enforces this.

## About the BIP39 word list
- Source: <https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt> (the official English word list, 2048 words). The program downloads the raw version of the same file and verifies it twice: structure (2048 distinct words, sorted alphabetically, first 4 letters unique) + the official BIP39 test vectors; if either fails it is not used.
- **The list is fixed**: changing any single word would invalidate existing wallets' mnemonics, so the English list has not changed since 2013; only new languages may be added in future, never edits to existing lists.
- **Other languages exist**: the official repository also has Japanese, Korean, Spanish, Simplified Chinese, Traditional Chinese, French, Italian, Czech and Portuguese (9 more). In practice almost all wallets use English; Faster currently checks only the English list.
- Other kinds of “mnemonics” are not BIP39 and are not covered: Electrum's own seed format, Trezor's SLIP39 (Shamir backup, 1024-word list) and Monero's 25-word mnemonic.
- **Bundling into the program**: `fetch_wordlist.py` downloads, verifies and bundles it at build time. To make builds fully offline-capable: run `python fetch_wordlist.py` once on a connected computer and commit the generated `bip39_english.txt` to the repository.
- Under “Wallet security → Key leak scan → View word list” you can see all words, the source, the file path and the SHA-256.

## FAQ
  ```
  macOS Gatekeeper may block it: Faster does not have an Apple developer signature or notarization yet, so the system cannot verify it. This does not mean anything is wrong with the program — use any one of the methods below to allow it.

  Method 1: allow it in System Settings (macOS 15 Sequoia and later)
  First drag Faster from the dmg into “Applications”.
  Double-click to open it once; when the warning above appears, click “Done” or “OK”.
  Open “System Settings → Privacy & Security”, scroll down, find “Faster was blocked”, and click “Open Anyway” next to it.
  Confirm with your login password or Touch ID, then click “Open” again.
  You only need to do this once; afterwards it opens normally with a double-click.

  Method 2: remove the quarantine flag with one command (easiest)
  Open “Terminal” and run:
  xattr -cr /Applications/Faster.app

  Then double-click to open it as usual. If your Faster.app is not in “Applications”, replace the path with its actual location. This command only removes the “downloaded from the internet” flag the system puts on downloaded files; it does not modify the program itself.

  Method 3: older macOS (14 and earlier)
  In “Applications”, right-click Faster → Open → click “Open” again; again you only need to do this once.
  ```
