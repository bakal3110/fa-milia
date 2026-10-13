"""Pamięć wykorzystania: które kategorie i pytania finałowe już były w grze.

Dane są w osobnym pliku usage.json, więc „Resetuj pamięć” nie musi
zmieniać plików kategorii.
"""

import json
from datetime import datetime
from pathlib import Path

from fa_milia.core.jsonio import read_json, write_json


def _now() -> str:
    return datetime.now().isoformat(timespec="minutes")


class UsageMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        # identyfikator → data i godzina pierwszego użycia
        self.categories: dict[str, str] = {}
        self.finals: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        try:
            data = read_json(self.path)
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        self.categories = dict(data.get("categories") or {})
        self.finals = dict(data.get("finals") or {})

    def save(self) -> None:
        write_json(self.path, {"version": 1, "categories": self.categories, "finals": self.finals})

    # --- Odczyt ------------------------------------------------------------

    def is_category_used(self, category_id: str) -> bool:
        return category_id in self.categories

    def is_final_used(self, final_id: str) -> bool:
        return final_id in self.finals

    def used_category_ids(self) -> set[str]:
        return set(self.categories)

    def used_final_ids(self) -> set[str]:
        return set(self.finals)

    # --- Zmiany (każda od razu zapisywana na dysk) -------------------------

    def mark_categories(self, category_ids: list[str]) -> None:
        for category_id in category_ids:
            self.categories.setdefault(category_id, _now())
        self.save()

    def mark_final(self, final_id: str) -> None:
        self.finals.setdefault(final_id, _now())
        self.save()

    def unmark_category(self, category_id: str) -> None:
        self.categories.pop(category_id, None)
        self.save()

    def unmark_final(self, final_id: str) -> None:
        self.finals.pop(final_id, None)
        self.save()

    def reset(self) -> None:
        self.categories.clear()
        self.finals.clear()
        self.save()
