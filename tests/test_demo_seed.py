from scripts.create_export_demo_project import PROJECT_NAME, main as seed_demo_project

import database


def test_demo_seed_project_has_rich_export_coverage():
    seed_demo_project()

    project = next(
        project for project in database.get_all_projects() if project["name"] == PROJECT_NAME
    )
    project_id = project["id"]

    participants = database.get_participants_for_project(project_id)
    documents = database.get_documents_for_project(project_id)
    nodes = database.get_nodes_for_project(project_id)
    segments = database.get_coded_segments_for_project(project_id)

    nodes_by_id = {node["id"]: node for node in nodes}

    def depth(node_id):
        level = 1
        current = nodes_by_id[node_id]
        while current["parent_id"] is not None:
            current = nodes_by_id[current["parent_id"]]
            level += 1
        return level

    assert len(participants) >= 5
    assert len(documents) >= 10
    assert len(segments) >= 20
    assert max(depth(node["id"]) for node in nodes) >= 4
    assert len({segment["participant_name"] for segment in segments}) >= 5
    assert sum(1 for node in nodes if node["parent_id"] is None) >= 3
