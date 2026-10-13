from fa_milia.core.text_format import (
    category_to_text,
    decode_text,
    parse_text,
    row_for_number,
    simplify,
)

BASIC = """KATEGORIA: Zwierzęta

1
P: Ile nóg ma pająk?
O: Osiem

2
P: Jak nazywa się to zwierzę?
O: Kapibara
"""


def test_basic_file():
    parsed = parse_text(BASIC)
    assert parsed.header_category == "Zwierzęta"
    assert [(b.number, b.question, b.answer) for b in parsed.blocks] == [
        (1, "Ile nóg ma pająk?", "Osiem"),
        (2, "Jak nazywa się to zwierzę?", "Kapibara"),
    ]
    assert parsed.problems == []


def test_keywords_are_case_and_accent_insensitive():
    text = """kategoria:   Kuchnia
    1.
    PYTANIE: Z czego są frytki?
    odpowiedź : Z ziemniaków
    2)
    Pytanie:Co to barszcz?
    ODPOWIEDZ: Zupa
    3
    p: Trzecie?
    o: Tak
    """
    parsed = parse_text(text)
    assert parsed.header_category == "Kuchnia"
    assert [(b.number, b.question, b.answer) for b in parsed.blocks] == [
        (1, "Z czego są frytki?", "Z ziemniaków"),
        (2, "Co to barszcz?", "Zupa"),
        (3, "Trzecie?", "Tak"),
    ]


def test_comments_blank_lines_and_extra_spaces_are_ignored():
    text = "# notatka\n\n   KATEGORIA: Sport   \n\n# jeszcze\n  1  \n\n  P:   Ile?  \n\n O:  Pięć \n"
    parsed = parse_text(text)
    assert parsed.header_category == "Sport"
    assert (parsed.blocks[0].question, parsed.blocks[0].answer) == ("Ile?", "Pięć")


def test_multiline_answer_until_next_number():
    text = "KATEGORIA: X\n1\nP: Wymień kolory flagi\nO: Biały\ni czerwony\n2\nP: Dwa\nO: B\n"
    parsed = parse_text(text)
    assert parsed.blocks[0].answer == "Biały\ni czerwony"
    assert parsed.blocks[1].question == "Dwa"


def test_text_without_prefix_after_number_is_the_question():
    parsed = parse_text("1\nIle nóg ma pająk?\nO: Osiem\n")
    assert parsed.blocks[0].question == "Ile nóg ma pająk?"


def test_problems_are_described_with_line_numbers():
    parsed = parse_text("Jakiś tekst\nP: pytanie bez numeru\n1\nP: ok\nO: ok\n")
    assert parsed.problems[0].startswith("linia 1: nie wiadomo")
    assert "linia 2" in parsed.problems[1] and "brakuje numeru" in parsed.problems[1]


def test_values_100_to_500_are_accepted_as_rows():
    assert [row_for_number(n) for n in (1, 5, 100, 300, 500)] == [1, 5, 1, 3, 5]
    assert row_for_number(6) is None
    assert row_for_number(250) is None
    assert row_for_number(0) is None


def test_decode_utf8_with_bom_and_windows_1250():
    text = "KATEGORIA: Zażółć gęślą jaźń"
    assert decode_text(text.encode("utf-8")) == text
    assert decode_text(text.encode("utf-8-sig")) == text  # BOM z Notatnika
    assert decode_text(text.encode("cp1250")) == text  # stary Notatnik w Windows


def test_simplify_removes_polish_letters():
    assert simplify("Odpowiedź") == "odpowiedz"
    assert simplify("FINAŁ") == "final"
    assert simplify("Zażółć") == "zazolc"


def test_written_text_can_be_parsed_back():
    questions = [(f"Pytanie {i}", f"Odp {i}") for i in range(1, 5)] + [("Linia 1\nLinia 2", "A\nB")]
    text = category_to_text("Muzyka", questions, "muzyka")
    parsed = parse_text(text)
    assert parsed.header_category == "Muzyka"
    assert [(b.question, b.answer) for b in parsed.blocks] == questions
