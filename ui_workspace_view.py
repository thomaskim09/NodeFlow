from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QFrame, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ui_participant_manager import ParticipantManager
from ui_node_tree_manager import NodeTreeManager
from ui_content_view import ContentView  # <-- 1. IMPORT
from ui_coded_segments_view import CodedSegmentsView  # <-- 1. IMPORT

import database


class WorkspaceView(QWidget):
    def __init__(self, project_id, project_name):
        super().__init__()

        self.project_id = project_id
        self.project_name = project_name

        main_layout = QVBoxLayout(self)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Panes ---
        self.left_pane = QFrame()
        self.left_pane_layout = QVBoxLayout(self.left_pane)

        # --- Center and Bottom Panes ---
        self.center_pane = ContentView(self.project_id)  # <-- 2. Use new class
        self.bottom_pane = CodedSegmentsView()  # <-- 2. Use new class

        # --- Add Managers to Left Pane ---
        self.participant_manager = ParticipantManager(self.project_id)
        self.node_tree_manager = NodeTreeManager(self.project_id)
        self.left_pane_layout.addWidget(self.participant_manager)
        self.left_pane_layout.addWidget(self.node_tree_manager)
        self.left_pane_layout.setStretch(0, 1)
        self.left_pane_layout.setStretch(1, 3)

        # --- Assemble Splitters ---
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.center_pane)
        right_splitter.addWidget(self.bottom_pane)
        right_splitter.setSizes([400, 200])

        main_splitter.addWidget(self.left_pane)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([350, 700])

        main_layout.addWidget(main_splitter)

        # --- 3. Connect Component Signals ---
        # When the document changes in ContentView, update CodedSegmentsView
        self.center_pane.doc_selector.currentIndexChanged.connect(
            self.on_document_changed
        )

        # Set up the custom context menu for the text editor
        self.center_pane.text_edit.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.center_pane.text_edit.customContextMenuRequested.connect(
            self.show_text_edit_context_menu
        )

    def on_document_changed(self):
        """Callback to update other views when the document changes."""
        doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(doc_id)

    def show_text_edit_context_menu(self, position):
        """Creates and shows the right-click menu on the text editor."""
        cursor = self.center_pane.text_edit.cursorForPosition(position)
        if not cursor.hasSelection():
            return  # Don't show menu if no text is selected

        menu = QMenu()
        code_menu = menu.addMenu("Code selection with...")

        # Dynamically build the submenu from the Node Tree
        def build_node_submenu(parent_menu, parent_tree_item):
            for i in range(parent_tree_item.childCount()):
                child_item = parent_tree_item.child(i)
                node_id = child_item.data(0, 1)
                node_name = child_item.text(0)

                action = QAction(node_name, self)
                action.triggered.connect(
                    lambda checked=False, n_id=node_id: self.code_selection(n_id)
                )

                if child_item.childCount() > 0:
                    submenu = parent_menu.addMenu(node_name)
                    build_node_submenu(submenu, child_item)
                else:
                    parent_menu.addAction(action)

        # Populate with top-level items
        for i in range(self.node_tree_manager.tree_widget.topLevelItemCount()):
            build_node_submenu(
                code_menu, self.node_tree_manager.tree_widget.topLevelItem(i)
            )

        # The globalpos() maps the widget's position to the screen's position
        menu.exec(self.center_pane.text_edit.viewport().mapToGlobal(position))

    def code_selection(self, node_id):
        """The final step: save the coded segment to the database."""
        cursor = self.center_pane.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        text = cursor.selectedText()

        doc_id = self.center_pane.current_document_id
        if not doc_id:
            return

        database.add_coded_segment(doc_id, node_id, start, end, text)
        print(f"Coded '{text[:20]}...' with node ID {node_id}")

        # Refresh views
        self.center_pane.highlight_text(start, end)
        self.bottom_pane.load_segments(doc_id)
