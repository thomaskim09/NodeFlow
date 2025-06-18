# Replace the contents of ui/workspace/node_tree_manager.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QInputDialog,
    QLabel,
    QHBoxLayout,
    QAbstractItemView,
    QMenu,
    QColorDialog,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDropEvent, QKeyEvent
from managers.export_manager import (
    export_node_family_to_word,
    export_node_family_to_excel,
    export_node_family_to_excel_multi_sheet,
)
import database

PRESET_COLORS = [
    "#FFB3BA",
    "#FFDFBA",
    "#FFFFBA",
    "#BAFFC9",
    "#BAE1FF",
    "#E0BBE4",
    "#FFD6E5",
    "#D4A5A5",
    "#A5D4A5",
    "#A5A5D4",
]


class DraggableTreeWidget(QTreeWidget):
    def __init__(self, parent_manager):
        super().__init__()
        self.parent_manager = parent_manager
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event: QDropEvent):
        source_item = self.currentItem()
        if not source_item:
            return
        source_id = source_item.data(0, 1)
        super().dropEvent(event)
        new_parent_item = source_item.parent()
        new_parent_id = new_parent_item.data(0, 1) if new_parent_item else None
        database.update_node_parent(source_id, new_parent_id)
        if new_parent_item:
            siblings = [
                new_parent_item.child(i) for i in range(new_parent_item.childCount())
            ]
        else:
            siblings = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        db_order_updates = [
            (i, item.data(0, 1))
            for i, item in enumerate(siblings)
            if item.data(0, 1) is not None
        ]
        database.update_node_order(db_order_updates)
        QTimer.singleShot(0, self.parent_manager.refresh_tree_and_emit_update)

    def keyPressEvent(self, event: QKeyEvent):
        current_item = self.currentItem()
        if not current_item:
            super().keyPressEvent(event)
            return
        node_id = current_item.data(0, 1)
        if node_id is None:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_F2:
            self.parent_manager.rename_node(node_id)
            event.accept()
        elif event.key() == Qt.Key.Key_Delete:
            self.parent_manager.delete_node(node_id)
            event.accept()
        else:
            super().keyPressEvent(event)


