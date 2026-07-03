from __future__ import annotations

from repositories.base import get_connection
from repositories.cache_invalidation import invalidate_analysis_cache


class SegmentRepository:
    @staticmethod
    def _with_live_preview(rows) -> list[dict]:
        normalized = []
        for row in rows:
            item = dict(row)
            live_preview = item.get("live_preview")
            if live_preview is not None:
                item["content_preview"] = live_preview
            item.pop("live_preview", None)
            normalized.append(item)
        return normalized

    def add(
        self,
        document_id: int,
        node_id: int,
        participant_id: int | None,
        start: int,
        end: int,
        text_preview: str,
    ) -> int:
        with get_connection() as conn:
            with conn:
                content = self._get_document_content(conn, document_id)
                self._validate_range(start, end, len(content))
                cursor = conn.execute(
                    "INSERT INTO coded_segments (document_id, node_id, participant_id, segment_start, segment_end, content_preview, remark) VALUES (?, ?, ?, ?, ?, ?, '')",
                    (document_id, node_id, participant_id, start, end, text_preview),
                )
                segment_id = cursor.lastrowid
        invalidate_analysis_cache()
        return segment_id

    def get_for_nodes(
        self, project_id: int, node_ids: list[int], document_id: int | None = None
    ) -> list[dict]:
        if not node_ids:
            return []
        placeholders = ",".join("?" * len(node_ids))
        params = [project_id] + node_ids
        sql = f"""
            SELECT
                cs.*,
                substr(d.content, cs.segment_start + 1, cs.segment_end - cs.segment_start) AS live_preview,
                d.title AS document_title,
                d.id AS document_id,
                n.name AS node_name,
                n.color AS node_color,
                p.name AS participant_name
            FROM coded_segments cs
            JOIN documents d ON cs.document_id = d.id
            JOIN nodes n ON cs.node_id = n.id
            LEFT JOIN participants p ON cs.participant_id = p.id
            WHERE d.project_id = ? AND cs.node_id IN ({placeholders})
        """
        if document_id:
            sql += " AND d.id = ?"
            params.append(document_id)
        sql += " ORDER BY d.title, cs.id"
        with get_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return self._with_live_preview(rows)

    def get_for_document(self, document_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.id, s.document_id, s.segment_start, s.segment_end, s.content_preview,
                    s.remark,
                    substr(d.content, s.segment_start + 1, s.segment_end - s.segment_start) AS live_preview,
                    n.id AS node_id, n.name AS node_name, n.color AS node_color,
                    d.participant_id, p.name AS participant_name, d.title AS document_title
                FROM coded_segments s
                JOIN nodes n ON s.node_id = n.id
                JOIN documents d ON s.document_id = d.id
                LEFT JOIN participants p ON d.participant_id = p.id
                WHERE s.document_id = ?
                ORDER BY s.segment_start
                """,
                (document_id,),
            ).fetchall()
        return self._with_live_preview(rows)

    def get_for_project(self, project_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    cs.*,
                    substr(d.content, cs.segment_start + 1, cs.segment_end - cs.segment_start) AS live_preview,
                    d.title AS document_title,
                    d.id AS document_id,
                    n.name AS node_name,
                    n.color AS node_color,
                    p.name AS participant_name
                FROM coded_segments cs
                JOIN documents d ON cs.document_id = d.id
                JOIN nodes n ON cs.node_id = n.id
                LEFT JOIN participants p ON cs.participant_id = p.id
                WHERE d.project_id = ?
                ORDER BY d.title, cs.id
                """,
                (project_id,),
            ).fetchall()
        return self._with_live_preview(rows)

    def get_for_participant(self, project_id: int, participant_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    cs.*,
                    substr(d.content, cs.segment_start + 1, cs.segment_end - cs.segment_start) AS live_preview,
                    d.title AS document_title,
                    d.id AS document_id,
                    n.name AS node_name,
                    n.color AS node_color,
                    p.name AS participant_name
                FROM coded_segments cs
                JOIN documents d ON cs.document_id = d.id
                JOIN nodes n ON cs.node_id = n.id
                LEFT JOIN participants p ON cs.participant_id = p.id
                WHERE d.project_id = ? AND cs.participant_id = ?
                ORDER BY d.title, cs.id
                """,
                (project_id, participant_id),
            ).fetchall()
        return self._with_live_preview(rows)

    def delete(self, segment_id: int) -> None:
        with get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    "DELETE FROM coded_segments WHERE id = ?", (segment_id,)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Segment {segment_id} does not exist.")
        invalidate_analysis_cache()

    def update(
        self,
        segment_id: int,
        new_start: int,
        new_end: int,
        new_content_preview: str,
        new_remark: str | None = None,
    ) -> None:
        with get_connection() as conn:
            with conn:
                row = conn.execute(
                    """
                    SELECT s.document_id, s.remark, d.content
                    FROM coded_segments s
                    JOIN documents d ON s.document_id = d.id
                    WHERE s.id = ?
                    """,
                    (segment_id,),
                ).fetchone()
                if not row:
                    raise ValueError(f"Segment {segment_id} does not exist.")
                self._validate_range(new_start, new_end, len(row["content"]))
                remark = row["remark"] if new_remark is None else new_remark
                cursor = conn.execute(
                    """
                    UPDATE coded_segments
                    SET segment_start = ?, segment_end = ?, content_preview = ?, remark = ?
                    WHERE id = ?
                    """,
                    (new_start, new_end, new_content_preview, remark, segment_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Segment {segment_id} does not exist.")
        invalidate_analysis_cache()

    def update_remark(self, segment_id: int, remark: str) -> None:
        with get_connection() as conn:
            with conn:
                cursor = conn.execute(
                    "UPDATE coded_segments SET remark = ? WHERE id = ?",
                    (remark, segment_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Segment {segment_id} does not exist.")
        invalidate_analysis_cache()

    @staticmethod
    def _get_document_content(conn, document_id: int) -> str:
        row = conn.execute(
            "SELECT content FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Document {document_id} does not exist.")
        return row["content"]

    @staticmethod
    def _validate_range(start: int, end: int, content_length: int) -> None:
        if not 0 <= int(start) < int(end) <= content_length:
            raise ValueError(
                f"Invalid segment range {start}:{end} for content length {content_length}."
            )

    def get_node_statistics(
        self, project_id: int, document_id: int | None = None
    ) -> dict[int, dict[str, int]]:
        with get_connection() as conn:
            if document_id:
                rows = conn.execute(
                    "SELECT node_id, content_preview FROM coded_segments WHERE document_id = ?",
                    (document_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT cs.node_id, cs.content_preview
                    FROM coded_segments cs
                    JOIN documents d ON cs.document_id = d.id
                    WHERE d.project_id = ?
                    """,
                    (project_id,),
                ).fetchall()
        stats: dict[int, dict[str, int]] = {}
        for row in rows:
            stats.setdefault(row["node_id"], {"word_count": 0, "segment_count": 0})
            stats[row["node_id"]]["segment_count"] += 1
            stats[row["node_id"]]["word_count"] += len(row["content_preview"].split())
        return stats

    def get_word_count_for_participant(self, project_id: int, participant_id: int) -> int:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT content FROM documents WHERE project_id = ? AND participant_id = ?",
                (project_id, participant_id),
            ).fetchall()
        return sum(len(row["content"].split()) for row in rows if row["content"])


segment_repository = SegmentRepository()
