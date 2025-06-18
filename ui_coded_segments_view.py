from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QGroupBox,
    QLineEdit,
    QHBoxLayout,
    QComboBox,
)
import database


class CodedSegmentsView(QWidget):
    def __init__(self):
        super().__init__()

        group_box = QGroupBox("Coded Segments")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter segments...")
        self.search_scope_combo = QComboBox()
        self.search_scope_combo.addItems(["All", "Coded Text", "Node", "Participant"])
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_scope_combo)
        group_box_layout.addLayout(search_layout)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Coded Text", "Node", "Participant"])
        self.tree_widget.setColumnWidth(0, 300)
        self.tree_widget.setColumnWidth(1, 150)
        group_box_layout.addWidget(self.tree_widget)

        self.search_input.textChanged.connect(self.filter_tree)
        self.search_scope_combo.currentTextChanged.connect(self.filter_tree)
        self.all_segments = []

    def load_segments(self, document_id):
        self.search_input.clear()
        if document_id is None:
            self.all_segments = []
            self.tree_widget.clear()
            return
        self.all_segments = database.get_coded_segments_for_document(document_id)
        self.populate_tree(self.all_segments)

    def populate_tree(self, segments):
        self.tree_widget.clear()
        for segment in segments:
            preview = segment["content_preview"]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            item = QTreeWidgetItem(
                self.tree_widget,
                [preview, segment["node_name"], segment["participant_name"] or "N/A"],
            )
            item.setData(0, 1, segment["id"])

    def filter_tree(self):
        search_text = self.search_input.text().lower()
        scope = self.search_scope_combo.currentText()

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

            if scope == "All" and (text_match or node_match or participant_match):
                filtered_segments.append(seg)
            elif scope == "Coded Text" and text_match:
                filtered_segments.append(seg)
            elif scope == "Node" and node_match:
                filtered_segments.append(seg)
            elif scope == "Participant" and participant_match:
                filtered_segments.append(seg)

        self.populate_tree(filtered_segments)

    def filter_by_node(self, node_id):
        self.search_input.clear()
        if not node_id:
            self.populate_tree(self.all_segments)
            return
        node_filtered_segments = [
            seg for seg in self.all_segments if seg["node_id"] == node_id
        ]
        self.populate_tree(node_filtered_segments)
