#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.10 or newer is required. Install Python 3 and try again." >&2
    exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "Python 3.10 or newer is required. Detected: $(python3 --version)" >&2
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating this tool's private Python environment..."
    if ! python3 -m venv .venv; then
        echo "Could not create the environment. On Debian/Ubuntu, install it with:" >&2
        echo "  sudo apt install python3-venv" >&2
        exit 1
    fi
fi

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
if ! "$VENV_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "The existing .venv uses Python older than 3.10. Remove .venv and retry." >&2
    exit 1
fi
echo "Checking required packages..."
"$VENV_PYTHON" -m pip install --disable-pip-version-check -r requirements.txt
exec "$VENV_PYTHON" start_backup.py
