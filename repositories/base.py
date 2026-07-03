from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from utils.app_paths import get_database_backups_dir, get_database_path

SCHEMA_VERSION = 4
DOCUMENT_METADATA_COLUMNS = {
    "source_filename": "TEXT",
    "source_copy_path": "TEXT",
    "source_sha256": "TEXT",
    "source_kind": "TEXT",
    "source_row": "INTEGER",
    "imported_at": "TIMESTAMP",
}
CODED_SEGMENT_COLUMNS = {
    "remark": "TEXT NOT NULL DEFAULT ''",
}


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
        has_existing_data = _has_existing_data(cursor)
        if current_version < SCHEMA_VERSION and has_existing_data:
            backup_path = backup_database()
            print(f"NodeFlow database backup created before migration: {backup_path}")

        _ensure_schema(cursor)
        if current_version < SCHEMA_VERSION:
            _migrate_schema(cursor, current_version)
            cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        conn.commit()
    from repositories.cache_invalidation import invalidate_analysis_cache

    invalidate_analysis_cache()


def backup_database() -> str:
    path = get_database_path()
    if not path.exists():
        return ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = get_database_backups_dir() / f"nodeflow_backup_{timestamp}.db"
    with sqlite3.connect(path) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    return str(backup_path)


def _has_existing_data(cursor: sqlite3.Cursor) -> bool:
    tables = cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name IN
            ('projects', 'participants', 'documents', 'nodes', 'coded_segments')
        """
    ).fetchall()
    for row in tables:
        table_name = row["name"] if isinstance(row, sqlite3.Row) else row[0]
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if count:
            return True
    return False


def _ensure_schema(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            participant_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            source_filename TEXT,
            source_copy_path TEXT,
            source_sha256 TEXT,
            source_kind TEXT,
            source_row INTEGER,
            imported_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS nodes (
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

        CREATE TABLE IF NOT EXISTS coded_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            node_id INTEGER NOT NULL,
            participant_id INTEGER,
            segment_start INTEGER NOT NULL,
            segment_end INTEGER NOT NULL,
            content_preview TEXT NOT NULL,
            remark TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes (id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
        CREATE INDEX IF NOT EXISTS idx_nodes_project_parent_position ON nodes(project_id, parent_id, position);
        CREATE INDEX IF NOT EXISTS idx_segments_lookup ON coded_segments(document_id, node_id, participant_id, segment_start);
        """
    )


def _migrate_schema(cursor: sqlite3.Cursor, current_version: int) -> None:
    if current_version < 3:
        _add_missing_columns(cursor, "documents", DOCUMENT_METADATA_COLUMNS)
    if current_version < 4:
        _add_missing_columns(cursor, "coded_segments", CODED_SEGMENT_COLUMNS)


def _add_missing_columns(
    cursor: sqlite3.Cursor, table_name: str, columns: dict[str, str]
) -> None:
    existing_columns = {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
