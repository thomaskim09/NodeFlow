from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QFrame,
    QMenu,
    QMessageBox,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ui_participant_manager import ParticipantManager
from ui_node_tree_manager import NodeTreeManager
from ui_content_view import ContentView
from ui_coded_segments_view import CodedSegmentsView
import export_manager
import database


class WorkspaceView(QWidget):
    def __init__(self, project_id, project_name):
        super().__init__()

        self.project_id = project_id
        self.project_name = project_name

        main_layout = QVBoxLayout(self)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panes
        self.left_pane = QFrame()
        self.left_pane_layout = QVBoxLayout(self.left_pane)
        self.center_pane = ContentView(self.project_id)
        self.bottom_pane = CodedSegmentsView()

        # Managers
        self.participant_manager = ParticipantManager(self.project_id)
        self.node_tree_manager = NodeTreeManager(self.project_id)
        self.left_pane_layout.addWidget(self.participant_manager)
        self.left_pane_layout.addWidget(self.node_tree_manager)

        # Export Button (no group box)
        export_button = QPushButton("Export Coded Data")
        export_button.setToolTip("Export the coded segments for the current document")
        export_menu = QMenu(self)
        self.action_export_word = export_menu.addAction("Export as Word (.docx)")
        self.action_export_json = export_menu.addAction("Export as JSON (.json)")
        export_button.setMenu(export_menu)

        # Add a spacer to push the export button to the bottom
        self.left_pane_layout.addStretch()
        self.left_pane_layout.addWidget(export_button)

        # Set stretch factors for the managers
        self.left_pane_layout.setStretchFactor(self.participant_manager, 2)
        self.left_pane_layout.setStretchFactor(self.node_tree_manager, 5)

        # Assemble Splitters
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.center_pane)
        right_splitter.addWidget(self.bottom_pane)
        right_splitter.setSizes([400, 200])

        main_splitter.addWidget(self.left_pane)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([350, 700])
        main_layout.addWidget(main_splitter)

        # Connect Signals
        self.center_pane.doc_selector.currentIndexChanged.connect(
            self.on_document_changed
        )
        self.center_pane.text_edit.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.center_pane.text_edit.customContextMenuRequested.connect(
            self.show_text_edit_context_menu
        )
        self.action_export_word.triggered.connect(self.export_as_word)
        self.action_export_json.triggered.connect(self.export_as_json)
        self.node_tree_manager.node_selected_signal.connect(
            self.bottom_pane.filter_by_node
        )
        # Connect signals for data updates
        self.participant_manager.participant_updated.connect(self.on_data_changed)
        self.node_tree_manager.node_updated.connect(self.on_data_changed)

    def on_data_changed(self):
        """A generic slot to refresh views when underlying data changes."""
        doc_id = self.center_pane.current_document_id
        # Reload doc list to update participant names in dropdown
        self.center_pane.load_document_list()
        # Reload segments to update node/participant names in the table
        self.bottom_pane.load_segments(doc_id)

    def export_as_word(self):
        doc_id = self.center_pane.current_document_id
        if not doc_id:
            QMessageBox.warning(
                self, "No Document", "Please select a document to export."
            )
            return
        export_manager.export_to_word(self.project_id, doc_id, self)

    def export_as_json(self):
        doc_id = self.center_pane.current_document_id
        if not doc_id:
            QMessageBox.warning(
                self, "No Document", "Please select a document to export."
            )
            return
        export_manager.export_to_json(self.project_id, doc_id, self)

    def on_document_changed(self):
        doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(doc_id)
        # Clear node selection filter when document changes
        self.node_tree_manager.tree_widget.clearSelection()

    def show_text_edit_context_menu(self, position):
        text_edit = self.center_pane.text_edit
        if not text_edit.textCursor().hasSelection():
            return
        menu = QMenu(text_edit)
        code_menu = menu.addMenu("Code selection with...")

        def populate_menu(parent_menu, parent_item):
            child_count = (
                parent_item.childCount()
                if parent_item
                else self.node_tree_manager.tree_widget.topLevelItemCount()
            )
            for i in range(child_count):
                child_item = (
                    parent_item.child(i)
                    if parent_item
                    else self.node_tree_manager.tree_widget.topLevelItem(i)
                )
                node_id = child_item.data(0, 1)
                full_node_name = child_item.text(0)
                clean_node_name = full_node_name.split(" ", 1)[-1]

                if child_item.childCount() > 0:
                    submenu = parent_menu.addMenu(full_node_name)
                    parent_action = QAction(f"Code with '{clean_node_name}'", self)
                    parent_action.triggered.connect(
                        lambda checked=False, n_id=node_id: self.code_selection(n_id)
                    )
                    submenu.addAction(parent_action)
                    submenu.addSeparator()
                    populate_menu(submenu, child_item)
                else:
                    action = QAction(full_node_name, self)
                    action.triggered.connect(
                        lambda checked=False, n_id=node_id: self.code_selection(n_id)
                    )
                    parent_menu.addAction(action)

        if self.node_tree_manager.tree_widget.topLevelItemCount() == 0:
            action = QAction("No nodes created", self)
            action.setEnabled(False)
            code_menu.addAction(action)
        else:
            populate_menu(code_menu, None)
        menu.exec(text_edit.viewport().mapToGlobal(position))

    def code_selection(self, node_id):
        cursor = self.center_pane.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        text = cursor.selectedText()
        doc_id = self.center_pane.current_document_id
        participant_id = self.center_pane.current_participant_id

        if not doc_id:
            return

        database.add_coded_segment(doc_id, node_id, participant_id, start, end, text)
        self.center_pane.highlight_text(start, end)
        self.bottom_pane.load_segments(doc_id)
