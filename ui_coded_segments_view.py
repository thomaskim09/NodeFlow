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

        group_box = QGroupBox("Coded Segments")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        self.tree_widget = QTreeWidget()
        # Add "Participant" as a new column
        self.tree_widget.setHeaderLabels(["Coded Text", "Node", "Participant"])
        self.tree_widget.setColumnWidth(0, 300)
        self.tree_widget.setColumnWidth(1, 150)

        group_box_layout.addWidget(self.tree_widget)

    def load_segments(self, document_id):
        self.tree_widget.clear()
        if document_id is None:
            return

        segments = database.get_coded_segments_for_document(document_id)
        for segment in segments:
            preview = segment["content_preview"]
            if len(preview) > 100:
                preview = preview[:100] + "..."

            # Create the item with all three columns
            item = QTreeWidgetItem(
                self.tree_widget,
                [preview, segment["node_name"], segment["participant_name"] or "N/A"],
            )
            item.setData(0, 1, segment["id"])
