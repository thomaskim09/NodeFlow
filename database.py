import sqlite3
import os

DB_FILE = "nodeflow.db"


def get_db_connection():
    # Add a timeout to prevent "database is locked" errors
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            participant_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#FFFF00',
            position INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS coded_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            participant_id INTEGER,
            segment_start INTEGER NOT NULL,
            segment_end INTEGER NOT NULL,
            content_preview TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );
    """
    )

    # --- Check and add 'color' column to nodes if it doesn't exist ---
    cursor.execute("PRAGMA table_info(nodes);")
    columns = [col[1] for col in cursor.fetchall()]
    if "color" not in columns:
        cursor.execute("ALTER TABLE nodes ADD COLUMN color TEXT DEFAULT '#FFFF00';")
        print("Upgraded 'nodes' table with 'color' column.")

    conn.commit()
    conn.close()
    print("Database tables created or verified successfully.")


def add_project(name, description=""):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description),
            )
    except sqlite3.IntegrityError as e:
        print(f"Error: A project with the name '{name}' already exists.")
        raise e
    finally:
        conn.close()


def get_all_projects():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects ORDER BY name;").fetchall()
    conn.close()
    return projects


def rename_project(project_id, new_name):
    """Renames an existing project. Can raise sqlite3.IntegrityError on duplicate name."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE projects SET name = ? WHERE id = ?", (new_name, project_id)
            )
    finally:
        conn.close()


def delete_project(project_id):
    """Deletes a project and all its associated data."""
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.close()


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


def add_node(project_id, name, parent_id, color):
    """
    Adds a new node robustly using automatic transaction management.
    """
    assert isinstance(
        project_id, int
    ), f"project_id must be an integer, but was {type(project_id)}"

    conn = get_db_connection()
    try:
        with conn:
            project_check = conn.execute(
                "SELECT id FROM projects WHERE id = ?", (project_id,)
            ).fetchone()

            if project_check is None:
                raise ValueError(
                    f"Attempted to add a node to a non-existent project (ID: {project_id})."
                )

            if parent_id is None:
                position_result = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE project_id = ? AND parent_id IS NULL",
                    (project_id,),
                ).fetchone()
            else:
                position_result = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE parent_id = ?", (parent_id,)
                ).fetchone()

            position = position_result[0]

            conn.execute(
                "INSERT INTO nodes (project_id, name, parent_id, color, position) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, parent_id, color, position),
            )
    except sqlite3.Error as e:
        print(f"Database error in add_node for project {project_id}: {e}")
        raise e
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
        new_position = count
        conn.execute(
            "UPDATE nodes SET parent_id = ?, position = ? WHERE id = ?",
            (new_parent_id, new_position, node_id),
        )
    conn.close()


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
    """Updates only the text content of a document, leaving codes untouched."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE documents SET content = ? WHERE id = ?",
                (new_content, document_id),
            )
    except sqlite3.Error as e:
        print(f"Database error in update_document_text_only: {e}")
        raise e
    finally:
        conn.close()


def add_coded_segment(document_id, node_id, participant_id, start, end, text_preview):
    conn = get_db_connection()
    with conn:
        conn.execute(
            "INSERT INTO coded_segments (document_id, node_id, participant_id, segment_start, segment_end, content_preview) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, node_id, participant_id, start, end, text_preview),
        )
    conn.close()


def get_coded_segments_for_document(document_id):
    conn = get_db_connection()
    segments = conn.execute(
        """
        SELECT
            cs.id, cs.node_id, cs.content_preview, cs.segment_start, cs.segment_end,
            n.name as node_name, n.color as node_color,
            p.name as participant_name
        FROM coded_segments cs
        JOIN nodes n ON cs.node_id = n.id
        LEFT JOIN participants p ON cs.participant_id = p.id
        WHERE cs.document_id = ?
        ORDER BY cs.id
    """,
        (document_id,),
    ).fetchall()
    conn.close()
    return segments


def get_coded_segments_for_project(project_id):
    """Gets all coded segments for an entire project."""
    conn = get_db_connection()
    segments = conn.execute(
        """
        SELECT
            cs.id, cs.node_id, cs.content_preview,
            d.title as document_title,
            n.name as node_name,
            p.name as participant_name
        FROM coded_segments cs
        JOIN documents d ON cs.document_id = d.id
        JOIN nodes n ON cs.node_id = n.id
        LEFT JOIN participants p ON cs.participant_id = p.id
        WHERE d.project_id = ?
        ORDER BY d.title, cs.id
    """,
        (project_id,),
    ).fetchall()
    conn.close()
    return segments


def delete_coded_segment(segment_id):
    """Deletes a specific coded segment from the database."""
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM coded_segments WHERE id = ?", (segment_id,))
    conn.close()


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        create_tables()
