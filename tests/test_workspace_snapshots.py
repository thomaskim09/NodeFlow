import database
from repositories.base import initialize_database
from repositories.workspace_snapshot_repository import workspace_snapshot_repository


def _create_project_fixture():
    initialize_database()
    database.add_project("Undo Demo")
    project_id = database.get_all_projects()[0]["id"]
    participant_id = database.add_participant(project_id, "Alice")
    document_id = database.add_document(
        project_id, "Doc 1", "alpha beta gamma", participant_id
    )
    root_id = database.add_node(project_id, "Theme", None, "#FFFF00")
    child_id = database.add_node(project_id, "Detail", root_id, "#FF0000")
    root_segment_id = database.add_coded_segment(
        document_id, root_id, participant_id, 0, 5, "alpha"
    )
    child_segment_id = database.add_coded_segment(
        document_id, child_id, participant_id, 6, 10, "beta"
    )
    return {
        "project_id": project_id,
        "participant_id": participant_id,
        "document_id": document_id,
        "root_id": root_id,
        "child_id": child_id,
        "root_segment_id": root_segment_id,
        "child_segment_id": child_segment_id,
    }


def test_node_subtree_snapshot_restores_nodes_and_segments():
    fixture = _create_project_fixture()
    snapshot = workspace_snapshot_repository.get_node_subtree_snapshot(
        fixture["root_id"]
    )

    database.delete_node_and_children(fixture["root_id"])
    assert database.get_nodes_for_project(fixture["project_id"]) == []
    assert database.get_coded_segments_for_document(fixture["document_id"]) == []

    workspace_snapshot_repository.restore_node_subtree_snapshot(snapshot)

    nodes = database.get_nodes_for_project(fixture["project_id"])
    segments = database.get_coded_segments_for_document(fixture["document_id"])
    assert {node["id"] for node in nodes} == {fixture["root_id"], fixture["child_id"]}
    assert {segment["id"] for segment in segments} == {
        fixture["root_segment_id"],
        fixture["child_segment_id"],
    }
    assert database.get_node_descendants(fixture["root_id"]) == [fixture["child_id"]]


def test_document_snapshot_restores_document_and_segments():
    fixture = _create_project_fixture()
    snapshot = workspace_snapshot_repository.get_document_snapshot(
        fixture["document_id"]
    )

    database.delete_document(fixture["document_id"])
    assert database.get_documents_for_project(fixture["project_id"]) == []

    workspace_snapshot_repository.restore_document_snapshot(snapshot)

    content, participant_id = database.get_document_content(fixture["document_id"])
    segments = database.get_coded_segments_for_document(fixture["document_id"])
    assert content == "alpha beta gamma"
    assert participant_id == fixture["participant_id"]
    assert {segment["id"] for segment in segments} == {
        fixture["root_segment_id"],
        fixture["child_segment_id"],
    }


def test_participant_snapshot_restores_unassigned_references():
    fixture = _create_project_fixture()
    snapshot = workspace_snapshot_repository.get_participant_snapshot(
        fixture["participant_id"]
    )

    database.delete_participant(fixture["participant_id"])
    _, document_participant_id = database.get_document_content(fixture["document_id"])
    segment = database.get_coded_segments_for_document(fixture["document_id"])[0]
    assert document_participant_id is None
    assert segment["participant_id"] is None

    workspace_snapshot_repository.restore_participant_snapshot(snapshot)

    _, document_participant_id = database.get_document_content(fixture["document_id"])
    segment = database.get_coded_segments_for_document(fixture["document_id"])[0]
    assert document_participant_id == fixture["participant_id"]
    assert segment["participant_id"] == fixture["participant_id"]


def test_segment_snapshot_restores_deleted_segment():
    fixture = _create_project_fixture()
    database.update_coded_segment_remark(
        fixture["root_segment_id"], "Restore this remark"
    )
    snapshot = workspace_snapshot_repository.get_segment(fixture["root_segment_id"])

    database.delete_coded_segment(fixture["root_segment_id"])
    remaining = database.get_coded_segments_for_document(fixture["document_id"])
    assert {segment["id"] for segment in remaining} == {fixture["child_segment_id"]}

    workspace_snapshot_repository.restore_segment(snapshot)

    restored = database.get_coded_segments_for_document(fixture["document_id"])
    assert {segment["id"] for segment in restored} == {
        fixture["root_segment_id"],
        fixture["child_segment_id"],
    }
    restored_segment = next(
        segment for segment in restored if segment["id"] == fixture["root_segment_id"]
    )
    assert restored_segment["remark"] == "Restore this remark"
