#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# install.sh — Install AI Remove Background plugin for GIMP 3.x
#
# Usage:  chmod +x install.sh && ./install.sh
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PLUGIN_NAME="ai-remove-background-g3"
PLUGIN_FILE="ai-remove-background-g3.py"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMBG_VENV="$HOME/.rembg"

# ── Detect OS ─────────────────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        *)       echo "unknown" ;;
    esac
}

OS="$(detect_os)"

if [ "$OS" = "unknown" ]; then
    echo "ERROR: This install script supports Linux and macOS only."
    echo "For Windows, see the manual installation steps in README.md."
    exit 1
fi

# ── Find GIMP plug-ins directory ──────────────────────────────────────────────

find_gimp_plugin_dir() {
    local candidates=()

    if [ "$OS" = "linux" ]; then
        # Check for 3.2 first (newer), then 3.0, then any 3.x
        candidates=(
            "$HOME/.config/GIMP/3.2/plug-ins"
            "$HOME/.config/GIMP/3.0/plug-ins"
        )
        # Also check for any other 3.x versions
        for d in "$HOME/.config/GIMP"/3.*/plug-ins; do
            [ -d "$d" ] && candidates+=("$d")
        done
    elif [ "$OS" = "macos" ]; then
        candidates=(
            "$HOME/Library/Application Support/GIMP/3.2/plug-ins"
            "$HOME/Library/Application Support/GIMP/3.0/plug-ins"
        )
        for d in "$HOME/Library/Application Support/GIMP"/3.*/plug-ins; do
            [ -d "$d" ] && candidates+=("$d")
        done
    fi

    # Return the first existing directory
    for dir in "${candidates[@]}"; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done

    # Nothing found — default to 3.0 and create it
    if [ "$OS" = "linux" ]; then
        echo "$HOME/.config/GIMP/3.0/plug-ins"
    else
        echo "$HOME/Library/Application Support/GIMP/3.0/plug-ins"
    fi
}

GIMP_PLUGINS_DIR="$(find_gimp_plugin_dir)"

# ── Banner ────────────────────────────────────────────────────────────────────

echo "=============================================="
echo "  AI Remove Background — GIMP 3.x Installer"
echo "=============================================="
echo ""
echo "  OS detected:    $OS"
echo "  Plugin dir:     $GIMP_PLUGINS_DIR"
echo "  rembg venv:     $REMBG_VENV"
echo ""

# ── Check for plugin source file ──────────────────────────────────────────────

if [ ! -f "$SCRIPT_DIR/$PLUGIN_FILE" ]; then
    echo "ERROR: Cannot find $PLUGIN_FILE in $SCRIPT_DIR"
    echo "Make sure you run this script from the project directory."
    exit 1
fi

# ── Check for Python 3 ───────────────────────────────────────────────────────

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        major=$(echo "$version" | cut -d. -f1)
        if [ "$major" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 is required but not found."
    echo "Install Python 3 and try again."
    exit 1
fi

echo "  Python found:   $PYTHON ($($PYTHON --version 2>&1))"
echo ""

# ── Set up rembg virtual environment ─────────────────────────────────────────

if [ -f "$REMBG_VENV/bin/python" ]; then
    echo "[OK] rembg virtual environment already exists at $REMBG_VENV"

    # Check if rembg is actually installed
    if "$REMBG_VENV/bin/python" -m rembg.cli --help &>/dev/null; then
        echo "[OK] rembg is installed and working"
    else
        echo "[..] rembg not found in venv, installing..."
        "$REMBG_VENV/bin/pip" install --upgrade rembg
        echo "[OK] rembg installed"
    fi
else
    echo "[..] Creating rembg virtual environment at $REMBG_VENV ..."
    "$PYTHON" -m venv "$REMBG_VENV"
    echo "[..] Installing rembg (this may take a minute)..."
    "$REMBG_VENV/bin/pip" install --upgrade pip
    "$REMBG_VENV/bin/pip" install rembg
    echo "[OK] rembg installed"
fi

echo ""

# ── Install the plugin ───────────────────────────────────────────────────────

DEST_DIR="$GIMP_PLUGINS_DIR/$PLUGIN_NAME"

echo "[..] Installing plugin to $DEST_DIR ..."

mkdir -p "$DEST_DIR"
cp "$SCRIPT_DIR/$PLUGIN_FILE" "$DEST_DIR/$PLUGIN_FILE"
chmod +x "$DEST_DIR/$PLUGIN_FILE"

echo "[OK] Plugin installed"
echo ""

# ── Verify ────────────────────────────────────────────────────────────────────

echo "=============================================="
echo "  Installation complete!"
echo "=============================================="
echo ""
echo "  Plugin:  $DEST_DIR/$PLUGIN_FILE"
echo "  rembg:   $REMBG_VENV/bin/python"
echo ""
echo "  Restart GIMP, then find the plugin at:"
echo "  Filters > AI > AI Remove Background..."
echo ""
