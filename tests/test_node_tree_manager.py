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
