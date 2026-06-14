#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PYTHON="$VENV_DIR/bin/python"
STAMP_FILE="$VENV_DIR/.nodeflow-runtime-installed"
FORCE_INSTALL=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --reinstall)
            FORCE_INSTALL=1
            shift
            ;;
        --help|-h)
            cat <<'EOF'
Usage: ./scripts/start-nodeflow.sh [--reinstall]

Starts NodeFlow with the local .venv Python.

Options:
  --reinstall   Reinstall runtime dependencies before launch.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run ./scripts/start-nodeflow.sh --help for usage."
            exit 1
            ;;
    esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python not found: $PYTHON_BIN"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    FORCE_INSTALL=1
fi

if [ "$FORCE_INSTALL" -eq 1 ] || [ ! -f "$STAMP_FILE" ]; then
    echo "Installing NodeFlow runtime dependencies"
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -e "$ROOT_DIR"
    touch "$STAMP_FILE"
fi

echo "Starting NodeFlow"
cd "$ROOT_DIR"
exec "$VENV_PYTHON" main.py
