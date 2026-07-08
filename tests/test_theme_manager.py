from PySide6.QtGui import QFont

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


def test_apply_theme_sets_application_font_size(monkeypatch):
    monkeypatch.setattr(
        theme_manager,
        "load_settings",
        lambda: {"theme": "Light", "font_size": 15},
    )

    class FakeApp:
        def __init__(self):
            self.stylesheet = None
            self._font = QFont()

        def setStyleSheet(self, stylesheet):
            self.stylesheet = stylesheet

        def font(self):
            return self._font

        def setFont(self, font):
            self._font = QFont(font)

    app = FakeApp()

    theme_manager.apply_theme(app)

    assert app.stylesheet
    assert app.font().pointSize() == 15
