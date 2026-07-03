import importlib.util
from pathlib import Path

from PIL import Image


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
    assert build_app_icons.windows_icon_sizes() == (256, 128, 96, 64, 48, 40, 32, 24, 16)


def test_build_windows_icon_writes_multi_size_ico(tmp_path):
    source = tmp_path / "icon.png"
    destination = tmp_path / "icon.ico"
    Image.new("RGBA", (512, 512), (255, 128, 0, 255)).save(source)

    build_app_icons.build_windows_icon(source, destination)

    with Image.open(destination) as icon_image:
        assert icon_image.format == "ICO"
        assert icon_image.info["sizes"] == {
            (256, 256),
            (128, 128),
            (96, 96),
            (64, 64),
            (48, 48),
            (40, 40),
            (32, 32),
            (24, 24),
            (16, 16),
        }
