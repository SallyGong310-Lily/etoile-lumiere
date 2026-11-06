# Setup

Tested on macOS 12–15 with Python 3.11. The launchers are zsh scripts and the
apps use `osascript`, so they are macOS-only. The Python CLIs also run on Linux,
but the `.app` wrappers do not.

## 1. Prerequisites

```bash
xcode-select --install        # command line tools (git, compilers)
brew install python@3.11      # or any Python 3.10–3.12
python3 --version             # should print 3.10, 3.11 or 3.12
```

A TikTok account is required. **Use a dedicated research account.** The session
is stored locally by PyTok under `~/.pytok`; treat that directory like a password.

## 2. Install

```bash
git clone https://github.com/SallyGong310-Lily/etoile-lumiere.git
cd etoile-lumiere
./scripts/install.sh
```

The script:

1. creates `.venv/`;
2. installs `requirements.txt` (including PyTok from its upstream repository);
3. downloads the Camoufox browser (`python -m camoufox fetch`). This is the
   slow part — roughly 300–600 MB.

Manual equivalent:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m camoufox fetch
```

## 3. Log in once

```bash
.venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login
```

A browser window opens. Log in to TikTok, finish any challenge, then return to
the terminal. Check the pool:

```bash
.venv/bin/python -m pytok.accounts.cli list
```

The username is only a local label for the account slot. It does not have to be
an email address.

## 4. Run

```bash
./scripts/etoile_launcher.sh      # market → hashtags → sample size
./scripts/lumiere_launcher.sh     # compare two videos, or analyse any URL(s)
```

Both launchers ask for macOS Automation permission the first time they use
`osascript` to show dialogs. Approve it in *System Settings → Privacy & Security
→ Automation*.

## 5. Build the `.app` bundles (optional)

```bash
./scripts/build_app.sh
open dist/Étoile.app
open dist/Lumière.app
```

The bundles are thin wrappers around `scripts/*_launcher.sh`. Keep them inside
the repository, or set `ETOILE_HOME` / `LUMIERE_HOME` to the repository path.

On first open, macOS may warn that the app is from an unidentified developer.
Right-click → **Open**, or allow it in *System Settings → Privacy & Security*.
The build script signs the bundle ad-hoc; it does not notarize it.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Python environment not found` | `.venv` missing or moved | run `./scripts/install.sh`, or set `ETOILE_PYTHON` |
| `No accounts` after login | login window closed before finishing | re-run the login command, complete the challenge |
| Browser opens but the page never loads | Camoufox not downloaded | `.venv/bin/python -m camoufox fetch` |
| `429` / frequent challenges | too fast, too many requests | increase `--delay` to 6–10 s, reduce `--count` |
| `osascript` dialogs do not appear | Automation permission denied | enable Terminal in *Privacy & Security → Automation* |
| `pytok` install fails | no GitHub access / proxy | install PyTok manually, then `pip install -r requirements.txt` without the first line |
| Excel file has no links | opened in a viewer that strips hyperlinks | open in Excel/Numbers/LibreOffice |

## Updating

```bash
git pull
.venv/bin/pip install -r requirements.txt
```

If PyTok changed its API and the scripts break, pin the commit that worked:

```bash
.venv/bin/pip install "pytok @ git+https://github.com/MEOMcGill/pytok.git@b04636c9c137d5b7622516f74af4d6a12a0d035f"
```

## Uninstall

```bash
rm -rf .venv dist
rm -rf ~/.pytok          # deletes the stored TikTok session
```
