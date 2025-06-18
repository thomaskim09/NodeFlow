# Replace the contents of ui/workspace/coded_segments_view.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QMessageBox,
    QTreeWidgetItemIterator,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
import database


class DeletableTreeWidget(QTreeWidget):
    """A QTreeWidget that handles the Delete key to remove a segment."""

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            current_item = self.currentItem()
            if current_item:
                segment_id = current_item.data(0, 1)
                preview = current_item.text(0)
                if segment_id is not None:
                    self.parent_view.confirm_delete_segment(segment_id, preview)
                    event.accept()
                    return
        super().keyPressEvent(event)


class CodedSegmentsView(QWidget):
    segment_deleted = Signal()

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.current_document_id = None
        self.all_segments = []
        self._last_active_node_filter = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        controls_layout = QHBoxLayout()
        header_label = QLabel("Coded Segments")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Current Document", "Entire Project"])
        self.scope_combo.setToolTip(
            "View coded segments in the current document or the entire project"
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter segments...")

        self.search_scope_combo = QComboBox()
        self.search_scope_combo.setToolTip("Filter segments by the selected field")

        controls_layout.addWidget(header_label)
        controls_layout.addWidget(self.scope_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.search_scope_combo)
        main_layout.addLayout(controls_layout)

        self.tree_widget = DeletableTreeWidget(self)
        main_layout.addWidget(self.tree_widget)

        self.scope_combo.currentTextChanged.connect(self.reload_view)
        self.search_input.textChanged.connect(self.filter_tree)
        self.search_scope_combo.currentTextChanged.connect(self.filter_tree)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

        self.scope_combo.setCurrentText("Current Document")
        self.reload_view()

    def select_segment_by_id(self, segment_id):
        if not segment_id:
            return

        self.tree_widget.blockSignals(True)
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            if item.data(0, 1) == segment_id:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                break
            it += 1
        self.tree_widget.blockSignals(False)

    def on_selection_changed(self, current, previous):
        if previous:
            self.tree_widget.setItemWidget(
                previous, self.tree_widget.columnCount() - 1, None
            )

        if current:
            segment_id = current.data(0, 1)
            preview = current.text(0)

            delete_button = QPushButton("🗑️")
            delete_button.setFixedSize(20, 20)
            delete_button.setToolTip("Delete this coded segment (Delete)")
            delete_button.clicked.connect(
                lambda: self.confirm_delete_segment(segment_id, preview)
            )

            button_container = QWidget()
            button_container.setFixedHeight(20)
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(0)
            button_layout.addStretch()
            button_layout.addWidget(delete_button)
            button_layout.addStretch()

            self.tree_widget.setItemWidget(
                current, self.tree_widget.columnCount() - 1, button_container
            )

    def confirm_delete_segment(self, segment_id, segment_preview):
        current_item = self.tree_widget.currentItem()
        if not current_item or current_item.data(0, 1) != segment_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this coded segment?\n\n'{segment_preview}'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_coded_segment(segment_id)
            self.all_segments = [s for s in self.all_segments if s["id"] != segment_id]
            (current_item.parent() or self.tree_widget.invisibleRootItem()).removeChild(
                current_item
            )
            self.segment_deleted.emit()

    def load_segments(self, document_id):
        self.search_input.clear()
        self.current_document_id = document_id
        if self.scope_combo.currentText() == "Current Document":
            self.reload_view()

    def reload_view(self):
        # --- FIXED: Suppress RuntimeWarning ---
        try:
            self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass

        self.tree_widget.clear()
        self.all_segments = []
        scope = self.scope_combo.currentText()

        if scope == "Current Document":
            headers = ["Coded Text", "Node", "Participant", ""]
            self.tree_widget.setHeaderLabels(headers)
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.tree_widget.setColumnWidth(2, 150)
            self.tree_widget.setColumnWidth(3, 50)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                ["All", "Coded Text", "Node", "Participant"]
            )
            if self.current_document_id:
                self.all_segments = database.get_coded_segments_for_document(
                    self.current_document_id
                )
        elif scope == "Entire Project":
            headers = ["Coded Text", "Node", "Participant", "Document", ""]
            self.tree_widget.setHeaderLabels(headers)
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.tree_widget.setColumnWidth(2, 150)
            self.tree_widget.setColumnWidth(3, 200)
            self.tree_widget.setColumnWidth(4, 50)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                ["All", "Coded Text", "Node", "Participant", "Document"]
            )
            self.all_segments = database.get_coded_segments_for_project(self.project_id)

        self.populate_tree(self.all_segments)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

        if self._last_active_node_filter is not None:
            self.filter_by_node_family(self._last_active_node_filter)
        else:
            self.filter_tree()

    def populate_tree(self, segments):
        scope = self.scope_combo.currentText()
        for segment in segments:
            # --- FIXED: Remove leading/trailing spaces ---
            preview = segment["content_preview"].strip()
            if len(preview) > 100:
                preview = preview[:100] + "..."

            item_data = [
                preview,
                segment["node_name"],
                segment["participant_name"] or "N/A",
            ]
            if scope == "Entire Project":
                item_data.append(segment["document_title"])

            item = QTreeWidgetItem(self.tree_widget, item_data)
            item.setData(0, 1, segment["id"])

    def filter_tree(self):
        self._last_active_node_filter = None
        search_text = self.search_input.text().lower()
        scope = self.search_scope_combo.currentText()
        view_scope = self.scope_combo.currentText()

        # --- FIXED: Suppress RuntimeWarning ---
        try:
            self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass

        self.tree_widget.clear()

        if not search_text:
            self.populate_tree(self.all_segments)
        else:
            filtered_segments = [
                seg
                for seg in self.all_segments
                if self._segment_matches_filter(seg, search_text, scope, view_scope)
            ]
            self.populate_tree(filtered_segments)

        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

    def _segment_matches_filter(self, seg, search_text, scope, view_scope):
        text_match = search_text in seg["content_preview"].lower()
        node_match = search_text in seg["node_name"].lower()
        participant_match = (
            seg["participant_name"] and search_text in seg["participant_name"].lower()
        )
        doc_match = (
            view_scope == "Entire Project"
            and "document_title" in seg
            and search_text in seg["document_title"].lower()
        )

        if scope == "All":
            return text_match or node_match or participant_match or doc_match
        elif scope == "Coded Text":
            return text_match
        elif scope == "Node":
            return node_match
        elif scope == "Participant":
            return participant_match
        elif scope == "Document":
            return doc_match
        return False

    def filter_by_node_family(self, node_ids: list):
        self.search_input.clear()
        self._last_active_node_filter = node_ids

        # --- FIXED: Suppress RuntimeWarning ---
        try:
            self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass

        self.tree_widget.clear()

        if not node_ids:
            self.populate_tree(self.all_segments)
        else:
            node_filtered_segments = [
                seg for seg in self.all_segments if seg["node_id"] in node_ids
            ]
            self.populate_tree(node_filtered_segments)

        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

    def filter_by_single_node(self, node_id: int):
        self.search_input.clear()
        self._last_active_node_filter = [node_id]

        # --- FIXED: Suppress RuntimeWarning ---
        try:
            self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass

        self.tree_widget.clear()

        if not node_id:
            self.populate_tree(self.all_segments)
        else:
            node_filtered_segments = [
                seg for seg in self.all_segments if seg["node_id"] == node_id
            ]
            self.populate_tree(node_filtered_segments)

        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)
