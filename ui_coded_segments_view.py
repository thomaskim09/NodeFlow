from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QGroupBox,
)

import database


class CodedSegmentsView(QWidget):
    def __init__(self):
        super().__init__()

        # --- Layouts and Widgets ---
        group_box = QGroupBox("Coded Segments")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Coded Text", "Node"])
        self.tree_widget.setColumnWidth(0, 300)  # Give more width to the text column

        # --- Assemble Layout ---
        group_box_layout.addWidget(self.tree_widget)

    def load_segments(self, document_id):
        """Loads all coded segments for a document into the tree view."""
        self.tree_widget.clear()
        if document_id is None:
            return

        segments = database.get_coded_segments_for_document(document_id)
        for segment in segments:
            # Shorten long text previews for display
            preview = segment["content_preview"]
            if len(preview) > 100:
                preview = preview[:100] + "..."

            item = QTreeWidgetItem(self.tree_widget, [preview, segment["node_name"]])
            item.setData(0, 1, segment["id"])  # Store segment ID
