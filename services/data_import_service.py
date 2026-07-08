from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from repositories.base import initialize_database
from utils.app_paths import get_user_data_dir


class DataImportService:
    def import_data_folder(
        self,
        source_dir: str | Path,
        target_dir: str | Path | None = None,
    ) -> tuple[Path, Path | None]:
        source = Path(source_dir).resolve()
        if not source.is_dir():
            raise ValueError("Selected path is not a folder.")
        if not (source / "nodeflow.db").exists():
            raise ValueError("Selected folder does not contain nodeflow.db.")

        target = Path(target_dir).resolve() if target_dir else get_user_data_dir().resolve()
        if source == target:
            raise ValueError("Selected folder is already the current NodeFlow data folder.")

        target.mkdir(parents=True, exist_ok=True)
        backup_path = self._backup_target_dir(target) if any(target.iterdir()) else None
        self._clear_directory(target)
        self._copy_directory_contents(source, target)
        initialize_database()
        return target, backup_path

    def _backup_target_dir(self, target: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target.parent / f"{target.name}_backup_{timestamp}"
        shutil.copytree(target, backup_path)
        return backup_path

    @staticmethod
    def _copy_directory_contents(source: Path, target: Path) -> None:
        for child in source.iterdir():
            destination = target / child.name
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)

    @staticmethod
    def _clear_directory(target: Path) -> None:
        for child in target.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


data_import_service = DataImportService()
