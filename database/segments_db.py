# In file: database/segments_db.py

from .db_core import get_db_connection


def add_coded_segment(document_id, node_id, participant_id, start, end, text_preview):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "INSERT INTO coded_segments (document_id, node_id, participant_id, segment_start, segment_end, content_preview) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, node_id, participant_id, start, end, text_preview),
        )
    conn.close()


def get_coded_segments_for_document(document_id):
    """
    Retrieves all coded segments for a specific document, including node, participant, and document info.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # FIXED: Added JOIN to documents table to fetch d.title as document_title.
    cursor.execute(
        """
        SELECT s.id, s.node_id, s.content_preview, s.segment_start, s.segment_end,
               n.name as node_name, n.color as node_color, s.participant_id,
               p.name as participant_name,
               d.title as document_title
        FROM coded_segments s
        JOIN nodes n ON s.node_id = n.id
        LEFT JOIN participants p ON s.participant_id = p.id
        JOIN documents d ON s.document_id = d.id
        WHERE s.document_id = ?
        ORDER BY s.segment_start
    """,
        (document_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_coded_segments_for_project(project_id):
    conn = get_db_connection()
    segments_rows = conn.execute(
        """
        SELECT cs.*, d.title as document_title, d.id as document_id, n.name as node_name, n.color as node_color, p.name as participant_name
        FROM coded_segments cs
        JOIN documents d ON cs.document_id = d.id
        JOIN nodes n ON cs.node_id = n.id
        LEFT JOIN participants p ON cs.participant_id = p.id
        WHERE d.project_id = ? ORDER BY d.title, cs.id
    """,
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in segments_rows]


def get_coded_segments_for_participant(project_id, participant_id):
    conn = get_db_connection()
    segments_rows = conn.execute(
        """
        SELECT cs.*, d.title as document_title, d.id as document_id, n.name as node_name, n.color as node_color, p.name as participant_name
        FROM coded_segments cs
        JOIN documents d ON cs.document_id = d.id
        JOIN nodes n ON cs.node_id = n.id
        LEFT JOIN participants p ON cs.participant_id = p.id
        WHERE d.project_id = ? AND cs.participant_id = ?
        ORDER BY d.title, cs.id
    """,
        (project_id, participant_id),
    ).fetchall()
    conn.close()
    return [dict(row) for row in segments_rows]


def delete_coded_segment(segment_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM coded_segments WHERE id = ?", (segment_id,))
    conn.close()


def get_node_statistics(project_id, document_id=None):
    stats = {}
    conn = get_db_connection()
    if document_id:
        sql = (
            "SELECT node_id, content_preview FROM coded_segments WHERE document_id = ?"
        )
        params = (document_id,)
    else:
        sql = """
            SELECT cs.node_id, cs.content_preview FROM coded_segments cs
            JOIN documents d ON cs.document_id = d.id WHERE d.project_id = ?
        """
        params = (project_id,)

    segments_rows = conn.execute(sql, params).fetchall()
    conn.close()

    segments = [dict(row) for row in segments_rows]
    for seg in segments:
        stats.setdefault(seg["node_id"], {"word_count": 0, "segment_count": 0})
        stats[seg["node_id"]]["segment_count"] += 1
        stats[seg["node_id"]]["word_count"] += len(seg["content_preview"].split())
    return stats


def get_word_count_for_participant(project_id, participant_id):
    conn = get_db_connection()
    docs_rows = conn.execute(
        "SELECT content FROM documents WHERE project_id = ? AND participant_id = ?",
        (project_id, participant_id),
    ).fetchall()
    conn.close()

    docs = [dict(row) for row in docs_rows]
    total_words = sum(len(doc["content"].split()) for doc in docs if doc["content"])
    return total_words
