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
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QColorDialog,
    QMessageBox,
    QProgressDialog,
    QTabWidget,
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QSignalBlocker
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QShortcut,
    QTextCursor,
)

from ui.combo_box import FitPopupComboBox
from .participant_manager import ParticipantManager
from .node_tree_manager import NodeTreeManager
from .content_view import ContentView
from .coded_segments_view import CodedSegmentsView
from .ai_suggestion_dialog import AISuggestionDialog
from ui.dashboard.dashboard_view import DashboardView

from managers.export_manager import export_to_word, export_to_json, export_to_excel
from managers.theme_manager import save_settings, load_settings, apply_theme
import database
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from repositories.workspace_snapshot_repository import workspace_snapshot_repository
from services.workspace_history_service import WorkspaceCommand, WorkspaceHistory
from services.ai_suggestion_service import (
    AIConfigurationError,
    AISuggestion,
    AISuggestionError,
    AISuggestionService,
    DEFAULT_GEMINI_MODEL,
)
from services.worker_service import TaskThread


class SettingsDialog(QDialog):
    theme_changed = Signal()
    settings_applied = Signal(str, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.language = self.settings.get("language", "English")
        self.setWindowTitle(get_translation("workspace.settings", self.language))
        self.setMinimumSize(680, 500)
        self.resize(760, 540)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        self.settings_tabs = QTabWidget()

        general_page = QWidget()
        form_layout = QFormLayout(general_page)
        form_layout.setVerticalSpacing(14)
        form_layout.setHorizontalSpacing(18)
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
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(int(self.settings.get("font_size", 12)))
        form_layout.addRow(
            QLabel(get_translation("workspace.font_size", self.language)),
            self.font_size_spin,
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

        ai_page = QWidget()
        ai_form_layout = QFormLayout(ai_page)
        ai_form_layout.setVerticalSpacing(14)
        ai_form_layout.setHorizontalSpacing(18)
        ai_note = QLabel(
            get_translation("workspace.ai_settings_note", self.language)
        )
        ai_note.setWordWrap(True)
        ai_form_layout.addRow(ai_note)
        self.ai_provider_combo = FitPopupComboBox()
        self.ai_provider_combo.addItem(
            get_translation("workspace.ai_provider_gemini", self.language), "gemini"
        )
        self.ai_provider_combo.addItem(
            get_translation("workspace.ai_provider_openai", self.language),
            "openai_compatible",
        )
        saved_provider = self.settings.get("ai_provider", "gemini")
        provider_index = self.ai_provider_combo.findData(saved_provider)
        self.ai_provider_combo.setCurrentIndex(max(0, provider_index))
        self.ai_provider_combo.setMinimumWidth(240)
        ai_form_layout.addRow(
            QLabel(get_translation("workspace.ai_provider", self.language)),
            self.ai_provider_combo,
        )
        self.ai_api_key_edit = QLineEdit(
            str(self.settings.get("ai_api_key") or "")
        )
        self.ai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_api_key_edit.setMinimumWidth(460)
        self.ai_api_key_edit.setPlaceholderText(
            get_translation("workspace.ai_api_key_placeholder", self.language)
        )
        ai_form_layout.addRow(
            QLabel(get_translation("workspace.ai_api_key", self.language)),
            self.ai_api_key_edit,
        )
        self.ai_model_edit = QLineEdit(
            str(self.settings.get("ai_model") or DEFAULT_GEMINI_MODEL)
        )
        self.ai_model_edit.setMinimumWidth(460)
        ai_form_layout.addRow(
            QLabel(get_translation("workspace.ai_model", self.language)),
            self.ai_model_edit,
        )
        self.ai_api_url_edit = QLineEdit(
            str(self.settings.get("ai_api_url") or "")
        )
        self.ai_api_url_edit.setMinimumWidth(460)
        self.ai_api_url_edit.setPlaceholderText(
            get_translation("workspace.ai_api_url_placeholder", self.language)
        )
        ai_form_layout.addRow(
            QLabel(get_translation("workspace.ai_api_url", self.language)),
            self.ai_api_url_edit,
        )
        self.settings_tabs.addTab(
            general_page,
            get_translation("workspace.general_category", self.language),
        )
        self.settings_tabs.addTab(
            ai_page,
            get_translation("workspace.ai_category", self.language),
        )
        layout.addWidget(self.settings_tabs, 1)
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
        self.settings["font_size"] = self.font_size_spin.value()
        self.settings["undo_depth"] = self.undo_depth_spin.value()
        self.settings["autosave_enabled"] = self.autosave_checkbox.isChecked()
        self.settings["autosave_delay_ms"] = self.autosave_delay_spin.value()
        self.settings["find_match_color"] = self.find_match_color
        self.settings["ai_provider"] = self.ai_provider_combo.currentData()
        self.settings["ai_api_key"] = self.ai_api_key_edit.text().strip()
        self.settings["ai_model"] = self.ai_model_edit.text().strip()
        self.settings["ai_api_url"] = self.ai_api_url_edit.text().strip()
        save_settings(self.settings)
        app = QApplication.instance()
        if app:
            apply_theme(app)
        self.settings_applied.emit(
            self.settings["theme"],
            self.settings["language"],
            self.settings["font_size"],
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
        self._ai_thread = None
        self._ai_request_active = False
        self._ai_progress_dialog = None
        self.history = WorkspaceHistory(int(load_settings().get("undo_depth", 100)))
        self.history.add_changed_callback(self.update_undo_redo_actions)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.toolbar = QToolBar(get_translation("toolbar.projects", self.language))
        self.toolbar.setMovable(False)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setStyleSheet(
            "QToolBar { padding: 1px 4px; spacing: 2px; }"
            " QToolBar::separator { width: 1px; margin: 4px 6px; }"
            " QToolButton { font-weight: 600; padding: 3px 8px; margin: 0px; }"
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
        self.left_pane.setMinimumWidth(280)
        self.left_pane_layout = QVBoxLayout(self.left_pane)
        self.center_pane = ContentView(self.project_id, self.language)
        self.center_pane.ai_suggestions_button.clicked.connect(
            self.request_ai_suggestions
        )
        self.center_pane.setMinimumWidth(420)
        self.center_pane.setMinimumHeight(260)
        self.bottom_pane = CodedSegmentsView(
            self.project_id, self.language, defer_load=True
        )
        self.bottom_pane.setMinimumHeight(180)
        self.participant_manager = ParticipantManager(
            self.project_id, self.language, defer_load=True
        )
        self.node_tree_manager = NodeTreeManager(
            self.project_id, self.language, defer_load=True
        )
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
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.addWidget(self.center_pane)
        self.right_splitter.addWidget(self.bottom_pane)
        self.right_splitter.setSizes([400, 400])
        self.main_splitter.addWidget(self.left_pane)
        self.main_splitter.addWidget(self.right_splitter)
        self.main_splitter.setSizes([350, 700])
        main_layout.addWidget(self.main_splitter)

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

    def _apply_runtime_settings(self, theme, language, font_size):
        app = QApplication.instance()
        if app:
            apply_theme(app)
            app_font = QFont(app.font())
            app_font.setPointSize(max(8, int(font_size)))
            app.setFont(app_font)
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
        self._update_ai_suggestions_button()
        self._apply_theme_icons(theme)
        if hasattr(self.bottom_pane, "update_language"):
            self.bottom_pane.update_language(self.language)
        if hasattr(self.bottom_pane, "update_theme"):
            self.bottom_pane.update_theme(theme)
        for dialog in list(self._open_dashboards):
            if hasattr(dialog, "update_language"):
                dialog.update_language(self.language)
            self._refresh_widget_fonts(dialog)
        self._refresh_widget_fonts(self.window())

    def _refresh_widget_fonts(self, widget):
        if widget is None:
            return
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.updateGeometry()
        widget.update()
        for child in widget.findChildren(QWidget):
            child_style = child.style()
            child_style.unpolish(child)
            child_style.polish(child)
            child.updateGeometry()
            child.update()

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

    def on_segment_deleted(self, segment_id=None, restored_segment=None):
        if restored_segment:
            self.center_pane.add_cached_coded_segment(restored_segment)
        elif segment_id is not None:
            self.center_pane.remove_cached_coded_segment(segment_id)
        else:
            self.center_pane.apply_all_highlights()
        self.refresh_coding_stats()

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
        previous_doc_id = self.center_pane.current_document_id
        editor_state = (
            self.center_pane._capture_editor_state() if previous_doc_id else None
        )
        doc_id_to_select = self._last_added_doc_id or self.center_pane.current_document_id
        participant_id_to_select = self.participant_manager.get_selected_participant_id()
        node_id_to_reselect = self.node_tree_manager.get_selected_node_id()
        self.participant_manager.load_participants(
            participant_id_to_select=participant_id_to_select
        )
        self.center_pane.load_document_list(doc_id_to_select=doc_id_to_select)
        new_doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(new_doc_id)
        self.node_tree_manager.load_nodes(node_id_to_reselect=node_id_to_reselect)
        if editor_state and new_doc_id == previous_doc_id:
            QTimer.singleShot(
                0, lambda state=editor_state: self.center_pane._restore_editor_state(state)
            )
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

            participant_id = database.get_participant_for_document(doc_id)
            if participant_id:
                self.participant_manager.highlight_participant_by_id(participant_id)
            else:
                self.participant_manager.clear_selection()

        finally:
            QApplication.restoreOverrideCursor()
        self._update_ai_suggestions_button()

    def on_segments_changed(self):
        """
        Called when segments are added or deleted.
        Reloads all relevant views.
        """
        doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(doc_id)
        self.center_pane.apply_all_highlights()
        self.refresh_coding_stats()

    def refresh_coding_stats(self):
        self.node_tree_manager.refresh_stats()
        self.participant_manager.refresh_stats()

    def _capture_ai_selection(self):
        if self._in_edit_mode or not self.center_pane.current_document_id:
            return None
        text_edit = self.center_pane.text_edit
        cursor = text_edit.textCursor()
        if not cursor.hasSelection():
            return None
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        document_text = text_edit.toPlainText()
        if not 0 <= start < end <= len(document_text):
            return None
        selected_text = document_text[start:end]
        if not selected_text.strip():
            return None
        return {
            "document_id": self.center_pane.current_document_id,
            "participant_id": self.center_pane.current_participant_id,
            "start": start,
            "end": end,
            "text": selected_text,
        }

    def _get_ai_node_context(self):
        nodes = database.get_nodes_for_project(self.project_id)
        context = [
            {"id": node["id"], "name": node["name"], "parent_id": node["parent_id"]}
            for node in nodes
        ]
        node_details = {
            node["id"]: {
                "name": node["name"],
                "color": node.get("color") or "#9CA3AF",
            }
            for node in nodes
        }
        return context, node_details

    def request_ai_suggestions(self):
        if self._ai_request_active or (
            self._ai_thread is not None and self._ai_thread.isRunning()
        ):
            return
        selection = self._capture_ai_selection()
        if selection is None:
            self._update_ai_suggestions_button()
            return

        privacy_reply = QMessageBox.question(
            self,
            get_translation("ai_suggestions.privacy_title", self.language),
            get_translation("ai_suggestions.privacy_message", self.language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if privacy_reply != QMessageBox.StandardButton.Yes:
            return

        node_context, node_details = self._get_ai_node_context()
        service = AISuggestionService()
        self._ai_request_active = True
        self._update_ai_suggestions_button()
        self._show_ai_progress_dialog()
        self.center_pane.ai_suggestions_button.setToolTip(
            get_translation("ai_suggestions.loading", self.language)
        )
        thread = TaskThread(service.suggest, selection["text"], node_context)
        thread.setParent(self)
        self._ai_thread = thread
        thread.succeeded.connect(
            lambda suggestions: self._on_ai_suggestions_ready(
                suggestions, selection, node_details
            )
        )
        thread.failed.connect(self._on_ai_suggestions_failed)
        thread.finished.connect(self._on_ai_thread_finished)
        thread.start()

    def _on_ai_suggestions_ready(self, suggestions, selection, node_details):
        self._close_ai_progress_dialog()
        if not isinstance(suggestions, list):
            return
        if not suggestions:
            QMessageBox.information(
                self,
                get_translation("ai_suggestions.title", self.language),
                get_translation("ai_suggestions.no_suggestions", self.language),
            )
            return
        dialog = AISuggestionDialog(
            suggestions,
            lambda suggestion: self._accept_ai_existing_suggestion(
                suggestion, selection
            ),
            node_details,
            language=self.language,
            parent=self,
        )
        dialog.exec()

    def _on_ai_suggestions_failed(self, failure):
        self._close_ai_progress_dialog()
        error = failure[1] if isinstance(failure, tuple) and len(failure) > 1 else failure
        if isinstance(error, AIConfigurationError):
            message = get_translation("ai_suggestions.missing_api_key", self.language)
        elif isinstance(error, AISuggestionError):
            message = get_translation("ai_suggestions.request_failed", self.language)
        else:
            message = get_translation("ai_suggestions.request_failed", self.language)
        message_box = QMessageBox(
            QMessageBox.Icon.Warning,
            get_translation("ai_suggestions.error_title", self.language),
            message,
            QMessageBox.StandardButton.Ok,
            self,
        )
        settings_button = None
        if isinstance(error, AIConfigurationError):
            settings_button = message_box.addButton(
                get_translation("ai_suggestions.open_settings", self.language),
                QMessageBox.ButtonRole.ActionRole,
            )
        message_box.exec()
        if settings_button is not None and message_box.clickedButton() is settings_button:
            self.open_settings()

    def _on_ai_thread_finished(self):
        self._close_ai_progress_dialog()
        self._ai_request_active = False
        self._update_ai_suggestions_button()
        thread = self._ai_thread
        self._ai_thread = None
        if thread is not None:
            thread.deleteLater()

    def _show_ai_progress_dialog(self):
        self._close_ai_progress_dialog()
        dialog = QProgressDialog(
            get_translation("ai_suggestions.loading", self.language),
            None,
            0,
            0,
            self,
        )
        dialog.setWindowTitle(get_translation("ai_suggestions.title", self.language))
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setCancelButton(None)
        self._ai_progress_dialog = dialog
        dialog.show()

    def _close_ai_progress_dialog(self):
        dialog = self._ai_progress_dialog
        self._ai_progress_dialog = None
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()

    def _update_ai_suggestions_button(self, selection_enabled=None):
        if selection_enabled is None:
            selection_enabled = self._capture_ai_selection() is not None
        enabled = (
            bool(selection_enabled)
            and not self._in_edit_mode
            and not self._ai_request_active
            and bool(self.center_pane.current_document_id)
        )
        self.center_pane.ai_suggestions_button.setEnabled(enabled)
        if not self._ai_request_active:
            self.center_pane.ai_suggestions_button.setToolTip(
                get_translation("content_view.ai_suggestions_tooltip", self.language)
            )

    def _validate_ai_selection(self, selection):
        if self.center_pane.current_document_id != selection["document_id"]:
            self._show_stale_ai_selection_message()
            return False
        document_text = self.center_pane.text_edit.toPlainText()
        start, end = selection["start"], selection["end"]
        if not 0 <= start < end <= len(document_text):
            self._show_stale_ai_selection_message()
            return False
        if document_text[start:end] != selection["text"]:
            self._show_stale_ai_selection_message()
            return False
        return True

    def _show_stale_ai_selection_message(self):
        QMessageBox.warning(
            self,
            get_translation("ai_suggestions.error_title", self.language),
            get_translation("ai_suggestions.selection_changed", self.language),
        )

    def _accept_ai_existing_suggestion(self, suggestion: AISuggestion, selection):
        if (
            isinstance(suggestion.existing_node_id, bool)
            or not isinstance(suggestion.existing_node_id, int)
            or not self._validate_ai_selection(selection)
        ):
            return False
        node_ids = {node["id"] for node in database.get_nodes_for_project(self.project_id)}
        if suggestion.existing_node_id not in node_ids:
            QMessageBox.warning(
                self,
                get_translation("ai_suggestions.error_title", self.language),
                get_translation("ai_suggestions.node_missing", self.language),
            )
            return False
        try:
            return self.code_selection(suggestion.existing_node_id, selection)
        except Exception:
            QMessageBox.warning(
                self,
                get_translation("ai_suggestions.error_title", self.language),
                get_translation("ai_suggestions.apply_failed", self.language),
            )
            return False

    def code_selection(self, node_id, selection=None):
        text_edit = self.center_pane.text_edit
        cursor = text_edit.textCursor()
        if selection is not None:
            start = int(selection["start"])
            end = int(selection["end"])
            document_text = text_edit.toPlainText()
            if not 0 <= start < end <= len(document_text):
                return False
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            text_edit.setTextCursor(cursor)
            text = document_text[start:end]
        else:
            if not cursor.hasSelection():
                return False
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            text = cursor.selectedText()
        selection_end_pos = end
        scrollbar = text_edit.verticalScrollBar()
        original_scroll_value = scrollbar.value()
        doc_id = self.center_pane.current_document_id
        participant_id = self.center_pane.current_participant_id
        if not doc_id:
            return False
        if self.center_pane.is_dirty:
            if not self.center_pane.save_document(show_success_prompt=False):
                return False
        segment_id = None
        segment_snapshot = None
        segment_added = False

        def refresh_after_coding():
            self.bottom_pane.reload_view()
            if segment_added:
                self.center_pane.add_cached_coded_segment(segment_snapshot)
            elif segment_id is not None:
                self.center_pane.remove_cached_coded_segment(segment_id)
            self.refresh_coding_stats()
            new_cursor = text_edit.textCursor()
            new_cursor.setPosition(selection_end_pos)
            with QSignalBlocker(text_edit):
                text_edit.setTextCursor(new_cursor)
            scrollbar.setValue(original_scroll_value)
            text_edit.setFocus()

        def do():
            nonlocal segment_id, segment_snapshot, segment_added
            if segment_snapshot:
                workspace_snapshot_repository.restore_segment(segment_snapshot)
            else:
                segment_id = database.add_coded_segment(
                    doc_id, node_id, participant_id, start, end, text
                )
                segment_snapshot = workspace_snapshot_repository.get_segment(segment_id)
                segment_snapshot["node_color"] = self.node_tree_manager.nodes_map.get(
                    node_id, {}
                ).get("color", "#FFFF00")
            segment_added = True

        def undo():
            nonlocal segment_added
            if segment_id:
                database.delete_coded_segment(segment_id)
            segment_added = False

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.execute_workspace_command(
                WorkspaceCommand("Code Selection", do, undo, refresh_after_coding)
            )
        finally:
            QApplication.restoreOverrideCursor()
        return True

    def handle_text_selection_changed(self, enabled):
        # Only allow selection mode if not in edit segment mode
        if not self._in_edit_mode:
            self.node_tree_manager.set_selection_mode(enabled)
        else:
            self.node_tree_manager.set_selection_mode(False)
        self._update_ai_suggestions_button()

    def handle_edit_mode_changed(self, in_edit_mode):
        self._in_edit_mode = in_edit_mode
        # Always disable selection mode when entering edit mode
        if in_edit_mode:
            self.node_tree_manager.set_selection_mode(False)
        self._update_ai_suggestions_button()


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
