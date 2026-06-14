from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QFrame,
    QMenu,
    QPushButton,
    QApplication,
    QToolBar,
    QDialog,
    QFormLayout,
    QLabel,
    QDialogButtonBox,
    QSpinBox,
    QCheckBox,
    QColorDialog,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QShortcut

from ui.combo_box import FitPopupComboBox
from .participant_manager import ParticipantManager
from .node_tree_manager import NodeTreeManager
from .content_view import ContentView
from .coded_segments_view import CodedSegmentsView
from ui.dashboard.dashboard_view import DashboardView

from managers.export_manager import export_to_word, export_to_json, export_to_excel
from managers.theme_manager import save_settings, load_settings, apply_theme
import database
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from repositories.workspace_snapshot_repository import workspace_snapshot_repository
from services.workspace_history_service import WorkspaceCommand, WorkspaceHistory


class SettingsDialog(QDialog):
    theme_changed = Signal()
    settings_applied = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.language = self.settings.get("language", "English")
        self.setWindowTitle(get_translation("workspace.settings", self.language))
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.theme_combo = FitPopupComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        saved_theme = self.settings.get("theme", "Light")
        if saved_theme not in ("Light", "Dark"):
            saved_theme = "Light"
        self.theme_combo.setCurrentText(saved_theme)
        self.theme_combo.setMinimumContentsLength(12)
        self.theme_combo.setMinimumWidth(180)
        form_layout.addRow(
            QLabel(get_translation("workspace.application_theme", self.language)),
            self.theme_combo,
        )
        # Language selection
        self.language_combo = FitPopupComboBox()
        self.language_combo.addItems(["English", "Chinese"])
        self.language_combo.setCurrentText(self.settings.get("language", "English"))
        self.language_combo.setMinimumContentsLength(12)
        self.language_combo.setMinimumWidth(180)
        form_layout.addRow(
            QLabel(get_translation("workspace.language", self.language)),
            self.language_combo,
        )
        self.undo_depth_spin = QSpinBox()
        self.undo_depth_spin.setRange(20, 500)
        self.undo_depth_spin.setValue(int(self.settings.get("undo_depth", 100)))
        self.undo_depth_spin.setSingleStep(10)
        form_layout.addRow(
            QLabel(get_translation("workspace.undo_depth", self.language)),
            self.undo_depth_spin,
        )
        self.autosave_checkbox = QCheckBox(
            get_translation("workspace.autosave_enabled", self.language)
        )
        self.autosave_checkbox.setChecked(
            bool(self.settings.get("autosave_enabled", True))
        )
        form_layout.addRow("", self.autosave_checkbox)
        self.autosave_delay_spin = QSpinBox()
        self.autosave_delay_spin.setRange(500, 10000)
        self.autosave_delay_spin.setValue(
            int(self.settings.get("autosave_delay_ms", 1500))
        )
        self.autosave_delay_spin.setSingleStep(250)
        form_layout.addRow(
            QLabel(get_translation("workspace.autosave_delay", self.language)),
            self.autosave_delay_spin,
        )
        self.find_match_color = self.settings.get("find_match_color", "#FFF59D")
        self.find_match_color_button = QPushButton()
        self.find_match_color_button.setFixedWidth(72)
        self.find_match_color_button.clicked.connect(self.choose_find_match_color)
        self._update_find_match_color_button()
        form_layout.addRow(
            QLabel(get_translation("workspace.find_match_color", self.language)),
            self.find_match_color_button,
        )
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_and_apply)
        button_box.rejected.connect(self.reject)
        # Set translated button text
        button_box.button(QDialogButtonBox.StandardButton.Save).setText(
            get_translation("workspace.save", self.language)
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            get_translation("workspace.cancel", self.language)
        )
        layout.addWidget(button_box)

    def save_and_apply(self):
        self.settings["theme"] = self.theme_combo.currentText()
        self.settings["language"] = self.language_combo.currentText()
        self.settings["undo_depth"] = self.undo_depth_spin.value()
        self.settings["autosave_enabled"] = self.autosave_checkbox.isChecked()
        self.settings["autosave_delay_ms"] = self.autosave_delay_spin.value()
        self.settings["find_match_color"] = self.find_match_color
        save_settings(self.settings)
        app = QApplication.instance()
        if app:
            apply_theme(app)
        self.settings_applied.emit(
            self.settings["theme"],
            self.settings["language"],
        )
        self.accept()

    def choose_find_match_color(self):
        color = QColorDialog.getColor(QColor(self.find_match_color), self)
        if not color.isValid():
            return
        self.find_match_color = color.name().upper()
        self._update_find_match_color_button()

    def _update_find_match_color_button(self):
        self.find_match_color_button.setText(self.find_match_color)
        self.find_match_color_button.setStyleSheet(
            f"background-color: {self.find_match_color}; color: #000000;"
        )


