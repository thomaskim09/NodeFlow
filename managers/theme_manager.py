# managers/theme_manager.py
import json
import os
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


# Define the data directory and the database file path
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "nodeflow.db")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


def get_system_theme():
    """
    Detects the system's theme preference (Light/Dark) by inspecting the QApplication's palette.
    This is a heuristic and may not be 100% accurate on all systems, but it's a common Qt approach.
    """
    app = QApplication.instance()
    if app:
        palette = app.palette()
        # Check the background color of the window
        window_color = palette.color(QPalette.ColorRole.Window)
        # If the perceived brightness is low, it's likely a dark theme
        brightness = (
            window_color.red() * 299
            + window_color.green() * 587
            + window_color.blue() * 114
        ) / 1000
        if brightness < 128:  # Arbitrary threshold for dark vs light
            return "Dark"
    return "Light"  # Default to Light if detection is ambiguous or fails


def get_dark_theme_stylesheet():
    """Returns the QSS for the dark theme."""
    return """
        QWidget {
            background-color: #2c2c2c; /* Slightly lighter dark background */
            color: #f0f0f0; /* Light text */
            border: none; /* Remove default borders from QWidget */
        }
        QMainWindow {
            background-color: #2c2c2c;
        }
        QMenuBar {
            background-color: #3a3a3a; /* Darker menu bar */
            color: #f0f0f0;
            border-bottom: 1px solid #505050; /* Subtle separator */
        }
        QMenuBar::item:selected {
            background-color: #555555;
        }
        QToolBar {
            background-color: #3a3a3a;
            color: #f0f0f0;
            border-bottom: 1px solid #505050;
            padding: 5px;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 5px;
            margin: 2px;
            color: #f0f0f0;
        }
        QToolButton:hover {
            background-color: #505050;
            border-radius: 3px;
        }
        QToolButton:pressed {
            background-color: #404040;
        }

        /* General QPushButton styling - remove explicit size overrides */
        QPushButton {
            background-color: #4a4a4a; /* Darker button background */
            border: 1px solid #606060; /* More defined border */
            padding: 4px 8px; /* Adjusted padding */
            border-radius: 4px; /* Slightly larger border-radius */
            color: #f0f0f0;
        }
        QPushButton:hover {
            background-color: #5a5a5a;
            border-color: #707070;
        }
        QPushButton:pressed {
            background-color: #3a3a3a;
            border-color: #505050;
        }

        /* Specifically target QDialogButtonBox buttons to allow them to be wider */
        QDialogButtonBox QPushButton {
            min-width: 80px; /* Standardize dialog buttons */
            padding: 6px 12px;
        }
        
        QLineEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox, QTableView {
            background-color: #363636; /* Darker input/list background */
            border: 1px solid #505050; /* Consistent border */
            selection-background-color: #2a6096; /* Less contrasting blue for selection */
            selection-color: #ffffff;
            padding: 3px; /* Add some padding inside inputs */
        }
        QComboBox::drop-down {
            border: none; /* Remove border from dropdown arrow */
            background-color: #363636;
        }
        /* Assuming you have a light arrow icon for dark theme */
        /* QComboBox::down-arrow { image: url(icons/down_arrow_light.png); } */
        
        QSplitter::handle {
            background-color: #505050;
            border: none;
        }
        QSplitter::handle:hover {
            background-color: #606060;
        }

        QHeaderView::section {
            background-color: #3a3a3a; /* Darker header background */
            color: #f0f0f0;
            border: 1px solid #505050;
            padding: 6px;
        }
        
        /* Ensure QLabel has no border and no padding/margins that might simulate a border */
        QLabel {
            border: none;
            color: #f0f0f0;
            padding: 0; /* Ensure no padding */
            margin: 0; /* Ensure no margin */
            background: transparent; /* Ensure no background that might show through a border */
        }
        /* Specific rules for QLabel inside QFrame, if they inherit borders */
        QFrame QLabel {
            border: none;
            padding: 0;
            margin: 0;
            background: transparent;
        }
        /* Specific rules for QLabel inside QWidget (general case), if they inherit borders */
        QWidget QLabel {
            border: none;
            padding: 0;
            margin: 0;
            background: transparent;
        }
        
        QFrame {
            border: 1px solid #505050; /* Consistent frame border */
            border-radius: 4px;
            background-color: #333333; /* Slightly different background for frames */
        }
        
        QMenu {
            background-color: #3a3a3a;
            border: 1px solid #505050;
            color: #f0f0f0;
        }
        QMenu::item:selected {
            background-color: #2a6096; /* Less contrasting blue for menu selection */
        }

        /* Specific style for the NodeItemWidget color button */
        NodeItemWidget #nodeColorButton { /* Target by objectName */
            width: 18px; /* Override to desired size */
            height: 18px; /* Override to desired size */
            min-width: 18px; /* Ensure fixed minimum */
            max-width: 18px; /* Ensure fixed maximum */
            min-height: 18px; /* Ensure fixed minimum */
            max-height: 18px; /* Ensure fixed maximum */
            padding: 0px; /* Remove any padding */
            border-radius: 2px; /* Maintain small radius */
            border: 1px solid #888; /* Keep the specific border for color button */
            background-color: transparent; /* Ensure transparent background */
        }

        /* Specific style for the CodedSegmentsView delete button */
        QPushButton#codedSegmentDeleteButton { /* Target by objectName */
            width: 20px;
            height: 20px;
            min-width: 20px;
            max-width: 20px;
            min-height: 20px;
            max-height: 20px;
            padding: 0px;
            border: none; /* Remove border from this button */
            background-color: transparent; /* Ensure background is transparent for icon */
        }
        /* Ensure hover/pressed states are applied to the delete button */
        QPushButton#codedSegmentDeleteButton:hover {
            background-color: #505050;
            border-radius: 2px; /* Add slight hover effect */
        }
        QPushButton#codedSegmentDeleteButton:pressed {
            background-color: #404040;
        }


        /* Specific styles for other smaller buttons within custom item widgets */
        ProjectItemWidget QPushButton, ParticipantItemWidget QPushButton, NodeItemWidget QPushButton {
            background-color: transparent;
            border: none; /* Remove border from these buttons */
            padding: 0px;
            margin: 0px;
            color: #f0f0f0;
            border-radius: 2px;
        }
        ProjectItemWidget QPushButton:hover, ParticipantItemWidget QPushButton:hover, NodeItemWidget QPushButton:hover {
            background-color: #505050;
        }
        ProjectItemWidget QPushButton:pressed, ParticipantItemWidget QPushButton:pressed, NodeItemWidget QPushButton:pressed {
            background-color: #404040;
        }

        /* Styles for QListWidget and QTreeWidget items */
        QListWidget::item {
            border: none;
            padding: 2px;
        }
        QListWidget::item:selected {
            background-color: #2a6096; /* Less contrasting blue for selected item */
            color: white;
            /* Removed border here as per request */
        }
        QTreeWidget::item {
            border: none;
            padding: 2px;
        }
        QTreeWidget::item:selected {
            background-color: #2a6096; /* Less contrasting blue for selected item */
            color: white;
            /* Removed border here as per request */
        }
        
        /* Ensure buttons AND their containers within selected list/tree items are transparent to show highlight */
        QListWidget::item QWidget, QTreeWidget::item QWidget { /* Target the button container */
            background-color: transparent;
        }
        QListWidget::item QPushButton, QTreeWidget::item QPushButton {
            background-color: transparent; /* Ensure button background is transparent */
        }
        /* Hover state for buttons within selected items */
        QListWidget::item:selected QPushButton:hover, QTreeWidget::item:selected QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.2); /* Slight white overlay on hover for selected buttons */
        }


        /* No border for the main container of stats labels in DashboardView */
        #statsContainer {
            border: none;
            background-color: #333333; /* Keep background as before */
        }

        /* Remove border from the info bar at the bottom of content view */
        /* Assuming 'info_bar' object name is set in ContentView */
        QFrame[objectName="info_bar"] {
            border: none;
            background-color: #3a3a3a;
        }

        /* Style for the drag-drop overlay in ContentView */
        #dropOverlay {
            background-color: rgba(60, 60, 60, 0.95); /* Semi-transparent dark */
            border: 2px dashed #888;
            border-radius: 10px;
            color: #f0f0f0;
        }

        /* General Tab Widget Styling */
        QTabWidget::pane { /* The tab widget frame */
            border: 1px solid #505050;
            background-color: #2c2c2c;
            border-radius: 4px;
        }
        QTabBar::tab {
            background: #3a3a3a; /* Tab background */
            color: #f0f0f0;
            border: 1px solid #505050;
            border-bottom-color: #3a3a3a; /* Same as pane color */
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #2c2c2c; /* Selected tab matches pane background */
            border-bottom-color: #2c2c2c; /* Remove border from selected tab bottom */
        }
        QTabBar::tab:hover {
            background: #4a4a4a;
        }

        /* Scrollbar styling for dark theme */
        QScrollBar:vertical, QScrollBar:horizontal {
            border: 1px solid #4a4a4a;
            background: #363636;
            width: 10px; /* vertical scrollbar width */
            height: 10px; /* horizontal scrollbar height */
            margin: 0px;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #606060;
            border: 1px solid #707070;
            border-radius: 4px;
            min-height: 20px;
            min-width: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """


