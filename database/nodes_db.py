from .db_core import get_db_connection


def add_node(project_id, name, parent_id, color):
    assert isinstance(project_id, int), "project_id must be an integer"
    conn = get_db_connection()
    try:
        with conn:
            if parent_id is None:
                pos_res = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE project_id = ? AND parent_id IS NULL",
                    (project_id,),
                ).fetchone()
            else:
                pos_res = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (parent_id,)
                ).fetchone()
            position = pos_res[0]
            cursor = conn.execute(
                "INSERT INTO nodes (project_id, name, parent_id, color, position) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, parent_id, color, position),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_nodes_for_project(project_id):
    conn = get_db_connection()
    nodes = conn.execute(
        "SELECT * FROM nodes WHERE project_id = ? ORDER BY position, name",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in nodes]


def update_node_name(node_id, new_name):
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE nodes SET name = ? WHERE id = ?", (new_name, node_id))
    conn.close()


def update_node_color(node_id, new_color):
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE nodes SET color = ? WHERE id = ?", (new_color, node_id))
    conn.close()


def delete_node_and_children(node_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    nodes_to_delete = [node_id]
    query_ids = [node_id]
    while query_ids:
        placeholders = ",".join("?" for _ in query_ids)
        children = cursor.execute(
            f"SELECT id FROM nodes WHERE parent_id IN ({placeholders})", query_ids
        ).fetchall()
        child_ids = [row["id"] for row in children]
        nodes_to_delete.extend(child_ids)
        query_ids = child_ids
    placeholders = ",".join("?" for _ in nodes_to_delete)
    cursor.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", nodes_to_delete)
    cursor.execute(
        f"DELETE FROM coded_segments WHERE node_id IN ({placeholders})",
        nodes_to_delete,
    )
    conn.commit()
    conn.close()


def update_node_order(node_positions):
    conn = get_db_connection()
    with conn:
        conn.executemany("UPDATE nodes SET position = ? WHERE id = ?", node_positions)
    conn.close()


def update_node_parent(node_id, new_parent_id):
    conn = get_db_connection()
    with conn:
        if new_parent_id is None:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE project_id = (SELECT project_id FROM nodes WHERE id = ?) AND parent_id IS NULL",
                (node_id,),
            )
        else:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (new_parent_id,)
            )
        count = cursor.fetchone()[0]
        conn.execute(
            "UPDATE nodes SET parent_id = ?, position = ? WHERE id = ?",
            (new_parent_id, count, node_id),
        )
    conn.close()


def get_node_descendants(node_id):
    """
    Recursively fetches all descendant node IDs for a given node_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    all_descendant_ids = []

    # Start with the direct children
    query_ids = [node_id]

    while query_ids:
        placeholders = ",".join("?" for _ in query_ids)
        children = cursor.execute(
            f"SELECT id FROM nodes WHERE parent_id IN ({placeholders})", query_ids
        ).fetchall()

        child_ids = [row["id"] for row in children]

        if not child_ids:
            break

        all_descendant_ids.extend(child_ids)
        query_ids = child_ids

    conn.close()
    return all_descendant_ids
