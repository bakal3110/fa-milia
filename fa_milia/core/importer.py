"""Import pytań z folderu (lub pliku .zip) w formacie tekstowym.

Import przebiega w dwóch krokach:
1. scan_folder() – czyta pliki i tworzy podgląd (co zostanie dodane, co jest
   niekompletne, jakie są błędy i konflikty nazw). Niczego jeszcze nie zapisuje.
2. apply_import() – zapisuje do biblioteki elementy wybrane przez użytkownika.
"""

import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from fa_milia.config import ROW_COUNT
from fa_milia.core.library import Library
from fa_milia.core.models import Category, ContentKind, FinalQuestion, Question, kind_for_file
from fa_milia.core.text_format import decode_text, parse_text, row_for_number, simplify

# Pliki .txt, które nie są kategoriami (instrukcje z szablonu).
IGNORED_TEXT_FILES = {"wzor", "jak_dodac_pytania", "instrukcja", "readme"}
FINAL_FILE_STEMS = {"final"}  # po uproszczeniu: final.txt i finał.txt

# Plik mediów: <nazwa pliku txt>_<numer>.<rozszerzenie>
MEDIA_NAME = re.compile(r"^(.*)_(\d+)$")


class ImportFailed(Exception):
    """Błąd całego importu (np. uszkodzony plik .zip)."""


class Status(StrEnum):
    OK = "ok"  # kompletne, gotowe do dodania
    INCOMPLETE = "incomplete"  # da się dodać, ale trzeba uzupełnić w edytorze
    ERROR = "error"  # nie da się dodać


class ConflictAction(StrEnum):
    SKIP = "skip"  # pomiń
    REPLACE = "replace"  # zastąp istniejące
    COPY = "copy"  # zapisz jako kopię (z nową nazwą)


@dataclass
class ImportItem:
    """Jedna kategoria albo jedno pytanie finałowe z importowanego folderu."""

    source: str  # np. „zwierzeta.txt” albo „final.txt, pytanie 2”
    title: str  # nazwa do wyświetlenia
    category: Category | None = None
    final: FinalQuestion | None = None
    # Nazwa pliku mediów w pytaniu → ścieżka źródłowa (skopiujemy go przy imporcie).
    media_sources: dict[str, Path] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    status: Status = Status.OK
    conflict_id: str | None = None  # id istniejącego elementu o tej samej nazwie

    @property
    def is_final(self) -> bool:
        return self.final is not None


@dataclass
class ImportPreview:
    items: list[ImportItem] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # ogólne (np. niepasujące pliki)


@dataclass
class ImportResult:
    added: int = 0
    replaced: int = 0
    skipped: int = 0


# ---------------------------------------------------------------------------
# Skanowanie folderu
# ---------------------------------------------------------------------------


def _read_text_file(path: Path) -> str:
    return decode_text(path.read_bytes())


def _media_by_stem(folder: Path, preview: ImportPreview) -> dict[str, dict[int, list[Path]]]:
    """Grupuje pliki mediów: uproszczona nazwa pliku txt → numer → pliki."""
    media: dict[str, dict[int, list[Path]]] = {}
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name.startswith(".") or path.suffix.lower() == ".txt":
            continue
        if kind_for_file(path.name) is None:
            preview.problems.append(f"Plik {path.name} ma nieobsługiwany format "
                                    "(obsługiwane: .jpg, .jpeg, .png, .mp3, .wav, .ogg)")
            continue
        match = MEDIA_NAME.match(path.stem)
        if not match:
            preview.problems.append(f"Plik {path.name} nie pasuje do żadnego pytania – nazwa "
                                    "powinna wyglądać tak: <nazwa pliku txt>_<numer>, "
                                    "np. zwierzeta_2.jpg")
            continue
        stem, number = simplify(match.group(1)), int(match.group(2))
        # setdefault: weź istniejący słownik albo wstaw nowy pusty i go zwróć.
        media.setdefault(stem, {}).setdefault(number, []).append(path)
    return media


def scan_folder(folder: Path, library: Library) -> ImportPreview:
    """Czyta folder z plikami .txt i mediami i przygotowuje podgląd importu."""
    preview = ImportPreview()
    media = _media_by_stem(folder, preview)
    used_media_stems: set[str] = set()

    text_files = sorted(p for p in folder.iterdir()
                        if p.is_file() and p.suffix.lower() == ".txt")
    for path in text_files:
        stem = simplify(path.stem)
        if stem in IGNORED_TEXT_FILES:
            continue
        used_media_stems.add(stem)
        try:
            text = _read_text_file(path)
        except OSError as error:
            preview.items.append(ImportItem(path.name, path.stem, status=Status.ERROR,
                                            problems=[f"{path.name}: nie można odczytać ({error})"]))
            continue
        file_media = media.get(stem, {})
        if stem in FINAL_FILE_STEMS:
            preview.items.extend(_finals_from_text(path.name, text, file_media, library))
        else:
            preview.items.append(_category_from_text(path, text, file_media, library))

    # Media, których nazwa nie pasuje do żadnego pliku .txt.
    for stem, numbers in media.items():
        if stem not in used_media_stems:
            for paths in numbers.values():
                for path in paths:
                    preview.problems.append(f"Plik {path.name} nie pasuje do żadnego pliku .txt "
                                            "w tym folderze")
    if not preview.items and not preview.problems:
        preview.problems.append("W wybranym folderze nie ma plików .txt z pytaniami.")
    return preview


