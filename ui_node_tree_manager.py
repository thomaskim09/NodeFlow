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
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QDropEvent

import database


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

        self.parent_manager.load_nodes()
        self.parent_manager.node_updated.emit()


class NodeItemWidget(QWidget):
    def __init__(self, node_id, display_text, parent_manager):
        super().__init__()
        self.node_id = node_id
        self.parent_manager = parent_manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(5)

        name_label = QLabel(display_text)

        self.filter_button = QPushButton("🔎")
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
        self.edit_button.setToolTip("Rename node")
        self.edit_button.clicked.connect(self.on_rename)
        self.edit_button.setVisible(False)

        self.delete_button = QPushButton("🗑")
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete node and its children")
        self.delete_button.clicked.connect(self.on_delete)
        self.delete_button.setVisible(False)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(self.filter_button)
        layout.addWidget(self.add_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_icons_visible(self, visible):
        self.filter_button.setVisible(visible)
        self.add_button.setVisible(visible)
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

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

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        header_label = QLabel("Nodes & Codes")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)

        add_root_button = QPushButton("＋ Add Root Node")
        add_root_button.clicked.connect(self.add_node)

        header_layout = QHBoxLayout()
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(add_root_button)
        main_layout.addLayout(header_layout)

        self.tree_widget = DraggableTreeWidget(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(20)
        main_layout.addWidget(self.tree_widget)

        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)
        self.load_nodes()

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
            # FIX: Call the corrected function without the extra argument
            descendants = self.get_all_descendant_ids(node_id)
            self.filter_by_node_family_signal.emit([node_id] + descendants)

        else:
            self.filter_by_node_family_signal.emit([])

    # FIX: Corrected method signature and implementation
    def get_all_descendant_ids(self, node_id):
        """Recursively gets all children of a node using the class's node map."""
        descendants = []
        # Use self.nodes_by_parent, which is defined in load_nodes
        for child_node in self.nodes_by_parent.get(node_id, []):
            descendants.append(child_node["id"])
            # The recursive call is also fixed to not pass the extra argument
            descendants.extend(self.get_all_descendant_ids(child_node["id"]))
        return descendants

    def load_nodes(self):
        self.tree_widget.currentItemChanged.disconnect(self.on_selection_changed)
        self.tree_widget.clear()

        nodes = database.get_nodes_for_project(self.project_id)
        self.nodes_map = {n["id"]: n for n in nodes}

        self.nodes_by_parent = {n_id: [] for n_id in self.nodes_map}
        self.nodes_by_parent[None] = []
        for n_id, node in self.nodes_map.items():
            self.nodes_by_parent.setdefault(node["parent_id"], []).append(node)

        for children_list in self.nodes_by_parent.values():
            children_list.sort(key=lambda x: x["position"])

        def add_items_recursively(parent_widget, parent_id, prefix=""):
            children = self.nodes_by_parent.get(parent_id, [])
            for i, node_data in enumerate(children):
                current_prefix = f"{prefix}{i + 1}."
                display_text = f"{current_prefix} {node_data['name']}"

                tree_item = QTreeWidgetItem(parent_widget)
                tree_item.setData(0, 1, node_data["id"])

                item_widget = NodeItemWidget(node_data["id"], display_text, self)
                self.tree_widget.setItemWidget(tree_item, 0, item_widget)

                child_nodes = self.nodes_by_parent.get(node_data["id"], [])
                if child_nodes:
                    add_items_recursively(
                        tree_item, node_data["id"], prefix=current_prefix
                    )

        add_items_recursively(self.tree_widget, None)
        self.tree_widget.expandAll()
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)

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
            self.load_nodes()
            self.node_updated.emit()

    def add_node(self, parent_id=None):
        name, ok = QInputDialog.getText(
            self, "Add Node", "Enter name for the new node:"
        )
        if ok and name.strip():
            database.add_node(self.project_id, name.strip(), parent_id)
            self.load_nodes()
            self.node_updated.emit()

    def delete_node(self, node_id):
        node_data = self.nodes_map.get(node_id)
        if not node_data:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{node_data['name']}' and all its children? This will also remove all associated codings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_node(node_id)
            self.load_nodes()
            self.node_updated.emit()

    def filter_by_single_node(self, node_id):
        self.filter_by_single_node_signal.emit(node_id)
