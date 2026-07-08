import database
from repositories.base import initialize_database
from ui.workspace.participant_manager import ParticipantManager
from ui.workspace import node_tree_manager as node_tree_manager_module
from ui.workspace.node_tree_manager import MergeNodeDialog, NodeTreeManager
from services.workspace_history_service import WorkspaceHistory


def test_show_excel_export_options_treats_qaction_bool_as_project_export(
    qtbot, monkeypatch
):
    initialize_database()
    database.add_project("Exports")
    project_id = database.get_all_projects()[0]["id"]
    database.add_participant(project_id, "R1")
    database.add_node(project_id, "Theme", None, "#111111")

    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)

    class FakeDialog:
        def __init__(self, language, participants, parent=None):
            self.language = language
            self.participants = participants

        def exec(self):
            return node_tree_manager_module.QDialog.DialogCode.Accepted

        def selected_mode(self):
            return "classification"

        def selected_participant_id(self):
            return None

    calls = []
    monkeypatch.setattr(node_tree_manager_module, "ExcelExportDialog", FakeDialog)
    monkeypatch.setattr(
        node_tree_manager_module,
        "export_classification_workbook",
        lambda project_id, parent, participant_id=None, start_node_id=None, language="English": calls.append(
            {
                "project_id": project_id,
                "participant_id": participant_id,
                "start_node_id": start_node_id,
                "language": language,
            }
        ),
    )

    manager.show_excel_export_options(False)

    assert calls == [
        {
            "project_id": project_id,
            "participant_id": None,
            "start_node_id": None,
            "language": "English",
        }
    ]


def test_load_nodes_scrolls_reselected_node_into_view(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Scroll Nodes")
    project_id = database.get_all_projects()[0]["id"]
    target_node_id = None
    for index in range(20):
        target_node_id = database.add_node(
            project_id, f"Theme {index}", None, f"#{index:06d}"
        )

    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)

    calls = []
    original_scroll = manager.tree_widget.scrollToItem

    def capture_scroll(item, hint):
        calls.append((item.data(0, 1), hint))
        return original_scroll(item, hint)

    monkeypatch.setattr(manager.tree_widget, "scrollToItem", capture_scroll)

    manager.load_nodes(node_id_to_reselect=target_node_id)
    qtbot.wait(10)

    assert calls
    assert calls[-1][0] == target_node_id
    assert calls[-1][1] == node_tree_manager_module.QAbstractItemView.ScrollHint.PositionAtCenter


def test_clicking_selected_node_clears_filter_and_selection(qtbot):
    initialize_database()
    database.add_project("Toggle Node")
    project_id = database.get_all_projects()[0]["id"]
    node_id = database.add_node(project_id, "Theme", None, "#111111")

    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)
    item = manager.tree_widget.topLevelItem(0)
    emitted_filters = []
    manager.filter_by_node_family_signal.connect(emitted_filters.append)

    manager.tree_widget.setCurrentItem(item)
    manager.on_item_clicked(item, 0)
    assert manager.get_selected_node_id() == node_id
    assert emitted_filters[-1] == [node_id]

    manager.on_item_clicked(item, 0)
    assert manager.get_selected_node_id() is None
    assert emitted_filters[-1] == []


def test_clicking_selected_participant_clears_filter_and_selection(qtbot):
    initialize_database()
    database.add_project("Toggle Participant")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")

    manager = ParticipantManager(project_id, "English")
    qtbot.addWidget(manager)
    item = manager.list_widget.item(0)
    emitted_filters = []
    manager.participant_selected.connect(emitted_filters.append)

    manager.list_widget.setCurrentItem(item)
    manager.on_item_clicked(item)
    assert manager.get_selected_participant_id() == participant_id
    assert emitted_filters[-1] == participant_id

    manager.on_item_clicked(item)
    assert manager.get_selected_participant_id() is None
    assert emitted_filters[-1] == 0


def test_long_node_names_wrap_instead_of_truncating(qtbot):
    initialize_database()
    database.add_project("Wrap Nodes")
    project_id = database.get_all_projects()[0]["id"]
    long_name = "This is a very long node name that should wrap onto multiple lines"
    database.add_node(project_id, long_name, None, "#111111")

    manager = NodeTreeManager(project_id, "English")
    manager.resize(320, 500)
    qtbot.addWidget(manager)
    manager.show()
    manager.load_nodes()
    qtbot.wait(10)

    item = manager.tree_widget.topLevelItem(0)
    widget = manager.tree_widget.itemWidget(item, 0)

    assert widget.name_label.wordWrap()
    assert widget.name_label.height() > widget.name_label.fontMetrics().height()
    assert item.sizeHint(0).height() >= widget.height()


def test_selected_row_geometry_stays_aligned_below_wrapped_node(qtbot):
    initialize_database()
    database.add_project("Selection Alignment")
    project_id = database.get_all_projects()[0]["id"]
    parent_id = database.add_node(
        project_id,
        "Analytics and Reporting",
        None,
        "#111111",
    )
    target_id = database.add_node(project_id, "Excel Exports", parent_id, "#222222")
    database.add_node(project_id, "Short Node", None, "#333333")

    manager = NodeTreeManager(project_id, "English")
    manager.resize(320, 500)
    qtbot.addWidget(manager)
    manager.show()
    manager.load_nodes(node_id_to_reselect=target_id)
    qtbot.wait(50)

    item = None
    it = node_tree_manager_module.QTreeWidgetItemIterator(manager.tree_widget)
    while it.value():
        candidate = it.value()
        if candidate.data(0, 1) == target_id:
            item = candidate
            break
        it += 1

    widget = manager.tree_widget.itemWidget(item, 0)
    item_rect = manager.tree_widget.visualItemRect(item)
    widget_rect = widget.geometry()

    assert item_rect.top() == widget_rect.top()
    assert item_rect.height() == widget_rect.height()


