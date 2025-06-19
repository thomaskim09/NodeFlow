# MODIFIED: Add new imports
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
from PySide6.QtCore import Qt, QThreadPool  # MODIFIED: Import QThreadPool
from PySide6.QtGui import QPixmap, QColor, QIcon

from managers.theme_manager import load_settings
from .charts_widget import ChartsWidget
from .crosstab_widget import CrosstabWidget
from .wordcloud_widget import WordCloudWidget
import database
from qt_material_icons import MaterialIcon
from utils.worker import Worker  # NEW: Import our new Worker class


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

        # NEW: Initialize a thread pool for running workers
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_layout = QHBoxLayout()

        stats_container = QFrame()
        stats_container.setObjectName("statsContainer")
        container_bg = "#2c2c2c" if self.is_dark else "#f2f2f2"
        stats_container.setStyleSheet(
            f"#statsContainer {{ background-color: {container_bg}; border-radius: 8px; }}"
        )

        overview_layout = QHBoxLayout(stats_container)
        overview_layout.setContentsMargins(0, 0, 25, 0)
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

        node_scope_layout = QHBoxLayout()
        node_scope_layout.addWidget(QLabel("Node Scope:"))
        self.node_scope_combo = QComboBox()
        node_scope_layout.addWidget(self.node_scope_combo)

        export_icon = MaterialIcon("download")
        self.export_button = QPushButton()
        self.export_button.setIcon(export_icon)
        self.export_button.setText("Export Options")
        export_menu = QMenu(self)
        export_menu.addAction("Export Chart as Image", self.export_chart_as_image)
        export_menu.addAction("Export Data Table as CSV", self.export_data_as_csv)
        export_menu.addAction("Export Cross-Tab as CSV", self.export_crosstab_as_csv)
        self.export_button.setMenu(export_menu)

        controls_layout.addLayout(doc_scope_layout)
        controls_layout.addLayout(part_scope_layout)
        controls_layout.addLayout(node_scope_layout)
        controls_layout.addWidget(self.export_button, 0, Qt.AlignmentFlag.AlignRight)

        top_layout.addWidget(stats_container, 2)
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

        self.wordcloud_widget = WordCloudWidget(self.settings)
        self.tabs.addTab(self.wordcloud_widget, "Word Cloud")

        self._populate_node_scope_combo()
        self.doc_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)
        self.part_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)
        self.node_scope_combo.currentIndexChanged.connect(self.load_dashboard_data)

        if self.initial_document_id:
            index = self.doc_scope_combo.findData(self.initial_document_id)
            if index != -1:
                self.doc_scope_combo.setCurrentIndex(index)
        else:
            self.load_dashboard_data()

    # MODIFIED: This function now triggers the background worker
    def load_dashboard_data(self):
        """
        Sets up and runs the background worker to load and process dashboard data.
        """
        doc_id = self.doc_scope_combo.currentData()
        part_id = self.part_scope_combo.currentData()
        node_id = self.node_scope_combo.currentData()
        if node_id is None:
            return

        # 1. Show a loading state in the UI
        self._set_loading_state(True)

        # 2. Create the worker and connect signals
        worker = Worker(self._get_data_from_db, doc_id, part_id, node_id)
        worker.signals.result.connect(self._update_ui_with_results)
        worker.signals.error.connect(self._on_loading_error)
        worker.signals.finished.connect(lambda: self._set_loading_state(False))

        # 3. Execute the worker in the thread pool
        self.threadpool.start(worker)

    # NEW: Function to show a "loading" state
    def _set_loading_state(self, is_loading):
        if is_loading:
            self.tree_widget.clear()
            self._update_stat_label(
                self.total_words_label, "Scope Words", "Calculating..."
            )
            self._update_stat_label(
                self.coded_segments_label, "Coded Segments", "Calculating..."
            )
            self._update_stat_label(
                self.coded_words_label, "Coded Words", "Calculating..."
            )
            self.charts_widget.clear_charts()
            self.crosstab_widget.clear_crosstab()
            self.wordcloud_widget.clear_wordcloud()

        self.export_button.setEnabled(not is_loading)

    # NEW: Function to handle errors from the worker
    def _on_loading_error(self, error_tuple):
        print("Error in worker thread:", error_tuple)
        exctype, value, tb = error_tuple
        QMessageBox.critical(
            self,
            f"Error: {exctype.__name__}",
            f"An error occurred while loading data:\n{value}",
        )
        self._set_loading_state(False)

    # NEW: This is the function that runs in the background. It only fetches and processes data.
    def _get_data_from_db(self, doc_id, part_id, node_id, progress_callback):
        """
        Fetches all data from the database and performs calculations.
        This function runs in the background and returns a dictionary of results.
        It does NOT interact with the UI.
        """
        results = {}
        nodes = database.get_nodes_for_project(self.project_id)
        nodes_map, nodes_by_parent = self._build_node_hierarchy(nodes)

        results["nodes"] = nodes
        results["nodes_map"] = nodes_map
        results["nodes_by_parent"] = nodes_by_parent

        if node_id != -1:
            all_project_segments = database.get_coded_segments_for_project(
                self.project_id
            )
            node_stats, _ = self._calculate_direct_stats(all_project_segments)
            aggregated_stats = self._calculate_aggregated_stats(
                nodes_by_parent, node_stats
            )

            results["node_id"] = node_id
            results["aggregated_stats"] = aggregated_stats
            results["all_project_segments"] = all_project_segments

        else:
            total_words, segments = self._get_scoped_data(doc_id, part_id)
            node_stats, coded_words = self._calculate_direct_stats(segments)
            aggregated_stats = self._calculate_aggregated_stats(
                nodes_by_parent, node_stats
            )

            results["total_words"] = total_words
            results["segments"] = segments
            results["coded_words"] = coded_words
            results["aggregated_stats"] = aggregated_stats

        return results

    # NEW: This function takes the results from the background worker and updates the UI
    def _update_ui_with_results(self, results):
        """
        This function is called when the worker is finished.
        It populates all the UI widgets with the pre-calculated data.
        """
        nodes = results.get("nodes", [])
        nodes_map = results.get("nodes_map", {})
        nodes_by_parent = results.get("nodes_by_parent", {})
        aggregated_stats = results.get("aggregated_stats", {})

        # Check if we are in "Node Scope" mode
        if "node_id" in results:
            node_id = results["node_id"]
            all_project_segments = results.get("all_project_segments", [])

            parent_stats = aggregated_stats.get(
                node_id, {"word_count": 0, "segment_count": 0}
            )
            parent_total_words = parent_stats.get("word_count", 0)
            parent_segment_count = parent_stats.get("segment_count", 0)

            self._update_stat_label(
                self.total_words_label,
                f"Words in '{nodes_map[node_id]['name']}'",
                f"{parent_total_words:,}",
            )
            self._update_stat_label(
                self.coded_segments_label,
                "Segments in Node",
                f"{parent_segment_count:,}",
            )
            self._update_stat_label(
                self.coded_words_label, "Coded Words", f"{parent_total_words:,}"
            )

            self.tree_widget.clear()
            direct_children_nodes = nodes_by_parent.get(node_id, [])

            if direct_children_nodes:
                children_data_for_charts = []
                for child_node in direct_children_nodes:
                    child_stats = aggregated_stats.get(
                        child_node["id"], {"word_count": 0, "segment_count": 0}
                    )
                    wc, sc = child_stats.get("word_count", 0), child_stats.get(
                        "segment_count", 0
                    )
                    p = (wc / parent_total_words * 100) if parent_total_words > 0 else 0
                    children_data_for_charts.append((child_node["name"], p, wc, sc))
                    self._populate_tree_item(self.tree_widget, child_node, wc, sc, p)
                self.charts_widget.update_charts(children_data_for_charts)
            else:  # Leaf node
                wc, sc = parent_total_words, parent_segment_count
                leaf_node_data = [(nodes_map[node_id]["name"], 100.0, wc, sc)]
                self._populate_tree_item(
                    self.tree_widget, nodes_map[node_id], wc, sc, 100.0
                )
                self.charts_widget.update_charts(leaf_node_data)

            self.tree_widget.expandAll()

            descendants = database.get_node_descendants(node_id)
            family_node_ids = [node_id] + descendants
            family_segments = [
                s for s in all_project_segments if s["node_id"] in family_node_ids
            ]

            self.crosstab_widget.update_crosstab(family_segments, nodes)
            self.wordcloud_widget.update_wordcloud(family_segments)

        # Otherwise, we are in regular project/doc/participant scope
        else:
            total_words = results.get("total_words", 0)
            segments = results.get("segments", [])
            coded_words = results.get("coded_words", 0)

            coded_percentage = (
                (coded_words / total_words * 100) if total_words > 0 else 0
            )
            percent_html = f"{coded_words:,} <span style='font-size: 11pt; font-weight: normal;'>({coded_percentage:.1f}%)</span>"

            self._update_stat_label(
                self.total_words_label, "Scope Words", f"{total_words:,}"
            )
            self._update_stat_label(
                self.coded_segments_label, "Coded Segments", f"{len(segments):,}"
            )
            self._update_stat_label(self.coded_words_label, "Coded Words", percent_html)

            self.tree_widget.clear()
            root_nodes_data = self._populate_tree_widget(
                nodes_by_parent, nodes_map, aggregated_stats, total_words
            )
            self.tree_widget.expandAll()

            self.charts_widget.update_charts(root_nodes_data)
            self.crosstab_widget.update_crosstab(segments, nodes)
            self.wordcloud_widget.update_wordcloud(segments)

    # NEW: Helper function to create a tree item, reducing code duplication
    def _populate_tree_item(
        self, parent_item, node, word_count, segment_count, percentage
    ):
        item = QTreeWidgetItem(parent_item)
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(node["color"]))
        item.setIcon(0, QIcon(pixmap))
        item.setText(0, f" {node['name']}")
        item.setText(1, f"{word_count:,}")
        item.setText(2, f"{percentage:.1f}%")
        item.setText(3, f"{segment_count:,}")
        for col in [1, 2, 3]:
            item.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)
        return item

    def _populate_node_scope_combo(self):
        """Populates the node scope dropdown with a node hierarchy."""
        self.node_scope_combo.blockSignals(True)
        self.node_scope_combo.clear()

        self.node_scope_combo.addItem("All Nodes", -1)

        nodes = database.get_nodes_for_project(self.project_id)
        if nodes:
            self.node_scope_combo.insertSeparator(self.node_scope_combo.count())

            nodes_by_parent = {}
            for n in nodes:
                pid = n.get("parent_id")
                nodes_by_parent.setdefault(pid, []).append(n)

            def add_nodes_recursively(parent_id, indent=0):
                if parent_id not in nodes_by_parent:
                    return

                def key(x):
                    return x.get("position", 0) or 0

                for node in sorted(nodes_by_parent[parent_id], key=key):
                    self.node_scope_combo.addItem(
                        f"{'  ' * indent}{node['name']}", node["id"]
                    )
                    add_nodes_recursively(node["id"], indent + 1)

            add_nodes_recursively(None)

        self.node_scope_combo.blockSignals(False)

    def _create_stat_label(self, title_text):
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setAlignment(Qt.AlignCenter)
        bg_color = "#2c2c2c" if self.is_dark else "#ffffff"
        border_color = "#4c566a" if self.is_dark else "#d8dee9"
        title_color = "#d8dee9" if self.is_dark else "#4c566a"
        value_color = "#eceff4" if self.is_dark else "#2e3440"
        label.setStyleSheet(
            f"QLabel {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 10px; }}"
        )
        html = f"<div style='color: {title_color}; font-size: 9pt;'>{title_text}</div><div style='color: {value_color}; font-size: 18pt; font-weight: 600;'>N/A</div>"
        label.setText(html)
        return label

    def _update_stat_label(self, label, title, value):
        title_color = "#d8dee9" if self.is_dark else "#4c566a"
        value_color = "#eceff4" if self.is_dark else "#2e3440"
        html = f"<div style='color: {title_color}; font-size: 9pt;'>{title}</div><div style='color: {value_color}; font-size: 18pt; font-weight: 600;'>{value}</div>"
        label.setText(html)

    def export_chart_as_image(self):
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index not in [1, 3]:
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
            L.sort(key=lambda x: (x.get("position", 0) or 0, x["name"]))
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

                # MODIFIED: Use the new helper function
                item = self._populate_tree_item(p_item, node_data, wc, sc, p)
                # Manually set the hierarchical text
                item.setText(0, f" {prefix}{i + 1}. {node_data['name']}")

                if p_id is None:
                    root_nodes_data.append((node_data["name"], p, wc, sc))
                recurse(item, node_data["id"], f"{prefix}{i + 1}.")

        recurse(self.tree_widget.invisibleRootItem(), None)
        return root_nodes_data

    def closeEvent(self, event):
        # Safely clear charts to release resources
        if hasattr(self, "charts_widget"):
            self.charts_widget.clear_charts()
        # NEW: Stop all running threads when closing the dialog
        self.threadpool.clear()
        self.threadpool.waitForDone()
        super().closeEvent(event)
