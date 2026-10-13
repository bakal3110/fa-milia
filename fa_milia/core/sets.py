"""Zestawy: zapisany wybór 6 + 6 kategorii i (opcjonalnie) pytania finałowego."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from fa_milia.config import CATEGORIES_PER_ROUND
from fa_milia.core.jsonio import read_json, write_json
from fa_milia.core.library import Library
from fa_milia.core.textutil import polish_sort_key


@dataclass
class GameSet:
    name: str
    round1: list[str] = field(default_factory=list)  # identyfikatory kategorii
    round2: list[str] = field(default_factory=list)
    final: str | None = None  # identyfikator pytania finałowego (None = losowe)

    def to_dict(self) -> dict:
        return {"name": self.name, "round1": list(self.round1), "round2": list(self.round2),
                "final": self.final}

    @classmethod
    def from_dict(cls, data: dict) -> "GameSet":
        return cls(
            name=str(data.get("name") or "Zestaw"),
            round1=[str(i) for i in data.get("round1") or []],
            round2=[str(i) for i in data.get("round2") or []],
            final=data.get("final") or None,
        )


def set_problems(game_set: GameSet, library: Library) -> list[str]:
    """Co jest nie tak z zestawem (np. kategoria została usunięta)."""
    problems = []
    complete = {c.id for c in library.complete_categories()}
    for number, ids in ((1, game_set.round1), (2, game_set.round2)):
        if len(ids) != CATEGORIES_PER_ROUND:
            problems.append(f"runda {number}: {len(ids)} kategorii zamiast {CATEGORIES_PER_ROUND}")
        for category_id in ids:
            category = library.categories.get(category_id)
            if category is None:
                problems.append(f"runda {number}: kategoria została usunięta")
            elif category_id not in complete:
                problems.append(f"runda {number}: kategoria „{category.name}” jest niekompletna")
    if set(game_set.round1) & set(game_set.round2):
        problems.append("ta sama kategoria jest w obu rundach")
    if game_set.final is not None:
        final = library.finals.get(game_set.final)
        if final is None:
            problems.append("pytanie finałowe zostało usunięte")
        elif not final.is_complete():
            problems.append("pytanie finałowe jest niekompletne")
    return problems


class SetStore:
    """Wszystkie zestawy w jednym pliku sets.json."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.sets: list[GameSet] = []
        self.load()

    def load(self) -> None:
        try:
            data = read_json(self.path)
        except (OSError, json.JSONDecodeError):
            data = []
        if isinstance(data, dict):  # format z polem "sets"
            data = data.get("sets", [])
        self.sets = [GameSet.from_dict(d) for d in data if isinstance(d, dict)]

    def save(self) -> None:
        write_json(self.path, {"version": 1, "sets": [s.to_dict() for s in self.sets]})

    def sorted_sets(self) -> list[GameSet]:
        return sorted(self.sets, key=lambda s: polish_sort_key(s.name))

    def find(self, name: str) -> GameSet | None:
        wanted = name.strip().casefold()
        return next((s for s in self.sets if s.name.strip().casefold() == wanted), None)

    def put(self, game_set: GameSet, replace_name: str | None = None) -> None:
        """Zapisuje zestaw. Zestaw o tej samej nazwie (lub `replace_name`) jest zastępowany."""
        for name in {game_set.name, replace_name or game_set.name}:
            existing = self.find(name)
            if existing is not None:
                self.sets.remove(existing)
        self.sets.append(game_set)
        self.save()

    def delete(self, name: str) -> None:
        existing = self.find(name)
        if existing is not None:
            self.sets.remove(existing)
            self.save()