class WorkspaceView(QWidget):
    def __init__(self, project_id, project_name, back_to_startup_callback):
        super().__init__()
        self.language = load_settings().get("language", "English")
        self.project_id = project_id
        self.project_name = project_name
        self.back_to_startup_callback = back_to_startup_callback
        self._last_added_doc_id = None
        self._in_edit_mode = False
        self._open_dashboards = []
        self.history = WorkspaceHistory(int(load_settings().get("undo_depth", 100)))
        self.history.add_changed_callback(self.update_undo_redo_actions)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.toolbar = QToolBar(get_translation("toolbar.projects", self.language))
        self.toolbar.setMovable(False)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setStyleSheet(
            "QToolBar { padding: 1px 4px; spacing: 2px; }"
            " QToolBar::separator { width: 1px; margin: 4px 6px; }"
            " QToolButton { font-size: 12px; font-weight: 600; padding: 3px 8px; margin: 0px; }"
        )
        self.back_action = QAction(get_translation("toolbar.projects", self.language), self)
        self.back_action.triggered.connect(self.back_to_startup_callback)
        self.dashboard_action = QAction(
            get_translation("toolbar.dashboard", self.language), self
        )
        self.dashboard_action.triggered.connect(self.open_dashboard)
        self.settings_action = QAction(
            get_translation("toolbar.settings", self.language), self
        )
        self.settings_action.triggered.connect(self.open_settings)
        self.undo_icon = MaterialIcon("undo")
        self.undo_action = QAction(
            self.undo_icon, get_translation("toolbar.undo", self.language), self
        )
        self.undo_action.setToolTip(get_translation("toolbar.undo_tooltip", self.language))
        self.undo_action.triggered.connect(self.undo_workspace_action)
        self.redo_icon = MaterialIcon("redo")
        self.redo_action = QAction(
            self.redo_icon, get_translation("toolbar.redo", self.language), self
        )
        self.redo_action.setToolTip(get_translation("toolbar.redo_tooltip", self.language))
        self.redo_action.triggered.connect(self.redo_workspace_action)
        self.toolbar.addAction(self.back_action)
        self.toolbar.addAction(self.undo_action)
        self.toolbar.addAction(self.redo_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.dashboard_action)
        self.toolbar.addAction(self.settings_action)
        main_layout.addWidget(self.toolbar)
        self.left_pane = QFrame()
        self.left_pane_layout = QVBoxLayout(self.left_pane)
        self.center_pane = ContentView(self.project_id, self.language)
        self.bottom_pane = CodedSegmentsView(self.project_id, self.language)
        self.participant_manager = ParticipantManager(self.project_id, self.language)
        self.node_tree_manager = NodeTreeManager(self.project_id, self.language)
        self.center_pane.set_undo_executor(self.execute_workspace_command)
        self.center_pane.set_applied_command_recorder(self.record_applied_command)
        self.bottom_pane.set_undo_executor(self.execute_workspace_command)
        self.participant_manager.set_undo_executor(self.execute_workspace_command)
        self.node_tree_manager.set_undo_executor(self.execute_workspace_command)
        self.left_pane_layout.addWidget(self.participant_manager)
        self.left_pane_layout.addWidget(self.node_tree_manager)
        self.export_all_icon = MaterialIcon("download")
        self.export_button = QPushButton()
        self.export_button.setIcon(self.export_all_icon)
        self.export_button.setText(
            get_translation("export.export_all_coded_data", self.language)
        )
        self.export_button.setToolTip(
            get_translation("export.export_all_coded_data_tooltip", self.language)
        )
        export_menu = QMenu(self)
        self.action_export_json = export_menu.addAction(
            get_translation("export.export_json", self.language)
        )
        self.action_export_word = export_menu.addAction(
            get_translation("export.export_word", self.language)
        )
        self.action_export_excel = export_menu.addAction(
            get_translation("export.excel", self.language)
        )
        self.export_button.setMenu(export_menu)
        self.left_pane_layout.addStretch()
        self.left_pane_layout.addWidget(self.export_button)
        self.left_pane_layout.setStretchFactor(self.participant_manager, 2)
        self.left_pane_layout.setStretchFactor(self.node_tree_manager, 5)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.center_pane)
        right_splitter.addWidget(self.bottom_pane)
        right_splitter.setSizes([400, 400])
        main_splitter.addWidget(self.left_pane)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([350, 700])
        main_layout.addWidget(main_splitter)

        # --- SIGNAL CONNECTIONS ---
        self.center_pane.doc_selector.currentIndexChanged.connect(
            self.on_document_changed
        )
        self.center_pane.document_added.connect(self.on_document_added)
        self.center_pane.document_deleted.connect(self.on_document_deleted)
        self.center_pane.bulk_documents_added.connect(self.on_document_deleted)
        self.center_pane.segment_clicked.connect(
            self.bottom_pane.highlight_segment_by_id
        )
        self.center_pane.node_clicked_in_content.connect(
            self.node_tree_manager.highlight_node_by_id
        )
        self.bottom_pane.segment_deleted.connect(self.on_segment_deleted)
        self.bottom_pane.segment_activated.connect(self.on_segment_navigation_requested)
        self.bottom_pane.segment_edit_requested.connect(
            self.center_pane.start_segment_edit_mode
        )
        self.action_export_json.triggered.connect(self.export_as_json)
        self.action_export_word.triggered.connect(self.export_as_word)
        self.action_export_excel.triggered.connect(
            self.node_tree_manager.show_excel_export_options
        )
        self.node_tree_manager.filter_by_node_family_signal.connect(
            self.bottom_pane.filter_by_node_family
        )
        self.node_tree_manager.filter_by_single_node_signal.connect(
            self.bottom_pane.filter_by_single_node
        )
        self.participant_manager.participant_selected.connect(
            self.bottom_pane.filter_segments_by_participant
        )
        self.center_pane.segments_changed.connect(self.on_segments_changed)
        self.participant_manager.participant_updated.connect(self.refresh_all_views)
        self.node_tree_manager.node_updated.connect(self.on_node_data_updated)
        self.center_pane.text_selection_changed.connect(
            self.handle_text_selection_changed
        )
        self.center_pane.undo_requested.connect(self.undo_workspace_action)
        self.center_pane.redo_requested.connect(self.redo_workspace_action)
        self.node_tree_manager.node_selected_for_coding.connect(self.code_selection)
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.handle_undo_shortcut)
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self.redo_workspace_action)

        # Disable node tree selection mode during segment edit mode
        self.center_pane.edit_mode_changed.connect(self.handle_edit_mode_changed)

        # Allow external highlight of participant in listview
        self.center_pane.participant_highlight_requested.connect(
            self.participant_manager.highlight_participant_by_id
        )

        # Initial Load
        self.center_pane.load_document_content()
        self._apply_theme_icons(load_settings().get("theme", "Light"))
        self.on_document_changed()
        # Ensure coded segments view is refreshed on first open
        if hasattr(self.center_pane, "current_document_id"):
            self.bottom_pane.load_segments(self.center_pane.current_document_id)
        self.update_undo_redo_actions()

    def execute_workspace_command(self, command: WorkspaceCommand):
        self.history.execute(command)

    def record_applied_command(self, command: WorkspaceCommand):
        self.history.record_applied(command)

    def handle_undo_shortcut(self):
        if self._should_use_text_edit_undo():
            self.center_pane.text_edit.undo()
            return
        self.undo_workspace_action()

    def undo_workspace_action(self):
        if self._should_use_text_edit_undo():
            self.center_pane.text_edit.undo()
            return
        self.history.undo()

    def redo_workspace_action(self):
        if self._should_use_text_edit_redo():
            self.center_pane.text_edit.redo()
            return
        self.history.redo()

    def _should_use_text_edit_undo(self):
        return self.center_pane.text_edit.document().isUndoAvailable()

    def _should_use_text_edit_redo(self):
        return self.center_pane.text_edit.document().isRedoAvailable()

    def update_undo_redo_actions(self):
        undo_label = self.history.next_undo_label()
        redo_label = self.history.next_redo_label()
        self.undo_action.setEnabled(self.history.can_undo())
        self.redo_action.setEnabled(self.history.can_redo())
        self.center_pane.undo_button.setEnabled(
            self.center_pane.text_edit.document().isUndoAvailable()
            or self.history.can_undo()
        )
        self.center_pane.redo_button.setEnabled(
            self.center_pane.text_edit.document().isRedoAvailable()
            or self.history.can_redo()
        )
        self.undo_action.setToolTip(
            get_translation(
                "toolbar.undo_named_tooltip" if undo_label else "toolbar.undo_tooltip",
                self.language,
                action=undo_label or "",
            )
        )
        self.redo_action.setToolTip(
            get_translation(
                "toolbar.redo_named_tooltip" if redo_label else "toolbar.redo_tooltip",
                self.language,
                action=redo_label or "",
            )
        )

    def on_segment_navigation_requested(self, document_id, start, end):
        """Receives signal from CodedSegmentsView and commands ContentView."""
        self.center_pane.go_to_segment(document_id, start, end)

    def open_dashboard(self):
        current_doc_id = self.center_pane.current_document_id
        dialog = DashboardView(
            self.project_id,
            self.project_name,
            current_doc_id,
            self,
            language=self.language,
        )
        self._open_dashboards.append(dialog)
        dialog.finished.connect(lambda _: self._remove_dashboard(dialog))
        dialog.exec()

    def _remove_dashboard(self, dialog):
        if dialog in self._open_dashboards:
            self._open_dashboards.remove(dialog)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.settings_applied.connect(self._apply_runtime_settings)
        dialog.exec()

    def _apply_runtime_settings(self, theme, language):
        self.language = language
        self.history.set_max_depth(int(load_settings().get("undo_depth", 100)))
        self.toolbar.setWindowTitle(get_translation("toolbar.projects", self.language))
        self.back_action.setText(get_translation("toolbar.projects", self.language))
        self.undo_action.setText(get_translation("toolbar.undo", self.language))
        self.redo_action.setText(get_translation("toolbar.redo", self.language))
        self.dashboard_action.setText(get_translation("toolbar.dashboard", self.language))
        self.settings_action.setText(get_translation("toolbar.settings", self.language))
        if hasattr(self.node_tree_manager, "update_language"):
            self.node_tree_manager.update_language(self.language)
        if hasattr(self.node_tree_manager, "update_theme"):
            self.node_tree_manager.update_theme(theme)
        if hasattr(self.participant_manager, "update_language"):
            self.participant_manager.update_language(self.language)
        if hasattr(self.participant_manager, "update_theme"):
            self.participant_manager.update_theme(theme)
        if hasattr(self.center_pane, "update_language"):
            self.center_pane.update_language(self.language)
        if hasattr(self.center_pane, "update_theme"):
            self.center_pane.update_theme(theme)
        if hasattr(self.center_pane, "apply_autosave_settings"):
            self.center_pane.apply_autosave_settings()
        self._apply_theme_icons(theme)
        if hasattr(self.bottom_pane, "update_language"):
            self.bottom_pane.update_language(self.language)
        if hasattr(self.bottom_pane, "update_theme"):
            self.bottom_pane.update_theme(theme)
        for dialog in list(self._open_dashboards):
            if hasattr(dialog, "update_language"):
                dialog.update_language(self.language)

    def _apply_theme_icons(self, theme):
        is_dark = theme == "Dark"
        fg = QColor("#f0f0f0" if is_dark else "#000000")
        disabled_fg = QColor("#a8a8a8" if is_dark else "#5e5e5e")
        self.undo_icon.set_color(fg, QIcon.Mode.Normal)
        self.undo_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.redo_icon.set_color(fg, QIcon.Mode.Normal)
        self.redo_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.export_all_icon.set_color(fg, QIcon.Mode.Normal)
        self.export_all_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.undo_action.setIcon(self.undo_icon)
        self.redo_action.setIcon(self.redo_icon)
        self.export_button.setIcon(self.export_all_icon)

    def on_segment_deleted(self):
        self.center_pane.apply_all_highlights()
        self.node_tree_manager.load_nodes()

    def on_node_data_updated(self):
        """Called when a node is changed. Refreshes text highlights and all views."""
        self.center_pane.apply_all_highlights()
        self.refresh_all_views()

    def on_document_added(self, new_doc_id):
        """Catches the new document's ID and triggers a refresh."""
        self._last_added_doc_id = new_doc_id
        self.refresh_all_views()

    def on_document_deleted(self):
        """Handles document deletion and triggers a refresh."""
        self._last_added_doc_id = None
        self.refresh_all_views()

    def refresh_all_views(self):
        """A single, reliable method to refresh the entire workspace."""
        self.participant_manager.load_participants()
        self.center_pane.load_document_list(doc_id_to_select=self._last_added_doc_id)
        new_doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(new_doc_id)
        self.node_tree_manager.load_nodes()
        self._last_added_doc_id = None

    def export_as_word(self):
        export_to_word(self.project_id, self)

    def export_as_json(self):
        export_to_json(self.project_id, self)

    def export_as_excel(self):
        export_to_excel(self.project_id, self)

    def on_document_changed(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc_id = self.center_pane.current_document_id
            self.bottom_pane.load_segments(doc_id)
            self.node_tree_manager.tree_widget.clearSelection()
            self.node_tree_manager.set_current_document_id(doc_id)
            self.participant_manager.set_current_document_id(doc_id)
            self.participant_manager.load_participants()

            participant_id = database.get_participant_for_document(doc_id)
            if participant_id:
                self.participant_manager.highlight_participant_by_id(participant_id)
            else:
                self.participant_manager.clear_selection()

        finally:
            QApplication.restoreOverrideCursor()

    def on_segments_changed(self):
        """
        Called when segments are added or deleted.
        Reloads all relevant views.
        """
        doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(doc_id)
        self.node_tree_manager.load_nodes()
        self.participant_manager.load_participants()

    def code_selection(self, node_id):
        text_edit = self.center_pane.text_edit
        cursor = text_edit.textCursor()
        if not cursor.hasSelection():
            return
        selection_end_pos = cursor.selectionEnd()
        scrollbar = text_edit.verticalScrollBar()
        original_scroll_value = scrollbar.value()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        text = cursor.selectedText()
        doc_id = self.center_pane.current_document_id
        participant_id = self.center_pane.current_participant_id
        if not doc_id:
            return
        if self.center_pane.is_dirty:
            if not self.center_pane.save_document(show_success_prompt=False):
                return
        segment_id = None
        segment_snapshot = None

        def refresh_after_coding():
            self.bottom_pane.reload_view()
            self.center_pane.apply_all_highlights()
            self.node_tree_manager.set_current_document_id(doc_id)
            self.node_tree_manager.load_nodes()
            self.participant_manager.load_participants()
            new_cursor = text_edit.textCursor()
            new_cursor.setPosition(selection_end_pos)
            text_edit.setTextCursor(new_cursor)
            scrollbar.setValue(original_scroll_value)
            text_edit.setFocus()

        def do():
            nonlocal segment_id, segment_snapshot
            if segment_snapshot:
                workspace_snapshot_repository.restore_segment(segment_snapshot)
            else:
                segment_id = database.add_coded_segment(
                    doc_id, node_id, participant_id, start, end, text
                )
                segment_snapshot = workspace_snapshot_repository.get_segment(segment_id)

        def undo():
            if segment_id:
                database.delete_coded_segment(segment_id)

        self.execute_workspace_command(
            WorkspaceCommand("Code Selection", do, undo, refresh_after_coding)
        )

    def handle_text_selection_changed(self, enabled):
        # Only allow selection mode if not in edit segment mode
        if not self._in_edit_mode:
            self.node_tree_manager.set_selection_mode(enabled)
        else:
            self.node_tree_manager.set_selection_mode(False)

    def handle_edit_mode_changed(self, in_edit_mode):
        self._in_edit_mode = in_edit_mode
        # Always disable selection mode when entering edit mode
        if in_edit_mode:
            self.node_tree_manager.set_selection_mode(False)


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
