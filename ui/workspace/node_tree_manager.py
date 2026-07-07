from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QMessageBox,
    QInputDialog,
    QLabel,
    QHBoxLayout,
    QAbstractItemView,
    QMenu,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSizePolicy,
    QRadioButton,
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent, QRect, QSize
from PySide6.QtGui import QDropEvent, QKeyEvent, QColor, QIcon, QPixmap
from managers.export_manager import (
    export_classification_workbook,
    export_project_to_excel_single_sheet,
    export_node_family_to_word,
    export_node_family_to_excel,
    export_node_family_to_excel_multi_sheet,
    export_to_excel,
)
import database
from qt_material_icons import MaterialIcon
from utils.common import get_translation, get_resource_path
from managers.theme_manager import load_settings, get_effective_theme_mode
from repositories.workspace_snapshot_repository import workspace_snapshot_repository
from services.workspace_history_service import WorkspaceCommand
from ui.combo_box import FitPopupComboBox

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
    "#FFCC00",
    "#FF6600",
    "#FF3300",
    "#CC3300",
    "#990000",
    "#993300",
    "#996600",
    "#999900",
    "#669900",
    "#339900",
    "#009900",
    "#009933",
    "#009966",
    "#009999",
    "#006699",
    "#003399",
    "#000099",
    "#330099",
    "#660099",
    "#990099",
    "#CC0099",
    "#FF0099",
    "#FF0066",
    "#FF0033",
    "#CC0033",
    "#990033",
    "#660033",
    "#330033",
    "#663333",
    "#996666",
    "#CCCCFF",
    "#99CCFF",
    "#66CCFF",
    "#33CCFF",
    "#00CCFF",
    "#00FFFF",
    "#00CC99",
    "#00FFCC",
    "#33FFCC",
    "#66FFCC",
]

def _resource_url(filename: str) -> str:
    return get_resource_path(filename).replace("\\", "/")


