from fa_milia.config import ROW_COUNT
from fa_milia.core.models import (
    Category,
    ContentKind,
    FinalQuestion,
    Question,
    kind_for_file,
)


def complete_category(name: str = "Zwierzęta") -> Category:
    questions = [Question(text=f"Pytanie {i}", answer=f"Odp {i}") for i in range(1, 6)]
    return Category(name=name, questions=questions)


def test_new_category_has_five_empty_questions():
    category = Category()
    assert len(category.questions) == ROW_COUNT
    assert not category.is_complete()


def test_each_category_gets_its_own_question_list():
    first, second = Category(), Category()
    first.questions[0].text = "zmiana"
    assert second.questions[0].text == ""
    assert first.id != second.id


def test_text_question_needs_text_and_answer():
    assert Question(text="Ile?", answer="Dwa").is_complete()
    assert Question(text="  ", answer="Dwa").problems() == ["brak treści pytania"]
    assert Question(text="Ile?", answer="").problems() == ["brak odpowiedzi"]


def test_image_question_needs_file_but_caption_is_optional():
    question = Question(kind=ContentKind.IMAGE, text="", media=None, answer="Kot")
    assert question.problems() == ["brak pliku obrazu"]
    question.media = "abc_kot.jpg"
    assert question.is_complete()


def test_media_must_match_question_kind():
    question = Question(kind=ContentKind.SOUND, media="abc_kot.jpg", answer="Kot")
    assert question.problems() == ["wybrany plik nie pasuje do rodzaju pytania"]


def test_category_problems_are_numbered():
    category = complete_category()
    category.name = ""
    category.questions[3].answer = ""
    assert category.problems() == ["brak nazwy kategorii", "pytanie 4: brak odpowiedzi"]


def test_category_round_trip_through_dict():
    category = complete_category()
    category.questions[1] = Question(ContentKind.IMAGE, "Podpis", "abc_x.png", "Odp")
    assert Category.from_dict(category.to_dict()) == category


def test_category_from_dict_always_has_five_questions():
    too_short = {"id": "x", "name": "K", "questions": [{"text": "a", "answer": "b"}]}
    assert len(Category.from_dict(too_short).questions) == ROW_COUNT
    too_long = {"id": "x", "name": "K", "questions": [{"text": "a"}] * 8}
    assert len(Category.from_dict(too_long).questions) == ROW_COUNT


def test_unknown_kind_falls_back_to_text():
    assert Question.from_dict({"kind": "video"}).kind == ContentKind.TEXT


def test_final_question_round_trip_and_problems():
    final = FinalQuestion(category="Historia", question=Question(text="Kiedy?", answer="966"))
    assert final.is_complete()
    assert FinalQuestion.from_dict(final.to_dict()) == final
    assert FinalQuestion(question=Question(text="Kiedy?")).problems() == [
        "brak kategorii",
        "brak odpowiedzi",
    ]


def test_kind_for_file_ignores_letter_case():
    assert kind_for_file("ZDJECIE.JPG") == ContentKind.IMAGE
    assert kind_for_file("melodia.Ogg") == ContentKind.SOUND
    assert kind_for_file("notatki.txt") is None