def _attach_media(question: Question, number: int, file_media: dict[int, list[Path]],
                  item: ImportItem, label: str) -> None:
    """Jeśli istnieje plik mediów dla pytania – pytanie staje się obrazkowe/dźwiękowe."""
    paths = file_media.get(number, [])
    if not paths:
        return
    if len(paths) > 1:
        names = ", ".join(p.name for p in paths)
        item.problems.append(f"{label}: kilka plików do jednego pytania ({names}) – "
                             f"użyto {paths[0].name}")
    path = paths[0]
    question.kind = kind_for_file(path.name)
    question.media = path.name  # tymczasowo nazwa źródłowa – podmienimy przy imporcie
    item.media_sources[path.name] = path


def _category_from_text(path: Path, text: str, file_media: dict[int, list[Path]],
                        library: Library) -> ImportItem:
    parsed = parse_text(text)
    source = path.name
    item = ImportItem(source, "")
    item.problems += [f"{source}, {p}" for p in parsed.problems]

    name = (parsed.header_category or "").strip()
    if not name:
        name = path.stem.replace("_", " ").strip().capitalize()
        item.problems.append(f"{source}: brak linii „KATEGORIA: …” – użyto nazwy pliku "
                             f"„{name}”")

    # Bloki → rzędy 1–5.
    blocks_by_row = {}
    for block in parsed.blocks:
        row = row_for_number(block.number)
        if row is None:
            item.problems.append(f"{source}, linia {block.line}: numer {block.number} jest spoza "
                                 "zakresu – użyj 1–5 (albo 100–500)")
        elif row in blocks_by_row:
            item.problems.append(f"{source}: pytanie {row} występuje dwa razy – "
                                 "użyto pierwszego")
        else:
            blocks_by_row[row] = block

    questions = []
    for row in range(1, ROW_COUNT + 1):
        block = blocks_by_row.get(row)
        question = Question(kind=ContentKind.TEXT,
                            text=block.question if block else "",
                            answer=block.answer if block else "")
        # Media mogą być nazwane numerem rzędu (zwierzeta_3.jpg) albo wartością (…_300.jpg).
        media_number = row if row in file_media else row * 100
        _attach_media(question, media_number, file_media, item, f"{source}, pytanie {row}")
        if block is None and question.media is None:
            item.problems.append(f"{source}, pytanie {row}: brak w pliku")
        else:
            item.problems += [f"{source}, pytanie {row}: {p}" for p in question.problems()]
        questions.append(question)

    # Media z numerami, które nie odpowiadają żadnemu pytaniu (np. zwierzeta_7.jpg).
    for number, paths in file_media.items():
        if row_for_number(number) is None:
            for media_path in paths:
                item.problems.append(f"Plik {media_path.name} nie pasuje do żadnego pytania "
                                     "(numery pytań to 1–5)")

    item.category = Category(name=name, questions=questions)
    item.title = name
    if not parsed.blocks and not file_media:
        item.status = Status.ERROR
        item.problems.append(f"{source}: nie znaleziono żadnego pytania")
    elif not item.category.is_complete():
        item.status = Status.INCOMPLETE
    item.conflict_id = _find_category_conflict(library, name)
    return item


def _finals_from_text(source: str, text: str, file_media: dict[int, list[Path]],
                      library: Library) -> list[ImportItem]:
    parsed = parse_text(text)
    items = []
    seen_numbers = set()
    for block in parsed.blocks:
        label = f"{source}, pytanie {block.number}"
        item = ImportItem(label, "")
        if block.number in seen_numbers:
            item.problems.append(f"{label}: ten numer występuje dwa razy")
        seen_numbers.add(block.number)
        question = Question(kind=ContentKind.TEXT, text=block.question, answer=block.answer)
        _attach_media(question, block.number, file_media, item, label)
        category = block.category or (parsed.header_category or "")
        final = FinalQuestion(category=category.strip(), question=question)
        item.problems += [f"{label}: {p}" for p in final.problems()]
        item.final = final
        item.title = f"{final.category or '(bez kategorii)'}: {_snippet(question)}"
        item.status = Status.OK if final.is_complete() else Status.INCOMPLETE
        item.conflict_id = _find_final_conflict(library, final)
        items.append(item)

    general = [f"{source}, {p}" for p in parsed.problems]
    for number, paths in file_media.items():
        if number not in seen_numbers:
            general += [f"Plik {p.name} nie pasuje do żadnego pytania w {source}" for p in paths]
    if items:
        items[0].problems = general + items[0].problems
    else:
        items.append(ImportItem(source, source, status=Status.ERROR,
                                problems=general + [f"{source}: nie znaleziono żadnego pytania"]))
    return items


