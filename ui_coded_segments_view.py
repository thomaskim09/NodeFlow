from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QComboBox,
    QLabel,
)
import database


class CodedSegmentsView(QWidget):
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.current_document_id = None
        self.all_segments = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        header_label = QLabel("Coded Segments")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)

        main_layout.addWidget(header_label)

        controls_layout = QHBoxLayout()
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Current Document", "Entire Project"])
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter segments...")
        self.search_scope_combo = QComboBox()

        controls_layout.addWidget(QLabel("View:"))
        controls_layout.addWidget(self.scope_combo)
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.search_scope_combo)
        main_layout.addLayout(controls_layout)

        self.tree_widget = QTreeWidget()
        main_layout.addWidget(self.tree_widget)

        self.scope_combo.currentTextChanged.connect(self.reload_view)
        self.search_input.textChanged.connect(self.filter_tree)
        self.search_scope_combo.currentTextChanged.connect(self.filter_tree)

        self.scope_combo.setCurrentText("Entire Project")
        self.reload_view()

    def load_segments(self, document_id):
        """Called when the document changes in the main view."""
        self.search_input.clear()
        self.current_document_id = document_id
        if self.scope_combo.currentText() == "Current Document":
            self.reload_view()

    def reload_view(self):
        """Central method to reload the tree based on the selected scope."""
        self.tree_widget.clear()
        self.all_segments = []
        scope = self.scope_combo.currentText()

        if scope == "Current Document":
            self.tree_widget.setHeaderLabels(["Coded Text", "Node", "Participant"])
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                ["All", "Coded Text", "Node", "Participant"]
            )
            if self.current_document_id:
                self.all_segments = database.get_coded_segments_for_document(
                    self.current_document_id
                )

        elif scope == "Entire Project":
            self.tree_widget.setHeaderLabels(
                ["Coded Text", "Node", "Participant", "Document"]
            )
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.tree_widget.setColumnWidth(2, 150)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                ["All", "Coded Text", "Node", "Participant", "Document"]
            )
            self.all_segments = database.get_coded_segments_for_project(self.project_id)

        self.populate_tree(self.all_segments)

    def populate_tree(self, segments):
        self.tree_widget.clear()
        scope = self.scope_combo.currentText()
        for segment in segments:
            preview = segment["content_preview"]
            if len(preview) > 100:
                preview = preview[:100] + "..."

            if scope == "Current Document":
                item_data = [
                    preview,
                    segment["node_name"],
                    segment["participant_name"] or "N/A",
                ]
            else:
                item_data = [
                    preview,
                    segment["node_name"],
                    segment["participant_name"] or "N/A",
                    segment["document_title"],
                ]

            item = QTreeWidgetItem(self.tree_widget, item_data)
            item.setData(0, 1, segment["id"])

    def filter_tree(self):
        # ... (filter logic remains the same)
        search_text = self.search_input.text().lower()
        scope = self.search_scope_combo.currentText()
        view_scope = self.scope_combo.currentText()

        if not search_text:
            self.populate_tree(self.all_segments)
            return

        filtered_segments = []
        for seg in self.all_segments:
            text_match = search_text in seg["content_preview"].lower()
            node_match = search_text in seg["node_name"].lower()
            participant_match = (
                seg["participant_name"]
                and search_text in seg["participant_name"].lower()
            )

            doc_match = False
            if view_scope == "Entire Project" and "document_title" in seg.keys():
                doc_match = search_text in seg["document_title"].lower()

            should_add = False
            if scope == "All":
                if text_match or node_match or participant_match or doc_match:
                    should_add = True
            elif scope == "Coded Text" and text_match:
                should_add = True
            elif scope == "Node" and node_match:
                should_add = True
            elif scope == "Participant" and participant_match:
                should_add = True
            elif scope == "Document" and doc_match:
                should_add = True

            if should_add:
                filtered_segments.append(seg)
        self.populate_tree(filtered_segments)

    def filter_by_node_family(self, node_ids: list):
        """Filters segments to show a node and all its descendants."""
        self.search_input.clear()
        if not node_ids:  # Empty list means show all
            self.populate_tree(self.all_segments)
            return

        node_filtered_segments = [
            seg for seg in self.all_segments if seg["node_id"] in node_ids
        ]
        self.populate_tree(node_filtered_segments)

    def filter_by_single_node(self, node_id: int):
        """Filters segments to show only a single, specific node."""
        self.search_input.clear()
        if not node_id:
            self.populate_tree(self.all_segments)
            return

        node_filtered_segments = [
            seg for seg in self.all_segments if seg["node_id"] == node_id
        ]
        self.populate_tree(node_filtered_segments)
