from __future__ import annotations

import os
import shutil
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


def get_appdata_user_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if location:
        path = Path(location)
    else:
        path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_portable_user_data_dir() -> Path:
    return Path(sys.executable).resolve().parent / "data"


def _portable_data_available() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    try:
        get_portable_user_data_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return True


@lru_cache(maxsize=1)
def get_user_data_dir() -> Path:
    override = os.environ.get("NODEFLOW_USER_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if not getattr(sys, "frozen", False):
        path = get_bundle_root() / "data"
    elif _portable_data_available():
        path = get_portable_user_data_dir()
    else:
        path = get_appdata_user_data_dir()
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


def get_database_backups_dir() -> Path:
    path = get_user_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_imports_dir() -> Path:
    path = get_user_data_dir() / "imports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_exports_dir() -> Path:
    path = get_user_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_portable_migration_notice_path() -> Path:
    return get_user_data_dir() / ".portable_data_migrated"


def has_portable_migration_notice() -> bool:
    return get_portable_migration_notice_path().exists()


def clear_portable_migration_notice() -> None:
    get_portable_migration_notice_path().unlink(missing_ok=True)


def prepare_user_data_dir() -> Path:
    target = get_user_data_dir()
    if os.environ.get("NODEFLOW_USER_DATA_DIR") or not _portable_data_available():
        return target

    legacy = get_appdata_user_data_dir()
    if legacy == target:
        return target

    # ponytail: copy once into portable storage for packaged builds; delete legacy manually if you want a full move.
    if not any(legacy.iterdir()) or any(target.iterdir()):
        return target

    for name in ("nodeflow.db", "settings.json", "logs", "backups", "imports", "exports"):
        source = legacy / name
        destination = target / name
        if not source.exists() or destination.exists():
            continue
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    get_portable_migration_notice_path().write_text(str(target), encoding="utf-8")
    return target


def set_test_user_data_dir(path: Path | str | None) -> None:
    get_user_data_dir.cache_clear()
    if path is None:
        os.environ.pop("NODEFLOW_USER_DATA_DIR", None)
        return
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.environ["NODEFLOW_USER_DATA_DIR"] = str(path)
