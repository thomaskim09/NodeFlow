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
from utils.common import get_translation


class CrosstabWidget(QWidget):
    """A widget to display a cross-tabulation/co-occurrence matrix."""

    def __init__(self, theme_settings, parent=None, language=None):
        super().__init__(parent)
        self.settings = theme_settings
        self.language = language or self.settings.get("language", "English")
        self.theme = self.settings.get("theme", "Default")
        self._last_segments = []
        self._last_nodes = []
        layout = QVBoxLayout(self)
        self.intro_label = QLabel(get_translation("crosstab.intro", self.language))
        layout.addWidget(self.intro_label)
        self.table = QTableWidget()
        self.table.setObjectName("dashboardCrosstabTable")
        layout.addWidget(self.table)
        self._apply_table_theme()

    def update_crosstab(self, segments, nodes):
        """Public method to calculate and populate the crosstab table."""
        self._last_segments = list(segments)
        self._last_nodes = list(nodes)
        node_map = {n["id"]: n["name"] for n in nodes}
        node_ids = sorted(node_map.keys())
        node_id_to_index = {node_id: i for i, node_id in enumerate(node_ids)}
        matrix_size = len(node_ids)
        matrix = [[0] * matrix_size for _ in range(matrix_size)]

        segments_by_doc = defaultdict(list)
        for seg in segments:
            segments_by_doc[seg["document_id"]].append(seg)

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

    def _is_dark(self):
        return self.theme == "Dark"

    def _populate_table(self, matrix, node_ids, node_map):
        matrix_size = len(node_ids)
        self._reset_table_state()
        self.table.clear()
        self.table.setRowCount(matrix_size)
        self.table.setColumnCount(matrix_size)
        header_labels = [node_map[nid] for nid in node_ids]
        self.table.setHorizontalHeaderLabels(header_labels)
        self.table.setVerticalHeaderLabels(header_labels)

        is_dark = self._is_dark()
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

    def _apply_table_theme(self):
        if self._is_dark():
            self.table.setStyleSheet(
                "QTableWidget { background-color: #2e2e2e; color: #f0f0f0; gridline-color: #4a4a4a; }"
            )
        else:
            self.table.setStyleSheet(
                "QTableWidget { background-color: #ffffff; color: #333333; gridline-color: #d0d0d0; }"
            )

    def set_theme(self, theme: str):
        self.theme = theme
        self._apply_table_theme()
        if self._last_nodes:
            self.update_crosstab(self._last_segments, self._last_nodes)

    def get_table_for_export(self):
        """Returns the table widget for the main view to export."""
        return self.table

    def clear_crosstab(self):
        """Clears the crosstab table."""
        self._reset_table_state()
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

    def _reset_table_state(self):
        # Avoid stale accessibility/current-index references while table size changes.
        self.table.clearSelection()
        self.table.setCurrentItem(None)
        self.table.setCurrentCell(-1, -1)

    def update_language(self, new_language):
        self.language = new_language
        self.intro_label.setText(get_translation("crosstab.intro", self.language))
