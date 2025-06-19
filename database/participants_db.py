from contextlib import closing
from .db_core import get_db_connection


def add_participant(project_id, name, details=""):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "INSERT INTO participants (project_id, name, details) VALUES (?, ?, ?)",
            (project_id, name, details),
        )
    conn.close()


def get_participants_for_project(project_id):
    conn = get_db_connection()
    participants = conn.execute(
        "SELECT * FROM participants WHERE project_id = ? ORDER BY name", (project_id,)
    ).fetchall()
    conn.close()
    return participants


def get_participant_for_document(document_id: int) -> int | None:
    """Gets the participant ID for a given document ID from the 'documents' table."""
    if not document_id:
        return None
    query = "SELECT participant_id FROM documents WHERE id = ?"
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cursor:
            result = cursor.execute(query, (document_id,)).fetchone()
            # fetchone() returns a Row object, which can be None. If not None, access by index.
            return result[0] if result else None


def update_participant(participant_id, name, details):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "UPDATE participants SET name = ?, details = ? WHERE id = ?",
            (name, details, participant_id),
        )
    conn.close()


def delete_participant(participant_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
    conn.close()
