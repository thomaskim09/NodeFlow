from __future__ import annotations

from repositories.base import get_connection


class DocumentRepository:
    def add(
        self,
        project_id: int,
        title: str,
        text: str,
        participant_id: int | None = None,
    ) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (project_id, title, content, participant_id) VALUES (?, ?, ?, ?)",
                (project_id, title, text, participant_id),
            )
            conn.commit()
            return cursor.lastrowid

    def list_for_project(self, project_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.id, d.title, d.participant_id, p.name AS participant_name
                FROM documents d
                LEFT JOIN participants p ON d.participant_id = p.id
                WHERE d.project_id = ?
                ORDER BY d.title, d.id
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_content(self, document_id: int) -> tuple[str, int | None]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT content, participant_id FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if not row:
            return "", None
        return row["content"], row["participant_id"]

    def delete(self, document_id: int) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def update_content(self, document_id: int, new_content: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    "UPDATE documents SET content = ? WHERE id = ?",
                    (new_content, document_id),
                )

    def update_content_and_segments(
        self,
        document_id: int,
        new_content: str,
        segments: list[dict],
        deleted_segment_ids: list[int],
    ) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    "UPDATE documents SET content = ? WHERE id = ?",
                    (new_content, document_id),
                )
                if segments:
                    conn.executemany(
                        """
                        UPDATE coded_segments
                        SET segment_start = ?, segment_end = ?, content_preview = ?
                        WHERE id = ? AND document_id = ?
                        """,
                        [
                            (
                                segment["segment_start"],
                                segment["segment_end"],
                                segment["content_preview"],
                                segment["id"],
                                document_id,
                            )
                            for segment in segments
                        ],
                    )
                if deleted_segment_ids:
                    placeholders = ",".join("?" for _ in deleted_segment_ids)
                    conn.execute(
                        f"""
                        DELETE FROM coded_segments
                        WHERE document_id = ? AND id IN ({placeholders})
                        """,
                        [document_id, *deleted_segment_ids],
                    )

    def get_word_count(self, document_id: int | None) -> int:
        if not document_id:
            return 0
        with get_connection() as conn:
            row = conn.execute(
                "SELECT content FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return len(row["content"].split()) if row and row["content"] else 0

    def get_project_word_count(self, project_id: int) -> int:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT content FROM documents WHERE project_id = ?",
                (project_id,),
            ).fetchall()
        return sum(len(row["content"].split()) for row in rows if row["content"])

    def exists(self, project_id: int, title: str, content: str) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM documents WHERE project_id = ? AND title = ? AND content = ?",
                (project_id, title, content),
            ).fetchone()
        return row is not None


document_repository = DocumentRepository()
