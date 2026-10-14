# Specyfikacja PyInstallera – wspólna dla Linuksa i Windows.
#
# Budowanie (z katalogu projektu):
#   Linux:   packaging/build_linux.sh
#   Windows: packaging\build_windows.bat
#
# Domyślnie powstaje JEDEN plik wykonywalny. Zmienna środowiskowa
# FA_MILIA_ONEDIR=1 tworzy zamiast tego folder z programem i bibliotekami
# (na Windows rzadziej fałszywie oznaczany przez antywirusy).

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # SPECPATH ustawia PyInstaller: folder z tym plikiem
ON_WINDOWS = sys.platform == "win32"
ONEDIR = os.environ.get("FA_MILIA_ONEDIR") == "1"
NAME = "Fa milia" if ON_WINDOWS else "fa-milia"

analysis = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    # Ikona, przykładowe media i dźwięki domyślne – rozpakowywane razem z programem.
    datas=[(str(ROOT / "fa_milia" / "resources"), "fa_milia/resources")],
    hiddenimports=[],
    excludes=[
        # Moduły, których program nie używa – mniejszy plik wynikowy.
        "tkinter",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtPdf",
        "PySide6.QtBluetooth",
        "PySide6.QtSql",
        "PySide6.QtTest",
    ],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

icon = str(ROOT / "fa_milia" / "resources" / "icon.ico") if ON_WINDOWS else None
common = dict(
    name=NAME,
    console=False,  # bez okna konsoli
    icon=icon,
    upx=False,  # kompresja UPX częściej wywołuje fałszywe alarmy antywirusów
)

if ONEDIR:
    exe = EXE(pyz, analysis.scripts, exclude_binaries=True, **common)
    coll = COLLECT(exe, analysis.binaries, analysis.datas, name=NAME, upx=False)
else:
    exe = EXE(pyz, analysis.scripts, analysis.binaries, analysis.datas, **common)
