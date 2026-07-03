import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "build_app_icons.py"
_SPEC = importlib.util.spec_from_file_location("build_app_icons", _MODULE_PATH)
assert _SPEC and _SPEC.loader
build_app_icons = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_app_icons)


def test_icon_artifact_paths_live_in_resource_dir():
    paths = build_app_icons.icon_artifact_paths(Path("/tmp/nodeflow"))

    assert paths["png"] == Path("/tmp/nodeflow/resource/icon.png")
    assert paths["ico"] == Path("/tmp/nodeflow/resource/icon.ico")
    assert paths["icns"] == Path("/tmp/nodeflow/resource/icon.icns")


def test_windows_icon_sizes_cover_pyinstaller_friendly_sizes():
    assert build_app_icons.windows_icon_sizes() == (256, 128, 64, 48, 32, 16)
