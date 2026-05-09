import yaml
from pathlib import Path

_LOCALE_CACHE = {}


def load_locale(language):
    # Map user-friendly names to locale codes
    lang_map = {"Chinese": "zh", "English": "en"}
    language_code = lang_map.get(language, language)
    if language_code not in _LOCALE_CACHE:
        path = Path(__file__).resolve().parent.parent / "locales" / f"{language_code}.yml"
        if not path.exists():
            # fallback to English if not found
            path = Path(__file__).resolve().parent.parent / "locales" / "en.yml"
        with path.open("r", encoding="utf-8") as f:
            _LOCALE_CACHE[language_code] = yaml.safe_load(f)
    return _LOCALE_CACHE[language_code]


def get_translation(key, language="en", **kwargs):
    data = load_locale(language)
    for part in key.split("."):
        if isinstance(data, dict):
            data = data.get(part, None)
        else:
            data = None
        if data is None:
            return key  # fallback to key if not found
    if isinstance(data, str):
        return data.format(**kwargs)
    return key


def get_resource_path(filename: str) -> str:
    from utils.app_paths import get_bundle_resource_path

    return str(get_bundle_resource_path(filename))
