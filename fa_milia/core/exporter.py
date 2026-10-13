"""Eksport kategorii i pytań finałowych do folderu w formacie tekstowym
oraz tworzenie pustego szablonu dla rodziny."""

import re
import shutil
from datetime import date
from pathlib import Path

from fa_milia.core.library import Library
from fa_milia.core.templates import INSTRUCTION_FILE_TEXT, TEMPLATE_FILE_TEXT
from fa_milia.core.text_format import category_to_text, finals_to_text, simplify

INSTRUCTION_FILE_NAME = "JAK_DODAC_PYTANIA.txt"
TEMPLATE_FILE_NAME = "WZOR.txt"


def write_notepad_text(path: Path, text: str) -> None:
    """Zapisuje plik tak, żeby dobrze otwierał się w Notatniku Windows.

    - końce linii \r\n (starszy Notatnik nie rozumie samego \n),
    - UTF-8 ze znacznikiem BOM – Notatnik rozpozna wtedy polskie litery.
    """
    path.write_text(text, encoding="utf-8-sig", newline="\r\n")


def file_stem_for(name: str, taken: set[str]) -> str:
    """Nazwa pliku z nazwy kategorii: „Zwierzęta domowe” → „zwierzeta_domowe”.

    Bez polskich znaków i spacji – takie nazwy najłatwiej przepisać przy
    nazywaniu zdjęć. Powtórzenia dostają końcówkę „-2”, „-3”…
    """
    base = re.sub(r"[^a-z0-9]+", "_", simplify(name)).strip("_") or "kategoria"
    if base in ("final", "wzor", "jak_dodac_pytania"):
        base += "_kategoria"  # te nazwy mają w imporcie specjalne znaczenie
    stem = base
    number = 2
    while stem in taken:
        stem = f"{base}-{number}"
        number += 1
    taken.add(stem)
    return stem


def unique_folder(parent: Path, name: str) -> Path:
    """Zwraca nieistniejący jeszcze folder: „name”, „name (2)”, …"""
    folder = parent / name
    number = 2
    while folder.exists():
        folder = parent / f"{name} ({number})"
        number += 1
    return folder


def export_to_folder(library: Library, category_ids: list[str], final_ids: list[str],
                     parent: Path) -> Path:
    """Tworzy w `parent` nowy folder z wybranymi kategoriami i finałami. Zwraca jego ścieżkę."""
    folder = unique_folder(parent, f"Pytania Fa milia {date.today().isoformat()}")
    folder.mkdir(parents=True)
    taken: set[str] = set()

    for category_id in category_ids:
        category = library.categories[category_id]
        stem = file_stem_for(category.name, taken)
        rows = [(q.text, q.answer) for q in category.questions]
        write_notepad_text(folder / f"{stem}.txt", category_to_text(category.name, rows, stem))
        for row, question in enumerate(category.questions, start=1):
            _copy_media(library, question.media, folder, f"{stem}_{row}")

    finals = [library.finals[i] for i in final_ids]
    if finals:
        rows = [(f.category, f.question.text, f.question.answer) for f in finals]
        write_notepad_text(folder / "final.txt", finals_to_text(rows))
        for number, final in enumerate(finals, start=1):
            _copy_media(library, final.question.media, folder, f"final_{number}")

    write_notepad_text(folder / INSTRUCTION_FILE_NAME, INSTRUCTION_FILE_TEXT)
    return folder


def _copy_media(library: Library, media: str | None, folder: Path, stem: str) -> None:
    if not media:
        return
    source = library.media_path(media)
    if source.is_file():
        shutil.copyfile(source, folder / f"{stem}{source.suffix.lower()}")


def create_template(parent: Path) -> Path:
    """Tworzy folder z plikiem WZOR.txt i instrukcją JAK_DODAC_PYTANIA.txt."""
    folder = unique_folder(parent, "Szablon pytań Fa milia")
    folder.mkdir(parents=True)
    write_notepad_text(folder / TEMPLATE_FILE_NAME, TEMPLATE_FILE_TEXT)
    write_notepad_text(folder / INSTRUCTION_FILE_NAME, INSTRUCTION_FILE_TEXT)
    return folder
