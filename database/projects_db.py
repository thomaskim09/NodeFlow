import sqlite3
from .db_core import get_db_connection


def add_project(name, description=""):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description),
            )
    except sqlite3.IntegrityError as e:
        raise e
    finally:
        conn.close()


def get_all_projects():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects ORDER BY name;").fetchall()
    conn.close()
    return projects


def rename_project(project_id, new_name):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE projects SET name = ? WHERE id = ?", (new_name, project_id)
            )
    finally:
        conn.close()


def delete_project(project_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.close()
