import sqlite3
import os

DB_FILE = "nodeflow.db"


def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
    return conn


def create_tables():
    """Creates all the necessary tables for the application if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Projects Table ---
    # Stores the top-level projects.
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

    # --- Participants Table ---
    # Stores participant info, linked to a project.
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

    # --- Documents Table ---
    # Stores the actual text content for analysis, linked to a project.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );
    """
    )

    # --- Nodes Table ---
    # Stores the hierarchical codes/labels.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            position INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES nodes (id) ON DELETE CASCADE
        );
    """
    )

    # --- Coded Segments Table ---
    # This is the crucial table linking text to nodes.
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

    conn.commit()
    conn.close()
    print("Database tables created or verified successfully.")


# Add these functions to the end of database.py


def add_project(name, description=""):
    """Adds a new project to the database."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        print(f"Project '{name}' added successfully.")
    except sqlite3.IntegrityError:
        # This error occurs if the project name already exists (due to UNIQUE constraint)
        print(f"Error: A project with the name '{name}' already exists.")
    finally:
        conn.close()


def get_all_projects():
    """Retrieves all projects from the database, ordered by name."""
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects ORDER BY name;").fetchall()
    conn.close()
    return projects


def add_participant(project_id, name, details=""):
    """Adds a new participant to a specific project."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO participants (project_id, name, details) VALUES (?, ?, ?)",
        (project_id, name, details),
    )
    conn.commit()
    conn.close()


def get_participants_for_project(project_id):
    """Retrieves all participants for a given project ID."""
    conn = get_db_connection()
    participants = conn.execute(
        "SELECT * FROM participants WHERE project_id = ? ORDER BY name", (project_id,)
    ).fetchall()
    conn.close()
    return participants


def update_participant(participant_id, name, details):
    """Updates an existing participant's details."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE participants SET name = ?, details = ? WHERE id = ?",
        (name, details, participant_id),
    )
    conn.commit()
    conn.close()


def delete_participant(participant_id):
    """Deletes a participant from the database."""
    conn = get_db_connection()
    conn.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
    conn.commit()
    conn.close()


def add_node(project_id, name, parent_id=None):
    """Adds a new node to a project, either as a root or a child."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO nodes (project_id, name, parent_id) VALUES (?, ?, ?)",
        (project_id, name, parent_id),
    )
    conn.commit()
    conn.close()


def get_nodes_for_project(project_id):
    """Retrieves all nodes for a given project ID."""
    conn = get_db_connection()
    nodes = conn.execute(
        "SELECT * FROM nodes WHERE project_id = ? ORDER BY position, name",
        (project_id,),
    ).fetchall()
    conn.close()
    return nodes


def update_node_name(node_id, new_name):
    """Updates the name of an existing node."""
    conn = get_db_connection()
    conn.execute("UPDATE nodes SET name = ? WHERE id = ?", (new_name, node_id))
    conn.commit()
    conn.close()


def delete_node(node_id):
    """Deletes a node. Child nodes will also be deleted due to CASCADE constraint."""
    conn = get_db_connection()
    conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    conn.commit()
    conn.close()


def update_node_order(node_positions):
    """
    Updates the position of multiple nodes in a single transaction.
    'node_positions' is a list of (new_position, node_id) tuples.
    """
    conn = get_db_connection()
    conn.executemany("UPDATE nodes SET position = ? WHERE id = ?", node_positions)
    conn.commit()
    conn.close()


def add_document(project_id, title, content):
    """Adds a new document to a project."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (project_id, title, content) VALUES (?, ?, ?)",
        (project_id, title, content),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def get_documents_for_project(project_id):
    """Retrieves all documents for a given project."""
    conn = get_db_connection()
    docs = conn.execute(
        "SELECT * FROM documents WHERE project_id = ?", (project_id,)
    ).fetchall()
    conn.close()
    return docs


def get_document_content(document_id):
    """Gets the full content of a single document."""
    conn = get_db_connection()
    content = conn.execute(
        "SELECT content FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    conn.close()
    return content["content"] if content else ""


def add_coded_segment(document_id, node_id, start, end, text_preview):
    """Adds a new coded segment to the database."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO coded_segments (document_id, node_id, segment_start, segment_end, content_preview) VALUES (?, ?, ?, ?, ?)",
        (document_id, node_id, start, end, text_preview),
    )
    conn.commit()
    conn.close()


def get_coded_segments_for_document(document_id):
    """Retrieves all coded segments for a given document, joining node names."""
    conn = get_db_connection()
    segments = conn.execute(
        """
        SELECT cs.id, cs.content_preview, n.name as node_name
        FROM coded_segments cs
        JOIN nodes n ON cs.node_id = n.id
        WHERE cs.document_id = ?
        ORDER BY cs.id
    """,
        (document_id,),
    ).fetchall()
    conn.close()
    return segments


if __name__ == "__main__":
    # This allows you to run this file directly to initialize the database
    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found, creating a new one.")
        create_tables()
    else:
        print(f"Database file '{DB_FILE}' already exists.")
