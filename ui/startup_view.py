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
    QProgressDialog,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QKeyEvent, QColor
from qt_material_icons import MaterialIcon
from PySide6.QtWidgets import QApplication

import database
from services.desktop_shortcut_service import desktop_shortcut_service
from utils.common import get_resource_path, get_translation
from ui.workspace.workspace_main_window import WorkspaceMainWindow
from managers.theme_manager import load_settings, get_effective_theme_mode


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
        self.language = load_settings().get("language", "English")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 10)
        self.name_label = QLabel(project_name)
        font = self.name_label.font()
        font.setPointSize(12)
        self.name_label.setFont(font)
        self.menu_button = QPushButton()
        self.menu_icon = MaterialIcon("more_vert")
        self.menu_button.setIcon(self.menu_icon)
        self.menu_button.setFixedSize(24, 24)
        self.menu_button.setToolTip(
            get_translation("startup.project_actions", self.language)
        )
        self.menu_button.clicked.connect(self.show_actions_menu)
        self.menu_button.setVisible(False)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.menu_button)
        self.set_selected_style(False)

    def set_icons_visible(self, visible):
        self.menu_button.setVisible(visible)

    def set_selected_style(self, is_selected: bool):
        is_dark = get_effective_theme_mode() == "Dark"
        selected_fg = "#f0f0f0" if is_dark else "#000000"
        normal_fg = "#f0f0f0" if is_dark else "#333333"
        if is_selected:
            self.name_label.setStyleSheet(f"color: {selected_fg};")
            self.menu_button.setStyleSheet(f"color: {selected_fg};")
            self.menu_icon.set_color(QColor(selected_fg))
        else:
            self.name_label.setStyleSheet(f"color: {normal_fg};")
            self.menu_button.setStyleSheet(f"color: {normal_fg};")
            self.menu_icon.set_color(QColor(normal_fg))
        self.menu_button.setIcon(self.menu_icon)

    def show_actions_menu(self):
        menu = QMenu(self.parent_view)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        menu.setWindowOpacity(1.0)
        rename_action = menu.addAction(
            get_translation("startup.rename_project", self.language)
        )
        delete_action = menu.addAction(
            get_translation("startup.delete_project", self.language)
        )
        action = menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
        if action == rename_action:
            self.on_rename_clicked()
        elif action == delete_action:
            self.on_delete_clicked()

    def on_rename_clicked(self):
        self.parent_view.rename_project(self.project_id, self.project_name)

    def on_delete_clicked(self):
        self.parent_view.delete_project(self.project_id, self.project_name)


