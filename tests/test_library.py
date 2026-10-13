import pytest

from fa_milia.core.library import Library
from fa_milia.core.models import Category, ContentKind, FinalQuestion, Question
from tests.test_models import complete_category


def test_saved_category_survives_reload(library, data_dir):
    category = complete_category()
    library.save_category(category)

    fresh = Library(data_dir)  # nowy obiekt czyta wszystko z dysku
    assert fresh.categories[category.id] == category


def test_delete_category(library, data_dir):
    category = complete_category()
    library.save_category(category)
    library.delete_category(category.id)
    assert category.id not in library.categories
    assert Library(data_dir).categories == {}


def test_broken_file_is_reported_not_fatal(library, data_dir):
    library.save_category(complete_category())
    (data_dir.categories / "zepsuty.json").write_text("{ to nie jest json", encoding="utf-8")

    fresh = Library(data_dir)
    assert len(fresh.categories) == 1
    assert len(fresh.load_errors) == 1
    assert "zepsuty.json" in fresh.load_errors[0]


def test_categories_sorted_by_polish_alphabet(library):
    for name in ("Zwierzęta", "Łamigłówki", "Lody", "Ąąą"):
        library.save_category(complete_category(name))
    names = [c.name for c in library.sorted_categories()]
    assert names == ["Ąąą", "Lody", "Łamigłówki", "Zwierzęta"]


def test_only_complete_categories_can_be_played(library):
    good = complete_category("Dobra")
    bad = complete_category("Niedokończona")
    bad.questions[2].answer = ""
    library.save_category(good)
    library.save_category(bad)
    assert library.complete_categories() == [good]


def test_import_media_copies_file_and_keeps_readable_name(library, sample_image):
    name = library.import_media(sample_image)
    assert library.media_path(name).read_bytes() == sample_image.read_bytes()
    assert name.endswith("_Moje_zdjęcie_kota.png")  # rozszerzenie małymi literami
    assert Library.display_media_name(name) == "Moje_zdjęcie_kota.png"


def test_import_media_rejects_unsupported_files(library, tmp_path):
    document = tmp_path / "dokument.pdf"
    document.write_bytes(b"%PDF")
    with pytest.raises(ValueError):
        library.import_media(document)


def test_missing_media_file_makes_category_incomplete(library, sample_image):
    category = complete_category()
    name = library.import_media(sample_image)
    category.questions[0] = Question(ContentKind.IMAGE, "", name, "Flaga")
    library.save_category(category)
    assert library.category_problems(category) == []

    library.media_path(name).unlink()
    assert library.category_problems(category) == [
        "pytanie 1: plik Moje_zdjęcie_kota.png nie istnieje"
    ]


def test_remove_unused_media_keeps_used_files(library, sample_image):
    used = library.import_media(sample_image)
    orphan = library.import_media(sample_image)
    final = FinalQuestion("Flagi", Question(ContentKind.IMAGE, "", used, "Polska"))
    library.save_final(final)

    assert library.remove_unused_media() == 1
    assert library.media_path(used).exists()
    assert not library.media_path(orphan).exists()


def test_remove_unused_media_does_nothing_after_load_errors(library, data_dir, sample_image):
    orphan = library.import_media(sample_image)
    (data_dir.categories / "zepsuty.json").write_text("???", encoding="utf-8")
    fresh = Library(data_dir)
    assert fresh.remove_unused_media() == 0
    assert fresh.media_path(orphan).exists()


def test_unique_category_name(library):
    assert library.unique_category_name("Nowa kategoria") == "Nowa kategoria"
    library.save_category(Category(name="Nowa kategoria"))
    library.save_category(Category(name="nowa KATEGORIA (2)"))
    assert library.unique_category_name("Nowa kategoria") == "Nowa kategoria (3)"


def test_category_name_taken_ignores_case_and_self(library):
    category = complete_category("Zwierzęta")
    library.save_category(category)
    assert library.category_name_taken(" zwierzęta ")
    assert not library.category_name_taken("Zwierzęta", except_id=category.id)