def _snippet(question: Question) -> str:
    if question.kind == ContentKind.IMAGE:
        return "[obraz]"
    if question.kind == ContentKind.SOUND:
        return "[dźwięk]"
    first = question.text.splitlines()[0] if question.text else ""
    return first if len(first) <= 40 else first[:40] + "…"


def _find_category_conflict(library: Library, name: str) -> str | None:
    wanted = name.strip().casefold()
    for category in library.categories.values():
        if category.name.strip().casefold() == wanted:
            return category.id
    return None


def _find_final_conflict(library: Library, final: FinalQuestion) -> str | None:
    """Ten sam finał = ta sama kategoria i treść (bez względu na wielkość liter)."""
    key = (final.category.casefold(), final.question.text.strip().casefold())
    for existing in library.finals.values():
        if (existing.category.casefold(), existing.question.text.strip().casefold()) == key:
            return existing.id
    return None


# ---------------------------------------------------------------------------
# Pliki .zip
# ---------------------------------------------------------------------------


def safe_extract(archive: zipfile.ZipFile, target: Path) -> None:
    """Rozpakowuje .zip, odrzucając ścieżki wychodzące poza katalog docelowy."""
    target = target.resolve()
    for member in archive.infolist():
        destination = (target / member.filename).resolve()
        # is_relative_to: czy ścieżka leży wewnątrz katalogu docelowego.
        if not destination.is_relative_to(target):
            raise ImportFailed(f"Plik .zip zawiera niedozwoloną ścieżkę: {member.filename}")
    archive.extractall(target)


def extract_zip(zip_path: Path) -> tuple[Path, tempfile.TemporaryDirectory]:
    """Rozpakowuje .zip do katalogu tymczasowego i zwraca folder z plikami .txt.

    Zwraca też obiekt TemporaryDirectory – katalog zostanie skasowany, gdy
    wywołujący wywoła .cleanup() (po zakończeniu importu).
    """
    temp = tempfile.TemporaryDirectory(prefix="fa-milia-import-")
    try:
        with zipfile.ZipFile(zip_path) as archive:
            safe_extract(archive, Path(temp.name))
    except zipfile.BadZipFile as error:
        temp.cleanup()
        raise ImportFailed("To nie jest poprawny plik .zip.") from error
    except Exception:
        temp.cleanup()
        raise
    root = Path(temp.name)
    # Szukamy najpłycej położonego folderu z plikami .txt (np. zip z jednym folderem w środku).
    candidates = sorted((p.parent for p in root.rglob("*.txt")
                         if "__MACOSX" not in p.parts),
                        key=lambda folder: len(folder.parts))
    return (candidates[0] if candidates else root), temp


# ---------------------------------------------------------------------------
# Zapis do biblioteki
# ---------------------------------------------------------------------------


def apply_import(library: Library, items: list[ImportItem],
                 actions: dict[int, ConflictAction] | None = None) -> ImportResult:
    """Zapisuje wybrane elementy do biblioteki.

    actions: indeks elementu na liście → co zrobić przy konflikcie nazw
    (domyślnie: zapisz jako kopię). Elementy ze statusem ERROR są pomijane.
    """
    actions = actions or {}
    result = ImportResult()
    for index, item in enumerate(items):
        if item.status == Status.ERROR:
            result.skipped += 1
            continue
        action = actions.get(index, ConflictAction.COPY) if item.conflict_id else None
        if action == ConflictAction.SKIP:
            result.skipped += 1
            continue

        rename = {source: library.import_media(path)
                  for source, path in item.media_sources.items()}

        if item.category is not None:
            category = item.category
            for question in category.questions:
                question.media = rename.get(question.media, question.media)
            if action == ConflictAction.REPLACE:
                category.id = item.conflict_id  # nadpisujemy istniejącą (pamięć użycia zostaje)
                result.replaced += 1
            else:
                if action == ConflictAction.COPY:
                    category.name = library.unique_category_name(category.name)
                result.added += 1
            library.save_category(category)
        else:
            final = item.final
            final.question.media = rename.get(final.question.media, final.question.media)
            if action == ConflictAction.REPLACE:
                final.id = item.conflict_id
                result.replaced += 1
            else:
                result.added += 1
            library.save_final(final)

    library.remove_unused_media()  # np. pliki zastąpionych kategorii
    return result

