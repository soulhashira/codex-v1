#!/usr/bin/env bash
set -euo pipefail

# Find a suitable Python >= 3.8
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)')
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.8+ is required but not found."
    exit 1
fi
echo "Found $PYTHON ($version)"

# Check for pip
if ! "$PYTHON" -m pip --version &>/dev/null; then
    echo "Error: pip is not installed for $PYTHON."
    exit 1
fi

# Install in editable mode (system-wide)
echo "Installing codex..."
sudo "$PYTHON" -m pip install --break-system-packages -e "$(dirname "$0")"

echo ""
echo "Done! Run 'codex' to start your journal."