def get_light_theme_stylesheet():
    """Returns the QSS for a custom light theme."""
    return """
        QWidget {
            background-color: #f0f0f0; /* Light grey background */
            color: #333333; /* Dark text */
            border: none;
        }
        QMainWindow {
            background-color: #f0f0f0;
        }
        QMenuBar {
            background-color: #e0e0e0; /* Slightly darker light menu bar */
            color: #333333;
            border-bottom: 1px solid #cccccc;
        }
        QMenuBar::item:selected {
            background-color: #d0d0d0;
        }
        QToolBar {
            background-color: #e0e0e0;
            color: #333333;
            border-bottom: 1px solid #cccccc;
            padding: 5px;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 5px;
            margin: 2px;
            color: #333333;
        }
        QToolButton:hover {
            background-color: #d0d0d0;
            border-radius: 3px;
        }
        QToolButton:pressed {
            background-color: #c0c0c0;
        }

        /* General QPushButton styling - remove explicit size overrides */
        QPushButton {
            background-color: #e8e8e8; /* Light button background */
            border: 1px solid #cccccc;
            padding: 4px 8px;
            border-radius: 4px;
            color: #333333;
        }
        QPushButton:hover {
            background-color: #d8d8d8;
            border-color: #bbbbbb;
        }
        QPushButton:pressed {
            background-color: #c8c8c8;
            border-color: #aaaaaa;
        }

        QDialogButtonBox QPushButton {
            min-width: 80px;
            padding: 6px 12px;
        }
        
        QLineEdit, QTextEdit, QListWidget, QTreeWidget, QComboBox, QTableView {
            background-color: #ffffff; /* White input/list background */
            border: 1px solid #cccccc;
            selection-background-color: #a6d5ff; /* Light blue for selection */
            selection-color: #000000;
            padding: 3px;
        }
        QComboBox::drop-down {
            border: none;
            background-color: #ffffff;
        }
        /* Assuming you have a dark arrow icon for light theme */
        /* QComboBox::down-arrow { image: url(icons/down_arrow_dark.png); } */
        
        QSplitter::handle {
            background-color: #cccccc;
            border: none;
        }
        QSplitter::handle:hover {
            background-color: #bbbbbb;
        }

        QHeaderView::section {
            background-color: #e0e0e0;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 6px;
        }
        
        QLabel {
            border: none;
            color: #333333;
            padding: 0;
            margin: 0;
            background: transparent;
        }
        QFrame QLabel {
            border: none;
            padding: 0;
            margin: 0;
            background: transparent;
        }
        QWidget QLabel {
            border: none;
            padding: 0;
            margin: 0;
            background: transparent;
        }
        
        QFrame {
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #ffffff; /* White background for frames */
        }
        
        QMenu {
            background-color: #e0e0e0;
            border: 1px solid #cccccc;
            color: #333333;
        }
        QMenu::item:selected {
            background-color: #a6d5ff; /* Light blue for menu selection */
        }

        NodeItemWidget #nodeColorButton {
            width: 18px;
            height: 18px;
            min-width: 18px;
            max-width: 18px;
            min-height: 18px;
            max-height: 18px;
            padding: 0px;
            border-radius: 2px;
            border: 1px solid #aaaaaa; /* Darker border for light theme */
            background-color: transparent;
        }

        QPushButton#codedSegmentDeleteButton {
            width: 20px;
            height: 20px;
            min-width: 20px;
            max-width: 20px;
            min-height: 20px;
            max-height: 20px;
            padding: 0px;
            border: none;
            background-color: transparent;
        }
        QPushButton#codedSegmentDeleteButton:hover {
            background-color: #d0d0d0;
            border-radius: 2px;
        }
        QPushButton#codedSegmentDeleteButton:pressed {
            background-color: #c0c0c0;
        }

        /* Specific styles for other smaller buttons within custom item widgets */
        ProjectItemWidget QPushButton, ParticipantItemWidget QPushButton, NodeItemWidget QPushButton {
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
            color: #333333; /* Dark icon color for light theme */
            border-radius: 2px;
        }
        ProjectItemWidget QPushButton:hover, ParticipantItemWidget QPushButton:hover, NodeItemWidget QPushButton:hover {
            background-color: #d0d0d0;
        }
        ProjectItemWidget QPushButton:pressed, ParticipantItemWidget QPushButton:pressed, NodeItemWidget QPushButton:pressed {
            background-color: #c0c0c0;
        }

        /* Styles for QListWidget and QTreeWidget items */
        QListWidget::item {
            border: none;
            padding: 2px;
        }
        QListWidget::item:selected {
            background-color: #a6d5ff;
            color: black;
            /* Removed border here as per request */
        }
        QTreeWidget::item {
            border: none;
            padding: 2px;
        }
        QTreeWidget::item:selected {
            background-color: #a6d5ff;
            color: black;
            /* Removed border here as per request */
        }

        /* Ensure buttons AND their containers within selected list/tree items are transparent to show highlight */
        QListWidget::item QWidget, QTreeWidget::item QWidget { /* Target the button container */
            background-color: transparent;
        }
        QListWidget::item QPushButton, QTreeWidget::item QPushButton {
            background-color: transparent; /* Ensure button background is transparent */
        }
        /* Hover state for buttons within selected items */
        QListWidget::item:selected QPushButton:hover, QTreeWidget::item:selected QPushButton:hover {
            background-color: rgba(0, 0, 0, 0.1); /* Slight black overlay on hover for selected buttons */
        }

        #statsContainer {
            border: none;
            background-color: #ffffff;
        }

        QFrame[objectName="info_bar"] {
            border: none;
            background-color: #e0e0e0;
        }

        #dropOverlay {
            background-color: rgba(240, 240, 240, 0.95); /* Semi-transparent light */
            border: 2px dashed #bbbbbb;
            border-radius: 10px;
            color: #333333;
        }

        QTabWidget::pane {
            border: 1px solid #cccccc;
            background-color: #f0f0f0;
            border-radius: 4px;
        }
        QTabBar::tab {
            background: #e0e0e0;
            color: #333333;
            border: 1px solid #cccccc;
            border-bottom-color: #e0e0e0;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #f0f0f0;
            border-bottom-color: #f0f0f0;
        }
        QTabBar::tab:hover {
            background: #d0d0d0;
        }

        QScrollBar:vertical, QScrollBar:horizontal {
            border: 1px solid #cccccc;
            background: #e0e0e0;
            width: 10px;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #aaaaaa;
            border: 1px solid #999999;
            border-radius: 4px;
            min-height: 20px;
            min-width: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """


def load_settings():
    """Loads settings from the JSON file."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"theme": "Default"}
    return {"theme": "Default"}


def save_settings(settings):
    """Saves settings to the JSON file."""
    # Ensure the data directory exists before saving
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def apply_theme(app):
    """Applies the saved theme to the application."""
    settings = load_settings()
    theme_setting = settings.get("theme", "Default")

    if theme_setting == "Dark":
        app.setStyleSheet(get_dark_theme_stylesheet())
    elif theme_setting == "Light":
        app.setStyleSheet(get_light_theme_stylesheet())
    elif theme_setting == "Default":
        app.setStyleSheet("")
