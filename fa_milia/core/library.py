"""Biblioteka: kategorie i pytania finałowe zapisane na dysku.

Każda kategoria to osobny plik categories/<id>.json, każde pytanie
finałowe to finals/<id>.json. Pliki mediów leżą w katalogu media/.
"""

import json
import re
import shutil
from pathlib import Path

from fa_milia.core.jsonio import read_json, write_json
from fa_milia.core.models import (
    Category,
    FinalQuestion,
    Question,
    kind_for_file,
    new_id,
)
from fa_milia.core.paths import DataDir
from fa_milia.core.textutil import polish_sort_key


class Library:
    """Wczytuje, zapisuje i usuwa kategorie oraz pytania finałowe."""

    def __init__(self, data_dir: DataDir) -> None:
        self.data_dir = data_dir
        self.data_dir.ensure()
        # Słowniki: identyfikator → obiekt. Pozwalają szybko znaleźć element po id.
        self.categories: dict[str, Category] = {}
        self.finals: dict[str, FinalQuestion] = {}
        # Opisy plików, których nie udało się wczytać (uszkodzone itp.).
        self.load_errors: list[str] = []
        self.reload()

    # --- Wczytywanie -------------------------------------------------------

    def reload(self) -> None:
        """Wczytuje od nowa wszystkie pliki z dysku."""
        self.load_errors = []
        self.categories = self._load_folder(self.data_dir.categories, Category)
        self.finals = self._load_folder(self.data_dir.finals, FinalQuestion)

    def _load_folder(self, folder: Path, model_class):
        """Wczytuje wszystkie pliki .json z folderu jako obiekty model_class.

        model_class to Category albo FinalQuestion – obie klasy mają metodę
        from_dict, więc ten sam kod obsługuje oba przypadki.
        """
        items = {}
        for path in sorted(folder.glob("*.json")):
            try:
                item = model_class.from_dict(read_json(path))
            except (OSError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as error:
                # Uszkodzony plik nie może zatrzymać programu – zapamiętujemy
                # problem i pokazujemy go później użytkownikowi.
                self.load_errors.append(f"{path.name}: nie udało się odczytać pliku ({error})")
                continue
            items[item.id] = item
        return items

    # --- Kategorie ---------------------------------------------------------

    def sorted_categories(self) -> list[Category]:
        return sorted(self.categories.values(), key=lambda c: polish_sort_key(c.name))

    def complete_categories(self) -> list[Category]:
        """Kategorie, które można wybrać do gry."""
        return [c for c in self.sorted_categories() if not self.category_problems(c)]

    def category_problems(self, category: Category) -> list[str]:
        """Braki kategorii, łącznie z brakującymi plikami mediów na dysku."""
        problems = category.problems()
        for number, question in enumerate(category.questions, start=1):
            problems.extend(f"pytanie {number}: {p}" for p in self._missing_media(question))
        return problems

    def save_category(self, category: Category) -> None:
        write_json(self.data_dir.categories / f"{category.id}.json", category.to_dict())
        self.categories[category.id] = category

    def delete_category(self, category_id: str) -> None:
        (self.data_dir.categories / f"{category_id}.json").unlink(missing_ok=True)
        self.categories.pop(category_id, None)

    def category_name_taken(self, name: str, except_id: str | None = None) -> bool:
        """Czy inna kategoria ma już taką nazwę (bez względu na wielkość liter)?"""
        wanted = name.strip().casefold()
        return any(
            c.name.strip().casefold() == wanted and c.id != except_id
            for c in self.categories.values()
        )

    def unique_category_name(self, base: str) -> str:
        """Zwraca `base`, a jeśli zajęte – `base (2)`, `base (3)` itd."""
        name = base
        number = 2
        while self.category_name_taken(name):
            name = f"{base} ({number})"
            number += 1
        return name

    # --- Pytania finałowe --------------------------------------------------

    def sorted_finals(self) -> list[FinalQuestion]:
        return sorted(
            self.finals.values(),
            key=lambda f: (polish_sort_key(f.category), polish_sort_key(f.question.text)),
        )

    def complete_finals(self) -> list[FinalQuestion]:
        return [f for f in self.sorted_finals() if not self.final_problems(f)]

    def final_problems(self, final: FinalQuestion) -> list[str]:
        return final.problems() + self._missing_media(final.question)

    def save_final(self, final: FinalQuestion) -> None:
        write_json(self.data_dir.finals / f"{final.id}.json", final.to_dict())
        self.finals[final.id] = final

    def delete_final(self, final_id: str) -> None:
        (self.data_dir.finals / f"{final_id}.json").unlink(missing_ok=True)
        self.finals.pop(final_id, None)

    # --- Media -------------------------------------------------------------

    def media_path(self, name: str) -> Path:
        return self.data_dir.media / name

    def import_media(self, source: Path) -> str:
        """Kopiuje plik obrazu/dźwięku do katalogu media/ i zwraca jego nową nazwę.

        Nowa nazwa ma postać <losowy prefiks>_<oryginalna nazwa>, np.
        „a1b2c3d4e5f6_kapibara.jpg”. Prefiks gwarantuje unikalność, a oryginalna
        nazwa pozwala rozpoznać plik w edytorze.
        """
        if kind_for_file(source.name) is None:
            raise ValueError(f"Nieobsługiwany format pliku: {source.name}")
        stem = _safe_file_stem(source.stem)
        name = f"{new_id()[:12]}_{stem}{source.suffix.lower()}"
        self.data_dir.media.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, self.media_path(name))
        return name

    @staticmethod
    def display_media_name(name: str) -> str:
        """Nazwa pliku bez losowego prefiksu – do wyświetlania."""
        # partition dzieli napis na (przed, separator, po) przy pierwszym "_".
        prefix, separator, rest = name.partition("_")
        return rest if separator and len(prefix) == 12 else name

    def used_media(self) -> set[str]:
        used = set()
        for category in self.categories.values():
            used.update(category.media_files())
        for final in self.finals.values():
            used.update(final.media_files())
        # Zapisana (niedokończona) gra ma własne kopie pytań – ich plików też nie ruszamy,
        # nawet jeśli kategorię usunięto z biblioteki.
        used.update(self._savegame_media())
        return used

    def _savegame_media(self) -> set[str]:
        try:
            data = read_json(self.data_dir.savegame_file)
        except (OSError, json.JSONDecodeError):
            return set()
        found: set[str] = set()
        _collect_media_names(data, found)
        return found

    def remove_unused_media(self) -> int:
        """Usuwa pliki mediów, do których nie odwołuje się żadne pytanie.

        Takie pliki powstają np. gdy ktoś wybierze obrazek w edytorze, ale nie
        zapisze zmian. Zwraca liczbę usuniętych plików.

        Jeśli jakiś plik kategorii był uszkodzony, nic nie usuwamy – nie wiemy,
        z jakich mediów korzystał.
        """
        if self.load_errors:
            return 0
        used = self.used_media()
        removed = 0
        for path in self.data_dir.media.iterdir():
            if path.is_file() and path.name not in used:
                path.unlink()
                removed += 1
        return removed

    def _missing_media(self, question: Question) -> list[str]:
        if question.media and not self.media_path(question.media).is_file():
            return [f"plik {self.display_media_name(question.media)} nie istnieje"]
        return []


def _collect_media_names(data, found: set[str]) -> None:
    """Przeszukuje (rekurencyjnie) dane JSON i zbiera wartości kluczy "media"."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "media" and isinstance(value, str):
                found.add(value)
            else:
                _collect_media_names(value, found)
    elif isinstance(data, list):
        for value in data:
            _collect_media_names(value, found)


def _safe_file_stem(stem: str) -> str:
    """Zostawia w nazwie pliku tylko litery, cyfry, „-” i „_” (maks. 40 znaków)."""
    # \w w Pythonie obejmuje też polskie litery. [^...] oznacza „wszystko poza”.
    cleaned = re.sub(r"[^\w-]+", "_", stem).strip("_")
    return cleaned[:40] or "plik"
