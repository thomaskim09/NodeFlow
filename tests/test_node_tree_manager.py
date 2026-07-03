import database
from repositories.base import initialize_database
from ui.workspace import node_tree_manager as node_tree_manager_module
from ui.workspace.node_tree_manager import NodeTreeManager


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