class NodeItemWidget(QWidget):
    def __init__(self, node_id, node_color, name_text, stats_text, parent_manager):
        super().__init__()
        self.node_id = node_id
        self.parent_manager = parent_manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 5, 7)
        layout.setSpacing(5)

        self.color_button = QPushButton()
        self.color_button.setFixedSize(18, 18)
        self.color_button.setToolTip("Click to change node color")
        self.set_button_color(node_color)
        self.color_button.clicked.connect(self.on_color_change)

        name_label = QLabel(name_text)
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("color: #888;")

        self.export_button = QPushButton("↓")
        self.export_button.setFixedSize(24, 24)
        self.export_button.setToolTip("Export this node and its children")
        self.export_button.clicked.connect(self.on_export)
        self.export_button.setVisible(False)

        self.filter_button = QPushButton("▼")
        self.filter_button.setFixedSize(24, 24)
        self.filter_button.setToolTip("Filter by this node only")
        self.filter_button.clicked.connect(self.on_filter)
        self.filter_button.setVisible(False)

        self.add_button = QPushButton("＋")
        self.add_button.setFixedSize(24, 24)
        self.add_button.setToolTip("Add a child node")
        self.add_button.clicked.connect(self.on_add_child)
        self.add_button.setVisible(False)

        self.edit_button = QPushButton("✎")
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Rename node (F2)")
        self.edit_button.clicked.connect(self.on_rename)
        self.edit_button.setVisible(False)

        self.delete_button = QPushButton("🗑")
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete node and its children (Delete)")
        self.delete_button.clicked.connect(self.on_delete)
        self.delete_button.setVisible(False)

        layout.addWidget(self.color_button)
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(stats_label)
        layout.addWidget(self.export_button)
        layout.addWidget(self.filter_button)
        layout.addWidget(self.add_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_button_color(self, color_hex):
        self.color_button.setStyleSheet(
            f"background-color: {color_hex}; border: 1px solid #888;"
        )

    def set_icons_visible(self, visible):
        self.export_button.setVisible(visible)
        self.filter_button.setVisible(visible)
        self.add_button.setVisible(visible)
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

    def on_color_change(self):
        current_color = self.color_button.palette().button().color()
        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            new_color_hex = color.name()
            self.set_button_color(new_color_hex)
            database.update_node_color(self.node_id, new_color_hex)
            self.parent_manager.node_updated.emit()

    def on_export(self):
        self.parent_manager.show_node_export_menu(self.node_id, self.export_button)

    def on_filter(self):
        self.parent_manager.filter_by_single_node(self.node_id)

    def on_add_child(self):
        self.parent_manager.add_node(parent_id=self.node_id)

    def on_rename(self):
        self.parent_manager.rename_node(self.node_id)

    def on_delete(self):
        self.parent_manager.delete_node(self.node_id)


class NodeTreeManager(QWidget):
    filter_by_node_family_signal = Signal(list)
    filter_by_single_node_signal = Signal(int)
    node_updated = Signal()
    node_selected_for_coding = Signal(int)

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.nodes_map = {}
        self._is_selection_mode = False
        self.current_document_id = None
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        header_label = QLabel("Nodes & Codes")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)
        add_root_button = QPushButton("＋ Add Root Node")
        add_root_button.clicked.connect(lambda: self.add_node())
        clear_filter_button = QPushButton("▼ Show All")
        clear_filter_button.setToolTip(
            "Clear the current node filter in the Coded Segments view"
        )
        clear_filter_button.clicked.connect(self.clear_all_filters)
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Project Total", "Current Document"])
        self.scope_combo.setToolTip("Switch the scope of the percentage calculation")
        self.scope_combo.currentTextChanged.connect(self.load_nodes)
        header_layout = QHBoxLayout()
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.scope_combo)
        header_layout.addWidget(clear_filter_button)
        header_layout.addWidget(add_root_button)
        main_layout.addLayout(header_layout)
        self.tree_widget = DraggableTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(20)
        main_layout.addWidget(self.tree_widget)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.load_nodes()

    # MODIFIED: The load_nodes method now accepts an optional ID to re-select.
    def load_nodes(self, node_id_to_reselect=None):
        try:
            self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass

        self.tree_widget.clear()
        scope = self.scope_combo.currentText()
        total_words = 0
        doc_id_for_stats = None
        if scope == "Current Document":
            if self.current_document_id:
                total_words = database.get_document_word_count(self.current_document_id)
                doc_id_for_stats = self.current_document_id
        else:
            total_words = database.get_project_word_count(self.project_id)

        node_stats = database.get_node_statistics(self.project_id, doc_id_for_stats)
        nodes = database.get_nodes_for_project(self.project_id)
        self.nodes_map = {n["id"]: n for n in nodes}
        self.nodes_by_parent = {n_id: [] for n_id in self.nodes_map}
        self.nodes_by_parent[None] = []
        for n_id, node in self.nodes_map.items():
            self.nodes_by_parent.setdefault(node["parent_id"], []).append(node)
        for children_list in self.nodes_by_parent.values():
            children_list.sort(key=lambda x: x["position"])

        item_to_reselect = None
        aggregated_stats = {}

        def calculate_aggregated_stats(parent_id):
            parent_word_count = 0
            parent_segment_count = 0
            children = self.nodes_by_parent.get(parent_id, [])
            for node_data in children:
                child_word_count, child_segment_count = calculate_aggregated_stats(
                    node_data["id"]
                )
                direct_stats = node_stats.get(
                    node_data["id"], {"word_count": 0, "segment_count": 0}
                )
                total_node_word_count = direct_stats["word_count"] + child_word_count
                total_node_segment_count = (
                    direct_stats["segment_count"] + child_segment_count
                )
                aggregated_stats[node_data["id"]] = {
                    "word_count": total_node_word_count,
                    "segment_count": total_node_segment_count,
                }
                parent_word_count += total_node_word_count
                parent_segment_count += total_node_segment_count
            return parent_word_count, parent_segment_count

        calculate_aggregated_stats(None)

        def add_items_recursively(parent_widget, parent_id, prefix=""):
            nonlocal item_to_reselect
            children = self.nodes_by_parent.get(parent_id, [])
            for i, node_data in enumerate(children):
                current_prefix = f"{prefix}{i + 1}."
                stats = aggregated_stats.get(
                    node_data["id"], {"word_count": 0, "segment_count": 0}
                )
                word_count = stats["word_count"]
                segment_count = stats["segment_count"]
                percentage = (word_count / total_words * 100) if total_words > 0 else 0

                name_text = f"{current_prefix} {node_data['name']}"
                stats_text = f"{percentage:.1f}% | {segment_count} Segments"

                tree_item = QTreeWidgetItem(parent_widget)
                tree_item.setData(0, 1, node_data["id"])

                item_widget = NodeItemWidget(
                    node_data["id"], node_data["color"], name_text, stats_text, self
                )
                self.tree_widget.setItemWidget(tree_item, 0, item_widget)

                # MODIFIED: Check against the new parameter instead of a local variable.
                if node_data["id"] == node_id_to_reselect:
                    item_to_reselect = tree_item
                add_items_recursively(tree_item, node_data["id"], prefix=current_prefix)

        add_items_recursively(self.tree_widget, None)
        self.tree_widget.expandAll()
        if item_to_reselect:
            self.tree_widget.setCurrentItem(item_to_reselect)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

    def set_current_document_id(self, doc_id):
        self.current_document_id = doc_id
        if self.scope_combo.currentText() == "Current Document":
            self.load_nodes()

    def set_selection_mode(self, enabled: bool):
        self._is_selection_mode = enabled
        if enabled:
            self.tree_widget.setStyleSheet("QTreeWidget { border: 2px solid #0078d7; }")
        else:
            self.tree_widget.setStyleSheet("")

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if self._is_selection_mode and item:
            self.tree_widget.blockSignals(True)
            node_id = item.data(0, 1)
            if node_id is not None:
                self.node_selected_for_coding.emit(node_id)
            self.tree_widget.blockSignals(False)

    # MODIFIED: This method now accepts an optional ID to re-select.
    def refresh_tree_and_emit_update(self, node_id_to_reselect=None):
        self.load_nodes(node_id_to_reselect=node_id_to_reselect)
        self.node_updated.emit()

    def clear_all_filters(self):
        self.tree_widget.clearSelection()
        self.filter_by_node_family_signal.emit([])

    def on_selection_changed(self, current_item, previous_item):
        if previous_item:
            widget = self.tree_widget.itemWidget(previous_item, 0)
            if widget:
                widget.set_icons_visible(False)
        if current_item:
            widget = self.tree_widget.itemWidget(current_item, 0)
            if widget:
                widget.set_icons_visible(True)
            node_id = current_item.data(0, 1)
            descendants = self.get_all_descendant_ids(node_id)
            self.filter_by_node_family_signal.emit([node_id] + descendants)
        else:
            self.filter_by_node_family_signal.emit([])

    def get_all_descendant_ids(self, node_id):
        descendants = []
        for child_node in self.nodes_by_parent.get(node_id, []):
            descendants.append(child_node["id"])
            descendants.extend(self.get_all_descendant_ids(child_node["id"]))
        return descendants

    def rename_node(self, node_id):
        node_data = self.nodes_map.get(node_id)
        if not node_data:
            return
        current_name = node_data["name"]
        new_name, ok = QInputDialog.getText(
            self, "Rename Node", "Enter new name:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            database.update_node_name(node_id, new_name.strip())
            self.refresh_tree_and_emit_update(
                node_id_to_reselect=node_id
            )  # Pass ID to re-select

    def set_stats_scope(self, scope, document_id=None):
        self.current_filter_scope = scope
        self.current_document_id = document_id
        self.load_nodes()

    def add_node(self, parent_id=None):
        name, ok = QInputDialog.getText(
            self, "Add Node", "Enter name for the new node:"
        )
        if ok and name.strip():
            existing_colors = {node["color"] for node in self.nodes_map.values()}
            new_color = PRESET_COLORS[0]
            for color in PRESET_COLORS:
                if color not in existing_colors:
                    new_color = color
                    break
            try:
                pid = int(self.project_id)
                database.add_node(pid, name.strip(), parent_id, new_color)
                # MODIFIED: Pass the parent_id to re-select it after the reload.
                self.refresh_tree_and_emit_update(node_id_to_reselect=parent_id)
            except (ValueError, TypeError) as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    (
                        str(e)
                        if isinstance(e, ValueError)
                        else f"Invalid Project ID: {self.project_id}"
                    ),
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add node: {str(e)}")

    def delete_node(self, node_id):
        node_data = self.nodes_map.get(node_id)
        if not node_data:
            return

        # Find parent before deleting to re-select it later
        self.tree_widget.findItems(
            str(node_id), Qt.MatchFlag.MatchRecursive, 1
        )  # This is not ideal, need a better way
        parent_id_to_reselect = None
        # A more robust find method would be better, but for now let's find it in the map
        parent_id_to_reselect = node_data["parent_id"]

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{node_data['name']}' and all its children? This will also remove all associated codings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_node(node_id)
            self.refresh_tree_and_emit_update(
                node_id_to_reselect=parent_id_to_reselect
            )  # Pass parent ID

    def filter_by_single_node(self, node_id):
        self.filter_by_single_node_signal.emit(node_id)

    def show_node_export_menu(self, node_id, button):
        menu = QMenu(self)
        action_export_word = menu.addAction("Export as Word (.docx)")
        action_export_excel = menu.addAction("Export as Excel (.xlsx)")
        action_export_word.triggered.connect(
            lambda: export_node_family_to_word(self.project_id, node_id, self)
        )
        action_export_excel.triggered.connect(
            lambda: self.export_node_family_to_excel_handler(node_id)
        )
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def export_node_family_to_excel_handler(self, node_id):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Excel Export Option")
        msg_box.setText("How would you like to export the Excel report?")
        msg_box.setInformativeText(
            "Choose whether to combine all data into a single sheet or create a separate sheet for each parent node."
        )
        single_sheet_button = msg_box.addButton(
            "Single Sheet", QMessageBox.ButtonRole.ActionRole
        )
        multi_sheet_button = msg_box.addButton(
            "Multiple Sheets", QMessageBox.ButtonRole.ActionRole
        )
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        if clicked_button == single_sheet_button:
            export_node_family_to_excel(self.project_id, node_id, self)
        elif clicked_button == multi_sheet_button:
            export_node_family_to_excel_multi_sheet(self.project_id, node_id, self)
