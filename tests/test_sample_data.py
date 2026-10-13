from fa_milia.core.library import Library
from fa_milia.core.sample_data import SAMPLE_CATEGORIES, install_if_first_run
from fa_milia.core.textutil import polish_sort_key
from tests.conftest import SAMPLE_MEDIA


def test_sample_data_is_complete_and_installed_once(library, data_dir):
    assert install_if_first_run(library, SAMPLE_MEDIA) is True

    fresh = Library(data_dir)
    assert len(fresh.categories) == len(SAMPLE_CATEGORIES) >= 14
    assert len(fresh.complete_categories()) == len(fresh.categories)
    assert len(fresh.complete_finals()) == 3
    assert fresh.load_errors == []

    # Drugie uruchomienie niczego nie dodaje – nawet gdy użytkownik usunął kategorie.
    for category_id in list(fresh.categories):
        fresh.delete_category(category_id)
    assert install_if_first_run(fresh, SAMPLE_MEDIA) is False
    assert fresh.categories == {}


def test_sample_category_names_are_unique():
    names = [name.casefold() for name, _ in SAMPLE_CATEGORIES]
    assert len(names) == len(set(names))


def test_polish_sort_key_puts_digits_first():
    assert sorted(["b", "1", "ą", "a"], key=polish_sort_key) == ["1", "a", "ą", "b"]