class NodeItemWidget(QWidget):
    def __init__(
        self,
        node_id,
        node_color,
        name_text,
        stats_text,
        parent_manager,
        language=None,
    ):
        super().__init__()
        self.node_id = node_id
        self.parent_manager = parent_manager
        self.language = language or getattr(parent_manager, "language", "English")
        self._base_row_height = 28
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 8, 2)
        layout.setSpacing(8)
        self.color_button = QPushButton()
        self.color_button.setObjectName("nodeColorButton")
        self.color_button.setFixedSize(18, 18)
        self.color_button.setToolTip(
            get_translation("node_tree.color_tooltip", self.language)
        )
        self.set_button_color(node_color)
        self.color_button.clicked.connect(self.on_color_change)
        self.name_label = QLabel(name_text)
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.stats_label = QLabel(stats_text)
        self.stats_label.setStyleSheet("color: #888;")
        self.stats_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        self.stats_label.setVisible(bool(stats_text))
        if stats_text:
            self.stats_label.setMinimumWidth(170)
        self.menu_button = QPushButton()
        self.menu_icon = MaterialIcon("more_vert")
        self.menu_button.setIcon(self.menu_icon)
        self.menu_button.setFixedSize(22, 22)
        self.menu_button.setToolTip(
            get_translation("node_tree.more_actions_tooltip", self.language)
        )
        self.menu_button.clicked.connect(self.show_actions_menu)
        layout.addWidget(self.color_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.name_label, 1, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.stats_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignTop)
        self.set_selected_style(False)

    def update_wrap_width(self, available_width):
        stats_width = (
            max(self.stats_label.minimumWidth(), self.stats_label.sizeHint().width())
            if self.stats_label.isVisible()
            else 0
        )
        reserved_width = (
            self.color_button.width()
            + stats_width
            + self.menu_button.width()
            + self.layout().contentsMargins().left()
            + self.layout().contentsMargins().right()
            + (self.layout().spacing() * 3)
        )
        name_width = max(120, available_width - reserved_width)
        text_rect = self.name_label.fontMetrics().boundingRect(
            QRect(0, 0, name_width, 10_000),
            int(Qt.TextFlag.TextWordWrap),
            self.name_label.text(),
        )
        text_height = max(self.name_label.fontMetrics().height(), text_rect.height())
        self.name_label.setFixedWidth(name_width)
        self.name_label.setFixedHeight(text_height)
        self.layout().activate()
        self.updateGeometry()
        content_height = max(
            text_height,
            self.color_button.height(),
            self.menu_button.height(),
            self.stats_label.sizeHint().height() if self.stats_label.isVisible() else 0,
        )
        margins = self.layout().contentsMargins()
        row_height = max(
            self._base_row_height,
            content_height + margins.top() + margins.bottom(),
        )
        self.setFixedHeight(row_height)
        return QSize(available_width, row_height)

    def set_button_color(self, color_hex):
        self.color_button.setStyleSheet(
            f"background-color: {color_hex}; border: 1px solid #888;"
        )

    def set_icons_visible(self, visible):
        self.menu_button.setVisible(True)

    def set_selected_style(self, is_selected: bool):
        is_dark = get_effective_theme_mode() == "Dark"
        selected_fg = "#f0f0f0" if is_dark else "#000000"
        normal_fg = "#f0f0f0" if is_dark else "#333333"
        stats_fg = "#b8b8b8" if is_dark else "#888888"
        current_fg = selected_fg if is_selected else normal_fg
        if is_selected:
            self.menu_button.setStyleSheet(f"color: {current_fg};")
        else:
            self.menu_button.setStyleSheet(f"color: {current_fg};")
        self.name_label.setStyleSheet(f"color: {current_fg};")
        self.stats_label.setStyleSheet(
            f"color: {current_fg if is_selected else stats_fg};"
        )
        self.menu_icon.set_color(QColor(current_fg))
        self.menu_button.setIcon(self.menu_icon)

    def on_color_change(self):
        current_color = self.color_button.palette().button().color()
        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            new_color_hex = color.name()
            old_color_hex = self.parent_manager.nodes_map[self.node_id]["color"]

            def do():
                database.update_node_color(self.node_id, new_color_hex)

            def undo():
                database.update_node_color(self.node_id, old_color_hex)

            self.parent_manager.execute_workspace_command(
                WorkspaceCommand(
                    "Change Node Color",
                    do,
                    undo,
                    lambda: self.parent_manager.refresh_tree_and_emit_update(
                        node_id_to_reselect=self.node_id
                    ),
                )
            )

    def on_export(self):
        self.parent_manager.show_node_export_menu(self.node_id, self.menu_button)

    def on_filter(self):
        self.parent_manager.filter_by_single_node(self.node_id)

    def on_add_child(self):
        self.parent_manager.add_node(parent_id=self.node_id)

    def on_rename(self):
        self.parent_manager.rename_node(self.node_id)

    def on_delete(self):
        self.parent_manager.delete_node(self.node_id)

    def on_merge(self):
        self.parent_manager.merge_node(self.node_id)

    def show_actions_menu(self):
        menu = QMenu(self.parent_manager)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        menu.setWindowOpacity(1.0)
        add_child_action = menu.addAction(
            get_translation("node_tree.add_child_tooltip", self.language)
        )
        rename_action = menu.addAction(
            get_translation("node_tree.rename_tooltip", self.language)
        )
        filter_action = menu.addAction(
            get_translation("node_tree.filter_tooltip", self.language)
        )
        export_action = menu.addAction(
            get_translation("node_tree.export_tooltip", self.language)
        )
        merge_action = menu.addAction(
            get_translation("node_tree.merge_action", self.language)
        )
        delete_action = menu.addAction(
            get_translation("node_tree.delete_tooltip", self.language)
        )
        action = menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
        if action == add_child_action:
            self.on_add_child()
        elif action == rename_action:
            self.on_rename()
        elif action == filter_action:
            self.on_filter()
        elif action == export_action:
            self.on_export()
        elif action == merge_action:
            self.on_merge()
        elif action == delete_action:
            self.on_delete()

    def update_language(self, new_language):
        self.language = new_language
        self.color_button.setToolTip(
            get_translation("node_tree.color_tooltip", self.language)
        )
        self.menu_button.setToolTip(
            get_translation("node_tree.more_actions_tooltip", self.language)
        )


class ExcelExportDialog(QDialog):
    def __init__(self, language, participants, parent=None):
        super().__init__(parent)
        self.language = language
        self.participants = participants
        self.setWindowTitle(get_translation("node_tree.export_excel_option", language))
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        title_label = QLabel(
            get_translation("node_tree.export_excel_question", self.language)
        )
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        info_label = QLabel(
            get_translation("node_tree.export_excel_info", self.language)
        )
        info_label.setWordWrap(True)

        self.mode_combo = FitPopupComboBox()
        self.mode_combo.addItem(
            get_translation("node_tree.export_excel_classification", self.language),
            "classification",
        )
        self.mode_combo.addItem(
            get_translation("node_tree.export_excel_single", self.language), "single"
        )
        self.mode_combo.addItem(
            get_translation("node_tree.export_excel_multi", self.language), "multi"
        )

        self.participant_combo = FitPopupComboBox()
        self.participant_combo.addItem(
            get_translation("node_tree.export_excel_participants_all", self.language),
            None,
        )
        for participant in sorted(self.participants, key=lambda item: item["name"].lower()):
            self.participant_combo.addItem(participant["name"], participant["id"])

        form_layout = QFormLayout()
        form_layout.addRow(
            get_translation("node_tree.export_excel_sheet_field", self.language),
            self.mode_combo,
        )
        form_layout.addRow(
            get_translation("node_tree.export_excel_participant_field", self.language),
            self.participant_combo,
        )

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            get_translation("node_tree.export_excel_confirm", self.language)
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            get_translation("workspace.cancel", self.language)
        )

        layout.addWidget(title_label)
        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def selected_mode(self):
        return self.mode_combo.currentData()

    def selected_participant_id(self):
        return self.participant_combo.currentData()


