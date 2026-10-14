from fa_milia.core.settings import Settings, load_settings, save_settings


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "brak.json") == Settings()


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(game_screen="HDMI-A-1", fullscreen=False, game_scale=150, host_scale=80)
    save_settings(path, settings)
    assert load_settings(path) == settings


def test_values_are_clamped_to_allowed_range():
    settings = Settings.from_dict({"game_scale": 999, "host_scale": 10, "volume": -5})
    assert (settings.game_scale, settings.host_scale, settings.volume) == (250, 50, 0)


def test_broken_or_strange_file_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ zepsute", encoding="utf-8")
    assert load_settings(path) == Settings()
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_settings(path) == Settings()
    path.write_text('{"game_scale": "dużo"}', encoding="utf-8")
    assert load_settings(path) == Settings()


def test_unknown_keys_are_ignored():
    assert Settings.from_dict({"cos_nowego": 1, "game_scale": 120}).game_scale == 120


def test_old_default_final_time_is_migrated_to_30(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"final_seconds": 60, "timer_enabled": true}', encoding="utf-8")
    assert load_settings(path).final_seconds == 30
    path.write_text('{"final_seconds": 45}', encoding="utf-8")
    assert load_settings(path).final_seconds == 45  # własny czas zostaje


def test_new_files_keep_60_seconds_if_chosen(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(path, Settings(final_seconds=60))
    assert load_settings(path).final_seconds == 60
