# Replace the contents of managers/theme_manager.py with this updated code.

import json
import os

# Define the data directory and the settings file path
DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


def get_dark_theme_stylesheet():
    """Returns the QSS for the dark theme."""
    return """
        QWidget {
            background-color: #2b2b2b;
            color: #f0f0f0;
            border: 1px solid #3c3c3c;
        }
        QMenuBar, QToolBar {
            background-color: #3c3c3c;
            border: none;
        }
        QPushButton, QDialogButtonBox > QPushButton {
            background-color: #555;
            border: 1px solid #666;
            padding: 5px;
            min-width: 50px;
            border-radius: 3px;
        }
        QPushButton:hover, QDialogButtonBox > QPushButton:hover {
            background-color: #666;
        }
        QPushButton:pressed, QDialogButtonBox > QPushButton:pressed {
            background-color: #444;
        }
        QLineEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            selection-background-color: #0078d7;
            selection-color: #ffffff;
        }
        QSplitter::handle {
            background-color: #555;
        }
        QHeaderView::section {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 4px;
        }
        QLabel {
            border: none;
        }
        QFrame {
            border: 1px solid #555;
        }
        QToolButton {
            background-color: transparent;
        }
        QMenu {
            background-color: #3c3c3c;
            border: 1px solid #555;
        }
        QMenu::item:selected {
            background-color: #0078d7;
        }
    """


def load_settings():
    """Loads settings from the JSON file."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"theme": "Light"}  # Default on corruption
    return {"theme": "Light"}


def save_settings(settings):
    """Saves settings to the JSON file."""
    # Ensure the data directory exists before saving
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def apply_theme(app):
    """Applies the saved theme to the application."""
    settings = load_settings()
    if settings.get("theme") == "Dark":
        app.setStyleSheet(get_dark_theme_stylesheet())
    else:  # Light Theme
        app.setStyleSheet("")  # Use default system style
