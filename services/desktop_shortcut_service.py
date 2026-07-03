from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from services.settings_service import settings_service

PROMPT_STATE_PENDING = "pending"
PROMPT_STATE_DONE = "done"
PROMPT_STATE_NEVER = "never"
PROMPT_MAX_DEFERRALS = 1


class DesktopShortcutService:
    def is_supported(self) -> bool:
        return sys.platform in {"win32", "darwin"}

    def is_packaged_build(self) -> bool:
        return bool(getattr(sys, "frozen", False))

    def get_desktop_dir(self) -> Path:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )
        return Path(location) if location else Path.home() / "Desktop"

    def get_shortcut_path(self) -> Path:
        desktop_dir = self.get_desktop_dir()
        if sys.platform == "win32":
            return desktop_dir / "NodeFlow.lnk"
        return desktop_dir / "NodeFlow.app"

    def shortcut_exists(self) -> bool:
        path = self.get_shortcut_path()
        return path.exists() or path.is_symlink()

    def should_prompt(self, settings: dict | None = None) -> bool:
        if not self.is_supported() or not self.is_packaged_build() or self.shortcut_exists():
            return False
        settings = settings or settings_service.load()
        state = settings.get("desktop_shortcut_prompt_state", PROMPT_STATE_PENDING)
        if state != PROMPT_STATE_PENDING:
            return False
        prompt_count = int(settings.get("desktop_shortcut_prompt_count", 0))
        return prompt_count <= PROMPT_MAX_DEFERRALS

    def mark_created(self) -> dict:
        return self._save_prompt_state(PROMPT_STATE_DONE)

    def mark_never(self) -> dict:
        return self._save_prompt_state(PROMPT_STATE_NEVER)

    def mark_deferred(self) -> dict:
        settings = settings_service.load()
        prompt_count = int(settings.get("desktop_shortcut_prompt_count", 0)) + 1
        state = (
            PROMPT_STATE_NEVER if prompt_count > PROMPT_MAX_DEFERRALS else PROMPT_STATE_PENDING
        )
        return settings_service.save(
            {
                **settings,
                "desktop_shortcut_prompt_count": prompt_count,
                "desktop_shortcut_prompt_state": state,
            }
        )

    def create_shortcut(self) -> Path:
        shortcut_path = self.get_shortcut_path()
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            self._create_windows_shortcut(shortcut_path)
        elif sys.platform == "darwin":
            self._create_macos_shortcut(shortcut_path)
        else:
            raise RuntimeError("Desktop shortcuts are not supported on this platform.")
        return shortcut_path

    def _save_prompt_state(self, state: str) -> dict:
        settings = settings_service.load()
        return settings_service.save(
            {
                **settings,
                "desktop_shortcut_prompt_state": state,
            }
        )

    def _create_windows_shortcut(self, shortcut_path: Path) -> None:
        target_path = self._windows_target_path()
        working_dir = target_path.parent
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$WshShell = New-Object -ComObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut('{str(shortcut_path)}'); "
                f"$Shortcut.TargetPath = '{str(target_path)}'; "
                f"$Shortcut.WorkingDirectory = '{str(working_dir)}'; "
                f"$Shortcut.IconLocation = '{str(target_path)},0'; "
                "$Shortcut.Save()"
            ),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)

    def _create_macos_shortcut(self, shortcut_path: Path) -> None:
        target_path = self._macos_target_path()
        if shortcut_path.is_symlink() or shortcut_path.exists():
            if shortcut_path.is_dir() and not shortcut_path.is_symlink():
                raise FileExistsError(f"Desktop item already exists at {shortcut_path}")
            shortcut_path.unlink()
        os.symlink(target_path, shortcut_path)

    def _windows_target_path(self) -> Path:
        return Path(sys.executable).resolve()

    def _macos_target_path(self) -> Path:
        executable = Path(sys.executable).resolve()
        if executable.parent.name == "MacOS" and executable.parent.parent.name == "Contents":
            return executable.parent.parent.parent
        return executable


desktop_shortcut_service = DesktopShortcutService()
