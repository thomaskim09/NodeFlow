import database
from repositories.base import initialize_database


def test_repository_crud_and_descendants():
    initialize_database()

    database.add_project("Demo")
    project = database.get_all_projects()[0]
    project_id = project["id"]

    database.add_participant(project_id, "Alice")
    participant = database.get_participants_for_project(project_id)[0]
    participant_id = participant["id"]

    document_id = database.add_document(project_id, "Doc 1", "alpha beta gamma", participant_id)
    root_id = database.add_node(project_id, "Theme", None, "#FFFF00")
    child_id = database.add_node(project_id, "Detail", root_id, "#FF0000")
    database.add_coded_segment(document_id, root_id, participant_id, 0, 5, "alpha")
    database.add_coded_segment(document_id, child_id, participant_id, 6, 10, "beta")

    descendants = database.get_node_descendants(root_id)
    segments = database.get_coded_segments_for_document(document_id)

    assert descendants == [child_id]
    assert len(segments) == 2
    assert database.get_document_word_count(document_id) == 3
