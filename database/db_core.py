# Replace the contents of database/db_core.py with this updated code.

import sqlite3
import os

# Define the data directory and the database file path
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "nodeflow.db")


def get_db_connection():
    """Establishes the database connection and configuration."""
    # Ensure the data directory exists before connecting
    os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables():
    """Creates all database tables if they don't already exist."""
    # This function requires no changes, as it uses get_db_connection()
    conn = get_db_connection()
    cursor = conn.cursor()
    # ... (rest of the create_tables function is unchanged)
    # Projects Table
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
    # Participants Table
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
    # Documents Table
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
    # Nodes Table
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
    # Coded Segments Table
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
    # Schema migration check for 'color' column
    cursor.execute("PRAGMA table_info(nodes);")
    columns = [col[1] for col in cursor.fetchall()]
    if "color" not in columns:
        cursor.execute("ALTER TABLE nodes ADD COLUMN color TEXT DEFAULT '#FFFF00';")

    conn.commit()
    conn.close()
    print("Database tables created or verified successfully.")