class MergeNodeDialog(QDialog):
    def __init__(self, node, nodes, language, parent=None):
        super().__init__(parent)
        self.node = node
        self.language = language
        self.nodes_by_id = {candidate["id"]: candidate for candidate in nodes}
        self.setWindowTitle(get_translation("node_tree.merge_title", language))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        self.node_combo = FitPopupComboBox()
        for candidate, depth, number in self._ordered_nodes():
            if candidate["id"] != node["id"]:
                candidate_path = self._node_path(candidate["id"])
                display_name = f"{'    ' * depth}{number} {candidate['name']}"
                self.node_combo.addItem(
                    self._color_icon(candidate["color"]),
                    display_name,
                    candidate["id"],
                )
                combo_index = self.node_combo.count() - 1
                self.node_combo.setItemData(combo_index, candidate_path, Qt.ItemDataRole.ToolTipRole)

        self.keep_current = QRadioButton(
            get_translation("node_tree.merge_keep_current", language, name=node["name"])
        )
        self.keep_other = QRadioButton()
        self.keep_current.setChecked(True)
        self.summary = QLabel()
        self.summary.setWordWrap(True)

        form = QFormLayout()
        form.addRow(get_translation("node_tree.merge_with", language), self.node_combo)
        layout.addLayout(form)
        layout.addWidget(self.keep_current)
        layout.addWidget(self.keep_other)
        layout.addWidget(self.summary)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            get_translation("node_tree.merge_confirm", language)
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            get_translation("workspace.cancel", language)
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.node_combo.currentIndexChanged.connect(self._update_labels)
        self.keep_current.toggled.connect(self._update_labels)
        self._update_labels()

    def _color_icon(self, color_hex):
        pixmap = QPixmap(12, 12)
        pixmap.fill(QColor(color_hex))
        return QIcon(pixmap)

    def _node_path(self, node_id):
        path = []
        current = self.nodes_by_id.get(node_id)
        while current is not None:
            path.append(current["name"])
            current = self.nodes_by_id.get(current["parent_id"])
        return " > ".join(reversed(path))

    def _ordered_nodes(self):
        nodes_by_parent = {None: []}
        for candidate in self.nodes_by_id.values():
            nodes_by_parent.setdefault(candidate["parent_id"], []).append(candidate)
        for children in nodes_by_parent.values():
            children.sort(key=lambda item: item["position"])

        ordered = []

        def visit(parent_id, depth, prefix=""):
            for index, candidate in enumerate(nodes_by_parent.get(parent_id, []), start=1):
                number = f"{prefix}{index}."
                ordered.append((candidate, depth, number))
                visit(candidate["id"], depth + 1, f"{number}")

        visit(None, 0)
        return ordered

    def _update_labels(self):
        other_id = self.node_combo.currentData()
        other_name = self.nodes_by_id[other_id]["name"] if other_id is not None else ""
        self.keep_other.setText(
            get_translation("node_tree.merge_keep_other", self.language, name=other_name)
        )
        removed_name = other_name if self.keep_current.isChecked() else self.node["name"]
        self.summary.setText(
            get_translation("node_tree.merge_summary", self.language, name=removed_name)
        )

    def node_ids(self):
        other_id = self.node_combo.currentData()
        if self.keep_current.isChecked():
            return other_id, self.node["id"]
        return self.node["id"], other_id


