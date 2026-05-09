import database
from repositories.base import initialize_database
from services.dashboard_service import DashboardQuery, dashboard_service


def test_dashboard_service_aggregates_project_scope():
    initialize_database()

    database.add_project("Analysis")
    project_id = database.get_all_projects()[0]["id"]
    database.add_participant(project_id, "Alice")
    participant_id = database.get_participants_for_project(project_id)[0]["id"]
    document_id = database.add_document(
        project_id, "Interview", "alpha beta gamma delta", participant_id
    )
    node_one = database.add_node(project_id, "Theme 1", None, "#111111")
    node_two = database.add_node(project_id, "Theme 2", None, "#222222")
    database.add_coded_segment(document_id, node_one, participant_id, 0, 5, "alpha")
    database.add_coded_segment(document_id, node_two, participant_id, 6, 10, "beta")
    database.add_coded_segment(document_id, node_one, participant_id, 0, 5, "alpha")

    results = dashboard_service.load(
        DashboardQuery(project_id=project_id, doc_id=-1, part_id=-1, node_id=-1)
    )

    assert results["total_words"] == 4
    assert results["coded_words"] == 3
    assert len(results["segments"]) == 3
    assert "Theme 1" in results["co_occurrence_headers"]
