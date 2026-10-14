"""Kopia zapasowa wszystkich danych programu w jednym pliku .zip."""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from fa_milia.core.paths import DataDir

MANIFEST = "fa-milia-kopia.json"  # plik-znacznik w archiwum
PREVIOUS_SUFFIX = "-przed-przywroceniem"


class BackupError(Exception):
    """Błąd tworzenia lub przywracania kopii (komunikat po polsku)."""


def create_backup(data_dir: DataDir, target: Path) -> int:
    """Zapisuje cały katalog danych do pliku .zip. Zwraca liczbę spakowanych plików."""
    count = 0
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {"app": "fa-milia", "version": 1,
                    "created": datetime.now().isoformat(timespec="seconds")}
        archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
        # rglob("*") – wszystkie pliki i katalogi wewnątrz, na dowolnej głębokości.
        for path in sorted(data_dir.root.rglob("*")):
            if path.is_file() and not path.name.endswith(".tmp"):
                archive.write(path, path.relative_to(data_dir.root).as_posix())
                count += 1
    return count


def restore_backup(data_dir: DataDir, source: Path) -> Path:
    """Zastępuje katalog danych zawartością kopii.

    Dotychczasowe dane nie są kasowane od razu – trafiają do katalogu
    „fa-milia-przed-przywroceniem” obok (na wypadek pomyłki). Zwraca jego ścieżkę.
    """
    root = data_dir.root
    staging = root.with_name(root.name + "-przywracanie")
    previous = root.with_name(root.name + PREVIOUS_SUFFIX)
    shutil.rmtree(staging, ignore_errors=True)

    try:
        with zipfile.ZipFile(source) as archive:
            if MANIFEST not in archive.namelist():
                raise BackupError("To nie jest kopia zapasowa programu Fa milia.")
            staging.mkdir(parents=True)
            resolved = staging.resolve()
            for member in archive.infolist():
                destination = (staging / member.filename).resolve()
                if not destination.is_relative_to(resolved):
                    raise BackupError(f"Kopia zawiera niedozwoloną ścieżkę: {member.filename}")
            archive.extractall(staging)
    except zipfile.BadZipFile as error:
        shutil.rmtree(staging, ignore_errors=True)
        raise BackupError("Plik jest uszkodzony albo nie jest plikiem .zip.") from error
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    (staging / MANIFEST).unlink(missing_ok=True)
    shutil.rmtree(previous, ignore_errors=True)
    try:
        if root.exists():
            root.rename(previous)
    except OSError as error:
        # Na Windows nie da się przenieść folderu, w którym jakiś plik jest otwarty
        # (np. właśnie odtwarzany dźwięk). Dane zostają nietknięte.
        shutil.rmtree(staging, ignore_errors=True)
        raise BackupError("Nie udało się podmienić danych – któryś plik jest w użyciu. "
                          "Uruchom program ponownie i od razu przywróć kopię.") from error
    staging.rename(root)
    data_dir.ensure()
    return previous
