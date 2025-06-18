from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QFrame,
    QMenu,
    QPushButton,
    QApplication,
    QToolBar,
    QMessageBox,
    QDialog,
    QFormLayout,
    QComboBox,
    QLabel,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from .participant_manager import ParticipantManager
from .node_tree_manager import NodeTreeManager
from .content_view import ContentView
from .coded_segments_view import CodedSegmentsView
from ui.dashboard.dashboard_view import DashboardView

from managers.export_manager import export_to_word, export_to_json, export_to_excel
from managers.theme_manager import save_settings, load_settings
import database


class SettingsDialog(QDialog):
    theme_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(300)
        self.settings = load_settings()
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Light"))
        form_layout.addRow(QLabel("Application Theme:"), self.theme_combo)
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_and_apply)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def save_and_apply(self):
        self.settings["theme"] = self.theme_combo.currentText()
        save_settings(self.settings)
        QMessageBox.information(
            self,
            "Settings Saved",
            "The new theme will be applied when you restart the application.",
        )
        self.accept()


class WorkspaceView(QWidget):
    def __init__(self, project_id, project_name, back_to_startup_callback):
        super().__init__()
        self.project_id = project_id
        self.project_name = project_name
        self.back_to_startup_callback = back_to_startup_callback
        self._last_added_doc_id = None
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        back_action = QAction("Projects", self)
        back_action.triggered.connect(self.back_to_startup_callback)
        dashboard_action = QAction("Dashboard", self)
        dashboard_action.triggered.connect(self.open_dashboard)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(back_action)
        toolbar.addAction(dashboard_action)
        toolbar.addAction(settings_action)
        main_layout.addWidget(toolbar)
        self.left_pane = QFrame()
        self.left_pane_layout = QVBoxLayout(self.left_pane)
        self.center_pane = ContentView(self.project_id)
        self.bottom_pane = CodedSegmentsView(self.project_id)
        self.participant_manager = ParticipantManager(self.project_id)
        self.node_tree_manager = NodeTreeManager(self.project_id)
        self.left_pane_layout.addWidget(self.participant_manager)
        self.left_pane_layout.addWidget(self.node_tree_manager)
        export_button = QPushButton("Export All Coded Data")
        export_button.setToolTip("Export all coded data for the project")
        export_menu = QMenu(self)
        self.action_export_json = export_menu.addAction("Export as JSON (.json)")
        self.action_export_word = export_menu.addAction("Export as Word (.docx)")
        self.action_export_excel = export_menu.addAction("Export as Excel (.xlsx)")
        export_button.setMenu(export_menu)
        self.left_pane_layout.addStretch()
        self.left_pane_layout.addWidget(export_button)
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
        self.center_pane.segment_clicked.connect(self.bottom_pane.select_segment_by_id)
        self.bottom_pane.segment_deleted.connect(self.on_segment_deleted)
        self.bottom_pane.segment_activated.connect(self.on_segment_navigation_requested)

        self.action_export_json.triggered.connect(self.export_as_json)
        self.action_export_word.triggered.connect(self.export_as_word)
        self.action_export_excel.triggered.connect(self.export_as_excel)

        self.node_tree_manager.filter_by_node_family_signal.connect(
            self.bottom_pane.filter_by_node_family
        )
        self.node_tree_manager.filter_by_single_node_signal.connect(
            self.bottom_pane.filter_by_single_node
        )

        self.participant_manager.participant_updated.connect(self.refresh_all_views)

        self.node_tree_manager.node_updated.connect(self.on_node_data_updated)
        self.center_pane.text_selection_changed.connect(
            self.node_tree_manager.set_selection_mode
        )
        self.node_tree_manager.node_selected_for_coding.connect(self.code_selection)

        # Initial Load
        self.center_pane.load_document_content()
        self.on_document_changed()

    def on_segment_navigation_requested(self, document_id, start, end):
        """Receives signal from CodedSegmentsView and commands ContentView."""
        self.center_pane.go_to_segment(document_id, start, end)

    def open_dashboard(self):
        current_doc_id = self.center_pane.current_document_id
        dialog = DashboardView(self.project_id, self.project_name, current_doc_id, self)
        dialog.exec()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

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

        # Pass the stored ID to the content view's loader
        self.center_pane.load_document_list(doc_id_to_select=self._last_added_doc_id)

        # Refresh the other panes
        new_doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(new_doc_id)
        self.node_tree_manager.load_nodes()

        # Clear the temporary ID after use
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
        finally:
            QApplication.restoreOverrideCursor()

    # In ui/workspace/workspace_view.py

    def code_selection(self, node_id):
        # Get the text edit widget for easier access
        text_edit = self.center_pane.text_edit

        cursor = text_edit.textCursor()
        if not cursor.hasSelection():
            return

        # Save the scrollbar's value and selection end point BEFORE any changes
        selection_end_pos = cursor.selectionEnd()
        scrollbar = text_edit.verticalScrollBar()
        original_scroll_value = scrollbar.value()

        # Perform database operation
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        text = cursor.selectedText()
        doc_id = self.center_pane.current_document_id
        participant_id = self.center_pane.current_participant_id
        if not doc_id:
            return
        database.add_coded_segment(doc_id, node_id, participant_id, start, end, text)

        # Refresh all other UI components
        self.bottom_pane.reload_view()
        self.center_pane.apply_all_highlights()
        self.node_tree_manager.load_nodes()

        # Restore cursor and then immediately restore scrollbar to prevent scrolling
        new_cursor = text_edit.textCursor()
        new_cursor.setPosition(selection_end_pos)
        text_edit.setTextCursor(new_cursor)
        scrollbar.setValue(original_scroll_value)

        # Ensure the editor remains focused
        text_edit.setFocus()
