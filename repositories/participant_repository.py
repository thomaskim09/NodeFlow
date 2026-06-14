from __future__ import annotations

from repositories.base import get_connection


class ParticipantRepository:
    def add(self, project_id: int, name: str, details: str = "") -> int:
        with get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO participants (project_id, name, details) VALUES (?, ?, ?)",
                    (project_id, name, details),
                )
                return cursor.lastrowid

    def list_for_project(self, project_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM participants WHERE project_id = ? ORDER BY name",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_for_document(self, document_id: int) -> int | None:
        if not document_id:
            return None
        with get_connection() as conn:
            row = conn.execute(
                "SELECT participant_id FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return row[0] if row else None

    def update(self, participant_id: int, name: str, details: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    "UPDATE participants SET name = ?, details = ? WHERE id = ?",
                    (name, details, participant_id),
                )

    def delete(self, participant_id: int) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("DELETE FROM participants WHERE id = ?", (participant_id,))


participant_repository = ParticipantRepository()
