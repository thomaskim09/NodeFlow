# Create this file at: database/documents_db.py

from .db_core import get_db_connection


def add_document(project_id, title, content, participant_id):
    conn = get_db_connection()
    with conn:
        cursor = conn.execute(
            "INSERT INTO documents (project_id, title, content, participant_id) VALUES (?, ?, ?, ?)",
            (project_id, title, content, participant_id),
        )
        doc_id = cursor.lastrowid
    conn.close()
    return doc_id


def get_documents_for_project(project_id):
    conn = get_db_connection()
    docs = conn.execute(
        """
        SELECT d.id, d.title, d.participant_id, p.name as participant_name
        FROM documents d
        LEFT JOIN participants p ON d.participant_id = p.id
        WHERE d.project_id = ?
    """,
        (project_id,),
    ).fetchall()
    conn.close()
    return docs


def get_document_content(document_id):
    conn = get_db_connection()
    doc_data = conn.execute(
        "SELECT content, participant_id FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    conn.close()
    return (doc_data["content"], doc_data["participant_id"]) if doc_data else ("", None)


def delete_document(document_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.close()


def update_document_text_only(document_id, new_content):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE documents SET content = ? WHERE id = ?",
                (new_content, document_id),
            )
    except Exception as e:
        # Consider more specific error handling if needed
        raise e
    finally:
        conn.close()


def get_document_word_count(document_id):
    if not document_id:
        return 0
    conn = get_db_connection()
    content_row = conn.execute(
        "SELECT content FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    conn.close()
    if content_row and content_row["content"]:
        return len(content_row["content"].split())
    return 0


def get_project_word_count(project_id):
    conn = get_db_connection()
    docs = conn.execute(
        "SELECT content FROM documents WHERE project_id = ?", (project_id,)
    ).fetchall()
    conn.close()
    total_words = sum(len(doc["content"].split()) for doc in docs if doc["content"])
    return total_words
