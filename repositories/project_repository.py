from __future__ import annotations

import sqlite3

from repositories.base import get_connection


class ProjectRepository:
    def add(self, name: str, description: str = "") -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO projects (name, description) VALUES (?, ?)",
                    (name, description),
                )

    def list_all(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def rename(self, project_id: int, new_name: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    "UPDATE projects SET name = ? WHERE id = ?",
                    (new_name, project_id),
                )

    def delete(self, project_id: int) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


project_repository = ProjectRepository()
