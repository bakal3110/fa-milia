import zipfile
from pathlib import Path

import pytest

from fa_milia.core.exporter import create_template, export_to_folder
from fa_milia.core.importer import (
    ConflictAction,
    ImportFailed,
    Status,
    apply_import,
    extract_zip,
    scan_folder,
)
from fa_milia.core.models import ContentKind
from fa_milia.core.sample_data import install_sample_data
from tests.conftest import SAMPLE_MEDIA

FULL = """KATEGORIA: Zwierzęta
1
P: Ile nóg ma pająk?
O: Osiem
2
P: Jak nazywa się to zwierzę?
O: Kapibara
3
P: Trzy?
O: Tak
4
P: Cztery?
O: Tak
5
P: Pięć?
O: Tak
"""


def write(folder: Path, name: str, text: str, encoding: str = "utf-8") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(text.encode(encoding))


def image(folder: Path, name: str) -> None:
    (folder / name).write_bytes((SAMPLE_MEDIA / "flaga_polska.png").read_bytes())


def problems(preview) -> list[str]:
    return preview.problems + [p for item in preview.items for p in item.problems]


# --- Skanowanie ----------------------------------------------------------------


def test_complete_category_with_image(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL)
    image(folder, "zwierzeta_2.jpg")

    preview = scan_folder(folder, library)
    assert problems(preview) == []
    [item] = preview.items
    assert item.status == Status.OK
    assert item.title == "Zwierzęta"
    question = item.category.questions[1]
    assert question.kind == ContentKind.IMAGE
    assert question.text == "Jak nazywa się to zwierzę?"  # tekst P: jest podpisem


def test_media_question_may_have_empty_caption(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL.replace("P: Trzy?", "P:"))
    image(folder, "zwierzeta_3.png")
    item = scan_folder(folder, library).items[0]
    assert item.status == Status.OK
    assert item.category.questions[2].text == ""


def test_human_readable_errors(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL.replace("O: Tak\n5", "\n5", 1))  # pyt. 4 bez odpowiedzi
    image(folder, "zwierzeta_7.jpg")
    image(folder, "kot.jpg")
    write(folder, "notatki.docx", "x")

    preview = scan_folder(folder, library)
    all_problems = problems(preview)
    assert "zwierzeta.txt, pytanie 4: brak odpowiedzi" in all_problems
    assert any(p.startswith("Plik zwierzeta_7.jpg nie pasuje do żadnego pytania")
               for p in all_problems)
    assert any(p.startswith("Plik kot.jpg nie pasuje do żadnego pytania") for p in all_problems)
    assert any("notatki.docx" in p and "nieobsługiwany" in p for p in all_problems)
    assert preview.items[0].status == Status.INCOMPLETE


def test_missing_questions_and_category_line(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "domowe_zwierzeta.txt", "1\nP: Jedno?\nO: Tak\n")
    item = scan_folder(folder, library).items[0]
    assert item.title == "Domowe zwierzeta"
    assert "domowe_zwierzeta.txt, pytanie 2: brak w pliku" in item.problems
    assert any("brak linii „KATEGORIA" in p for p in item.problems)
    assert item.status == Status.INCOMPLETE


def test_file_without_questions_is_an_error(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "pusty.txt", "# tylko komentarz\n")
    item = scan_folder(folder, library).items[0]
    assert item.status == Status.ERROR


def test_windows_1250_file(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL.replace("Zwierzęta", "Zwierzęta źrebięce"), "cp1250")
    item = scan_folder(folder, library).items[0]
    assert item.title == "Zwierzęta źrebięce"
    assert item.category.questions[0].text == "Ile nóg ma pająk?"


def test_values_as_numbers_and_matching_media(tmp_path, library):
    text = FULL
    for row in range(1, 6):
        text = text.replace(f"\n{row}\n", f"\n{row * 100}\n")
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", text)
    image(folder, "Zwierzęta_300.JPG")  # wielkość liter i polskie znaki bez znaczenia
    item = scan_folder(folder, library).items[0]
    assert item.status == Status.OK
    assert item.category.questions[2].kind == ContentKind.IMAGE


def test_ignores_instruction_and_template_files(tmp_path, library):
    folder = create_template(tmp_path)
    preview = scan_folder(folder, library)
    assert preview.items == []
    assert "nie ma plików .txt" in preview.problems[0]


def test_finals_file_with_polish_name(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "finał.txt", """1
KATEGORIA: Historia
P: Kiedy chrzest Polski?
O: 966

2
KATEGORIA: Sztuka
P:
O: Jan Matejko
""")
    image(folder, "final_2.jpg")
    preview = scan_folder(folder, library)
    first, second = preview.items
    assert first.final.category == "Historia" and first.status == Status.OK
    assert second.final.question.kind == ContentKind.IMAGE and second.status == Status.OK


