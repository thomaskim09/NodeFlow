from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "NodeFlow"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def get_bundle_root() -> Path:
    return _bundle_root()


def get_bundle_resource_path(name: str) -> Path:
    return get_bundle_root() / "resource" / name


@lru_cache(maxsize=1)
def get_user_data_dir() -> Path:
    override = os.environ.get("NODEFLOW_USER_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if location:
        path = Path(location)
    else:
        path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_user_data_dir() / "nodeflow.db"


def get_settings_path() -> Path:
    return get_user_data_dir() / "settings.json"


def get_logs_dir() -> Path:
    path = get_user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_exports_dir() -> Path:
    path = get_user_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_test_user_data_dir(path: Path | str | None) -> None:
    get_user_data_dir.cache_clear()
    if path is None:
        os.environ.pop("NODEFLOW_USER_DATA_DIR", None)
        return
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.environ["NODEFLOW_USER_DATA_DIR"] = str(path)
