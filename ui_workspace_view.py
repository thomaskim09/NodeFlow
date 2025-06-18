from PySide6.QtWidgets import (
    QWidget,
    QSplitter,
    QVBoxLayout,
    QFrame,
    QMenu,
    QPushButton,
    QApplication,
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

        # --- Connect Signals ---
        self.center_pane.doc_selector.currentIndexChanged.connect(
            self.on_document_changed
        )
        self.center_pane.text_edit.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.center_pane.text_edit.customContextMenuRequested.connect(
            self.show_text_edit_context_menu
        )

        self.action_export_json.triggered.connect(self.export_as_json)
        self.action_export_word.triggered.connect(self.export_as_word)
        self.action_export_excel.triggered.connect(self.export_as_excel)

        # Connect the NEW filter signals
        self.node_tree_manager.filter_by_node_family_signal.connect(
            self.bottom_pane.filter_by_node_family
        )
        self.node_tree_manager.filter_by_single_node_signal.connect(
            self.bottom_pane.filter_by_single_node
        )

        self.participant_manager.participant_updated.connect(self.on_data_changed)
        self.node_tree_manager.node_updated.connect(self.on_data_changed)

    def on_data_changed(self):
        self.center_pane.load_document_list()
        self.bottom_pane.reload_view()

    def export_as_word(self):
        export_manager.export_to_word(self.project_id, self)

    def export_as_json(self):
        export_manager.export_to_json(self.project_id, self)

    def export_as_excel(self):
        export_manager.export_to_excel(self.project_id, self)

    def on_document_changed(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc_id = self.center_pane.current_document_id
            self.bottom_pane.load_segments(doc_id)
            self.node_tree_manager.tree_widget.clearSelection()
        finally:
            QApplication.restoreOverrideCursor()

    def show_text_edit_context_menu(self, position):
        text_edit = self.center_pane.text_edit
        if not text_edit.textCursor().hasSelection():
            return
        menu = QMenu(text_edit)
        code_menu = menu.addMenu("Code selection with...")

        nodes_by_parent = self.node_tree_manager.nodes_by_parent

        def populate_menu(parent_menu, parent_id, prefix=""):
            children = nodes_by_parent.get(parent_id, [])
            for i, node_data in enumerate(children):
                current_prefix = f"{prefix}{i + 1}."
                full_node_name = f"{current_prefix} {node_data['name']}"

                child_nodes = nodes_by_parent.get(node_data["id"], [])
                if child_nodes:
                    submenu = parent_menu.addMenu(full_node_name)
                    parent_action = QAction(f"Code with '{node_data['name']}'", self)
                    parent_action.triggered.connect(
                        lambda checked=False, n_id=node_data["id"]: self.code_selection(
                            n_id
                        )
                    )
                    submenu.addAction(parent_action)
                    submenu.addSeparator()
                    populate_menu(submenu, node_data["id"], current_prefix)
                else:
                    action = QAction(full_node_name, self)
                    action.triggered.connect(
                        lambda checked=False, n_id=node_data["id"]: self.code_selection(
                            n_id
                        )
                    )
                    parent_menu.addAction(action)

        if not self.node_tree_manager.nodes_map:
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
        self.bottom_pane.reload_view()
