from services.settings_service import settings_service
from utils.app_paths import get_bundle_resource_path, get_settings_path, get_user_data_dir


def test_user_data_dir_is_writable():
    path = get_user_data_dir()
    assert path.exists()
    assert path.is_dir()


def test_bundle_resource_path_points_into_resource_dir():
    path = get_bundle_resource_path("icon.png")
    assert path.name == "icon.png"
    assert "resource" in path.parts


def test_settings_round_trip():
    saved = settings_service.save(
        {"theme": "Dark", "language": "Chinese", "undo_depth": 150}
    )
    loaded = settings_service.load()

    assert saved["theme"] == "Dark"
    assert loaded["language"] == "Chinese"
    assert loaded["undo_depth"] == 150
    assert get_settings_path().exists()


def test_settings_default_undo_depth_for_older_settings():
    get_settings_path().write_text(
        '{"theme": "Dark", "language": "Chinese"}',
        encoding="utf-8",
    )
    loaded = settings_service.load()

    assert loaded["undo_depth"] == 100
