"""Model danych: pytania, kategorie i pytania finałowe.

Używamy @dataclass – dekoratora, który na podstawie listy pól sam tworzy
konstruktor __init__, czytelne __repr__ i porównywanie (==).
"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fa_milia.config import IMAGE_EXTENSIONS, ROW_COUNT, SOUND_EXTENSIONS

# Wersja formatu plików JSON. Jeśli kiedyś zmienimy format, po tym numerze
# rozpoznamy stare pliki i będziemy mogli je przekształcić.
FORMAT_VERSION = 1


def new_id() -> str:
    """Tworzy unikalny identyfikator, np. '3f2a9c…' (32 znaki szesnastkowe)."""
    return uuid.uuid4().hex


class ContentKind(StrEnum):
    """Rodzaj treści pytania.

    StrEnum to wyliczenie, którego wartości są jednocześnie napisami,
    więc ContentKind.IMAGE == "image" i łatwo zapisać je w JSON.
    """

    TEXT = "text"
    IMAGE = "image"
    SOUND = "sound"


# Nazwy rodzajów wyświetlane w interfejsie.
KIND_LABELS = {
    ContentKind.TEXT: "Tekst",
    ContentKind.IMAGE: "Obraz",
    ContentKind.SOUND: "Dźwięk",
}

# Rozszerzenia plików dozwolone dla danego rodzaju treści.
KIND_EXTENSIONS = {
    ContentKind.TEXT: (),
    ContentKind.IMAGE: IMAGE_EXTENSIONS,
    ContentKind.SOUND: SOUND_EXTENSIONS,
}


def kind_for_file(file_name: str) -> ContentKind | None:
    """Na podstawie rozszerzenia mówi, czy plik jest obrazem, czy dźwiękiem."""
    lower = file_name.lower()
    if lower.endswith(IMAGE_EXTENSIONS):  # endswith przyjmuje też krotkę
        return ContentKind.IMAGE
    if lower.endswith(SOUND_EXTENSIONS):
        return ContentKind.SOUND
    return None


def _parse_kind(value: Any) -> ContentKind:
    """Zamienia napis z JSON na ContentKind; nieznane wartości → tekst."""
    try:
        return ContentKind(value)
    except ValueError:
        return ContentKind.TEXT


@dataclass
class Question:
    """Pojedyncze pytanie.

    - kind:   rodzaj treści (tekst, obraz, dźwięk),
    - text:   treść pytania; przy obrazie/dźwięku jest to opcjonalny podpis,
    - media:  nazwa pliku w katalogu media/ (tylko dla obrazu i dźwięku),
    - answer: poprawna odpowiedź.
    """

    kind: ContentKind = ContentKind.TEXT
    text: str = ""
    media: str | None = None
    answer: str = ""

    def problems(self) -> list[str]:
        """Lista braków opisanych po ludzku. Pusta lista = pytanie kompletne."""
        problems = []
        if self.kind == ContentKind.TEXT:
            if not self.text.strip():
                problems.append("brak treści pytania")
        elif not self.media:
            if self.kind == ContentKind.IMAGE:
                problems.append("brak pliku obrazu")
            else:
                problems.append("brak pliku dźwięku")
        elif kind_for_file(self.media) != self.kind:
            problems.append("wybrany plik nie pasuje do rodzaju pytania")
        if not self.answer.strip():
            problems.append("brak odpowiedzi")
        return problems

    def is_complete(self) -> bool:
        return not self.problems()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "media": self.media,
            "answer": self.answer,
        }

    # @classmethod: metoda wywoływana na klasie, a nie na obiekcie:
    # Question.from_dict({...}). Typowy sposób na „alternatywny konstruktor”.
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Question":
        return cls(
            kind=_parse_kind(data.get("kind", "text")),
            text=str(data.get("text") or ""),
            media=data.get("media") or None,
            answer=str(data.get("answer") or ""),
        )


def _empty_questions() -> list[Question]:
    return [Question() for _ in range(ROW_COUNT)]


@dataclass
class Category:
    """Kategoria: nazwa i dokładnie 5 pytań (indeks 0 = rząd 1, najłatwiejszy).

    - name:       nazwa w bibliotece (do porządkowania, np. „Nauka 2”),
    - board_name: napis wyświetlany w grze (np. „Nauka”); pusty = taki jak name.
    """

    name: str = ""
    # field(default_factory=...) – każda nowa kategoria dostaje WŁASNĄ listę.
    # Zwykłe `= []` sprawiłoby, że wszystkie obiekty dzieliłyby jedną listę.
    questions: list[Question] = field(default_factory=_empty_questions)
    id: str = field(default_factory=new_id)
    board_name: str = ""

    @property
    def display_name(self) -> str:
        """Nazwa pokazywana na planszy i ekranie gry."""
        return self.board_name.strip() or self.name

    def problems(self) -> list[str]:
        problems = []
        if not self.name.strip():
            problems.append("brak nazwy kategorii")
        # enumerate(..., start=1) daje pary (numer, element), numerując od 1.
        for number, question in enumerate(self.questions, start=1):
            for problem in question.problems():
                problems.append(f"pytanie {number}: {problem}")
        return problems

    def is_complete(self) -> bool:
        return not self.problems()

    def media_files(self) -> list[str]:
        return [q.media for q in self.questions if q.media]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": FORMAT_VERSION,
            "id": self.id,
            "name": self.name,
            "board_name": self.board_name,
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        questions = [Question.from_dict(q) for q in data.get("questions", [])]
        # Pilnujemy, żeby zawsze było dokładnie ROW_COUNT pytań.
        questions = questions[:ROW_COUNT]
        while len(questions) < ROW_COUNT:
            questions.append(Question())
        return cls(
            name=str(data.get("name") or ""),
            questions=questions,
            id=str(data.get("id") or new_id()),
            board_name=str(data.get("board_name") or ""),
        )


@dataclass
class FinalQuestion:
    """Pytanie finałowe: kategoria (pokazywana przed obstawianiem) i pytanie."""

    category: str = ""
    question: Question = field(default_factory=Question)
    id: str = field(default_factory=new_id)

    def problems(self) -> list[str]:
        problems = []
        if not self.category.strip():
            problems.append("brak kategorii")
        problems.extend(self.question.problems())
        return problems

    def is_complete(self) -> bool:
        return not self.problems()

    def media_files(self) -> list[str]:
        return [self.question.media] if self.question.media else []

    def to_dict(self) -> dict[str, Any]:
        # ** „rozpakowuje” słownik pytania do nowego słownika,
        # dzięki czemu plik JSON jest płaski i czytelny.
        return {
            "version": FORMAT_VERSION,
            "id": self.id,
            "category": self.category,
            **self.question.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinalQuestion":
        return cls(
            category=str(data.get("category") or ""),
            question=Question.from_dict(data),
            id=str(data.get("id") or new_id()),
        )
