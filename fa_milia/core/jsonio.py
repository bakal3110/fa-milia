"""Bezpieczny zapis i odczyt plików JSON."""

import json
import os
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """Wczytuje plik JSON. Błędy (brak pliku, zła składnia) przekazuje dalej."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    """Zapisuje dane do pliku JSON „atomowo”.

    Najpierw zapisujemy do pliku tymczasowego, a dopiero potem podmieniamy
    nim właściwy plik. Dzięki temu, jeśli program zostanie przerwany w trakcie
    zapisu (np. zabraknie prądu), stary plik pozostanie nienaruszony.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        # ensure_ascii=False zapisuje polskie litery normalnie, a nie jako ą.
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())  # wymusza fizyczny zapis na dysk
    os.replace(temp_path, path)  # podmiana jest niepodzielna (atomowa)