# --- Zapis do biblioteki i konflikty -------------------------------------------


def test_apply_import_copies_media_into_library(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL)
    image(folder, "zwierzeta_2.jpg")
    preview = scan_folder(folder, library)

    result = apply_import(library, preview.items)
    assert result.added == 1
    [category] = library.categories.values()
    media = category.questions[1].media
    assert media.endswith("_zwierzeta_2.jpg")
    assert library.media_path(media).is_file()
    assert library.category_problems(category) == []


def test_name_conflict_skip_replace_copy(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "zwierzeta.txt", FULL)
    apply_import(library, scan_folder(folder, library).items)
    original_id = next(iter(library.categories))

    preview = scan_folder(folder, library)
    assert preview.items[0].conflict_id == original_id
    assert apply_import(library, preview.items, {0: ConflictAction.SKIP}).skipped == 1
    assert len(library.categories) == 1

    write(folder, "zwierzeta.txt", FULL.replace("Osiem", "8"))
    preview = scan_folder(folder, library)
    assert apply_import(library, preview.items, {0: ConflictAction.REPLACE}).replaced == 1
    assert library.categories[original_id].questions[0].answer == "8"

    preview = scan_folder(folder, library)
    apply_import(library, preview.items, {0: ConflictAction.COPY})
    assert sorted(c.name for c in library.categories.values()) == ["Zwierzęta", "Zwierzęta (2)"]


def test_error_items_are_not_imported(tmp_path, library):
    folder = tmp_path / "import"
    write(folder, "pusty.txt", "\n")
    result = apply_import(library, scan_folder(folder, library).items)
    assert result.skipped == 1 and library.categories == {}


# --- .zip ------------------------------------------------------------------------


def test_zip_with_folder_inside(tmp_path, library):
    folder = tmp_path / "Pytania"
    write(folder, "zwierzeta.txt", FULL)
    zip_path = tmp_path / "pytania.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(folder / "zwierzeta.txt", "Pytania/zwierzeta.txt")
    found, temp = extract_zip(zip_path)
    try:
        assert scan_folder(found, library).items[0].status == Status.OK
    finally:
        temp.cleanup()


def test_bad_zip_and_path_traversal(tmp_path):
    bad = tmp_path / "zly.zip"
    bad.write_text("to nie zip")
    with pytest.raises(ImportFailed):
        extract_zip(bad)
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as archive:
        archive.writestr("../poza.txt", "x")
    with pytest.raises(ImportFailed):
        extract_zip(evil)


# --- Eksport -----------------------------------------------------------------------


def test_export_then_import_gives_the_same_content(tmp_path, library, data_dir):
    install_sample_data(library, SAMPLE_MEDIA)
    category_ids = [c.id for c in library.sorted_categories()]
    final_ids = [f.id for f in library.sorted_finals()]
    folder = export_to_folder(library, category_ids, final_ids, tmp_path)

    assert (folder / "JAK_DODAC_PYTANIA.txt").exists()
    assert (folder / "flagi_1.png").exists()
    raw = (folder / "zwierzeta.txt").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw  # BOM i końce linii Notatnika

    from fa_milia.core.library import Library
    from fa_milia.core.paths import DataDir
    other = Library(DataDir(tmp_path / "inna"))
    preview = scan_folder(folder, other)
    assert problems(preview) == []
    apply_import(other, preview.items)

    def content(lib):
        cats = {c.name: [(q.kind, q.text, q.answer, lib.media_path(q.media).read_bytes()
                          if q.media else None) for q in c.questions]
                for c in lib.categories.values()}
        finals = sorted((f.category, f.question.text, f.question.answer)
                        for f in lib.finals.values())
        return cats, finals

    assert content(other) == content(library)


def test_export_names_are_unique_and_safe(tmp_path, library):
    from tests.test_models import complete_category
    for name in ("Zwierzęta", "zwierzęta!", "Final"):
        library.save_category(complete_category(name))
    folder = export_to_folder(library, list(library.categories), [], tmp_path)
    names = sorted(p.name for p in folder.glob("*.txt"))
    assert names == ["JAK_DODAC_PYTANIA.txt", "final_kategoria.txt",
                     "zwierzeta-2.txt", "zwierzeta.txt"]


def test_template_contents(tmp_path):
    folder = create_template(tmp_path)
    template = (folder / "WZOR.txt").read_text(encoding="utf-8-sig")
    instruction = (folder / "JAK_DODAC_PYTANIA.txt").read_text(encoding="utf-8-sig")
    assert template.count("P:") >= 5 and "KATEGORIA:" in template
    assert "zwierzeta_2.jpg" in instruction
    assert create_template(tmp_path).name == "Szablon pytań Fa milia (2)"
