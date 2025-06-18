from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QGroupBox,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QInputDialog,
    QGridLayout,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
import database


class NodeTreeManager(QWidget):
    node_selected_signal = Signal(int)
    node_updated = Signal()

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

        group_box = QGroupBox("Nodes & Codes")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(20)

        # --- Button Layout ---
        button_layout = QGridLayout()
        add_button = QPushButton("Add Node")
        add_button.setToolTip("Add a new root node, or a child to the selected node")
        rename_button = QPushButton("Rename")
        rename_button.setToolTip("Rename the selected node")
        delete_button = QPushButton("Delete")
        delete_button.setToolTip("Delete the selected node and all its children")

        up_button = QPushButton("↑ Move Up")
        up_button.setToolTip("Move selected node up among its siblings (Alt+Up)")
        up_button.setShortcut(QKeySequence("Alt+Up"))

        down_button = QPushButton("↓ Move Down")
        down_button.setToolTip("Move selected node down among its siblings (Alt+Down)")
        down_button.setShortcut(QKeySequence("Alt+Down"))

        left_button = QPushButton("← Promote")
        left_button.setToolTip("Promote (outdent) the selected node (Alt+Left)")
        left_button.setShortcut(QKeySequence("Alt+Left"))

        right_button = QPushButton("Demote →")
        right_button.setToolTip("Demote (indent) the selected node (Alt+Right)")
        right_button.setShortcut(QKeySequence("Alt+Right"))

        button_layout.addWidget(add_button, 0, 0, 1, 2)
        button_layout.addWidget(up_button, 1, 0)
        button_layout.addWidget(down_button, 1, 1)
        button_layout.addWidget(left_button, 2, 0)
        button_layout.addWidget(right_button, 2, 1)
        button_layout.addWidget(rename_button, 3, 0)
        button_layout.addWidget(delete_button, 3, 1)

        group_box_layout.addWidget(self.tree_widget)
        group_box_layout.addLayout(button_layout)

        # --- Connect Signals ---
        add_button.clicked.connect(self.add_node_or_child)
        rename_button.clicked.connect(self.rename_node)
        delete_button.clicked.connect(self.delete_node)
        up_button.clicked.connect(lambda: self.move_node_up_down(-1))
        down_button.clicked.connect(lambda: self.move_node_up_down(1))
        left_button.clicked.connect(self.promote_node)
        right_button.clicked.connect(self.demote_node)
        self.tree_widget.currentItemChanged.connect(self.on_node_selected)

        self.load_nodes()

    def on_node_selected(self, current, previous):
        if current:
            node_id = current.data(0, 1)
            self.node_selected_signal.emit(node_id)
        else:
            self.node_selected_signal.emit(-1)

    def load_nodes(self):
        self.tree_widget.clear()
        nodes = database.get_nodes_for_project(self.project_id)
        node_map = {node["id"]: {"data": node, "children": []} for node in nodes}
        root_nodes = []
        for node_id, item_data in node_map.items():
            parent_id = item_data["data"]["parent_id"]
            if parent_id is None:
                root_nodes.append(item_data)
            else:
                if parent_id in node_map:
                    node_map[parent_id]["children"].append(item_data)
        root_nodes.sort(key=lambda x: x["data"]["position"])
        for item in node_map.values():
            item["children"].sort(key=lambda x: x["data"]["position"])

        def add_items_recursively(parent_widget, items, prefix=""):
            for i, item in enumerate(items):
                node_data = item["data"]
                current_prefix = f"{prefix}{i + 1}."
                display_text = f"{current_prefix} {node_data['name']}"
                tree_item = QTreeWidgetItem(parent_widget, [display_text])
                tree_item.setData(0, 1, node_data["id"])
                if item["children"]:
                    add_items_recursively(
                        tree_item, item["children"], prefix=current_prefix
                    )

        add_items_recursively(self.tree_widget, root_nodes)
        self.tree_widget.expandAll()

    def rename_node(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return
        node_id = selected_item.data(0, 1)
        full_text = selected_item.text(0)
        current_name = full_text.split(" ", 1)[-1]
        new_name, ok = QInputDialog.getText(
            self, "Rename Node", "Enter new name:", text=current_name
        )
        if ok and new_name and new_name != current_name:
            database.update_node_name(node_id, new_name)
            self.load_nodes()
            self.node_updated.emit()

    def add_node_or_child(self):
        selected_item = self.tree_widget.currentItem()
        parent_id = selected_item.data(0, 1) if selected_item else None
        name, ok = QInputDialog.getText(
            self, "Add Node", "Enter name for the new node:"
        )
        if ok and name:
            database.add_node(self.project_id, name, parent_id)
            self.load_nodes()
            self.node_updated.emit()

    def promote_node(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item or not selected_item.parent():
            return
        node_id = selected_item.data(0, 1)
        grandparent = selected_item.parent().parent()
        new_parent_id = grandparent.data(0, 1) if grandparent else None
        database.update_node_parent(node_id, new_parent_id)
        self.load_nodes()
        self.node_updated.emit()

    def demote_node(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return
        parent = selected_item.parent()
        if parent:
            index = parent.indexOfChild(selected_item)
            if index == 0:
                return
            new_parent_item = parent.child(index - 1)
        else:
            index = self.tree_widget.indexOfTopLevelItem(selected_item)
            if index == 0:
                return
            new_parent_item = self.tree_widget.topLevelItem(index - 1)
        node_id = selected_item.data(0, 1)
        new_parent_id = new_parent_item.data(0, 1)
        database.update_node_parent(node_id, new_parent_id)
        self.load_nodes()
        self.node_updated.emit()

    def move_node_up_down(self, direction):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return
        parent = selected_item.parent()
        if parent:
            index = parent.indexOfChild(selected_item)
            if (direction == -1 and index == 0) or (
                direction == 1 and index == parent.childCount() - 1
            ):
                return
            parent.takeChild(index)
            parent.insertChild(index + direction, selected_item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(selected_item)
            if (direction == -1 and index == 0) or (
                direction == 1 and index == self.tree_widget.topLevelItemCount() - 1
            ):
                return
            self.tree_widget.takeTopLevelItem(index)
            self.tree_widget.insertTopLevelItem(index + direction, selected_item)
        self.tree_widget.setCurrentItem(selected_item)
        all_siblings = (
            [parent.child(i) for i in range(parent.childCount())]
            if parent
            else [
                self.tree_widget.topLevelItem(i)
                for i in range(self.tree_widget.topLevelItemCount())
            ]
        )
        db_updates = [(i, item.data(0, 1)) for i, item in enumerate(all_siblings)]
        database.update_node_order(db_updates)
        self.load_nodes()
        self.node_updated.emit()

    def delete_node(self):
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            return
        node_id = selected_item.data(0, 1)
        node_name = selected_item.text(0)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{node_name}' and all its children? This will also remove all associated codings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_node(node_id)
            self.load_nodes()
            self.node_updated.emit()
