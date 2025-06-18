# Create this file at: database/nodes_db.py

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
            conn.execute(
                "INSERT INTO nodes (project_id, name, parent_id, color, position) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, parent_id, color, position),
            )
    finally:
        conn.close()


def get_nodes_for_project(project_id):
    conn = get_db_connection()
    nodes = conn.execute(
        "SELECT * FROM nodes WHERE project_id = ? ORDER BY position, name",
        (project_id,),
    ).fetchall()
    conn.close()
    return nodes


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


def delete_node(node_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
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
