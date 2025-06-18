# In file: ui/dashboard/dashboard_view.py

import csv
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QWidget,
    QComboBox,
    QMenu,
    QHeaderView,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QIcon

from managers.theme_manager import load_settings
from .charts_widget import ChartsWidget
from .crosstab_widget import CrosstabWidget
from .wordcloud_widget import WordCloudWidget  # Import the new widget
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
        self.is_dark = self.settings.get("theme") == "Dark"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_layout = QHBoxLayout()

        stats_container = QFrame()
        stats_container.setObjectName("statsContainer")
        container_bg = "#2e3440" if self.is_dark else "#f2f2f2"
        stats_container.setStyleSheet(
            f"#statsContainer {{ background-color: {container_bg}; border-radius: 8px; }}"
        )

        overview_layout = QHBoxLayout(stats_container)
        overview_layout.setContentsMargins(15, 15, 15, 15)
        overview_layout.setSpacing(15)

        self.total_words_label = self._create_stat_label("Scope Words")
        self.coded_segments_label = self._create_stat_label("Coded Segments")
        self.coded_words_label = self._create_stat_label("Coded Words")

        overview_layout.addWidget(self.total_words_label)
        overview_layout.addWidget(self.coded_segments_label)
        overview_layout.addWidget(self.coded_words_label)

        controls_layout = QVBoxLayout()
        doc_scope_layout = QHBoxLayout()
        doc_scope_layout.addWidget(QLabel("Document Scope:"))
        self.doc_scope_combo = QComboBox()
        self.doc_scope_combo.addItem("Project Total", -1)
        for doc in self.docs:
            self.doc_scope_combo.addItem(doc["title"], doc["id"])
        doc_scope_layout.addWidget(self.doc_scope_combo)

        part_scope_layout = QHBoxLayout()
        part_scope_layout.addWidget(QLabel("Participant Scope:"))
        self.part_scope_combo = QComboBox()
        self.part_scope_combo.addItem("All Participants", -1)
        for p in self.participants:
            self.part_scope_combo.addItem(p["name"], p["id"])
        part_scope_layout.addWidget(self.part_scope_combo)

        self.export_button = QPushButton("Export Options")
        export_menu = QMenu(self)
        export_menu.addAction("Export Chart as Image", self.export_chart_as_image)
        export_menu.addAction("Export Data Table as CSV", self.export_data_as_csv)
        export_menu.addAction("Export Cross-Tab as CSV", self.export_crosstab_as_csv)
        self.export_button.setMenu(export_menu)

        controls_layout.addLayout(doc_scope_layout)
        controls_layout.addLayout(part_scope_layout)
        controls_layout.addWidget(self.export_button, 0, Qt.AlignmentFlag.AlignRight)

        top_layout.addWidget(stats_container, 2)
        top_layout.addLayout(controls_layout, 1)
        main_layout.addLayout(top_layout)

        # --- Tab Widget Setup ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Breakdown
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

        # Tab 2: Charts
        self.charts_widget = ChartsWidget(self.settings)
        self.tabs.addTab(self.charts_widget, "Charts")

        # Tab 3: Crosstab
        self.crosstab_widget = CrosstabWidget(self.settings)
        self.tabs.addTab(self.crosstab_widget, "Cross-Tabulation")

        # Tab 4: Word Cloud (New)
        self.wordcloud_widget = WordCloudWidget(self.settings)
        self.tabs.addTab(self.wordcloud_widget, "Word Cloud")

        # --- Connections & Initial Load ---
        self.doc_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)
        self.part_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)

        if self.initial_document_id:
            index = self.doc_scope_combo.findData(self.initial_document_id)
            if index != -1:
                self.doc_scope_combo.setCurrentIndex(index)
        else:
            self.load_dashboard_data()

    def _create_stat_label(self, title_text):
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setAlignment(Qt.AlignCenter)

        bg_color = "#3b4252" if self.is_dark else "#ffffff"
        border_color = "#4c566a" if self.is_dark else "#d8dee9"
        title_color = "#d8dee9" if self.is_dark else "#4c566a"
        value_color = "#eceff4" if self.is_dark else "#2e3440"

        label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """
        )

        html = f"""
            <div style='color: {title_color}; font-size: 9pt;'>{title_text}</div>
            <div style='color: {value_color}; font-size: 18pt; font-weight: 600;'>N/A</div>
        """
        label.setText(html)
        return label

    def _update_stat_label(self, label, title, value):
        title_color = "#d8dee9" if self.is_dark else "#4c566a"
        value_color = "#eceff4" if self.is_dark else "#2e3440"

        html = f"""
            <div style='color: {title_color}; font-size: 9pt;'>{title}</div>
            <div style='color: {value_color}; font-size: 18pt; font-weight: 600;'>{value}</div>
        """
        label.setText(html)

    def load_dashboard_data(self):
        doc_id, part_id = (
            self.doc_scope_combo.currentData(),
            self.part_scope_combo.currentData(),
        )
        total_words, segments = self._get_scoped_data(doc_id, part_id)
        nodes = database.get_nodes_for_project(self.project_id)

        self._update_stat_label(
            self.total_words_label, "Scope Words", f"{total_words:,}"
        )
        self._update_stat_label(
            self.coded_segments_label, "Coded Segments", f"{len(segments):,}"
        )

        node_stats, coded_words = self._calculate_direct_stats(segments)
        coded_percentage = (coded_words / total_words * 100) if total_words > 0 else 0

        percent_html = f"{coded_words:,} <span style='font-size: 11pt; font-weight: normal;'>({coded_percentage:.1f}%)</span>"
        self._update_stat_label(self.coded_words_label, "Coded Words", percent_html)

        nodes_map, nodes_by_parent = self._build_node_hierarchy(nodes)
        aggregated_stats = self._calculate_aggregated_stats(nodes_by_parent, node_stats)
        self.tree_widget.clear()
        root_nodes_data = self._populate_tree_widget(
            nodes_by_parent, nodes_map, aggregated_stats, total_words
        )
        self.tree_widget.expandAll()

        # Update all visual tabs with the new data
        self.charts_widget.update_charts(root_nodes_data)
        self.crosstab_widget.update_crosstab(segments, nodes)
        self.wordcloud_widget.update_wordcloud(segments)  # Update the new widget

    def export_chart_as_image(self):
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index not in [1, 3]:  # Charts or Word Cloud tab
            QMessageBox.warning(
                self,
                "Incorrect Tab",
                "Please switch to the 'Charts' or 'Word Cloud' tab to export an image.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Image (*.png)"
        )
        if path:
            # Grab the contents of the currently visible tab widget
            self.tabs.currentWidget().grab().save(path)

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
