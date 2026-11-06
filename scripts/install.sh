#!/bin/zsh
# Create .venv, install dependencies and fetch the Camoufox browser.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer targets macOS. The Python CLIs also run on Linux;"
    echo "install requirements.txt manually there." >&2
    exit 1
fi

PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.10–3.12 (brew install python@3.11)." >&2
    exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required; found %s" % sys.version.split()[0])
if sys.version_info >= (3, 13):
    print("Warning: Python 3.13 is untested; 3.10–3.12 is recommended.", file=sys.stderr)
PY

if [[ ! -d .venv ]]; then
    echo "==> Creating .venv"
    "$PYTHON_BIN" -m venv .venv
fi

echo "==> Installing Python dependencies"
.venv/bin/python -m pip install -U pip
.venv/bin/pip install -r requirements.txt

echo "==> Fetching the Camoufox browser (this can take a few minutes)"
.venv/bin/python -m camoufox fetch || {
    echo "Camoufox download failed. Re-run: .venv/bin/python -m camoufox fetch" >&2
}

cat <<'MSG'

==> Done.

Next steps:
  1. Log in once:
       .venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login
  2. Launch:
       ./scripts/etoile_launcher.sh
       ./scripts/lumiere_launcher.sh
  3. Optional: build the .app bundles:
       ./scripts/build_app.sh

Read docs/legal.md before collecting data.
MSG
