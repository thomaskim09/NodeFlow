from services.settings_service import settings_service
from utils import app_paths
from utils.app_paths import (
    get_bundle_resource_path,
    get_settings_path,
    get_user_data_dir,
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


def test_prepare_user_data_dir_uses_existing_user_data_dir(monkeypatch, tmp_path):
    exe_dir = tmp_path / "NodeFlow"
    exe_dir.mkdir()
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str(exe_dir / "NodeFlow.exe"))
    monkeypatch.delenv("NODEFLOW_USER_DATA_DIR", raising=False)
    app_paths.get_user_data_dir.cache_clear()

    target = prepare_user_data_dir()

    assert target == exe_dir / "data"
    assert target.exists()


def test_settings_round_trip():
    saved = settings_service.save(
        {
            "theme": "Dark",
            "language": "Chinese",
            "font_size": 14,
            "undo_depth": 150,
            "autosave_enabled": False,
            "autosave_delay_ms": 3000,
            "find_match_color": "#FFD54F",
        }
    )
    loaded = settings_service.load()

    assert saved["theme"] == "Dark"
    assert loaded["language"] == "Chinese"
    assert loaded["font_size"] == 14
    assert loaded["undo_depth"] == 150
    assert loaded["autosave_enabled"] is False
    assert loaded["autosave_delay_ms"] == 3000
    assert loaded["find_match_color"] == "#FFD54F"
    assert get_settings_path().exists()


def test_settings_default_undo_depth_for_older_settings():
    get_settings_path().write_text(
        '{"theme": "Dark", "language": "Chinese"}',
        encoding="utf-8",
    )
    loaded = settings_service.load()

    assert loaded["undo_depth"] == 100
    assert loaded["font_size"] == 12
    assert loaded["autosave_enabled"] is True
    assert loaded["autosave_delay_ms"] == 1500
    assert loaded["find_match_color"] == "#FFF59D"


def test_explicit_user_data_override_still_wins(monkeypatch, tmp_path):
    override_dir = tmp_path / "override"
    monkeypatch.setenv("NODEFLOW_USER_DATA_DIR", str(override_dir))
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_paths.sys, "executable", str((tmp_path / "NodeFlow.exe")))
    app_paths.get_user_data_dir.cache_clear()

    path = get_user_data_dir()

    assert path == override_dir