def test_merge_node_supports_undo_and_redo(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Merge History")
    project_id = database.get_all_projects()[0]["id"]
    source_id = database.add_node(project_id, "Source", None, "#111111")
    target_id = database.add_node(project_id, "Target", None, "#222222")
    child_id = database.add_node(project_id, "Child", source_id, "#333333")
    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)
    history = WorkspaceHistory()
    manager.set_undo_executor(history.execute)

    class AcceptedMergeDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return node_tree_manager_module.QDialog.DialogCode.Accepted

        def node_ids(self):
            return source_id, target_id

    monkeypatch.setattr(node_tree_manager_module, "MergeNodeDialog", AcceptedMergeDialog)

    manager.merge_node(source_id)
    nodes = {node["id"]: node for node in database.get_nodes_for_project(project_id)}
    assert source_id not in nodes
    assert nodes[child_id]["parent_id"] == target_id

    history.undo()
    nodes = {node["id"]: node for node in database.get_nodes_for_project(project_id)}
    assert source_id in nodes
    assert nodes[child_id]["parent_id"] == source_id

    history.redo()
    nodes = {node["id"]: node for node in database.get_nodes_for_project(project_id)}
    assert source_id not in nodes
    assert nodes[child_id]["parent_id"] == target_id


def test_merge_node_allows_second_merge_after_refresh(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Merge Twice")
    project_id = database.get_all_projects()[0]["id"]
    first_id = database.add_node(project_id, "First", None, "#111111")
    second_id = database.add_node(project_id, "Second", None, "#222222")
    third_id = database.add_node(project_id, "Third", None, "#333333")

    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)

    selections = iter([(first_id, second_id), (second_id, third_id)])

    class AcceptedMergeDialog:
        def __init__(self, *args, **kwargs):
            self._selection = next(selections)

        def exec(self):
            return node_tree_manager_module.QDialog.DialogCode.Accepted

        def node_ids(self):
            return self._selection

    monkeypatch.setattr(node_tree_manager_module, "MergeNodeDialog", AcceptedMergeDialog)

    manager.merge_node(second_id)
    manager.merge_node(third_id)

    remaining_ids = {node["id"] for node in database.get_nodes_for_project(project_id)}

    assert remaining_ids == {third_id}


def test_merge_node_allows_double_undo_after_two_merges(qtbot, monkeypatch):
    initialize_database()
    database.add_project("Merge Undo Twice")
    project_id = database.get_all_projects()[0]["id"]
    first_id = database.add_node(project_id, "First", None, "#111111")
    second_id = database.add_node(project_id, "Second", None, "#222222")
    third_id = database.add_node(project_id, "Third", None, "#333333")

    manager = NodeTreeManager(project_id, "English")
    qtbot.addWidget(manager)
    history = WorkspaceHistory()
    manager.set_undo_executor(history.execute)

    selections = iter([(first_id, second_id), (second_id, third_id)])

    class AcceptedMergeDialog:
        def __init__(self, *args, **kwargs):
            self._selection = next(selections)

        def exec(self):
            return node_tree_manager_module.QDialog.DialogCode.Accepted

        def node_ids(self):
            return self._selection

    monkeypatch.setattr(node_tree_manager_module, "MergeNodeDialog", AcceptedMergeDialog)

    manager.merge_node(second_id)
    manager.merge_node(third_id)
    history.undo()
    history.undo()

    remaining_ids = {node["id"] for node in database.get_nodes_for_project(project_id)}

    assert remaining_ids == {first_id, second_id, third_id}


def test_merge_dialog_shows_node_path_and_color_in_dropdown(qtbot):
    initialize_database()
    database.add_project("Merge Labels")
    project_id = database.get_all_projects()[0]["id"]
    parent_id = database.add_node(project_id, "Parent", None, "#111111")
    current_id = database.add_node(project_id, "Current", None, "#222222")
    child_id = database.add_node(project_id, "Child", parent_id, "#33AA55")
    sibling_id = database.add_node(project_id, "Sibling", None, "#AA3355")
    nodes = database.get_nodes_for_project(project_id)
    current_node = next(node for node in nodes if node["id"] == current_id)

    dialog = MergeNodeDialog(current_node, nodes, "English")
    qtbot.addWidget(dialog)

    parent_index = dialog.node_combo.findData(parent_id)
    option_index = dialog.node_combo.findData(child_id)
    sibling_index = dialog.node_combo.findData(sibling_id)

    assert parent_index < option_index < sibling_index
    assert dialog.node_combo.itemText(parent_index) == "1. Parent"
    assert dialog.node_combo.itemText(option_index) == "    1.1. Child"
    assert dialog.node_combo.itemData(option_index, node_tree_manager_module.Qt.ItemDataRole.ToolTipRole) == "Parent > Child"
    assert not dialog.node_combo.itemIcon(option_index).isNull()
