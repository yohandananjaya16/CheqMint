# LedgerDesk

LedgerDesk is a production-oriented Windows 10/11 (64-bit) PySide6 desktop application foundation. It builds as a windowed, self-contained PyInstaller folder and installs per user with Inno Setup. Customers do not need Python, Git, a terminal, or administrator privileges.

## Configure before release

Edit `config.json` and replace `YOUR_ORG`, `Your Company`, URLs, and copyright values. Make the identical publisher/name replacements in `installer/LedgerDesk.iss` and `build.py`. Keep the permanent Inno Setup `AppId` unchanged across releases; changing it creates a separate Installed Apps entry.

The update client only accepts HTTPS release assets from GitHub and requires two assets in each release:

- `LedgerDesk-Setup-X.Y.Z.exe`
- `LedgerDesk-Setup-X.Y.Z.exe.sha256`

The application reads the latest public GitHub Release, compares semantic versions, downloads in a background thread, validates size and SHA-256, launches the signed/verified installer outside the running process, then exits. Inno Setup upgrades the existing per-user installation and starts the new application. User data lives under `%LOCALAPPDATA%\Your Company\LedgerDesk` and is never part of the installation directory.

## Developer setup and build

Install Python 3.12 x64 and [Inno Setup 6](https://jrsoftware.org/isdl.php) on the developer PC only. From a normal PowerShell window in this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -v
python build.py
```

`build.py` cleans prior artifacts, generates Windows version resources, runs PyInstaller, invokes Inno Setup, and writes a SHA-256 sidecar. Outputs are:

If Inno Setup is installed in a custom location, set `LEDGERDESK_ISCC` to the full path of `ISCC.exe` before running the build.

```text
dist\LedgerDesk\
release\LedgerDesk-Setup-1.0.0.exe
release\LedgerDesk-Setup-1.0.0.exe.sha256
```

For the first public release, test `release\LedgerDesk-Setup-1.0.0.exe` on clean Windows 10 and Windows 11 virtual machines. Code-sign both `LedgerDesk.exe` and the final installer with an Authenticode certificate before distribution; the project is structured for this, but a private signing certificate cannot be included in source control.

## Release workflow

1. Change the single value in `version.json` (for example, `1.0.0` to `1.1.0`).
2. Update release notes and run `python -m unittest discover -s tests -v`.
3. Run `python build.py`.
4. Install over the previous version and complete the verification checklist below.
5. Create a GitHub Release whose tag is exactly `v1.1.0`.
6. Add readable Markdown release notes.
7. Upload both generated files from `release\` and publish.

No GitHub token is embedded. Public repositories use the unauthenticated Releases API. For private distribution, use a dedicated authenticated update service rather than shipping a repository token in the executable.

## Verification checklist

- Fresh install: wizard, Desktop/Start shortcuts, taskbar icon, Installed Apps metadata, launch and uninstall.
- Offline: disconnect networking; startup remains usable and only a non-blocking status message appears.
- Current version: manual check shows “You're up to date.”
- Update: publish a test release, choose Later once, then Update Now; verify progress, automatic close/install/restart, and new About version.
- Failure safety: cancel mid-download; use a deliberately wrong sidecar checksum; interrupt networking. In every case, the installed application remains unchanged.
- Upgrade/data: create settings and sample files under the displayed Data Folder, install over the old version, and confirm they survive.
- Uninstall: answer No to data removal and confirm user data survives; repeat and answer Yes to confirm explicit removal.

Automated tests cover semantic versions, invalid metadata, non-GitHub URLs, cancellation, and corrupted downloads. Installer/shortcut/Apps & Features behavior requires a real Windows VM and cannot be truthfully certified by unit tests alone.

## Project layout

```text
app/             GUI, services, configuration, logging, updater
assets/          PNG and multi-resolution ICO branding
installer/       Inno Setup script and generated version resource
tests/           update safety tests
.github/         Windows CI
build.py          one-command release build
LedgerDesk.spec   windowed onedir PyInstaller build
config.json       public application/repository configuration
version.json      single semantic version source
```

## Security and data handling

Do not store passwords, OTPs, tokens, customer records, private keys, or bank credentials in source or logs. `.gitignore` excludes common secret and local-data files. Real cheque templates or databases should use access controls and encryption appropriate to the eventual threat model; this foundation intentionally contains no banking credentials or sample customer data.

