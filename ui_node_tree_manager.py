from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QInputDialog,
)
import database


class NodeTreeManager(QWidget):
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

        # --- Layouts and Main GroupBox ---
        group_box = QGroupBox("Nodes & Codes")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        # --- Widgets ---
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)  # Hide the column header

        button_layout = QHBoxLayout()
        add_node_button = QPushButton("Add Node")
        add_child_button = QPushButton("Add Child")
        rename_button = QPushButton("Rename")
        delete_button = QPushButton("Delete")

        reorder_layout = QHBoxLayout()
        move_up_button = QPushButton("Move Up ↑")
        move_down_button = QPushButton("Move Down ↓")

        # --- Assemble Layout ---
        button_layout.addWidget(add_node_button)
        button_layout.addWidget(add_child_button)
        button_layout.addWidget(rename_button)
        button_layout.addWidget(delete_button)

        reorder_layout.addWidget(move_up_button)
        reorder_layout.addWidget(move_down_button)

        group_box_layout.addWidget(self.tree_widget)
        group_box_layout.addLayout(button_layout)
        group_box_layout.addLayout(reorder_layout)

        # --- Connect Signals to Slots ---
        add_node_button.clicked.connect(self.add_node)
        add_child_button.clicked.connect(self.add_child_node)
        rename_button.clicked.connect(self.rename_node)
        delete_button.clicked.connect(self.delete_node)
        move_up_button.clicked.connect(lambda: self.move_node(-1))
        move_down_button.clicked.connect(lambda: self.move_node(1))

        # --- Load Initial Data ---
        self.load_nodes()

    def load_nodes(self):
        """Loads all nodes for the project and recursively builds the tree."""
        self.tree_widget.clear()
        nodes = database.get_nodes_for_project(self.project_id)

        node_map = {
            node["id"]: {"data": node, "item": None, "children": []} for node in nodes
        }
        root_items = []

        for node_id, item_data in node_map.items():
            parent_id = item_data["data"]["parent_id"]
            if parent_id is None:
                root_items.append(item_data)
            else:
                if parent_id in node_map:
                    node_map[parent_id]["children"].append(item_data)

        # Sort by position before inserting
        root_items.sort(key=lambda x: x["data"]["position"])
        for item in node_map.values():
            item["children"].sort(key=lambda x: x["data"]["position"])

        def add_items_recursively(parent_widget, items):
            for item in items:
                node_data = item["data"]
                tree_item = QTreeWidgetItem(parent_widget, [node_data["name"]])
                tree_item.setData(0, 1, node_data["id"])  # Store node ID in item's data
                item["item"] = tree_item  # Store the item for lookup

                if item["children"]:
                    add_items_recursively(tree_item, item["children"])

        add_items_recursively(self.tree_widget, root_items)
        self.tree_widget.expandAll()

    def add_node(self):
        """Adds a new top-level node."""
        name, ok = QInputDialog.getText(
            self, "Add Node", "Enter name for the new node:"
        )
        if ok and name:
            database.add_node(self.project_id, name)
            self.load_nodes()

    def add_child_node(self):
        """Adds a new child node to the selected node."""
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(
                self, "No Selection", "Please select a parent node first."
            )
            return

        parent_id = selected_item.data(0, 1)
        name, ok = QInputDialog.getText(
            self,
            "Add Child Node",
            f"Enter name for the child of '{selected_item.text(0)}':",
        )
        if ok and name:
            database.add_node(self.project_id, name, parent_id)
            self.load_nodes()

    def rename_node(self):
        """Renames the selected node."""
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a node to rename.")
            return

        node_id = selected_item.data(0, 1)
        current_name = selected_item.text(0)

        new_name, ok = QInputDialog.getText(
            self, "Rename Node", "Enter new name:", text=current_name
        )
        if ok and new_name:
            database.update_node_name(node_id, new_name)
            self.load_nodes()

    def delete_node(self):
        """Deletes the selected node and its children."""
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a node to delete.")
            return

        node_id = selected_item.data(0, 1)
        node_name = selected_item.text(0)

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{node_name}' and all its children?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_node(node_id)
            self.load_nodes()

    def move_node(self, direction):
        """Moves the selected node up (-1) or down (1) among its siblings."""
        selected_item = self.tree_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "No Selection", "Please select a node to move.")
            return

        parent = selected_item.parent()
        if parent:
            index = parent.indexOfChild(selected_item)
            parent.removeChild(selected_item)
            parent.insertChild(index + direction, selected_item)
        else:  # Top-level item
            index = self.tree_widget.indexOfTopLevelItem(selected_item)
            self.tree_widget.takeTopLevelItem(index)
            self.tree_widget.insertTopLevelItem(index + direction, selected_item)

        self.tree_widget.setCurrentItem(selected_item)

        # Now update the database positions for all siblings
        db_updates = []
        if parent:
            for i in range(parent.childCount()):
                child_item = parent.child(i)
                node_id = child_item.data(0, 1)
                db_updates.append((i, node_id))
        else:  # Top-level items
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                node_id = item.data(0, 1)
                db_updates.append((i, node_id))

        database.update_node_order(db_updates)
