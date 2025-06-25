import os
import yaml

_LOCALE_CACHE = {}


def load_locale(language):
    # Map user-friendly names to locale codes
    lang_map = {"Chinese": "zh", "English": "en"}
    language_code = lang_map.get(language, language)
    if language_code not in _LOCALE_CACHE:
        path = os.path.join(
            os.path.dirname(__file__), "..", "locales", f"{language_code}.yml"
        )
        if not os.path.exists(path):
            # fallback to English if not found
            path = os.path.join(os.path.dirname(__file__), "..", "locales", "en.yml")
        with open(path, "r", encoding="utf-8") as f:
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
    os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    resource_folder_path = os.path.join(project_root, "resource")
    os.makedirs(resource_folder_path, exist_ok=True)
    full_path = os.path.join(resource_folder_path, filename)
    return full_path
