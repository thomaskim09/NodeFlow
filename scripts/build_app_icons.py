from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


def icon_artifact_paths(root: Path) -> dict[str, Path]:
    resource_dir = root / "resource"
    return {
        "png": resource_dir / "icon.png",
        "ico": resource_dir / "icon.ico",
        "icns": resource_dir / "icon.icns",
    }


def windows_icon_sizes() -> tuple[int, ...]:
    return (256, 128, 96, 64, 48, 40, 32, 24, 16)


def build_windows_icon(source: Path, destination: Path) -> None:
    from PIL import Image

    with Image.open(source) as image:
        base_image = image.convert("RGBA")
        base_image.save(
            destination,
            format="ICO",
            bitmap_format="bmp",
            sizes=[(size, size) for size in windows_icon_sizes()],
        )


def build_macos_icon(source: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        iconset_dir = Path(tmp_dir) / "NodeFlow.iconset"
        iconset_dir.mkdir()

        for size in (16, 32, 128, 256, 512):
            subprocess.run(
                [
                    "sips",
                    "-z",
                    str(size),
                    str(size),
                    str(source),
                    "--out",
                    str(iconset_dir / f"icon_{size}x{size}.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "sips",
                    "-z",
                    str(size * 2),
                    str(size * 2),
                    str(source),
                    "--out",
                    str(iconset_dir / f"icon_{size}x{size}@2x.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(destination)],
            check=True,
            capture_output=True,
            text=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build NodeFlow app icons for packaging.")
    parser.add_argument("target", choices=("windows", "macos"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    paths = icon_artifact_paths(root)
    source = paths["png"]

    if not source.exists():
        raise FileNotFoundError(f"Missing source icon: {source}")

    if args.target == "windows":
        build_windows_icon(source, paths["ico"])
        print(f"Built {paths['ico']}")
        return

    build_macos_icon(source, paths["icns"])
    print(f"Built {paths['icns']}")


if __name__ == "__main__":
    main()
