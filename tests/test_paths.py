import sys

from fa_milia.core import paths


def test_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("FA_MILIA_DATA_DIR", str(tmp_path / "x"))
    assert paths.default_data_root() == tmp_path / "x"


def test_linux_uses_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.delenv("FA_MILIA_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.default_data_root() == tmp_path / "fa-milia"


def test_windows_exe_keeps_data_next_to_exe(monkeypatch, tmp_path):
    monkeypatch.delenv("FA_MILIA_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Fa milia.exe"))
    assert paths.default_data_root() == tmp_path / "Fa milia - dane"


def test_windows_falls_back_to_appdata_when_not_writable(monkeypatch, tmp_path):
    monkeypatch.delenv("FA_MILIA_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Fa milia.exe"))
    monkeypatch.setattr(paths, "_is_writable", lambda folder: False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert paths.default_data_root() == tmp_path / "Roaming" / "fa-milia"


def test_windows_source_run_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("FA_MILIA_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.default_data_root() == tmp_path / "fa-milia"
