"""Wspólne „fixtures” dla testów.

Fixture to funkcja przygotowująca dane do testu. Pytest sam ją wywołuje,
gdy test ma parametr o tej samej nazwie. `tmp_path` to wbudowany fixture
pytesta – tymczasowy katalog, kasowany po testach.
"""

from pathlib import Path

import pytest

from fa_milia.core.library import Library
from fa_milia.core.paths import DataDir

SAMPLE_MEDIA = Path(__file__).resolve().parent.parent / "fa_milia" / "resources" / "sample_media"


@pytest.fixture
def data_dir(tmp_path: Path) -> DataDir:
    data_dir = DataDir(tmp_path / "data")
    data_dir.ensure()
    return data_dir


@pytest.fixture
def library(data_dir: DataDir) -> Library:
    return Library(data_dir)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Kopia przykładowego obrazka w „obcym” miejscu (jak plik użytkownika)."""
    target = tmp_path / "Moje zdjęcie kota.PNG"
    target.write_bytes((SAMPLE_MEDIA / "flaga_polska.png").read_bytes())
    return target