class NodeTreeManager(QWidget):
    filter_by_node_family_signal = Signal(list)
    filter_by_single_node_signal = Signal(int)
    node_updated = Signal()
    node_selected_for_coding = Signal(int)

    def __init__(self, project_id, language=None, defer_load=False):
        super().__init__()
        self.project_id = project_id
        self.language = language or "English"
        self.nodes_map = {}
        self.undo_executor = None
        self.setAcceptDrops(True)
        self._is_selection_mode = False
        self.current_document_id = None
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        self.header_label = QLabel(get_translation("node_tree.header", self.language))
        font = self.header_label.font()
        font.setBold(True)
        self.header_label.setFont(font)
        self.add_root_button = QPushButton()
        self.add_root_icon = MaterialIcon("add")
        self.add_root_button.setIcon(self.add_root_icon)
        self.add_root_button.setText(
            get_translation("node_tree.add_root", self.language)
        )
        self.add_root_button.setToolTip(
            get_translation("node_tree.add_root_tooltip", self.language)
        )
        self.add_root_button.clicked.connect(self.add_root_node)
        self.clear_filter_button = QPushButton()
        self.clear_filter_icon = MaterialIcon("filter_list")
        self.clear_filter_button.setIcon(self.clear_filter_icon)
        self.clear_filter_button.setText(
            get_translation("node_tree.show_all", self.language)
        )
        self.clear_filter_button.setToolTip(
            get_translation("node_tree.show_all_tooltip", self.language)
        )
        self.clear_filter_button.clicked.connect(self.clear_all_filters)
        self.scope_combo = FitPopupComboBox()
        self.scope_combo.addItems(
            [
                get_translation("node_tree.scope_current", self.language),
                get_translation("node_tree.scope_project", self.language),
            ]
        )
        self.scope_combo.setToolTip(
            get_translation("node_tree.scope_tooltip", self.language)
        )
        self.scope_combo.setCurrentText(
            get_translation("node_tree.scope_current", self.language)
        )
        self.scope_combo.currentTextChanged.connect(self.load_nodes)
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.scope_combo)
        header_layout.addWidget(self.clear_filter_button)
        header_layout.addWidget(self.add_root_button)
        main_layout.addLayout(header_layout)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setIndentation(20)
        self.tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.setAcceptDrops(True)
        self.tree_widget.highlighting_enabled = True
        self.tree_widget.viewport().installEventFilter(self)
        self._resize_rows_timer = QTimer(self)
        self._resize_rows_timer.setSingleShot(True)
        self._resize_rows_timer.setInterval(90)
        self._resize_rows_timer.timeout.connect(self._update_node_item_sizes)
        main_layout.addWidget(self.tree_widget)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.mousePressEvent = self.mousePressEvent
        self.original_tree_widget_dropEvent = self.tree_widget.dropEvent
        self.tree_widget.dropEvent = self.dropEvent
        self.tree_widget.keyPressEvent = self.keyPressEvent
        self._branch_right_icon = ""
        self._branch_down_icon = ""
        self.update_theme(load_settings().get("theme", "Light"))
        if not defer_load:
            self.load_nodes()

    def set_undo_executor(self, undo_executor):
        self.undo_executor = undo_executor

    def execute_workspace_command(self, command: WorkspaceCommand):
        if self.undo_executor:
            self.undo_executor(command)
        else:
            command.do()
            command.after_refresh()

    def set_highlighting_active(self, active):
        """Public slot to enable/disable drag-drop highlighting."""
        self.tree_widget.highlighting_enabled = active

    def mousePressEvent(self, event):
        if self.tree_widget.itemAt(event.position().toPoint()) is None:
            self.tree_widget.clearSelection()
            self.tree_widget.setCurrentItem(None)
        super(QTreeWidget, self.tree_widget).mousePressEvent(event)

    def dropEvent(self, event: QDropEvent):
        """
        Handles dropping an item to reorder or reparent it. This method defers the
        final UI refresh to prevent crashing.
        """
        if not self.tree_widget.highlighting_enabled or not event.source():
            event.ignore()
            return

        source_item = self.tree_widget.currentItem()
        if not source_item:
            event.ignore()
            return

        source_id = source_item.data(0, 1)
        if source_id is None:
            event.ignore()
            return
        before_layout = workspace_snapshot_repository.get_node_layout(self.project_id)
        self.original_tree_widget_dropEvent(event)
        it = QTreeWidgetItemIterator(self.tree_widget)
        new_item = None
        while it.value():
            item = it.value()
            if item.data(0, 1) == source_id:
                new_item = item
                break
            it += 1

        if not new_item:
            QTimer.singleShot(0, self.refresh_tree_and_emit_update)
            return

        new_parent_item = new_item.parent()
        new_parent_id = new_parent_item.data(0, 1) if new_parent_item else None

        if new_parent_item:
            siblings = [
                new_parent_item.child(i) for i in range(new_parent_item.childCount())
            ]
        else:
            siblings = [
                self.tree_widget.topLevelItem(i)
                for i in range(self.tree_widget.topLevelItemCount())
            ]

        db_order_updates = [
            (i, item.data(0, 1))
            for i, item in enumerate(siblings)
            if item.data(0, 1) is not None
        ]

        def do():
            database.update_node_parent(source_id, new_parent_id)
            if db_order_updates:
                database.update_node_order(db_order_updates)

        def undo():
            workspace_snapshot_repository.restore_node_layout(before_layout)

        self.execute_workspace_command(
            WorkspaceCommand(
                "Move Node",
                do,
                undo,
                lambda: QTimer.singleShot(
                    0,
                    lambda: self.refresh_tree_and_emit_update(
                        node_id_to_reselect=source_id
                    ),
                ),
            )
        )

    def keyPressEvent(self, event: QKeyEvent):
        """Handles key presses for actions like rename and delete."""
        current_item = self.tree_widget.currentItem()
        if not current_item:
            super(QTreeWidget, self.tree_widget).keyPressEvent(event)
            return

        node_id = current_item.data(0, 1)
        if node_id is None:
            super(QTreeWidget, self.tree_widget).keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_F2:
            self.rename_node(node_id)
            event.accept()
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_node(node_id)
            event.accept()
        else:
            super(QTreeWidget, self.tree_widget).keyPressEvent(event)

    def load_nodes(self, node_id_to_reselect=None):
        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)
        self._clear_tree_items()
        nodes = database.get_nodes_for_project(self.project_id)
        self.nodes_map = {n["id"]: n for n in nodes}
        self.nodes_by_parent = {n_id: [] for n_id in self.nodes_map}
        self.nodes_by_parent[None] = []
        for n_id, node in self.nodes_map.items():
            self.nodes_by_parent.setdefault(node["parent_id"], []).append(node)
        for children_list in self.nodes_by_parent.values():
            children_list.sort(key=lambda x: x["position"])
        total_words, aggregated_stats = self._node_stats_for_current_scope()

        item_to_reselect = None

        def add_items_recursively(parent_widget, parent_id, prefix=""):
            nonlocal item_to_reselect
            children = self.nodes_by_parent.get(parent_id, [])
            for i, node_data in enumerate(children):
                current_prefix = f"{prefix}{i + 1}."
                name_text = f"{current_prefix} {node_data['name']}"
                stats_text = self._format_stats_text(
                    aggregated_stats.get(
                        node_data["id"], {"word_count": 0, "segment_count": 0}
                    ),
                    total_words,
                )

                tree_item = QTreeWidgetItem(parent_widget)
                tree_item.setData(0, 1, node_data["id"])

                item_widget = NodeItemWidget(
                    node_data["id"],
                    node_data["color"],
                    name_text,
                    stats_text,
                    self,
                    language=self.language,
                )
                self.tree_widget.setItemWidget(tree_item, 0, item_widget)

                if node_data["id"] == node_id_to_reselect:
                    item_to_reselect = tree_item
                add_items_recursively(tree_item, node_data["id"], prefix=current_prefix)

        add_items_recursively(self.tree_widget, None)
        self.tree_widget.expandAll()
        self._update_node_item_sizes()
        if item_to_reselect:
            self.tree_widget.setCurrentItem(item_to_reselect)
        self.tree_widget.blockSignals(False)
        if node_id_to_reselect is not None:
            QTimer.singleShot(
                0,
                lambda node_id=node_id_to_reselect: self._scroll_node_into_view(node_id),
            )

    def refresh_stats(self):
        total_words, aggregated_stats = self._node_stats_for_current_scope()
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            widget = self.tree_widget.itemWidget(item, 0)
            if isinstance(widget, NodeItemWidget):
                stats_text = self._format_stats_text(
                    aggregated_stats.get(
                        widget.node_id, {"word_count": 0, "segment_count": 0}
                    ),
                    total_words,
                )
                widget.stats_label.setText(stats_text)
                widget.stats_label.setVisible(bool(stats_text))
            it += 1
        self.tree_widget.viewport().update()

    def _node_stats_for_current_scope(self):
        scope = self.scope_combo.currentText()
        total_words = 0
        doc_id_for_stats = None
        if scope == get_translation("node_tree.scope_current", self.language):
            if self.current_document_id:
                total_words = database.get_document_word_count(self.current_document_id)
                doc_id_for_stats = self.current_document_id
        else:
            total_words = database.get_project_word_count(self.project_id)

        node_stats = database.get_node_statistics(self.project_id, doc_id_for_stats)
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
        return total_words, aggregated_stats

    @staticmethod
    def _format_stats_text(stats, total_words):
        segment_count = stats["segment_count"]
        if segment_count <= 0:
            return ""
        percentage = (stats["word_count"] / total_words * 100) if total_words > 0 else 0
        return f"{percentage:.1f}% | {segment_count} Segments"

    def set_current_document_id(self, doc_id):
        self.current_document_id = doc_id
        if self.scope_combo.currentText() == get_translation(
            "node_tree.scope_current", self.language
        ):
            self.load_nodes()

    def set_selection_mode(self, enabled: bool):
        self._is_selection_mode = enabled
        self._apply_tree_widget_style()

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if self._is_selection_mode and item:
            self.tree_widget.blockSignals(True)
            node_id = item.data(0, 1)
            if node_id is not None:
                self.node_selected_for_coding.emit(node_id)
            self.tree_widget.blockSignals(False)

    def refresh_tree_and_emit_update(self, node_id_to_reselect=None):
        self.load_nodes(node_id_to_reselect=node_id_to_reselect)
        self.node_updated.emit()

    def _clear_tree_items(self):
        while self.tree_widget.topLevelItemCount():
            item = self.tree_widget.takeTopLevelItem(0)
            self._dispose_tree_item(item)

    def _dispose_tree_item(self, item):
        while item.childCount():
            child = item.takeChild(0)
            self._dispose_tree_item(child)
        widget = self.tree_widget.itemWidget(item, 0)
        if widget is not None:
            self.tree_widget.removeItemWidget(item, 0)
            widget.deleteLater()
        del item

    def _scroll_node_into_view(self, node_id):
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            if item.data(0, 1) == node_id:
                self.tree_widget.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
                break
            it += 1

    def _update_node_item_sizes(self):
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            widget = self.tree_widget.itemWidget(item, 0)
            if isinstance(widget, NodeItemWidget):
                item.setSizeHint(
                    0, widget.update_wrap_width(self._available_node_item_width(item))
                )
            it += 1
        self.tree_widget.doItemsLayout()
        self.tree_widget.viewport().update()

    def _available_node_item_width(self, item):
        depth = 0
        parent = item.parent()
        while parent:
            depth += 1
            parent = parent.parent()
        scrollbar_width = self.tree_widget.verticalScrollBar().sizeHint().width()
        return max(
            220,
            self.tree_widget.viewport().width()
            - (depth * self.tree_widget.indentation())
            - scrollbar_width
            - 24,
        )

    def eventFilter(self, watched, event):
        if watched is self.tree_widget.viewport() and event.type() == QEvent.Type.Resize:
            self._resize_rows_timer.start()
        return super().eventFilter(watched, event)

    def clear_all_filters(self):
        self.tree_widget.clearSelection()
        self.tree_widget.setCurrentItem(None)
        self.filter_by_node_family_signal.emit([])

    def on_selection_changed(
        self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem
    ):
        if previous_item:
            widget = self.tree_widget.itemWidget(previous_item, 0)
            if widget:
                widget.set_selected_style(False)

        if current_item:
            widget = self.tree_widget.itemWidget(current_item, 0)
            if widget:
                widget.set_selected_style(True)

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
            cleaned_name = new_name.strip()

            def do():
                database.update_node_name(node_id, cleaned_name)

            def undo():
                database.update_node_name(node_id, current_name)

            self.execute_workspace_command(
                WorkspaceCommand(
                    "Rename Node",
                    do,
                    undo,
                    lambda: self.refresh_tree_and_emit_update(
                        node_id_to_reselect=node_id
                    ),
                )
            )

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
                node_id = None
                snapshot = None

                def do():
                    nonlocal node_id, snapshot
                    if snapshot:
                        workspace_snapshot_repository.restore_node_subtree_snapshot(
                            snapshot
                        )
                    else:
                        node_id = database.add_node(
                            pid, name.strip(), parent_id, new_color
                        )
                        snapshot = (
                            workspace_snapshot_repository.get_node_subtree_snapshot(
                                node_id
                            )
                        )

                def undo():
                    if node_id:
                        database.delete_node_and_children(node_id)

                self.execute_workspace_command(
                    WorkspaceCommand(
                        "Add Node",
                        do,
                        undo,
                        lambda: self.refresh_tree_and_emit_update(
                            node_id_to_reselect=node_id or parent_id
                        ),
                    )
                )
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

        parent_id_to_reselect = node_data["parent_id"]

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{node_data['name']}' and all its children? This will also remove all associated codings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            snapshot = workspace_snapshot_repository.get_node_subtree_snapshot(node_id)

            def do():
                database.delete_node_and_children(node_id)

            def undo():
                workspace_snapshot_repository.restore_node_subtree_snapshot(snapshot)

            self.execute_workspace_command(
                WorkspaceCommand(
                    "Delete Node",
                    do,
                    undo,
                    lambda: self.refresh_tree_and_emit_update(
                        node_id_to_reselect=parent_id_to_reselect
                    ),
                )
            )

    def merge_node(self, node_id):
        node = self.nodes_map.get(node_id)
        if not node or len(self.nodes_map) < 2:
            QMessageBox.information(
                self,
                get_translation("node_tree.merge_title", self.language),
                get_translation("node_tree.merge_no_candidates", self.language),
            )
            return

        dialog = MergeNodeDialog(node, list(self.nodes_map.values()), self.language, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        source_id, target_id = dialog.node_ids()
        source_snapshot = workspace_snapshot_repository.get_node_subtree_snapshot(
            source_id
        )
        target_snapshot = workspace_snapshot_repository.get_node_subtree_snapshot(
            target_id
        )

        def do():
            database.merge_nodes(source_id, target_id)

        def undo():
            database.delete_node_and_children(target_id)
            workspace_snapshot_repository.restore_node_subtree_snapshot(target_snapshot)
            workspace_snapshot_repository.restore_node_subtree_snapshot(source_snapshot)

        try:
            self.execute_workspace_command(
                WorkspaceCommand(
                    "Merge Nodes",
                    do,
                    undo,
                    lambda: self.refresh_tree_and_emit_update(
                        node_id_to_reselect=target_id
                    ),
                )
            )
        except ValueError as error:
            QMessageBox.warning(
                self,
                get_translation("node_tree.merge_error_title", self.language),
                str(error),
            )

    def filter_by_single_node(self, node_id):
        self.filter_by_single_node_signal.emit(node_id)

    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        node_id = item.data(0, 1)
        if node_id is None:
            return
        menu = QMenu()
        rename_action = menu.addAction(
            get_translation("node_tree.context_rename", self.language)
        )
        delete_action = menu.addAction(
            get_translation("node_tree.context_delete", self.language)
        )
        merge_action = menu.addAction(
            get_translation("node_tree.merge_action", self.language)
        )
        menu.addSeparator()
        add_child_action = menu.addAction(
            get_translation("node_tree.context_add_child", self.language)
        )
        menu.addSeparator()
        export_action = menu.addAction(
            get_translation("node_tree.context_export", self.language)
        )
        action = menu.exec(self.tree_widget.mapToGlobal(position))
        if action == rename_action:
            self.rename_node(node_id)
        elif action == delete_action:
            self.delete_node(node_id)
        elif action == merge_action:
            self.merge_node(node_id)
        elif action == add_child_action:
            self.add_node(parent_id=node_id)
        elif action == export_action:
            widget = self.tree_widget.itemWidget(item, 0)
            self.show_node_export_menu(node_id, widget.menu_button)

    def show_node_export_menu(self, node_id, button):
        menu = QMenu(self)
        action_export_word = menu.addAction(
            get_translation("node_tree.export_word", self.language)
        )
        action_export_excel = menu.addAction(
            get_translation("node_tree.export_excel", self.language)
        )
        action_export_word.triggered.connect(
            lambda: export_node_family_to_word(self.project_id, node_id, self)
        )
        action_export_excel.triggered.connect(
            lambda: self.export_node_family_to_excel_handler(node_id)
        )
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def show_excel_export_options(self, node_id=None):
        """
        Displays a dialog box with all available Excel export options.
        This can be called from the node tree context menu or the main menu.
        """
        if isinstance(node_id, bool):
            node_id = None
        if node_id is None:
            node_id = self.get_selected_node_id()
        participants = database.get_participants_for_project(self.project_id)
        dialog = ExcelExportDialog(self.language, participants, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_mode = dialog.selected_mode()
        participant_id = dialog.selected_participant_id()
        if selected_mode == "classification":
            export_classification_workbook(
                self.project_id,
                self,
                participant_id=participant_id,
                start_node_id=node_id,
                language=self.language,
            )
        elif selected_mode == "single":
            if node_id is None:
                export_project_to_excel_single_sheet(
                    self.project_id, self, participant_id=participant_id
                )
            else:
                export_node_family_to_excel(
                    self.project_id, node_id, self, participant_id=participant_id
                )
        elif selected_mode == "multi":
            if node_id is None:
                export_to_excel(self.project_id, self, participant_id=participant_id)
            else:
                export_node_family_to_excel_multi_sheet(
                    self.project_id, node_id, self, participant_id=participant_id
                )

    def export_node_family_to_excel_handler(self, node_id):
        """
        This handler is specifically for the right-click context menu.
        It now calls the main dialog function.
        """
        self.show_excel_export_options(node_id=node_id)

    def add_root_node(self):
        name, ok = QInputDialog.getText(
            self,
            get_translation("node_tree.add_root_dialog", self.language),
            get_translation("node_tree.add_root_prompt", self.language),
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
                node_id = None
                snapshot = None

                def do():
                    nonlocal node_id, snapshot
                    if snapshot:
                        workspace_snapshot_repository.restore_node_subtree_snapshot(
                            snapshot
                        )
                    else:
                        node_id = database.add_node(pid, name.strip(), None, new_color)
                        snapshot = (
                            workspace_snapshot_repository.get_node_subtree_snapshot(
                                node_id
                            )
                        )

                def undo():
                    if node_id:
                        database.delete_node_and_children(node_id)

                self.execute_workspace_command(
                    WorkspaceCommand(
                        "Add Root Node",
                        do,
                        undo,
                        lambda: self.refresh_tree_and_emit_update(
                            node_id_to_reselect=node_id
                        ),
                    )
                )
            except (ValueError, TypeError) as e:
                QMessageBox.critical(
                    self,
                    get_translation("node_tree.error", self.language),
                    (
                        str(e)
                        if isinstance(e, ValueError)
                        else get_translation(
                            "node_tree.error_invalid_project",
                            self.language,
                            project_id=self.project_id,
                        )
                    ),
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    get_translation("node_tree.error", self.language),
                    get_translation(
                        "node_tree.error_failed_add_root", self.language, error=str(e)
                    ),
                )

    def select_node_by_id(self, node_id: int):
        """
        Navigates the tree widget to select and highlight the node with the given ID.
        """
        self.tree_widget.blockSignals(True)

        it = QTreeWidgetItemIterator(self.tree_widget)
        found_item = None
        while it.value():
            item = it.value()
            if item.data(0, 1) == node_id:
                found_item = item
                break
            it += 1

        previous_item = self.tree_widget.currentItem()

        if found_item:
            self.tree_widget.setCurrentItem(found_item)
            self.tree_widget.scrollToItem(
                found_item, QAbstractItemView.ScrollHint.PositionAtCenter
            )
            self.on_selection_changed(found_item, previous_item)

        self.tree_widget.blockSignals(False)

    def highlight_node_by_id(self, node_id: int):
        """
        Highlights (selects and scrolls to) the node with the given ID in the tree widget,
        but does NOT trigger filtering or emit any signals. Used for visual highlight only.
        Also updates the stats style for the highlighted item.
        """
        self.tree_widget.blockSignals(True)

        # Un-highlight previous item
        previous_item = self.tree_widget.currentItem()
        if previous_item:
            prev_widget = self.tree_widget.itemWidget(previous_item, 0)
            if prev_widget:
                prev_widget.set_selected_style(False)

        it = QTreeWidgetItemIterator(self.tree_widget)
        found_item = None
        while it.value():
            item = it.value()
            if item.data(0, 1) == node_id:
                found_item = item
                break
            it += 1

        if found_item:
            self.tree_widget.setCurrentItem(found_item)
            self.tree_widget.scrollToItem(
                found_item, QAbstractItemView.ScrollHint.PositionAtCenter
            )
            widget = self.tree_widget.itemWidget(found_item, 0)
            if widget:
                widget.set_selected_style(True)

        self.tree_widget.blockSignals(False)

    def update_language(self, new_language):
        self.language = new_language
        self.header_label.setText(get_translation("node_tree.header", self.language))
        self.add_root_button.setText(
            get_translation("node_tree.add_root", self.language)
        )
        self.add_root_button.setToolTip(
            get_translation("node_tree.add_root_tooltip", self.language)
        )
        self.clear_filter_button.setText(
            get_translation("node_tree.show_all", self.language)
        )
        self.clear_filter_button.setToolTip(
            get_translation("node_tree.show_all_tooltip", self.language)
        )
        self.update_theme(load_settings().get("theme", "Light"))
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        self.scope_combo.addItems(
            [
                get_translation("node_tree.scope_current", self.language),
                get_translation("node_tree.scope_project", self.language),
            ]
        )
        self.scope_combo.setCurrentText(
            get_translation("node_tree.scope_current", self.language)
        )
        self.scope_combo.setToolTip(
            get_translation("node_tree.scope_tooltip", self.language)
        )
        self.scope_combo.blockSignals(False)
        # Update all NodeItemWidgets
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            widget = self.tree_widget.itemWidget(item, 0)
            if widget and hasattr(widget, "update_language"):
                widget.update_language(new_language)
            it += 1

    def update_theme(self, theme):
        is_dark = get_effective_theme_mode(theme) == "Dark"
        fg = QColor("#f0f0f0" if is_dark else "#000000")
        disabled_fg = QColor("#a8a8a8" if is_dark else "#5e5e5e")
        branch_suffix = "dark" if is_dark else "light"
        self._branch_right_icon = _resource_url(f"tree-chevron-right-{branch_suffix}.svg")
        self._branch_down_icon = _resource_url(f"tree-chevron-down-{branch_suffix}.svg")
        self.add_root_icon.set_color(fg, QIcon.Mode.Normal)
        self.add_root_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.clear_filter_icon.set_color(fg, QIcon.Mode.Normal)
        self.clear_filter_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.add_root_button.setIcon(self.add_root_icon)
        self.clear_filter_button.setIcon(self.clear_filter_icon)
        self._apply_tree_widget_style()

    def _apply_tree_widget_style(self):
        border = "2px solid #0078d7" if self._is_selection_mode else "none"
        self.tree_widget.setStyleSheet(
            f"""
            QTreeWidget {{
                border: {border};
            }}
            QTreeView::branch {{
                background: transparent;
                border-image: none;
                image: none;
                width: 14px;
                height: 14px;
            }}
            QTreeView::branch:has-children:closed,
            QTreeView::branch:closed:has-children:!has-siblings,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: url("{self._branch_right_icon}");
            }}
            QTreeView::branch:open:has-children,
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: url("{self._branch_down_icon}");
            }}
            """
        )

    def get_selected_node_id(self):
        """
        Returns the node ID of the currently selected item in the tree widget, or None if nothing is selected.
        """
        current_item = self.tree_widget.currentItem()
        if current_item is not None:
            return current_item.data(0, 1)
        return None
