from PySide6.QtCore import QStandardPaths

from services.settings_service import settings_service
from utils import app_paths
from utils.app_paths import (
    clear_portable_migration_notice,
    get_bundle_resource_path,
    get_settings_path,
    get_user_data_dir,
    has_portable_migration_notice,
    prepare_user_data_dir,
)


def test_user_data_dir_is_writable():
    path = get_user_data_dir()
    assert path.exists()
    assert path.is_dir()


def test_bundle_resource_path_points_into_resource_dir():
    path = get_bundle_resource_path("icon.png")
    assert path.name == "icon.png"
    assert "resource" in path.parts


def test_frozen_build_prefers_portable_data_dir(monkeypatch, tmp_path):
    exe_dir = tmp_path / "NodeFlow"
    exe_dir.mkdir()
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str(exe_dir / "NodeFlow.exe"))
    monkeypatch.delenv("NODEFLOW_USER_DATA_DIR", raising=False)
    app_paths.get_user_data_dir.cache_clear()

    path = get_user_data_dir()

    assert path == exe_dir / "data"
    assert path.exists()


def test_frozen_build_copies_legacy_appdata_into_portable_dir(monkeypatch, tmp_path):
    exe_dir = tmp_path / "NodeFlow"
    exe_dir.mkdir()
    legacy_dir = tmp_path / "roaming"
    legacy_dir.mkdir()
    (legacy_dir / "nodeflow.db").write_text("db", encoding="utf-8")
    (legacy_dir / "settings.json").write_text("{}", encoding="utf-8")
    (legacy_dir / "logs").mkdir()
    (legacy_dir / "logs" / "nodeflow.log").write_text("log", encoding="utf-8")

    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str(exe_dir / "NodeFlow.exe"))
    monkeypatch.delenv("NODEFLOW_USER_DATA_DIR", raising=False)
    monkeypatch.setattr(
        QStandardPaths,
        "writableLocation",
        lambda location: str(legacy_dir),
    )
    app_paths.get_user_data_dir.cache_clear()

    target = prepare_user_data_dir()

    assert target == exe_dir / "data"
    assert (target / "nodeflow.db").read_text(encoding="utf-8") == "db"
    assert (target / "settings.json").read_text(encoding="utf-8") == "{}"
    assert (target / "logs" / "nodeflow.log").read_text(encoding="utf-8") == "log"
    assert has_portable_migration_notice()
    clear_portable_migration_notice()
    assert not has_portable_migration_notice()


def test_settings_round_trip():
    saved = settings_service.save(
        {
            "theme": "Dark",
            "language": "Chinese",
            "undo_depth": 150,
            "autosave_enabled": False,
            "autosave_delay_ms": 3000,
            "find_match_color": "#FFD54F",
        }
    )
    loaded = settings_service.load()

    assert saved["theme"] == "Dark"
    assert loaded["language"] == "Chinese"
    assert loaded["undo_depth"] == 150
    assert loaded["autosave_enabled"] is False
    assert loaded["autosave_delay_ms"] == 3000
    assert loaded["find_match_color"] == "#FFD54F"
    assert loaded["desktop_shortcut_prompt_state"] == "pending"
    assert loaded["desktop_shortcut_prompt_count"] == 0
    assert get_settings_path().exists()


def test_settings_default_undo_depth_for_older_settings():
    get_settings_path().write_text(
        '{"theme": "Dark", "language": "Chinese"}',
        encoding="utf-8",
    )
    loaded = settings_service.load()

    assert loaded["undo_depth"] == 100
    assert loaded["autosave_enabled"] is True
    assert loaded["autosave_delay_ms"] == 1500
    assert loaded["find_match_color"] == "#FFF59D"
    assert loaded["desktop_shortcut_prompt_state"] == "pending"
    assert loaded["desktop_shortcut_prompt_count"] == 0


def test_explicit_user_data_override_still_wins(monkeypatch, tmp_path):
    override_dir = tmp_path / "override"
    monkeypatch.setenv("NODEFLOW_USER_DATA_DIR", str(override_dir))
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str((tmp_path / "NodeFlow.exe")))
    app_paths.get_user_data_dir.cache_clear()

    path = get_user_data_dir()

    assert path == override_dir
