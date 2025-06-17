from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QDialog,
    QLineEdit,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import database


class StartupView(QWidget):
    """
    The startup view for project selection and creation.
    """

    def __init__(self, show_workspace_callback):
        super().__init__()

        self.show_workspace_callback = show_workspace_callback
        self.project_map = {}

        # --- Layouts ---
        # Main vertical layout for the whole widget
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Horizontal layout for the buttons
        button_layout = QHBoxLayout()

        # --- Widgets ---
        title_label = QLabel("NodeFlow")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Select a project to begin")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.project_list_widget = QListWidget()
        self.project_list_widget.setMaximumWidth(500)  # Constrain the width
        self.project_list_widget.itemDoubleClicked.connect(self.open_selected_project)

        open_button = QPushButton("Open Selected Project")
        open_button.clicked.connect(self.open_selected_project)

        new_button = QPushButton("Create New Project")
        new_button.clicked.connect(self.open_new_project_dialog)

        # --- Assemble Layout ---
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(self.project_list_widget)

        # Add buttons to the button layout
        button_layout.addWidget(open_button)
        button_layout.addWidget(new_button)

        # Add the button layout to the main layout
        main_layout.addLayout(button_layout)

        # --- Load Initial Data ---
        self.load_projects()

    def load_projects(self):
        """Fetches projects from the database and populates the list widget."""
        self.project_list_widget.clear()
        projects = database.get_all_projects()
        self.project_map = {p["name"]: (p["id"], p["name"]) for p in projects}
        for name in sorted(self.project_map.keys()):
            self.project_list_widget.addItem(name)

    def open_selected_project(self):
        """Gets the selected project and tells the main app to switch views."""
        selected_items = self.project_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Project Selected",
                "Please select a project from the list to open.",
            )
            return

        selected_name = selected_items[0].text()
        project_id, project_name = self.project_map[selected_name]

        # This calls the function passed in from main.py to switch the view
        self.show_workspace_callback(project_id, project_name)

    def open_new_project_dialog(self):
        """Opens a dialog to create a new project."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Project")

        dialog_layout = QVBoxLayout(dialog)

        label = QLabel("Enter new project name:")
        name_input = QLineEdit()

        # Standard OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        dialog_layout.addWidget(label)
        dialog_layout.addWidget(name_input)
        dialog_layout.addWidget(button_box)

        # If the user clicks OK, process the input
        if dialog.exec() == QDialog.DialogCode.Accepted:
            project_name = name_input.text().strip()
            if project_name:
                database.add_project(project_name)
                self.load_projects()  # Refresh the list
            else:
                QMessageBox.critical(self, "Error", "Project name cannot be empty.")
