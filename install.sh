#!/usr/bin/env bash
# Instaluje Fa milię dla bieżącego użytkownika (bez sudo) i dodaje ją do menu KDE.
#
# Użycie:
#   ./install.sh               – instalacja (jeśli trzeba, najpierw zbuduje program)
#   ./install.sh --odinstaluj  – usunięcie programu z menu (dane użytkownika zostają)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor"
TARGET="$BIN_DIR/fa-milia"
DESKTOP="$APPS_DIR/fa-milia.desktop"

refresh_menu() {
    # Odświeżenie menu i ikon – brak tych narzędzi nie jest błędem.
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
    gtk-update-icon-cache -q -t "$ICONS_DIR" 2>/dev/null || true
    kbuildsycoca6 2>/dev/null || kbuildsycoca5 2>/dev/null || true
}

if [ "${1:-}" = "--odinstaluj" ]; then
    rm -f "$TARGET" "$DESKTOP" \
          "$ICONS_DIR/scalable/apps/fa-milia.svg" "$ICONS_DIR/256x256/apps/fa-milia.png"
    refresh_menu
    echo "Usunięto Fa milię z menu. Dane (kategorie, zapisy) zostały w ~/.local/share/fa-milia."
    exit 0
fi

if [ ! -x "$ROOT/dist/fa-milia" ]; then
    echo "Brak zbudowanego programu – buduję (to potrwa kilka minut)…"
    "$ROOT/packaging/build_linux.sh"
fi
if [ ! -f "$ROOT/dist/fa-milia" ]; then
    echo "Nie znaleziono pliku dist/fa-milia. Zbuduj program: packaging/build_linux.sh"
    exit 1
fi

install -Dm755 "$ROOT/dist/fa-milia" "$TARGET"
install -Dm644 "$ROOT/fa_milia/resources/icon.svg" "$ICONS_DIR/scalable/apps/fa-milia.svg"
install -Dm644 "$ROOT/fa_milia/resources/icon.png" "$ICONS_DIR/256x256/apps/fa-milia.png"
mkdir -p "$APPS_DIR"
# W pliku .desktop wpisujemy pełną ścieżkę do programu.
sed "s|@EXEC@|\"$TARGET\"|" "$ROOT/packaging/fa-milia.desktop" > "$DESKTOP"
chmod 644 "$DESKTOP"
refresh_menu

echo "Zainstalowano: $TARGET"
echo "Fa milia jest w menu KDE (kategoria Gry). Możesz też uruchomić: fa-milia"
