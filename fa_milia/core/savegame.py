"""Zapis i odczyt przerwanej gry (savegame.json).

Zapisujemy całą historię (GameHistory), więc po wznowieniu gry nadal
można cofać wcześniejsze akcje.
"""

import json
from datetime import datetime
from pathlib import Path

from fa_milia.core.history import GameHistory
from fa_milia.core.jsonio import read_json, write_json

SAVE_VERSION = 1


def save_game(path: Path, history: GameHistory) -> None:
    data = {"version": SAVE_VERSION, "saved_at": datetime.now().isoformat(timespec="seconds")}
    data.update(history.to_dict())
    write_json(path, data)


def load_game(path: Path) -> GameHistory | None:
    """Wczytuje zapis. Brak lub uszkodzenie pliku → None (bez błędu)."""
    try:
        data = read_json(path)
        return GameHistory.from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError):
        return None


def delete_game(path: Path) -> None:
    path.unlink(missing_ok=True)


def describe_game(history: GameHistory) -> str:
    """Krótki opis zapisanej gry, np. „Ania, Bartek · runda 2”."""
    state = history.state
    names = ", ".join(p.name for p in state.players)
    if state.phase.value.startswith("final"):
        stage = "finał"
    else:
        stage = f"runda {state.round.number}"
    return f"{names} · {stage}"
