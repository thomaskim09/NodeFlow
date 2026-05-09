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
    saved = settings_service.save({"theme": "Dark", "language": "Chinese"})
    loaded = settings_service.load()

    assert saved["theme"] == "Dark"
    assert loaded["language"] == "Chinese"
    assert get_settings_path().exists()
