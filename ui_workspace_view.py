from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QFrame,
    QMenu,
    QMessageBox,  # Added for completeness
    QPushButton,  # Added for completeness
    QGroupBox,  # Added for completeness
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ui_participant_manager import ParticipantManager
from ui_node_tree_manager import NodeTreeManager
from ui_content_view import ContentView
from ui_coded_segments_view import CodedSegmentsView
import export_manager  # Added for completeness
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

        # Export Section
        export_group_box = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group_box)
        export_button = QPushButton("Export Coded Data...")
        export_layout.addWidget(export_button)
        self.left_pane_layout.addWidget(export_group_box)

        self.left_pane_layout.setStretch(0, 2)
        self.left_pane_layout.setStretch(1, 5)
        self.left_pane_layout.setStretch(2, 1)

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
        export_button.clicked.connect(self.show_export_options)

    def show_export_options(self):
        doc_id = self.center_pane.current_document_id
        if not doc_id:
            QMessageBox.warning(
                self, "No Document", "Please select a document to export."
            )
            return
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Choose Export Format")
        msg_box.setText("Which format would you like to export to?")
        word_button = msg_box.addButton(
            "Word (.docx)", QMessageBox.ButtonRole.ActionRole
        )
        json_button = msg_box.addButton(
            "JSON (.json)", QMessageBox.ButtonRole.ActionRole
        )
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        if clicked_button == word_button:
            export_manager.export_to_word(self.project_id, doc_id, self)
        elif clicked_button == json_button:
            export_manager.export_to_json(self.project_id, doc_id, self)

    def on_document_changed(self):
        doc_id = self.center_pane.current_document_id
        self.bottom_pane.load_segments(doc_id)

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
                node_name = child_item.text(0)
                if child_item.childCount() > 0:
                    submenu = parent_menu.addMenu(node_name)
                    populate_menu(submenu, child_item)
                else:
                    action = QAction(node_name, self)
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
        """The final step: save the coded segment to the database."""
        cursor = self.center_pane.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        text = cursor.selectedText()

        doc_id = self.center_pane.current_document_id
        participant_id = (
            self.center_pane.current_participant_id
        )  # Get the participant ID

        if not doc_id:
            return

        # --- THIS IS THE FIX ---
        # We now pass all 6 required arguments to the database function.
        database.add_coded_segment(doc_id, node_id, participant_id, start, end, text)

        # Refresh views
        self.center_pane.highlight_text(start, end)
        self.bottom_pane.load_segments(doc_id)