class StartupView(QWidget):
    def __init__(self):
        super().__init__()
        self.language = load_settings().get("language", "English")
        self._current_selected_widget = None
        self.workspace_window = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout = QHBoxLayout()

        icon_label = QLabel()
        pixmap = QPixmap(get_resource_path("icon.png"))
        icon_label.setPixmap(
            pixmap.scaledToWidth(64, Qt.TransformationMode.SmoothTransformation)
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(get_translation("startup.nodeflow_title", self.language))
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline_label = QLabel(get_translation("startup.tagline", self.language))
        tagline_font = QFont()
        tagline_font.setPointSize(10)
        tagline_font.setItalic(True)
        tagline_label.setFont(tagline_font)
        tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline_label.setStyleSheet("color: #555;")

        self.subtitle_label = QLabel(get_translation("startup.subtitle", self.language))
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.project_list_widget = QListWidget()
        self.project_list_widget = ProjectListWidget(self)
        self.project_list_widget.setMaximumWidth(500)
        self.project_list_widget.itemDoubleClicked.connect(self.open_selected_project)
        self.project_list_widget.currentItemChanged.connect(self.on_selection_changed)

        self.open_button = QPushButton(
            get_translation("startup.open_selected", self.language)
        )
        self.open_button.clicked.connect(self.open_selected_project)
        self.new_button = QPushButton(
            get_translation("startup.create_new", self.language)
        )
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
        QTimer.singleShot(0, self.maybe_prompt_desktop_shortcut)

    def on_selection_changed(self, current_item, previous_item):
        if previous_item:
            widget = self.project_list_widget.itemWidget(previous_item)
            if widget:
                widget.set_icons_visible(False)
                widget.set_selected_style(False)

        if current_item:
            widget = self.project_list_widget.itemWidget(current_item)
            if widget:
                widget.set_icons_visible(True)
                widget.set_selected_style(True)

    def load_projects(self):
        self.project_list_widget.currentItemChanged.disconnect(
            self.on_selection_changed
        )
        self.project_list_widget.clear()
        projects = database.get_all_projects()

        if not projects:
            # If no projects exist, hide the list and "Open" button for a clean UI
            self.subtitle_label.setText(
                get_translation("startup.create_new_project_to_begin", self.language)
            )
            self.project_list_widget.setVisible(False)
            self.open_button.setVisible(False)
        else:
            # If projects exist, ensure the UI elements are visible
            self.subtitle_label.setText(
                get_translation(
                    "startup.select_a_project_to_open_or_create_a_new_one",
                    self.language,
                )
            )
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
            return
        selected_item = self.project_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(
                self,
                get_translation("startup.no_project_selected", self.language),
                get_translation("startup.no_project_selected_message", self.language),
            )
            return

        widget = self.project_list_widget.itemWidget(selected_item)
        if isinstance(widget, ProjectItemWidget):
            loading = QProgressDialog(
                get_translation("startup.loading_workspace", self.language),
                None,
                0,
                0,
                self,
            )
            loading.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.Tool)
            loading.setCancelButton(None)
            loading.setStyleSheet(
                "QProgressDialog { border: 3px solid #0078d7; border-radius: 10px; }"
            )
            loading.show()
            center_on_screen(loading)
            QApplication.processEvents()
            self.workspace_window = WorkspaceMainWindow(
                widget.project_id, widget.project_name, self
            )
            loading.close()
            self.window().hide()
            self.workspace_window.show()

    def maybe_prompt_desktop_shortcut(self):
        settings = load_settings()
        if not desktop_shortcut_service.should_prompt(settings):
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(
            get_translation("startup.desktop_shortcut_title", self.language)
        )
        dialog.setText(
            get_translation("startup.desktop_shortcut_message", self.language)
        )
        create_button = dialog.addButton(
            get_translation("startup.desktop_shortcut_create", self.language),
            QMessageBox.ButtonRole.AcceptRole,
        )
        later_button = dialog.addButton(
            get_translation("startup.desktop_shortcut_later", self.language),
            QMessageBox.ButtonRole.RejectRole,
        )
        never_button = dialog.addButton(
            get_translation("startup.desktop_shortcut_never", self.language),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == create_button:
            self.create_desktop_shortcut()
        elif clicked == later_button:
            desktop_shortcut_service.mark_deferred()
        elif clicked == never_button:
            desktop_shortcut_service.mark_never()

    def create_desktop_shortcut(self):
        try:
            shortcut_path = desktop_shortcut_service.create_shortcut()
            desktop_shortcut_service.mark_created()
            QMessageBox.information(
                self,
                get_translation("startup.desktop_shortcut_created_title", self.language),
                get_translation(
                    "startup.desktop_shortcut_created_message",
                    self.language,
                    path=str(shortcut_path),
                ),
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                get_translation("startup.desktop_shortcut_error_title", self.language),
                get_translation(
                    "startup.desktop_shortcut_error_message",
                    self.language,
                    error=str(error),
                ),
            )

    def rename_project(self, project_id, current_name):
        new_name, ok = QInputDialog.getText(
            self,
            get_translation("startup.rename_project", self.language),
            get_translation("startup.enter_new_project_name", self.language),
            text=current_name,
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            try:
                database.rename_project(project_id, new_name.strip())
                self.load_projects()
            except database.sqlite3.IntegrityError:
                QMessageBox.critical(
                    self,
                    get_translation("startup.error", self.language),
                    get_translation(
                        "startup.project_exists", self.language, name=new_name.strip()
                    ),
                )

    def delete_project(self, project_id, project_name):
        confirm_text, ok = QInputDialog.getText(
            self,
            get_translation("startup.confirm_delete", self.language),
            get_translation(
                "startup.confirm_delete_message", self.language, name=project_name
            )
            + f"\n\nType the project name '{project_name}' to confirm:",
        )

        if ok:
            if confirm_text.strip() == project_name:
                database.delete_project(project_id)
                self.load_projects()
            else:
                QMessageBox.warning(
                    self,
                    get_translation("startup.error", self.language),
                    "The project name you entered was incorrect. Deletion has been cancelled.",
                )

    def open_new_project_dialog(self):
        project_name, ok = QInputDialog.getText(
            self,
            get_translation("startup.create_new_project", self.language),
            get_translation("startup.create_new_project_prompt", self.language),
        )
        if ok and project_name.strip():
            try:
                database.add_project(project_name.strip())
                self.load_projects()
            except database.sqlite3.IntegrityError:
                QMessageBox.critical(
                    self,
                    get_translation("startup.error", self.language),
                    get_translation(
                        "startup.project_exists",
                        self.language,
                        name=project_name.strip(),
                    ),
                )
        elif ok:
            QMessageBox.critical(
                self,
                get_translation("startup.error", self.language),
                get_translation("startup.project_name_empty", self.language),
            )


def center_on_screen(window):
    screen = (
        window.screen()
        if hasattr(window, "screen") and window.screen()
        else QApplication.primaryScreen()
    )
    center_point = screen.availableGeometry().center()
    frame_geometry = window.frameGeometry()
    frame_geometry.moveCenter(center_point)
    window.move(frame_geometry.topLeft())
