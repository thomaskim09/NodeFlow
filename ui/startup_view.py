from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QKeyEvent
from qt_material_icons import MaterialIcon

import database
from utils.common import get_resource_path


class ProjectListWidget(QListWidget):
    """A QListWidget that handles F2 for rename and Delete for delete."""

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    def keyPressEvent(self, event: QKeyEvent):
        """Handles keyboard shortcuts for project actions."""
        current_item = self.currentItem()
        if not current_item:
            super().keyPressEvent(event)
            return

        item_widget = self.itemWidget(current_item)
        if not item_widget:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_F2:
            if hasattr(item_widget, "on_rename_clicked"):
                item_widget.on_rename_clicked()
            event.accept()

        elif event.key() == Qt.Key.Key_Delete:
            if hasattr(item_widget, "on_delete_clicked"):
                item_widget.on_delete_clicked()
            event.accept()

        else:
            super().keyPressEvent(event)


class ProjectItemWidget(QWidget):
    def __init__(self, project_id, project_name, parent_view):
        super().__init__()
        self.project_id = project_id
        self.project_name = project_name
        self.parent_view = parent_view

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 10)

        name_label = QLabel(project_name)
        font = name_label.font()
        font.setPointSize(12)
        name_label.setFont(font)

        # Edit button with pencil icon
        self.edit_button = QPushButton()
        pencil_icon = MaterialIcon("edit")
        self.edit_button.setIcon(pencil_icon)
        font = self.edit_button.font()
        font.setPointSize(12)
        self.edit_button.setFont(font)
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Rename Project (F2)")
        self.edit_button.clicked.connect(self.on_rename_clicked)
        self.edit_button.setVisible(False)

        # Delete button with trash icon
        self.delete_button = QPushButton()
        trash_icon = MaterialIcon("delete")
        self.delete_button.setIcon(trash_icon)
        font = self.delete_button.font()
        font.setPointSize(12)
        self.delete_button.setFont(font)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete Project (Delete)")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setVisible(False)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_icons_visible(self, visible):
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

    def on_rename_clicked(self):
        self.parent_view.rename_project(self.project_id, self.project_name)

    def on_delete_clicked(self):
        self.parent_view.delete_project(self.project_id, self.project_name)


class StartupView(QWidget):
    def __init__(self, show_workspace_callback):
        super().__init__()
        self.show_workspace_callback = show_workspace_callback
        self._current_selected_widget = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout = QHBoxLayout()

        icon_label = QLabel()
        pixmap = QPixmap(get_resource_path("icon.png"))
        icon_label.setPixmap(
            pixmap.scaledToWidth(64, Qt.TransformationMode.SmoothTransformation)
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel("NodeFlow")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline_label = QLabel("Your compass for qualitative data.")
        tagline_font = QFont()
        tagline_font.setPointSize(10)
        tagline_font.setItalic(True)
        tagline_label.setFont(tagline_font)
        tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline_label.setStyleSheet("color: #555;")

        self.subtitle_label = QLabel("Select a project to open or create a new one.")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.project_list_widget = QListWidget()
        self.project_list_widget = ProjectListWidget(self)
        self.project_list_widget.setMaximumWidth(500)
        self.project_list_widget.itemDoubleClicked.connect(self.open_selected_project)
        self.project_list_widget.currentItemChanged.connect(self.on_selection_changed)

        self.open_button = QPushButton("Open Selected Project")
        self.open_button.clicked.connect(self.open_selected_project)
        self.new_button = QPushButton("Create New Project")
        self.new_button.clicked.connect(self.open_new_project_dialog)

        main_layout.addWidget(icon_label)
        main_layout.addWidget(title_label)
        main_layout.addWidget(tagline_label)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.subtitle_label)
        main_layout.addWidget(self.project_list_widget)
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.new_button)
        main_layout.addLayout(button_layout)
        self.load_projects()

    def on_selection_changed(self, current_item, previous_item):
        if previous_item:
            widget = self.project_list_widget.itemWidget(previous_item)
            if widget:
                widget.set_icons_visible(False)

        if current_item:
            widget = self.project_list_widget.itemWidget(current_item)
            if widget:
                widget.set_icons_visible(True)

    def load_projects(self):
        self.project_list_widget.currentItemChanged.disconnect(
            self.on_selection_changed
        )
        self.project_list_widget.clear()
        projects = database.get_all_projects()

        if not projects:
            # If no projects exist, hide the list and "Open" button for a clean UI
            self.subtitle_label.setText("Create a new project to begin.")
            self.project_list_widget.setVisible(False)
            self.open_button.setVisible(False)
        else:
            # If projects exist, ensure the UI elements are visible
            self.subtitle_label.setText("Select a project to open or create a new one.")
            self.project_list_widget.setVisible(True)
            self.open_button.setVisible(True)
            for project in sorted(projects, key=lambda p: p["name"]):
                list_item = QListWidgetItem(self.project_list_widget)
                item_widget = ProjectItemWidget(project["id"], project["name"], self)
                list_item.setSizeHint(item_widget.sizeHint())
                self.project_list_widget.addItem(list_item)
                self.project_list_widget.setItemWidget(list_item, item_widget)

        self.project_list_widget.currentItemChanged.connect(self.on_selection_changed)

    def open_selected_project(self, item=None):
        if not self.open_button.isVisible():
            return  # Don't do anything if the button is hidden
        selected_item = self.project_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(
                self,
                "No Project Selected",
                "Please select a project from the list to open.",
            )
            return

        widget = self.project_list_widget.itemWidget(selected_item)
        if isinstance(widget, ProjectItemWidget):
            self.show_workspace_callback(widget.project_id, widget.project_name)

    def rename_project(self, project_id, current_name):
        new_name, ok = QInputDialog.getText(
            self, "Rename Project", "Enter new project name:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            try:
                database.rename_project(project_id, new_name.strip())
                self.load_projects()
            except database.sqlite3.IntegrityError:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"A project named '{new_name.strip()}' already exists.",
                )

    def delete_project(self, project_id, project_name):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the project '{project_name}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_project(project_id)
            self.load_projects()

    def open_new_project_dialog(self):
        project_name, ok = QInputDialog.getText(
            self, "Create New Project", "Enter new project name:"
        )
        if ok and project_name.strip():
            try:
                database.add_project(project_name.strip())
                self.load_projects()
            except database.sqlite3.IntegrityError:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"A project named '{project_name.strip()}' already exists.",
                )
        elif ok:
            QMessageBox.critical(self, "Error", "Project name cannot be empty.")
