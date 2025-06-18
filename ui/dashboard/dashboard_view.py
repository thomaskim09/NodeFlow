# Replace the contents of ui/dashboard/dashboard_view.py

import csv
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QSizePolicy,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QWidget,
    QComboBox,
    QMenu,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QIcon

# Updated import
from managers.theme_manager import load_settings

# The rest of the imports are unchanged.
# ...

# The class definition for DashboardView has been updated to import from managers,
# but otherwise its logic from the last step remains the same.
# The full, correct code is provided below for completeness.
from .charts_widget import ChartsWidget
from .crosstab_widget import CrosstabWidget
import database


class DashboardView(QDialog):
    def __init__(self, project_id, project_name, current_document_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.initial_document_id = current_document_id
        self.setWindowTitle(f"Dashboard: {project_name}")
        self.setMinimumSize(1100, 800)
        self.docs = database.get_documents_for_project(self.project_id)
        self.participants = database.get_participants_for_project(self.project_id)
        self.settings = load_settings()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 10)
        top_layout = QHBoxLayout()
        overview_layout = QHBoxLayout()
        controls_layout = QVBoxLayout()
        self.total_words_label = self._create_stat_label("Scope Words\nN/A")
        self.coded_segments_label = self._create_stat_label("Coded Segments\nN/A")
        self.coded_words_label = self._create_stat_label("Coded Words\nN/A")
        overview_layout.addWidget(self.total_words_label)
        overview_layout.addWidget(self.coded_segments_label)
        overview_layout.addWidget(self.coded_words_label)
        doc_scope_layout = QHBoxLayout()
        doc_scope_layout.addWidget(QLabel("Document Scope:"))
        self.doc_scope_combo = QComboBox()
        self.doc_scope_combo.addItem("Project Total", -1)
        for doc in self.docs:
            self.doc_scope_combo.addItem(doc["title"], doc["id"])
        self.doc_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)
        doc_scope_layout.addWidget(self.doc_scope_combo)
        part_scope_layout = QHBoxLayout()
        part_scope_layout.addWidget(QLabel("Participant Scope:"))
        self.part_scope_combo = QComboBox()
        self.part_scope_combo.addItem("All Participants", -1)
        for p in self.participants:
            self.part_scope_combo.addItem(p["name"], p["id"])
        self.part_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)
        part_scope_layout.addWidget(self.part_scope_combo)
        self.export_button = QPushButton("Export...")
        export_menu = QMenu(self)
        export_menu.addAction("Export Chart as Image", self.export_chart_as_image)
        export_menu.addAction("Export Data Table as CSV", self.export_data_as_csv)
        export_menu.addAction("Export Cross-Tab as CSV", self.export_crosstab_as_csv)
        self.export_button.setMenu(export_menu)
        controls_layout.addLayout(doc_scope_layout)
        controls_layout.addLayout(part_scope_layout)
        controls_layout.addWidget(self.export_button, 0, Qt.AlignmentFlag.AlignBottom)
        top_layout.addLayout(overview_layout, 3)
        top_layout.addLayout(controls_layout, 1)
        main_layout.addLayout(top_layout)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        breakdown_tab = QWidget()
        breakdown_layout = QVBoxLayout(breakdown_tab)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(
            ["Code", "Coded Words", "% of Total", "Segments"]
        )
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        breakdown_layout.addWidget(self.tree_widget)
        self.tabs.addTab(breakdown_tab, "Code Breakdown")
        self.charts_widget = ChartsWidget(self.settings)
        self.tabs.addTab(self.charts_widget, "Charts")
        self.crosstab_widget = CrosstabWidget(self.settings)
        self.tabs.addTab(self.crosstab_widget, "Cross-Tabulation")
        if self.initial_document_id:
            index = self.doc_scope_combo.findData(self.initial_document_id)
            if index != -1:
                self.doc_scope_combo.setCurrentIndex(index)
        else:
            self.load_dashboard_data()

    def export_chart_as_image(self):
        if self.tabs.currentIndex() != 1:
            QMessageBox.warning(
                self,
                "Not on Charts Tab",
                "Please switch to the 'Charts' tab to export an image.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Chart", "", "PNG Image (*.png)"
        )
        if path:
            self.tabs.widget(1).grab().save(path)

    def export_data_as_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Data Table", "", "CSV File (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [self.tree_widget.headerItem().text(i) for i in range(4)]
                )

                def write_item(item):
                    writer.writerow([item.text(i).strip() for i in range(4)])
                    for i in range(item.childCount()):
                        write_item(item.child(i))

                for i in range(self.tree_widget.topLevelItemCount()):
                    write_item(self.tree_widget.topLevelItem(i))
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred: {e}")

    def export_crosstab_as_csv(self):
        if self.tabs.currentIndex() != 2:
            QMessageBox.warning(
                self,
                "Not on Crosstab Tab",
                "Please switch to the 'Cross-Tabulation' tab to export.",
            )
            return
        table = self.crosstab_widget.get_table_for_export()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Cross-Tabulation Data", "", "CSV File (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [""] + [
                    table.horizontalHeaderItem(i).text()
                    for i in range(table.columnCount())
                ]
                writer.writerow(headers)
                for r in range(table.rowCount()):
                    row_data = [table.verticalHeaderItem(r).text()] + [
                        table.item(r, c).text() for c in range(table.columnCount())
                    ]
                    writer.writerow(row_data)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred: {e}")

    def _create_stat_label(self, text):
        label = QLabel(text)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("padding: 2px; font-weight: bold;")
        return label

    def load_dashboard_data(self):
        doc_id, part_id = (
            self.doc_scope_combo.currentData(),
            self.part_scope_combo.currentData(),
        )
        total_words, segments = self._get_scoped_data(doc_id, part_id)
        nodes = database.get_nodes_for_project(self.project_id)
        self.total_words_label.setText(f"Scope Words\n{total_words:,}")
        self.coded_segments_label.setText(f"Coded Segments\n{len(segments):,}")
        node_stats, coded_words = self._calculate_direct_stats(segments)
        coded_percentage = (coded_words / total_words * 100) if total_words > 0 else 0
        self.coded_words_label.setText(
            f"Coded Words\n{coded_words:,} ({coded_percentage:.1f}%)"
        )
        nodes_map, nodes_by_parent = self._build_node_hierarchy(nodes)
        aggregated_stats = self._calculate_aggregated_stats(nodes_by_parent, node_stats)
        self.tree_widget.clear()
        root_nodes_data = self._populate_tree_widget(
            nodes_by_parent, nodes_map, aggregated_stats, total_words
        )
        self.tree_widget.expandAll()
        self.charts_widget.update_charts(root_nodes_data)
        self.crosstab_widget.update_crosstab(segments, nodes)

    def _get_scoped_data(self, doc_id, part_id):
        if doc_id != -1:
            total_words, segments = database.get_document_word_count(
                doc_id
            ), database.get_coded_segments_for_document(doc_id)
            if part_id != -1:
                segments = [
                    s
                    for s in segments
                    if s["participant_name"] == self.part_scope_combo.currentText()
                ]
        elif part_id != -1:
            total_words, segments = database.get_word_count_for_participant(
                self.project_id, part_id
            ), database.get_coded_segments_for_participant(self.project_id, part_id)
        else:
            total_words, segments = database.get_project_word_count(
                self.project_id
            ), database.get_coded_segments_for_project(self.project_id)
        return total_words, segments

    def _calculate_direct_stats(self, segments):
        node_stats, total_coded_words = {}, 0
        for seg in segments:
            node_stats.setdefault(seg["node_id"], {"word_count": 0, "segment_count": 0})
            word_count = len(seg["content_preview"].split())
            node_stats[seg["node_id"]]["segment_count"] += 1
            node_stats[seg["node_id"]]["word_count"] += word_count
            total_coded_words += word_count
        return node_stats, total_coded_words

    def _build_node_hierarchy(self, nodes):
        nodes_map = {n["id"]: n for n in nodes}
        nodes_by_parent = {n["id"]: [] for n in nodes}
        nodes_by_parent[None] = []
        for node in nodes:
            nodes_by_parent.setdefault(node["parent_id"], []).append(node)
        for L in nodes_by_parent.values():
            L.sort(key=lambda x: x["position"])
        return nodes_map, nodes_by_parent

    def _calculate_aggregated_stats(self, nodes_by_parent, node_stats):
        agg_stats = {}

        def recurse(p_id):
            p_wc, p_sc = 0, 0
            for node in nodes_by_parent.get(p_id, []):
                c_wc, c_sc = recurse(node["id"])
                d_stats = node_stats.get(node["id"], {})
                t_wc, t_sc = (
                    d_stats.get("word_count", 0) + c_wc,
                    d_stats.get("segment_count", 0) + c_sc,
                )
                agg_stats[node["id"]] = {"word_count": t_wc, "segment_count": t_sc}
                p_wc, p_sc = p_wc + t_wc, p_sc + t_sc
            return p_wc, p_sc

        recurse(None)
        return agg_stats

    def _populate_tree_widget(self, nodes_by_parent, nodes_map, agg_stats, total_words):
        root_nodes_data = []

        def recurse(p_item, p_id, prefix=""):
            for i, node_data in enumerate(nodes_by_parent.get(p_id, [])):
                stats = agg_stats.get(node_data["id"], {})
                wc, sc = stats.get("word_count", 0), stats.get("segment_count", 0)
                p = (wc / total_words * 100) if total_words > 0 else 0
                item = QTreeWidgetItem(p_item)
                pixmap = QPixmap(16, 16)
                pixmap.fill(QColor(nodes_map[node_data["id"]]["color"]))
                item.setIcon(0, QIcon(pixmap))
                item.setText(0, f" {prefix}{i + 1}. {node_data['name']}")
                item.setText(1, f"{wc:,}")
                item.setText(2, f"{p:.1f}%")
                item.setText(3, f"{sc:,}")
                for col in [1, 2, 3]:
                    item.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)
                if p_id is None:
                    root_nodes_data.append((node_data["name"], p, wc, sc))
                recurse(item, node_data["id"], f"{prefix}{i + 1}.")

        recurse(self.tree_widget.invisibleRootItem(), None)
        return root_nodes_data
