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


def test_update_document_text_and_segments_persists_ranges_and_deletes_empty_segments():
    initialize_database()

    database.add_project("Segment Save")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")
    document_id = database.add_document(
        project_id, "Doc 1", "alpha beta gamma", participant_id
    )
    node_id = database.add_node(project_id, "Theme", None, "#FFFF00")
    kept_id = database.add_coded_segment(
        document_id, node_id, participant_id, 6, 10, "beta"
    )
    deleted_id = database.add_coded_segment(
        document_id, node_id, participant_id, 11, 16, "gamma"
    )

    database.update_document_text_and_segments(
        document_id,
        "alpha delta",
        [
            {
                "id": kept_id,
                "segment_start": 6,
                "segment_end": 11,
                "content_preview": "delta",
            }
        ],
        [deleted_id],
    )

    content, _ = database.get_document_content(document_id)
    segments = database.get_coded_segments_for_document(document_id)

    assert content == "alpha delta"
    assert len(segments) == 1
    assert segments[0]["id"] == kept_id
    assert segments[0]["segment_start"] == 6
    assert segments[0]["segment_end"] == 11
    assert segments[0]["content_preview"] == "delta"


def test_segment_remark_updates_and_survives_range_update():
    initialize_database()
    database.add_project("Segment Remark")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")
    document_id = database.add_document(
        project_id, "Doc 1", "alpha beta gamma", participant_id
    )
    node_id = database.add_node(project_id, "Theme", None, "#FFFF00")
    segment_id = database.add_coded_segment(
        document_id, node_id, participant_id, 6, 10, "beta"
    )

    database.update_coded_segment_remark(segment_id, "Needs review")
    database.update_coded_segment(segment_id, 6, 16, "beta gamma")

    segment = database.get_coded_segments_for_document(document_id)[0]
    assert segment["remark"] == "Needs review"
    assert segment["content_preview"] == "beta gamma"
