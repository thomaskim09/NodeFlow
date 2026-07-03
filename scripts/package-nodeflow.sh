#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TARGET="${1:-auto}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python not found: $PYTHON_BIN"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Installing packaging dependencies"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$ROOT_DIR[dev]"

case "$(uname -s)" in
    Darwin) CURRENT_OS="macos" ;;
    Linux) CURRENT_OS="linux" ;;
    MINGW*|MSYS*|CYGWIN*) CURRENT_OS="windows" ;;
    *) CURRENT_OS="unknown" ;;
esac

if [ "$TARGET" = "auto" ]; then
    TARGET="$CURRENT_OS"
fi

if [ "$TARGET" = "macos" ]; then
    if [ "$CURRENT_OS" != "macos" ]; then
        echo "macOS bundles must be built on macOS."
        exit 1
    fi
    SPEC_FILE="$ROOT_DIR/packaging/macos.spec"
elif [ "$TARGET" = "windows" ]; then
    if [ "$CURRENT_OS" != "windows" ]; then
        echo "Windows bundles must be built on Windows."
        echo "Use scripts/package-nodeflow.ps1 on a Windows machine."
        exit 1
    fi
    SPEC_FILE="$ROOT_DIR/packaging/windows.spec"
else
    echo "Unsupported target: $TARGET"
    echo "Usage: ./scripts/package-nodeflow.sh [macos|windows]"
    exit 1
fi

echo "Packaging NodeFlow for $TARGET"
cd "$ROOT_DIR"
"$VENV_DIR/bin/python" "$ROOT_DIR/scripts/build_app_icons.py" "$TARGET"
exec "$VENV_DIR/bin/pyinstaller" "$SPEC_FILE" --clean
