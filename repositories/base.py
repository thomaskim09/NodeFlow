from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from utils.app_paths import get_database_path

SCHEMA_VERSION = 2


def _configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def connect() -> sqlite3.Connection:
    path = get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return _configure_connection(sqlite3.connect(path, timeout=10))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def initialize_database() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version;")
        current_version = cursor.fetchone()[0]
        if current_version < SCHEMA_VERSION:
            _rebuild_schema(cursor)
            cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        conn.commit()


def _rebuild_schema(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        DROP TABLE IF EXISTS coded_segments;
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS participants;
        DROP TABLE IF EXISTS projects;

        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );

        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            participant_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );

        CREATE TABLE nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#FFFF00',
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES nodes (id) ON DELETE CASCADE
        );

        CREATE TABLE coded_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            participant_id INTEGER,
            segment_start INTEGER NOT NULL,
            segment_end INTEGER NOT NULL,
            content_preview TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );

        CREATE INDEX idx_documents_project_id ON documents(project_id);
        CREATE INDEX idx_nodes_project_parent_position ON nodes(project_id, parent_id, position);
        CREATE INDEX idx_segments_lookup ON coded_segments(document_id, node_id, participant_id, segment_start);
        """
    )
