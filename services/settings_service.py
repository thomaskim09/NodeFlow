from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from utils.app_paths import get_settings_path

DEFAULT_SETTINGS = {
    "theme": "Default",
    "language": "English",
    "undo_depth": 100,
    "autosave_enabled": True,
    "autosave_delay_ms": 1500,
    "find_match_color": "#FFF59D",
}


class SettingsService:
    def load(self) -> dict[str, Any]:
        path = get_settings_path()
        if not path.exists():
            return deepcopy(DEFAULT_SETTINGS)
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return deepcopy(DEFAULT_SETTINGS)
            settings = deepcopy(DEFAULT_SETTINGS)
            settings.update(data)
            return settings
        except (OSError, json.JSONDecodeError):
            return deepcopy(DEFAULT_SETTINGS)

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(DEFAULT_SETTINGS)
        merged.update(settings)
        path = get_settings_path()
        with path.open("w", encoding="utf-8") as handle:
            json.dump(merged, handle, indent=2, ensure_ascii=False)
        return merged


settings_service = SettingsService()
