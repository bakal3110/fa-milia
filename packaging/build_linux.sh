#!/usr/bin/env bash
# Buduje plik wykonywalny dist/fa-milia (Linux).
# Użycie:  packaging/build_linux.sh          – jeden plik
#          packaging/build_linux.sh folder   – folder z programem
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo "Tworzę środowisko wirtualne .venv…"
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements-dev.txt

if [ "${1:-}" = "folder" ]; then
    export FA_MILIA_ONEDIR=1
fi
.venv/bin/pyinstaller --noconfirm --clean --distpath dist --workpath build packaging/fa-milia.spec
echo
echo "Gotowe: $(pwd)/dist/fa-milia"
