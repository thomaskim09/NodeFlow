from managers import theme_manager


def test_effective_theme_mode_uses_dark_only_for_explicit_dark():
    assert theme_manager.get_effective_theme_mode("Dark") == "Dark"
    assert theme_manager.get_effective_theme_mode("Light") == "Light"
    assert theme_manager.get_effective_theme_mode("Default") == "Light"


def test_effective_theme_mode_reads_saved_setting(monkeypatch):
    monkeypatch.setattr(
        theme_manager,
        "load_settings",
        lambda: {"theme": "Dark"},
    )
    assert theme_manager.get_effective_theme_mode() == "Dark"
