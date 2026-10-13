"""Historia akcji i cofanie.

Przed każdą akcją zapamiętujemy „migawkę” całego stanu gry (słownik z
GameState.to_dict()). Cofnięcie to po prostu przywrócenie ostatniej migawki.
Stan gry jest mały (kilka KB), więc to proste rozwiązanie jest w pełni wystarczające.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fa_milia.core.game_state import GameState

MAX_HISTORY = 1000


@dataclass
class HistoryEntry:
    label: str  # opis akcji, np. „Ania +300”
    snapshot: dict[str, Any]  # stan sprzed akcji


class GameHistory:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self.entries: list[HistoryEntry] = []

    def apply(self, label: str, action: Callable[[GameState], Any]) -> Any:
        """Wykonuje akcję na stanie gry i zapamiętuje stan sprzed niej.

        `action` to funkcja przyjmująca GameState, np.
        history.apply("Ania +300", lambda state: state.mark(0, True)).
        Jeśli akcja zgłosi błąd, stan zostaje przywrócony, a błąd przekazany dalej.
        """
        before = self.state.to_dict()
        try:
            result = action(self.state)
        except Exception:
            self.state = GameState.from_dict(before)
            raise
        self.entries.append(HistoryEntry(label, before))
        if len(self.entries) > MAX_HISTORY:
            self.entries.pop(0)
        return result

    def can_undo(self) -> bool:
        return bool(self.entries)

    def last_label(self) -> str | None:
        return self.entries[-1].label if self.entries else None

    def undo(self) -> str | None:
        """Cofa ostatnią akcję. Zwraca jej opis (albo None, gdy nie ma czego cofać)."""
        if not self.entries:
            return None
        entry = self.entries.pop()
        self.state = GameState.from_dict(entry.snapshot)
        return entry.label

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "history": [{"label": e.label, "state": e.snapshot} for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameHistory":
        history = cls(GameState.from_dict(data["state"]))
        history.entries = [HistoryEntry(e["label"], e["state"]) for e in data["history"]]
        return history
