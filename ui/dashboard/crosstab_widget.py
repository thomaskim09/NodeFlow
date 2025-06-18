# Create this new file at: ui/dashboard/crosstab_widget.py

import itertools
from collections import defaultdict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class CrosstabWidget(QWidget):
    """A widget to display a cross-tabulation/co-occurrence matrix."""

    def __init__(self, theme_settings, parent=None):
        super().__init__(parent)
        self.settings = theme_settings

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "This table shows how many times two codes were applied to overlapping text segments."
            )
        )
        self.table = QTableWidget()
        layout.addWidget(self.table)

    def update_crosstab(self, segments, nodes):
        """Public method to calculate and populate the crosstab table."""
        node_map = {n["id"]: n["name"] for n in nodes}
        node_ids = sorted(node_map.keys())
        node_id_to_index = {node_id: i for i, node_id in enumerate(node_ids)}
        matrix_size = len(node_ids)
        matrix = [[0] * matrix_size for _ in range(matrix_size)]

        segments_by_doc = defaultdict(list)
        for seg in segments:
            segments_by_doc[seg["document_title"]].append(seg)

        for doc_segs in segments_by_doc.values():
            for seg1, seg2 in itertools.combinations(doc_segs, 2):
                if (
                    seg1["segment_start"] < seg2["segment_end"]
                    and seg2["segment_start"] < seg1["segment_end"]
                ) and seg1["node_id"] != seg2["node_id"]:

                    idx1 = node_id_to_index.get(seg1["node_id"])
                    idx2 = node_id_to_index.get(seg2["node_id"])
                    if idx1 is not None and idx2 is not None:
                        matrix[idx1][idx2] += 1
                        matrix[idx2][idx1] += 1

        self._populate_table(matrix, node_ids, node_map)

    def _populate_table(self, matrix, node_ids, node_map):
        matrix_size = len(node_ids)
        self.table.clear()
        self.table.setRowCount(matrix_size)
        self.table.setColumnCount(matrix_size)
        header_labels = [node_map[nid] for nid in node_ids]
        self.table.setHorizontalHeaderLabels(header_labels)
        self.table.setVerticalHeaderLabels(header_labels)

        is_dark = self.settings.get("theme") == "Dark"
        base_bg = QColor("#2E2E2E") if is_dark else QColor("white")
        text_color = QColor("white") if is_dark else QColor("black")

        for r in range(matrix_size):
            for c in range(matrix_size):
                count = matrix[r][c]
                item = QTableWidgetItem(str(count))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(text_color)
                if r == c:
                    item.setBackground(QColor("#555") if is_dark else QColor("#EFEFEF"))
                elif count > 0:
                    intensity = min(200, 20 + count * 20)
                    color = (
                        QColor(40, intensity, 40)
                        if is_dark
                        else QColor(255 - intensity, 255, 255 - intensity)
                    )
                    item.setBackground(color)
                else:
                    item.setBackground(base_bg)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def get_table_for_export(self):
        """Returns the table widget for the main view to export."""
        return self.table
