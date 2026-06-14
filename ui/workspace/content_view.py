from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QApplication,
    QFrame,
    QStackedLayout,
    QInputDialog,
    QMenu,
    QToolTip,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QTimer
from PySide6.QtGui import (
    QAction,
    QTextCursor,
    QColor,
    QTextDocument,
    QFont,
    QIcon,
    QKeySequence,
    QShortcut,
)
import os
import database

from managers.export_manager import export_annotated_document
from managers.theme_manager import load_settings
from .excel_import_dialog import ExcelImportDialog
from managers import excel_import_manager
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from services.import_service import import_service
from services.segment_rebasing_service import (
    rebase_segments_for_edit,
    replace_all_and_rebase_segments,
)
from services.settings_service import settings_service
from services.worker_service import TaskThread
from repositories.workspace_snapshot_repository import workspace_snapshot_repository
from services.workspace_history_service import WorkspaceCommand
from ui.combo_box import FitPopupComboBox


class InstantToolTipButton(QPushButton):
    def enterEvent(self, event):
        if self.toolTip():
            anchor = self.mapToGlobal(self.rect().center()) + QPoint(0, 12)
            QToolTip.showText(anchor, self.toolTip(), self, self.rect())
        super().enterEvent(event)

    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)


class ContentView(QWidget):
    document_deleted = Signal()
    document_added = Signal(int)
    bulk_documents_added = Signal()
    segment_clicked = Signal(int)
    text_selection_changed = Signal(bool)
    node_clicked_in_content = Signal(int)
    participant_highlight_requested = Signal(int)
    documents_changed = Signal()
    segments_changed = Signal()
    edit_mode_changed = Signal(bool)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, project_id, language=None):
        super().__init__()
        self.language = language or load_settings().get("language", "English")
        self.project_id = project_id
        self.documents_map = {}
        self.current_document_id = None
        self.current_participant_id = None
        self.editing_segment_id = None
        self.is_dirty = False
        self._coded_segments_cache = []
        self._pending_deleted_segments = {}
        self._loading_document = False
        self._document_change_connected = False
        self._pending_highlight = None
        self._import_thread = None
        self._excel_import_before_ids = None
        self.undo_executor = None
        self.applied_command_recorder = None
        self.setAcceptDrops(True)
        main_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()
        self.title_label = QLabel(
            get_translation("content_view.document_view", self.language)
        )
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        self.doc_selector = FitPopupComboBox()
        self.doc_selector.setMinimumWidth(300)

        self.import_button = InstantToolTipButton()
        self.import_icon = MaterialIcon("upload")
        self.import_button.setIcon(self.import_icon)
        self.import_button.setToolTip(
            get_translation("content_view.import_tooltip", self.language)
        )
        self.save_button = InstantToolTipButton()
        self.save_icon = MaterialIcon("save")
        self.save_button.setIcon(self.save_icon)
        self.save_button.setToolTip(
            get_translation("content_view.save_tooltip", self.language)
        )
        self.save_button.setFixedSize(28, 28)
        self.save_button.setIconSize(QSize(16, 16))
        self.save_button.setEnabled(False)
        self.undo_button = InstantToolTipButton()
        self.undo_icon = MaterialIcon("undo")
        self.undo_button.setIcon(self.undo_icon)
        self.undo_button.setToolTip(
            get_translation("content_view.undo_tooltip", self.language)
        )
        self.undo_button.setFixedSize(28, 28)
        self.undo_button.setIconSize(QSize(16, 16))
        self.undo_button.setEnabled(False)
        self.redo_button = InstantToolTipButton()
        self.redo_icon = MaterialIcon("redo")
        self.redo_button.setIcon(self.redo_icon)
        self.redo_button.setToolTip(
            get_translation("content_view.redo_tooltip", self.language)
        )
        self.redo_button.setFixedSize(28, 28)
        self.redo_button.setIconSize(QSize(16, 16))
        self.redo_button.setEnabled(False)
        self.find_button = InstantToolTipButton()
        self.find_icon = MaterialIcon("search")
        self.find_button.setIcon(self.find_icon)
        self.find_button.setToolTip(
            get_translation("content_view.find_tooltip", self.language)
        )
        self.find_button.setFixedSize(28, 28)
        self.find_button.setIconSize(QSize(16, 16))
        self.delete_button = InstantToolTipButton()
        self.delete_icon = MaterialIcon("delete")
        self.delete_button.setIcon(self.delete_icon)
        self.delete_button.setToolTip(
            get_translation("content_view.delete_tooltip", self.language)
        )
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setIconSize(QSize(16, 16))
        self.export_annotated_button = InstantToolTipButton()
        self.export_annotated_icon = MaterialIcon("description")
        self.export_annotated_button.setIcon(self.export_annotated_icon)
        self.export_annotated_button.setToolTip(
            get_translation("content_view.export_annotated_tooltip", self.language)
        )
        self.export_annotated_button.setFixedSize(28, 28)
        self.export_annotated_button.setIconSize(QSize(16, 16))
        self.import_button.setFixedSize(28, 28)
        self.import_button.setIconSize(QSize(16, 16))
        self.document_menu_button = InstantToolTipButton()
        self.document_menu_icon = MaterialIcon("more_vert")
        self.document_menu_button.setIcon(self.document_menu_icon)
        self.document_menu_button.setToolTip(
            get_translation("content_view.document_actions_tooltip", self.language)
        )
        self.document_menu_button.setFixedSize(28, 28)
        self.document_menu_button.setIconSize(QSize(16, 16))
        self.document_menu = QMenu(self)
        self.import_action = QAction(
            get_translation("content_view.import_tooltip", self.language), self
        )
        self.export_annotated_action = QAction(
            get_translation("content_view.export_annotated_tooltip", self.language), self
        )
        self.delete_document_action = QAction(
            get_translation("content_view.delete_tooltip", self.language), self
        )
        self.document_menu.addAction(self.import_action)
        self.document_menu.addAction(self.export_annotated_action)
        self.document_menu.addAction(self.delete_document_action)

        self.find_bar = QFrame()
        self.find_bar.setObjectName("findBar")
        find_bar_layout = QHBoxLayout(self.find_bar)
        find_bar_layout.setContentsMargins(5, 2, 5, 2)
        find_bar_layout.setSpacing(6)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText(
            get_translation("content_view.find_placeholder", self.language)
        )
        self.find_input.setMinimumWidth(180)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(
            get_translation("content_view.replace_placeholder", self.language)
        )
        self.replace_input.setMinimumWidth(180)
        self.find_previous_button = QPushButton()
        self.find_previous_icon = MaterialIcon("arrow_back")
        self.find_previous_button.setIcon(self.find_previous_icon)
        self.find_previous_button.setToolTip(
            get_translation("content_view.find_previous", self.language)
        )
        self.find_previous_button.setFixedSize(30, 30)
        self.find_previous_button.setIconSize(QSize(16, 16))
        self.find_next_button = QPushButton()
        self.find_next_icon = MaterialIcon("arrow_forward")
        self.find_next_button.setIcon(self.find_next_icon)
        self.find_next_button.setToolTip(
            get_translation("content_view.find_next", self.language)
        )
        self.find_next_button.setFixedSize(30, 30)
        self.find_next_button.setIconSize(QSize(16, 16))
        self.replace_button = QPushButton(
            get_translation("content_view.replace_one", self.language)
        )
        self.replace_button.setFixedWidth(84)
        self.replace_all_button = QPushButton(
            get_translation("content_view.replace_all", self.language)
        )
        self.replace_all_button.setFixedWidth(118)
        self.find_count_label = QLabel("")
        self.find_count_label.setMinimumWidth(100)
        self.find_count_label.setMaximumWidth(120)
        self.find_count_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        self.find_count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.find_status_label = QLabel("")
        self.find_status_label.setMinimumWidth(120)
        self.find_status_label.setMaximumWidth(150)
        self.find_status_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        self.find_status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.find_close_button = QPushButton()
        self.find_close_icon = MaterialIcon("close")
        self.find_close_button.setIcon(self.find_close_icon)
        self.find_close_button.setToolTip(
            get_translation("content_view.find_close", self.language)
        )
        self.find_close_button.setFixedSize(28, 28)
        self.find_close_button.setIconSize(QSize(16, 16))
        find_bar_layout.addWidget(self.find_input, 1)
        find_bar_layout.addWidget(self.replace_input, 1)
        find_bar_layout.addWidget(self.find_previous_button)
        find_bar_layout.addWidget(self.find_next_button)
        find_bar_layout.addWidget(self.replace_button)
        find_bar_layout.addWidget(self.replace_all_button)
        find_bar_layout.addWidget(self.find_count_label)
        find_bar_layout.addWidget(self.find_status_label)
        find_bar_layout.addWidget(self.find_close_button)
        self.find_bar.setVisible(False)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(False)
        self.text_edit.setAcceptDrops(False)
        self.drop_overlay = QFrame()
        self.drop_overlay.setObjectName("dropOverlay")
        overlay_layout = QVBoxLayout(self.drop_overlay)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.setSpacing(10)
        icon_label = QLabel()
        upload_icon = MaterialIcon("upload")
        icon_label.setPixmap(upload_icon.pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drop_text_label = QLabel(
            get_translation("content_view.drop_text", self.language)
        )
        text_font = QFont()
        text_font.setPointSize(12)
        self.drop_text_label.setFont(text_font)
        self.drop_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(icon_label)
        overlay_layout.addWidget(self.drop_text_label)
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.addWidget(self.text_edit)
        self.stacked_layout.addWidget(self.drop_overlay)
        self.stacked_layout.setCurrentWidget(self.text_edit)
        info_bar = QFrame()
        info_bar.setFrameShape(QFrame.Shape.StyledPanel)
        info_bar_layout = QHBoxLayout(info_bar)
        info_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.word_count_label = QLabel(
            get_translation("content_view.word_count", self.language, count=0)
        )
        self.segment_count_label = QLabel(
            get_translation("content_view.coded_segments_count", self.language, count=0)
        )
        info_bar_layout.addWidget(self.word_count_label)
        info_bar_layout.addStretch()
        info_bar_layout.addWidget(self.segment_count_label)
        top_bar_layout.addWidget(self.title_label)
        top_bar_layout.addWidget(self.doc_selector)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.undo_button)
        top_bar_layout.addWidget(self.redo_button)
        top_bar_layout.addWidget(self.find_button)
        top_bar_layout.addWidget(self.save_button)
        top_bar_layout.addWidget(self.document_menu_button)

        # Edit Mode Bar
        self.edit_bar = QFrame()
        self.edit_bar.setObjectName("editBar")
        edit_bar_layout = QHBoxLayout(self.edit_bar)
        edit_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.edit_label = QLabel(
            get_translation("edit_bar.editing_segment", self.language)
        )
        self.save_edit_button = QPushButton(
            get_translation("edit_bar.save_changes", self.language)
        )
        self.cancel_edit_button = QPushButton(
            get_translation("edit_bar.cancel", self.language)
        )
        edit_bar_layout.addWidget(self.edit_label)
        edit_bar_layout.addStretch()
        edit_bar_layout.addWidget(self.save_edit_button)
        edit_bar_layout.addWidget(self.cancel_edit_button)
        self.edit_bar.setVisible(False)

        main_layout.addLayout(top_bar_layout)
        main_layout.addWidget(self.find_bar)
        main_layout.addWidget(self.edit_bar)
        main_layout.addLayout(self.stacked_layout)
        main_layout.addWidget(info_bar)

        self.import_action.triggered.connect(self.open_import_dialog)
        self.undo_button.clicked.connect(self.request_undo)
        self.redo_button.clicked.connect(self.request_redo)
        self.find_button.clicked.connect(self.show_find_bar)
        self.save_button.clicked.connect(self.save_document)
        self.document_menu_button.clicked.connect(self.show_document_actions_menu)
        self.export_annotated_action.triggered.connect(self.export_annotated)
        self.delete_document_action.triggered.connect(self.delete_current_document)
        self.text_edit.selectionChanged.connect(self.on_edit_selection_changed)
        self.save_edit_button.clicked.connect(self.save_segment_edit)
        self.cancel_edit_button.clicked.connect(self.cancel_segment_edit)
        self.doc_selector.currentIndexChanged.connect(self.handle_document_switch)
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.text_edit.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.text_edit.selectionChanged.connect(self.on_selection_changed_for_coding)
        self.find_input.returnPressed.connect(self.find_next)
        self.replace_input.returnPressed.connect(self.replace_current)
        self.find_previous_button.clicked.connect(self.find_previous)
        self.find_next_button.clicked.connect(self.find_next)
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button.clicked.connect(self.replace_all)
        self.find_close_button.clicked.connect(self.hide_find_bar)
        self.find_input.textChanged.connect(self.clear_find_status)
        self.replace_input.textChanged.connect(self.clear_find_status)
        self.find_input.textChanged.connect(self.update_match_count)
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.activated.connect(self.show_find_bar)
        self.find_close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.find_bar)
        self.find_close_shortcut.activated.connect(self.hide_find_bar)
        self.text_edit.undoAvailable.connect(self.undo_button.setEnabled)
        self.text_edit.redoAvailable.connect(self.redo_button.setEnabled)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.autosave_document)
        self.load_document_list()
        self.update_theme(load_settings().get("theme", "Light"))

    def set_undo_executor(self, undo_executor):
        self.undo_executor = undo_executor

    def set_applied_command_recorder(self, applied_command_recorder):
        self.applied_command_recorder = applied_command_recorder

    def execute_workspace_command(self, command: WorkspaceCommand):
        if self.undo_executor:
            self.undo_executor(command)
        else:
            command.do()
            command.after_refresh()

    def record_applied_command(self, command: WorkspaceCommand):
        if self.applied_command_recorder:
            self.applied_command_recorder(command)

    def request_undo(self):
        if self.text_edit.document().isUndoAvailable():
            self.text_edit.undo()
        else:
            self.undo_requested.emit()

    def request_redo(self):
        if self.text_edit.document().isRedoAvailable():
            self.text_edit.redo()
        else:
            self.redo_requested.emit()

    def show_find_bar(self):
        self.find_bar.setVisible(True)
        selected_text = self.text_edit.textCursor().selectedText().replace("\u2029", "\n")
        if selected_text and "\n" not in selected_text:
            self.find_input.setText(selected_text)
        self.clear_find_status()
        self.update_match_count()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_find_bar(self):
        self.find_bar.setVisible(False)
        self.clear_find_status()
        self.find_count_label.setText("")
        self._render_highlights()
        self.text_edit.setFocus()

    def show_document_actions_menu(self):
        self.document_menu.popup(
            self.document_menu_button.mapToGlobal(
                self.document_menu_button.rect().bottomLeft()
            )
        )

    def clear_find_status(self):
        self.find_status_label.setText("")

    def _autosave_settings(self):
        settings = settings_service.load()
        return (
            bool(settings.get("autosave_enabled", True)),
            int(settings.get("autosave_delay_ms", 1500)),
        )

    def _find_match_color(self):
        return settings_service.load().get("find_match_color", "#FFF59D")

    def _schedule_autosave(self):
        autosave_enabled, delay_ms = self._autosave_settings()
        if autosave_enabled and self.current_document_id:
            self.autosave_timer.start(max(250, delay_ms))

    def autosave_document(self):
        if self.is_dirty and self.current_document_id:
            self.save_document(
                show_success_prompt=False,
                record_history=False,
                reload_after_save=False,
            )

    def apply_autosave_settings(self):
        autosave_enabled, delay_ms = self._autosave_settings()
        if not autosave_enabled:
            self.autosave_timer.stop()
        elif self.is_dirty and self.current_document_id:
            self.autosave_timer.start(max(250, delay_ms))
        self._render_highlights()

    def update_match_count(self):
        search_text = self.find_input.text()
        if not search_text:
            self.find_count_label.setText("")
            return 0
        count = self.text_edit.toPlainText().count(search_text)
        self.find_count_label.setText(
            get_translation("content_view.find_match_count", self.language, count=count)
        )
        self._render_highlights()
        return count

    def _find_text(self, backward=False):
        search_text = self.find_input.text()
        if not search_text:
            self.find_status_label.setText(
                get_translation("content_view.find_enter_text", self.language)
            )
            return False

        flags = QTextDocument.FindFlag(0)
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward

        found = self.text_edit.find(search_text, flags)
        if found:
            self.find_status_label.setText("")
            return True

        cursor = self.text_edit.textCursor()
        if backward:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_edit.setTextCursor(cursor)
        found = self.text_edit.find(search_text, flags)
        if found:
            self.find_status_label.setText("")
            return True

        self.find_status_label.setText(
            get_translation("content_view.find_not_found", self.language)
        )
        return False

    def find_next(self):
        self._find_text(backward=False)

    def find_previous(self):
        self._find_text(backward=True)

    def replace_current(self):
        search_text = self.find_input.text()
        if not search_text:
            self.find_status_label.setText(
                get_translation("content_view.find_enter_text", self.language)
            )
            return

        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n")
        if selected_text != search_text and not self._find_text(backward=False):
            return
        reply = QMessageBox.question(
            self,
            get_translation("content_view.replace_confirm_title", self.language),
            get_translation(
                "content_view.replace_confirm_message",
                self.language,
                search=search_text,
                replacement=self.replace_input.text(),
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        cursor = self.text_edit.textCursor()
        cursor.insertText(self.replace_input.text())
        self.text_edit.setTextCursor(cursor)
        self.apply_all_highlights()
        self.find_status_label.setText(
            get_translation("content_view.replace_done", self.language)
        )
        self.update_match_count()
        self.find_next()

    def replace_all(self):
        search_text = self.find_input.text()
        if not search_text:
            self.find_status_label.setText(
                get_translation("content_view.find_enter_text", self.language)
            )
            return

        replacement = self.replace_input.text()
        count = self.update_match_count()
        if count == 0:
            self.find_status_label.setText(
                get_translation("content_view.find_not_found", self.language)
            )
            return
        confirm_box = QMessageBox(self)
        confirm_box.setIcon(QMessageBox.Icon.Warning)
        confirm_box.setWindowTitle(
            get_translation("content_view.replace_all_confirm_title", self.language)
        )
        confirm_box.setText(
            get_translation(
                "content_view.replace_all_confirm_message",
                self.language,
                count=count,
                search=search_text,
                replacement=replacement,
            )
        )
        confirm_box.setInformativeText(
            get_translation("content_view.replace_all_risk_note", self.language)
        )
        confirm_box.setDetailedText(
            get_translation("content_view.replace_all_best_for", self.language)
        )
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
        if confirm_box.exec() != QMessageBox.StandardButton.Yes:
            return

        before_snapshot = self._get_live_document_snapshot()
        if not before_snapshot:
            return
        self._replace_all_confirmed(search_text, replacement, before_snapshot)

    def _replace_all_confirmed(self, search_text, replacement, before_snapshot=None):
        before_snapshot = before_snapshot or self._get_live_document_snapshot()
        if not before_snapshot:
            return 0
        self.autosave_timer.stop()
        old_text = self.text_edit.toPlainText()
        new_text, new_segments, deleted_segment_ids, replaced_count = (
            replace_all_and_rebase_segments(
                old_text,
                self._coded_segments_cache,
                search_text,
                replacement,
            )
        )
        if replaced_count == 0:
            return 0

        self._loading_document = True
        try:
            self.text_edit.setPlainText(new_text)
        finally:
            self._loading_document = False
        self._coded_segments_cache = new_segments
        self._pending_deleted_segments = {
            segment_id: {"id": segment_id} for segment_id in deleted_segment_ids
        }
        self.is_dirty = True
        self.save_button.setEnabled(True)
        self.save_document(
            show_success_prompt=False,
            record_history=False,
            reload_after_save=True,
            allow_segment_deletion=True,
        )
        after_snapshot = workspace_snapshot_repository.get_document_snapshot(
            before_snapshot["document"]["id"]
        )
        if after_snapshot:
            self.record_applied_command(
                WorkspaceCommand(
                    "Replace All",
                    lambda snapshot=after_snapshot: self._restore_document_snapshot(
                        snapshot
                    ),
                    lambda snapshot=before_snapshot: self._restore_document_snapshot(
                        snapshot
                    ),
                    self._after_document_snapshot_restore,
                )
            )
        self.apply_all_highlights()
        self.find_status_label.setText(
            get_translation(
                "content_view.replace_all_done", self.language, count=replaced_count
            )
        )
        self.update_match_count()
        return replaced_count

    def _get_live_document_snapshot(self):
        if not self.current_document_id:
            return None
        snapshot = workspace_snapshot_repository.get_document_snapshot(
            self.current_document_id
        )
        if not snapshot:
            return None
        document = dict(snapshot["document"])
        document["content"] = self.text_edit.toPlainText()
        active_segments = {
            segment["id"]: dict(segment) for segment in self._coded_segments_cache
        }
        deleted_ids = set(self._pending_deleted_segments)
        segments = []
        for segment in snapshot["segments"]:
            segment_id = segment["id"]
            if segment_id in deleted_ids or segment_id not in active_segments:
                continue
            active_segment = active_segments[segment_id]
            restored_segment = dict(segment)
            restored_segment["segment_start"] = active_segment["segment_start"]
            restored_segment["segment_end"] = active_segment["segment_end"]
            restored_segment["content_preview"] = active_segment["content_preview"]
            segments.append(restored_segment)
        return {"document": document, "segments": segments}

    def _restore_document_snapshot(self, snapshot):
        document_id = snapshot["document"]["id"]
        database.delete_document(document_id)
        workspace_snapshot_repository.restore_document_snapshot(snapshot)

    def _after_document_snapshot_restore(self):
        self.load_document_content()
        self.segments_changed.emit()
        self.is_dirty = False
        self.save_button.setEnabled(False)

    def _select_and_scroll(self, start, end):
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def go_to_segment(self, document_id, start, end, mode="view"):
        if document_id == self.current_document_id:
            if mode == "edit":
                self._highlight_for_edit(start, end)
            elif mode == "view":
                self._select_and_scroll(start, end)
        else:
            self._pending_highlight = (mode, start, end)
            id_to_display_text = {v: k for k, v in self.documents_map.items()}
            display_text = id_to_display_text.get(document_id)
            if display_text:
                index = self.doc_selector.findText(display_text)
                if index != -1:
                    self.doc_selector.setCurrentIndex(index)

    def start_segment_edit_mode(self, segment_id, document_id, start, end):
        if self.editing_segment_id is not None:
            QMessageBox.warning(
                self,
                "Edit in Progress",
                "Please save or cancel the current segment edit first.",
            )
            return
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The document has unsaved text changes that must be saved first. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_document(show_success_prompt=False):
                    return
            else:
                return
        self.editing_segment_id = segment_id
        self.go_to_segment(document_id, start, end, mode="edit")
        self.edit_mode_changed.emit(True)

    def _highlight_for_edit(self, start, end):
        self.apply_all_highlights()
        self._render_highlights((start, end))
        self._select_and_scroll(start, end)
        self.edit_bar.setVisible(True)

    def save_segment_edit(self):
        if self.editing_segment_id is None:
            return

        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            QMessageBox.warning(
                self,
                "No Selection",
                "Cannot save an empty segment. Please select text.",
            )
            return

        new_start = cursor.selectionStart()
        new_end = cursor.selectionEnd()
        new_text = cursor.selectedText()

        segment_id = self.editing_segment_id
        old_segment = workspace_snapshot_repository.get_segment(segment_id)
        if not old_segment:
            return

        def do():
            database.update_coded_segment(segment_id, new_start, new_end, new_text)

        def undo():
            database.update_coded_segment(
                segment_id,
                old_segment["segment_start"],
                old_segment["segment_end"],
                old_segment["content_preview"],
            )

        self.execute_workspace_command(
            WorkspaceCommand(
                "Edit Coded Segment",
                do,
                undo,
                lambda: (self.end_segment_edit_mode(), self.segments_changed.emit()),
            )
        )

        self.is_dirty = False
        self.text_edit.document().setModified(False)

        # Find the updated segment in the cache (after highlights are reapplied)
        for segment in self._coded_segments_cache:
            if (
                segment["id"] == segment_id
                and segment["segment_start"] == new_start
                and segment["segment_end"] == new_end
            ):
                self._select_and_scroll(new_start, new_end)
                self.segment_clicked.emit(segment["id"])
                break

    def cancel_segment_edit(self):
        self.end_segment_edit_mode()

    def end_segment_edit_mode(self):
        self.editing_segment_id = None
        self.edit_bar.setVisible(False)
        self.save_edit_button.setStyleSheet("")  # Clear special border
        self.apply_all_highlights()
        self.edit_mode_changed.emit(False)

    def on_edit_selection_changed(self):
        if (
            self.editing_segment_id is not None
            and self.text_edit.textCursor().hasSelection()
        ):
            self.save_edit_button.setStyleSheet("border: 2px solid #0078D7;")
        else:
            self.save_edit_button.setStyleSheet("")

    def open_import_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Documents",
            "",
            "All Supported Files (*.txt *.docx *.xlsx);;Text Files (*.txt);;Word Documents (*.docx);;Excel Files (*.xlsx)",
        )
        if file_paths:
            self.handle_files_dropped(file_paths)

    def handle_file_import(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            self._import_from_excel(file_path)
        elif ext in [".txt", ".docx"]:
            self._process_text_document(file_path)
        else:
            QMessageBox.warning(
                self, "Unsupported File", f"The file type '{ext}' is not supported."
            )

    def _import_from_excel(self, file_path):
        participants = database.get_participants_for_project(self.project_id)
        dialog = ExcelImportDialog(file_path, participants, self)
        if not dialog.valid_headers:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not read headers from '{os.path.basename(file_path)}'. Please ensure it is a valid .xlsx file with a header row.",
            )
            return
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mappings = dialog.get_column_mappings()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self._import_thread = TaskThread(
                excel_import_manager.import_data, self.project_id, file_path, mappings
            )
            self._excel_import_before_ids = (
                workspace_snapshot_repository.get_project_entity_ids(self.project_id)
            )
            self._import_thread.succeeded.connect(
                lambda result, filename=os.path.basename(file_path): self._finish_excel_import(
                    filename, result
                )
            )
            self._import_thread.failed.connect(self._handle_background_error)
            self._import_thread.start()

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile().lower()
                    if file_path.endswith((".txt", ".docx", ".xlsx")):
                        event.acceptProposedAction()
                        self.show_drop_overlay()
                        return
        event.ignore()

    def dropEvent(self, event):
        self.hide_drop_overlay()
        if event.mimeData().hasUrls():
            file_paths = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            self.handle_files_dropped(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def handle_files_dropped(self, file_paths):
        for path in file_paths:
            self.handle_file_import(path)

    def _process_text_document(self, file_path):
        try:
            title, content, source_metadata = import_service.read_text_document(file_path)
            if database.check_document_exists(self.project_id, title, content):
                reply = QMessageBox.question(
                    self,
                    "Duplicate Document",
                    f"The document '{title}' has been imported before.\n\nDo you want to add it as a new copy?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            participants = database.get_participants_for_project(self.project_id)
            if not participants:
                name, ok = QInputDialog.getText(
                    self,
                    "Create Participant",
                    "Enter a name for the first participant:",
                )
                if not ok or not name.strip():
                    QMessageBox.warning(
                        self,
                        "No Participants",
                        "You must create at least one participant to import documents.",
                    )
                    return
                self._import_and_add_document_with_new_participant(
                    name.strip(), title, content, source_metadata
                )
                return
            if len(participants) == 1:
                self._import_and_add_document(
                    participants[0]["id"], title, content, source_metadata
                )
            else:
                dialog = AssignParticipantDialog(participants, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    participant_id = dialog.get_selected_participant_id()
                    if participant_id:
                        self._import_and_add_document(
                            participant_id, title, content, source_metadata
                        )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to process file '{os.path.basename(file_path)}': {e}",
            )

    def dragLeaveEvent(self, event):
        self.hide_drop_overlay()
        event.accept()

    def show_drop_overlay(self):
        if self.stacked_layout.currentWidget() is not self.drop_overlay:
            settings = settings_service.load()
            is_dark = settings.get("theme") == "Dark"
            bg_color_str = (
                "rgba(60, 60, 60, 0.95)" if is_dark else "rgba(240, 240, 240, 0.95)"
            )
            border_color_str = "#aaa" if is_dark else "#888"
            self.drop_overlay.setStyleSheet(
                f"#dropOverlay {{ background-color: {bg_color_str}; border: 2px dashed {border_color_str}; border-radius: 10px; }}"
            )
            self.stacked_layout.setCurrentWidget(self.drop_overlay)

    def hide_drop_overlay(self):
        self.stacked_layout.setCurrentWidget(self.text_edit)

    def on_selection_changed_for_coding(self):
        self.text_selection_changed.emit(self.text_edit.textCursor().hasSelection())

    def load_document_list(self, doc_id_to_select=None):
        self.doc_selector.blockSignals(True)
        self.doc_selector.clear()
        docs = database.get_documents_for_project(self.project_id)
        display_count = {}
        display_texts = []
        for doc in docs:
            key = (doc["title"], doc["participant_name"] or "Unassigned")
            display_count[key] = display_count.get(key, 0) + 1
        seen = {}
        self.documents_map = {}
        for doc in docs:
            title = doc["title"]
            participant = doc["participant_name"] or "Unassigned"
            key = (title, participant)
            seen[key] = seen.get(key, 0) + 1
            if display_count[key] > 1:
                display_text = f"{title} ({participant}) [{seen[key]}]"
            else:
                display_text = f"{title} ({participant})"
            self.documents_map[display_text] = doc["id"]
            display_texts.append(display_text)
        for display_text in sorted(display_texts):
            self.doc_selector.addItem(display_text)
        self.doc_selector.blockSignals(False)
        new_index = -1
        if doc_id_to_select:
            id_to_display_text = {v: k for k, v in self.documents_map.items()}
            display_text = id_to_display_text.get(doc_id_to_select)
            if display_text:
                new_index = self.doc_selector.findText(display_text)
        if new_index == -1 and self.doc_selector.count() > 0:
            new_index = 0
        self.doc_selector.setCurrentIndex(new_index)
        self.handle_document_switch(new_index)

    def _import_and_add_document(
        self, participant_id, title, content, source_metadata=None
    ):
        new_doc_id = None
        snapshot = None

        def do():
            nonlocal new_doc_id, snapshot
            if snapshot:
                workspace_snapshot_repository.restore_document_snapshot(snapshot)
            else:
                new_doc_id = database.add_document(
                    self.project_id, title, content, participant_id, source_metadata
                )
                snapshot = workspace_snapshot_repository.get_document_snapshot(
                    new_doc_id
                )

        def undo():
            if new_doc_id:
                database.delete_document(new_doc_id)

        def after_refresh():
            self.is_dirty = False
            self.save_button.setEnabled(False)
            self.document_added.emit(new_doc_id)

        try:
            self.execute_workspace_command(
                WorkspaceCommand("Import Document", do, undo, after_refresh)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import file: {e}")

    def _import_and_add_document_with_new_participant(
        self, participant_name, title, content, source_metadata=None
    ):
        participant_id = None
        document_id = None
        participant_snapshot = None
        document_snapshot = None

        def do():
            nonlocal participant_id, document_id, participant_snapshot, document_snapshot
            if participant_snapshot and document_snapshot:
                workspace_snapshot_repository.restore_participant_snapshot(
                    participant_snapshot
                )
                workspace_snapshot_repository.restore_document_snapshot(document_snapshot)
            else:
                participant_id = database.add_participant(
                    self.project_id, participant_name
                )
                document_id = database.add_document(
                    self.project_id, title, content, participant_id, source_metadata
                )
                participant_snapshot = (
                    workspace_snapshot_repository.get_participant_snapshot(
                        participant_id
                    )
                )
                document_snapshot = workspace_snapshot_repository.get_document_snapshot(
                    document_id
                )

        def undo():
            if document_id:
                database.delete_document(document_id)
            if participant_id:
                database.delete_participant(participant_id)

        def after_refresh():
            self.is_dirty = False
            self.save_button.setEnabled(False)
            self.document_added.emit(document_id)

        try:
            self.execute_workspace_command(
                WorkspaceCommand("Import Document", do, undo, after_refresh)
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import file: {e}")

    def delete_current_document(self):
        if not self.current_document_id:
            QMessageBox.warning(self, "No document", "No document is selected.")
            return
        selected_text = self.doc_selector.currentText()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{selected_text}' and all its coded segments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            document_id = self.current_document_id
            snapshot = workspace_snapshot_repository.get_document_snapshot(document_id)
            if not snapshot:
                return

            def do():
                database.delete_document(document_id)

            def undo():
                workspace_snapshot_repository.restore_document_snapshot(snapshot)

            def after_refresh():
                self.is_dirty = False
                self.document_deleted.emit()

            self.execute_workspace_command(
                WorkspaceCommand("Delete Document", do, undo, after_refresh)
            )

    def on_text_changed(self):
        if not self.text_edit.isReadOnly():
            self.is_dirty = True
            self.save_button.setEnabled(True)
            if self.find_bar.isVisible():
                self.update_match_count()
            self._schedule_autosave()

    def on_document_contents_changed(self, position, chars_removed, chars_added):
        if self._loading_document or not self.current_document_id:
            return
        current_text = self.text_edit.toPlainText()
        segments_before = {
            segment["id"]: dict(segment)
            for segment in [
                *self._coded_segments_cache,
                *self._pending_deleted_segments.values(),
            ]
        }
        rebased_segments, deleted_segment_ids = rebase_segments_for_edit(
            list(segments_before.values()),
            position,
            chars_removed,
            chars_added,
            current_text,
        )
        self._coded_segments_cache = rebased_segments
        for segment in rebased_segments:
            self._pending_deleted_segments.pop(segment["id"], None)
        for segment_id in deleted_segment_ids:
            segment = segments_before.get(segment_id)
            if segment:
                tombstone_position = max(0, min(position, len(current_text)))
                segment["segment_start"] = tombstone_position
                segment["segment_end"] = tombstone_position
                self._pending_deleted_segments[segment_id] = segment
        self._render_highlights()

    def save_document(
        self,
        show_success_prompt=True,
        record_history=True,
        reload_after_save=True,
        allow_segment_deletion=False,
    ):
        if not self.is_dirty or not self.current_document_id:
            return False
        document_id = self.current_document_id
        old_content, _ = database.get_document_content(document_id)
        new_content = self.text_edit.toPlainText()
        old_snapshot = workspace_snapshot_repository.get_document_snapshot(document_id)
        new_segments = [dict(segment) for segment in self._coded_segments_cache]
        deleted_segment_ids = sorted(self._pending_deleted_segments)
        if deleted_segment_ids and not allow_segment_deletion:
            if not record_history:
                return False
            if not self._confirm_pending_segment_deletions(deleted_segment_ids):
                return False

        def do():
            database.update_document_text_and_segments(
                document_id, new_content, new_segments, deleted_segment_ids
            )

        def undo():
            if old_snapshot:
                database.delete_document(document_id)
                workspace_snapshot_repository.restore_document_snapshot(old_snapshot)
            else:
                database.update_document_text_only(document_id, old_content)

        def after_refresh():
            if reload_after_save:
                self.load_document_content()
            else:
                self._pending_deleted_segments = {}
            self.segments_changed.emit()
            self.is_dirty = False
            self.save_button.setEnabled(False)

        if record_history:
            self.execute_workspace_command(
                WorkspaceCommand("Save Document Text", do, undo, after_refresh)
            )
        else:
            do()
            after_refresh()
        if show_success_prompt:
            QMessageBox.information(
                self, "Success", "Document text saved successfully."
            )
        return True

    def _confirm_pending_segment_deletions(self, deleted_segment_ids):
        previews = []
        for segment_id in deleted_segment_ids[:5]:
            segment = self._pending_deleted_segments.get(segment_id, {})
            preview = segment.get("content_preview") or f"Segment #{segment_id}"
            previews.append(preview[:80])
        if len(deleted_segment_ids) > 5:
            previews.append(f"...and {len(deleted_segment_ids) - 5} more")
        details = "\n".join(previews)
        reply = QMessageBox.warning(
            self,
            "Confirm Coded Segment Deletion",
            (
                f"Saving this edit will delete {len(deleted_segment_ids)} coded "
                f"segment(s) whose selected text was removed.\n\n{details}\n\n"
                "Do you want to delete these coded segments and save?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def export_annotated(self):
        if self.current_document_id:
            export_annotated_document(
                self.project_id,
                self.current_document_id,
                self.doc_selector.currentText(),
                self,
            )
        else:
            QMessageBox.warning(
                self, "No Document Selected", "Please select a document to export."
            )

    def handle_document_switch(self, new_index):
        self.autosave_timer.stop()
        if self.editing_segment_id is not None:
            self.cancel_segment_edit()
        if self.is_dirty and self.current_document_id is not None:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Changes")
            msg_box.setText("You have unsaved changes. What would you like to do?")
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Save)
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_document(show_success_prompt=False):
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                id_to_display_text = {v: k for k, v in self.documents_map.items()}
                old_display_text = id_to_display_text.get(self.current_document_id)
                if old_display_text:
                    old_index = self.doc_selector.findText(old_display_text)
                    self.doc_selector.blockSignals(True)
                    self.doc_selector.setCurrentIndex(old_index)
                    self.doc_selector.blockSignals(False)
                return
        self.load_document_content()

    def load_document_content(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.autosave_timer.stop()
            self._loading_document = True
            try:
                self.text_edit.textChanged.disconnect(self.on_text_changed)
            except RuntimeError:
                pass
            if self._document_change_connected:
                try:
                    self.text_edit.document().contentsChange.disconnect(
                        self.on_document_contents_changed
                    )
                except RuntimeError:
                    pass
                self._document_change_connected = False
            self.text_edit.setDocument(QTextDocument(self))
            self.is_dirty = False
            self._pending_deleted_segments = {}
            self.save_button.setEnabled(False)
            selected_display_text = self.doc_selector.currentText()
            if not selected_display_text:
                self.current_document_id = None
                self.current_participant_id = None
                self._coded_segments_cache = []
                self.text_edit.setReadOnly(True)
                self.text_edit.clear()
                self.import_button.setStyleSheet(
                    "QPushButton { border: 2px solid #0078d7; }"
                )
                self.update_counts(0, 0)
            else:
                self.text_edit.setReadOnly(False)
                self.import_button.setStyleSheet("")
                self.text_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.current_document_id = self.documents_map[selected_display_text]
                content, participant_id = database.get_document_content(
                    self.current_document_id
                )
                self.current_participant_id = participant_id
                self.text_edit.setPlainText(content)
                self.apply_all_highlights()
                word_count = len(content.split())
                self.update_counts(word_count, len(self._coded_segments_cache))

            if self._pending_highlight:
                mode, start, end = self._pending_highlight
                if mode == "edit":
                    self._highlight_for_edit(start, end)
                elif mode == "view":
                    self._select_and_scroll(start, end)
                self._pending_highlight = None

            self.text_edit.textChanged.connect(self.on_text_changed)
            self.text_edit.document().contentsChange.connect(
                self.on_document_contents_changed
            )
            self._document_change_connected = True
            self.clear_find_status()
            self.update_match_count()
        finally:
            self._loading_document = False
            QApplication.restoreOverrideCursor()

    def _finish_excel_import(self, filename, result):
        QApplication.restoreOverrideCursor()
        docs_imported, errors = result
        if docs_imported > 0:
            self._record_excel_import_command()
        if docs_imported > 0:
            self.bulk_documents_added.emit()
        summary_message = (
            f"Successfully imported {docs_imported} document(s) from '{filename}'."
        )
        if errors:
            detailed_errors = "\n".join(errors[:5])
            if len(errors) > 5:
                detailed_errors += "\n(And more...)"
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Import Complete with Errors")
            error_dialog.setText(summary_message)
            error_dialog.setDetailedText(detailed_errors)
            error_dialog.exec()
        else:
            QMessageBox.information(self, "Import Complete", summary_message)

    def _handle_background_error(self, error_tuple):
        QApplication.restoreOverrideCursor()
        self._excel_import_before_ids = None
        _, error, _ = error_tuple
        QMessageBox.critical(self, "Error", str(error))

    def _record_excel_import_command(self):
        if self._excel_import_before_ids is None:
            return
        before_ids = self._excel_import_before_ids
        self._excel_import_before_ids = None
        after_ids = workspace_snapshot_repository.get_project_entity_ids(self.project_id)
        document_ids = sorted(after_ids["documents"] - before_ids["documents"])
        participant_ids = sorted(
            after_ids["participants"] - before_ids["participants"]
        )
        document_snapshots = [
            workspace_snapshot_repository.get_document_snapshot(document_id)
            for document_id in document_ids
        ]
        participant_snapshots = [
            workspace_snapshot_repository.get_participant_snapshot(participant_id)
            for participant_id in participant_ids
        ]
        document_snapshots = [snapshot for snapshot in document_snapshots if snapshot]
        participant_snapshots = [
            snapshot for snapshot in participant_snapshots if snapshot
        ]

        def do():
            for snapshot in participant_snapshots:
                workspace_snapshot_repository.restore_participant_snapshot(snapshot)
            for snapshot in document_snapshots:
                workspace_snapshot_repository.restore_document_snapshot(snapshot)

        def undo():
            for snapshot in reversed(document_snapshots):
                database.delete_document(snapshot["document"]["id"])
            for snapshot in reversed(participant_snapshots):
                database.delete_participant(snapshot["participant"]["id"])

        self.record_applied_command(
            WorkspaceCommand(
                "Import Excel Documents",
                do,
                undo,
                self.bulk_documents_added.emit,
            )
        )

    def apply_all_highlights(self):
        self.text_edit.blockSignals(True)
        original_position = self.text_edit.textCursor().position()
        try:
            if not self.current_document_id:
                self.text_edit.setExtraSelections([])
                self.segment_count_label.setText("Coded Segments: 0")
                return
            if not self.is_dirty:
                self._coded_segments_cache = database.get_coded_segments_for_document(
                    self.current_document_id
                )
            self.segment_count_label.setText(
                f"Coded Segments: {len(self._coded_segments_cache)}"
            )
            self._render_highlights()
        finally:
            cursor = self.text_edit.textCursor()
            cursor.setPosition(original_position)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.blockSignals(False)

    def _create_selection(self, start, end, color_hex, foreground_hex=None):
        selection = QTextEdit.ExtraSelection()
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        fmt = selection.format
        bg_color = QColor(color_hex)
        brightness = (
            bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114
        ) / 1000
        text_color = (
            QColor(foreground_hex)
            if foreground_hex
            else QColor("black") if brightness > 128 else QColor("white")
        )
        fmt.setBackground(bg_color)
        fmt.setForeground(text_color)
        return selection

    def _render_highlights(self, edit_range=None):
        selections = [
            self._create_selection(
                segment["segment_start"], segment["segment_end"], segment["node_color"]
            )
            for segment in self._coded_segments_cache
        ]
        selections.extend(self._create_find_match_selections())
        if edit_range is not None:
            selections.append(
                self._create_selection(
                    edit_range[0], edit_range[1], "#FFD700", foreground_hex="#000000"
                )
            )
        self.text_edit.setExtraSelections(selections)

    def _create_find_match_selections(self):
        if not self.find_bar.isVisible():
            return []
        search_text = self.find_input.text()
        if not search_text:
            return []

        selections = []
        content = self.text_edit.toPlainText()
        start = 0
        while True:
            position = content.find(search_text, start)
            if position == -1:
                break
            selections.append(
                self._create_selection(
                    position,
                    position + len(search_text),
                    self._find_match_color(),
                    foreground_hex="#000000",
                )
            )
            start = position + len(search_text)
        return selections

    def on_cursor_position_changed(self):
        pos = self.text_edit.textCursor().position()
        found_segment = None
        for segment in self._coded_segments_cache:
            if segment["segment_start"] <= pos < segment["segment_end"]:
                found_segment = segment
                break
        if found_segment:
            self.segment_clicked.emit(found_segment["id"])
            self.node_clicked_in_content.emit(found_segment["node_id"])
            if found_segment.get("participant_id"):
                self.participant_highlight_requested.emit(
                    found_segment["participant_id"]
                )

    def on_segment_coded(self):
        self.segments_changed.emit()

    def set_word_count(self, count):
        self.word_count_label.setText(
            get_translation("content_view.word_count", self.language, count=count)
        )

    def set_segment_count(self, count):
        self.segment_count_label.setText(
            get_translation(
                "content_view.coded_segments_count", self.language, count=count
            )
        )

    def update_counts(self, word_count, segment_count):
        self.word_count_label.setText(
            get_translation("content_view.word_count", self.language, count=word_count)
        )
        self.segment_count_label.setText(
            get_translation(
                "content_view.coded_segments_count", self.language, count=segment_count
            )
        )

    def update_language(self, new_language):
        self.language = new_language
        self.title_label.setText(get_translation("content_view.document_view", self.language))
        self.import_button.setToolTip(
            get_translation("content_view.import_tooltip", self.language)
        )
        self.import_action.setText(
            get_translation("content_view.import_tooltip", self.language)
        )
        self.undo_button.setToolTip(
            get_translation("content_view.undo_tooltip", self.language)
        )
        self.redo_button.setToolTip(
            get_translation("content_view.redo_tooltip", self.language)
        )
        self.find_button.setToolTip(
            get_translation("content_view.find_tooltip", self.language)
        )
        self.save_button.setToolTip(
            get_translation("content_view.save_tooltip", self.language)
        )
        self.delete_button.setToolTip(
            get_translation("content_view.delete_tooltip", self.language)
        )
        self.delete_document_action.setText(
            get_translation("content_view.delete_tooltip", self.language)
        )
        self.export_annotated_button.setToolTip(
            get_translation("content_view.export_annotated_tooltip", self.language)
        )
        self.export_annotated_action.setText(
            get_translation("content_view.export_annotated_tooltip", self.language)
        )
        self.document_menu_button.setToolTip(
            get_translation("content_view.document_actions_tooltip", self.language)
        )
        self.drop_text_label.setText(get_translation("content_view.drop_text", self.language))
        self.find_input.setPlaceholderText(
            get_translation("content_view.find_placeholder", self.language)
        )
        self.replace_input.setPlaceholderText(
            get_translation("content_view.replace_placeholder", self.language)
        )
        self.find_previous_button.setText(
            ""
        )
        self.find_previous_button.setToolTip(
            get_translation("content_view.find_previous", self.language)
        )
        self.find_next_button.setText(
            ""
        )
        self.find_next_button.setToolTip(
            get_translation("content_view.find_next", self.language)
        )
        self.replace_button.setText(
            get_translation("content_view.replace_one", self.language)
        )
        self.replace_all_button.setText(
            get_translation("content_view.replace_all", self.language)
        )
        self.find_close_button.setToolTip(
            get_translation("content_view.find_close", self.language)
        )
        self.edit_label.setText(get_translation("edit_bar.editing_segment", self.language))
        self.save_edit_button.setText(get_translation("edit_bar.save_changes", self.language))
        self.cancel_edit_button.setText(get_translation("edit_bar.cancel", self.language))
        self.update_counts(
            len(self.text_edit.toPlainText().split()),
            len(self._coded_segments_cache),
        )
        self.clear_find_status()
        self.update_match_count()

    def update_theme(self, theme):
        is_dark = theme == "Dark"
        fg = QColor("#f0f0f0" if is_dark else "#000000")
        disabled_fg = QColor("#a8a8a8" if is_dark else "#5e5e5e")
        for icon, button in (
            (self.import_icon, self.import_button),
            (self.undo_icon, self.undo_button),
            (self.redo_icon, self.redo_button),
            (self.find_icon, self.find_button),
            (self.find_previous_icon, self.find_previous_button),
            (self.find_next_icon, self.find_next_button),
            (self.save_icon, self.save_button),
            (self.export_annotated_icon, self.export_annotated_button),
            (self.delete_icon, self.delete_button),
            (self.document_menu_icon, self.document_menu_button),
        ):
            icon.set_color(fg, QIcon.Mode.Normal)
            icon.set_color(disabled_fg, QIcon.Mode.Disabled)
            button.setIcon(icon)
        self.import_action.setIcon(self.import_icon)
        self.export_annotated_action.setIcon(self.export_annotated_icon)
        self.delete_document_action.setIcon(self.delete_icon)
        self.find_close_icon.set_color(fg, QIcon.Mode.Normal)
        self.find_close_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.find_close_button.setIcon(self.find_close_icon)


class AssignParticipantDialog(QDialog):
    def __init__(self, participants, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Participant")
        self.participants = {p["name"]: p["id"] for p in participants}
        layout = QVBoxLayout(self)
        label = QLabel("Assign this document to which participant?")
        self.combo = FitPopupComboBox()
        self.combo.addItems(sorted(self.participants.keys()))
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(label)
        layout.addWidget(self.combo)
        layout.addWidget(button_box)

    def get_selected_participant_id(self):
        return self.participants.get(self.combo.currentText())
