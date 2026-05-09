from repositories.node_repository import node_repository


def add_node(project_id, name, parent_id, color):
    assert isinstance(project_id, int), "project_id must be an integer"
    return node_repository.add(project_id, name, parent_id, color)


def get_nodes_for_project(project_id):
    return node_repository.list_for_project(project_id)


def update_node_name(node_id, new_name):
    node_repository.update_name(node_id, new_name)


def update_node_color(node_id, new_color):
    node_repository.update_color(node_id, new_color)


def delete_node_and_children(node_id):
    node_repository.delete_with_children(node_id)


def update_node_order(node_positions):
    node_repository.update_order(node_positions)


def update_node_parent(node_id, new_parent_id):
    node_repository.update_parent(node_id, new_parent_id)


def get_node_descendants(node_id):
    return node_repository.get_descendants(node_id)
