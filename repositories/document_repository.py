from __future__ import annotations

from repositories.base import get_connection
from repositories.cache_invalidation import invalidate_analysis_cache

DOCUMENT_METADATA_FIELDS = (
    "source_filename",
    "source_copy_path",
    "source_sha256",
    "source_kind",
    "source_row",
    "imported_at",
)


class DocumentRepository:
    def add(
        self,
        project_id: int,
        title: str,
        text: str,
        participant_id: int | None = None,
        source_metadata: dict | None = None,
    ) -> int:
        metadata = source_metadata or {}
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO documents
                    (project_id, title, content, participant_id,
                     source_filename, source_copy_path, source_sha256,
                     source_kind, source_row, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    title,
                    text,
                    participant_id,
                    *[metadata.get(field) for field in DOCUMENT_METADATA_FIELDS],
                ),
            )
            conn.commit()
            document_id = cursor.lastrowid
        invalidate_analysis_cache()
        return document_id

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
                cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                if cursor.rowcount == 0:
                    raise ValueError(f"Document {document_id} does not exist.")
        invalidate_analysis_cache()

    def update_content(self, document_id: int, new_content: str) -> None:
        with get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    "UPDATE documents SET content = ? WHERE id = ?",
                    (new_content, document_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Document {document_id} does not exist.")
        invalidate_analysis_cache()

    def update_content_and_segments(
        self,
        document_id: int,
        new_content: str,
        segments: list[dict],
        deleted_segment_ids: list[int],
    ) -> None:
        self._validate_segments_for_content(segments, new_content)
        with get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    "UPDATE documents SET content = ? WHERE id = ?",
                    (new_content, document_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Document {document_id} does not exist.")
                if segments:
                    for segment in segments:
                        cursor = conn.execute(
                        """
                        UPDATE coded_segments
                        SET segment_start = ?, segment_end = ?, content_preview = ?
                        WHERE id = ? AND document_id = ?
                        """,
                            (
                                segment["segment_start"],
                                segment["segment_end"],
                                segment["content_preview"],
                                segment["id"],
                                document_id,
                            ),
                        )
                        if cursor.rowcount == 0:
                            raise ValueError(
                                f"Segment {segment['id']} does not exist for document {document_id}."
                            )
                if deleted_segment_ids:
                    for segment_id in deleted_segment_ids:
                        cursor = conn.execute(
                            """
                            DELETE FROM coded_segments
                            WHERE document_id = ? AND id = ?
                            """,
                            (document_id, segment_id),
                        )
                        if cursor.rowcount == 0:
                            raise ValueError(
                                f"Segment {segment_id} does not exist for document {document_id}."
                            )
        invalidate_analysis_cache()

    @staticmethod
    def _validate_segments_for_content(segments: list[dict], content: str) -> None:
        content_length = len(content)
        for segment in segments:
            start = int(segment["segment_start"])
            end = int(segment["segment_end"])
            if not 0 <= start < end <= content_length:
                raise ValueError(
                    f"Invalid segment range {start}:{end} for content length {content_length}."
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
