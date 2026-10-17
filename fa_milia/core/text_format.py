"""Format tekstowy pytań (pliki .txt z Notatnika) – odczyt i zapis.

Przykład pliku kategorii:

    KATEGORIA: Zwierzęta

    1
    P: Ile nóg ma pająk?
    O: Osiem

Parser jest wyrozumiały: wielkość liter i polskie znaki w słowach-kluczach
nie mają znaczenia („Odpowiedz:” = „ODPOWIEDŹ:” = „O:”), puste linie
i komentarze (#) są pomijane, a odpowiedź może mieć kilka linii.
"""

import re
import unicodedata
from dataclasses import dataclass, field

# Słowa-klucze (po uproszczeniu: małe litery, bez polskich znaków) → znaczenie.
KEY_ALIASES = {
    "kategoria": "category",
    "plansza": "board",  # opcjonalny napis na planszy (gdy inny niż nazwa kategorii)
    "p": "question",
    "pytanie": "question",
    "o": "answer",
    "odp": "answer",
    "odpowiedz": "answer",
}

# Linia z samym numerem pytania, np. „3”, „3.”, „3)”, „300”.
NUMBER_LINE = re.compile(r"^(\d+)\s*[.)]?$")
# Linia „słowo: treść”, np. „P: Ile nóg ma pająk?”.
KEY_LINE = re.compile(r"^([^\W\d_]+)\s*:\s*(.*)$")


def simplify(text: str) -> str:
    """Upraszcza tekst do porównań: małe litery, bez polskich znaków.

    „Odpowiedź” → „odpowiedz”, „Finał” → „final”. Litera „ł” nie rozkłada się
    na „l” + znak diakrytyczny, więc zamieniamy ją osobno.
    """
    text = text.casefold().replace("ł", "l")
    # NFKD rozkłada np. „ą” na „a” + ogonek; potem odrzucamy same ogonki/kreski.
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def decode_text(data: bytes) -> str:
    """Odczytuje bajty pliku jako tekst: najpierw UTF-8, a w razie błędu Windows-1250.

    Stary Notatnik w Windows zapisywał polskie litery w kodowaniu Windows-1250.
    utf-8-sig pomija też niewidoczny znacznik BOM, który Notatnik dodaje na początku.
    """
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1250", errors="replace")


@dataclass
class TextBlock:
    """Jeden numerowany blok pliku (jedno pytanie)."""

    number: int  # numer zapisany w pliku (np. 3 albo 300)
    line: int  # numer linii w pliku – do komunikatów o błędach
    category: str = ""  # tylko w pliku finałowym
    question_lines: list[str] = field(default_factory=list)
    answer_lines: list[str] = field(default_factory=list)

    @property
    def question(self) -> str:
        return "\n".join(self.question_lines).strip()

    @property
    def answer(self) -> str:
        return "\n".join(self.answer_lines).strip()


@dataclass
class ParsedText:
    header_category: str | None = None  # „KATEGORIA:” przed pierwszym numerem
    header_board: str | None = None  # „PLANSZA:” przed pierwszym numerem
    blocks: list[TextBlock] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _short(text: str, limit: int = 40) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def parse_text(text: str) -> ParsedText:
    """Dzieli tekst na nagłówek i numerowane bloki pytań."""
    result = ParsedText()
    current: TextBlock | None = None
    target: list[str] | None = None  # lista, do której dopisujemy kolejne linie

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue  # pusta linia albo komentarz

        number_match = NUMBER_LINE.match(line)
        if number_match:
            current = TextBlock(int(number_match.group(1)), line_number)
            result.blocks.append(current)
            target = None
            continue

        key_match = KEY_LINE.match(line)
        key = KEY_ALIASES.get(simplify(key_match.group(1))) if key_match else None
        if key is not None:
            value = key_match.group(2).strip()
            if key == "board":
                if current is None:
                    result.header_board = value
                else:
                    result.problems.append(
                        f"linia {line_number}: „PLANSZA:” wpisz na górze pliku, "
                        "pod „KATEGORIA:”")
                target = None
                continue
            if key == "category":
                if current is None:
                    if result.header_category is not None:
                        result.problems.append(
                            f"linia {line_number}: druga linia „KATEGORIA:” – użyto pierwszej")
                    else:
                        result.header_category = value
                else:
                    current.category = value
                target = None
                continue
            if current is None:
                result.problems.append(
                    f"linia {line_number}: przed „{key_match.group(1)}:” brakuje numeru pytania "
                    "(numer wpisz w osobnej linii, np. „1”)")
                target = None
                continue
            # Kolejna linia „P:” w tym samym bloku dopisuje się do poprzedniej.
            target = current.question_lines if key == "question" else current.answer_lines
            if value:
                target.append(value)
            continue

        # Zwykła linia tekstu – ciąg dalszy pytania lub odpowiedzi.
        if current is None:
            result.problems.append(
                f"linia {line_number}: nie wiadomo, do którego pytania należy tekst "
                f"„{_short(line)}”")
            continue
        if target is None:
            target = current.question_lines  # tekst bez „P:” traktujemy jako pytanie
        target.append(line)

    return result


def row_for_number(number: int) -> int | None:
    """Numer z pliku → rząd planszy (1–5). Akceptuje też wartości 100–500."""
    if 1 <= number <= 5:
        return number
    if number in (100, 200, 300, 400, 500):
        return number // 100
    return None


# ---------------------------------------------------------------------------
# Zapis
# ---------------------------------------------------------------------------


def _field_lines(prefix: str, value: str) -> list[str]:
    """„P: pierwsza linia” + kolejne linie bez przedrostka."""
    lines = value.splitlines() or [""]
    return [f"{prefix} {lines[0]}".rstrip()] + lines[1:]


def category_to_text(name: str, questions: list[tuple[str, str]], stem: str,
                     board_name: str = "") -> str:
    """Tekst pliku kategorii. questions: lista (treść/podpis, odpowiedź) dla rzędów 1–5.

    board_name: napis na planszy, jeśli inny niż nazwa (linia „PLANSZA:”).
    """
    lines = [
        "# Kategoria do programu Fa milia.",
        f"# Zdjęcia i dźwięki nazwij: {stem}_<numer pytania>.<rozszerzenie>,",
        f"# np. {stem}_2.jpg albo {stem}_3.mp3",
        "",
        f"KATEGORIA: {name}",
    ]
    if board_name.strip() and board_name.strip() != name.strip():
        lines.append(f"PLANSZA: {board_name.strip()}")
    lines.append("")
    for row, (question, answer) in enumerate(questions, start=1):
        lines.append(str(row))
        lines += _field_lines("P:", question)
        lines += _field_lines("O:", answer)
        lines.append("")
    return "\n".join(lines)


def finals_to_text(finals: list[tuple[str, str, str]], stem: str = "final") -> str:
    """Tekst pliku final.txt. finals: lista (kategoria, pytanie, odpowiedź)."""
    lines = [
        "# Pytania finałowe do programu Fa milia.",
        f"# Zdjęcia i dźwięki nazwij: {stem}_<numer pytania>.<rozszerzenie>, np. {stem}_1.jpg",
        "",
    ]
    for number, (category, question, answer) in enumerate(finals, start=1):
        lines.append(str(number))
        lines.append(f"KATEGORIA: {category}")
        lines += _field_lines("P:", question)
        lines += _field_lines("O:", answer)
        lines.append("")
    return "\n".join(lines)
