from __future__ import annotations

from repositories.base import get_connection


class WorkspaceSnapshotRepository:
    def get_segment(self, segment_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM coded_segments WHERE id = ?",
                (segment_id,),
            ).fetchone()
        return dict(row) if row else None

    def restore_segment(self, segment: dict) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO coded_segments
                        (id, document_id, node_id, participant_id, segment_start,
                         segment_end, content_preview, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        segment["id"],
                        segment["document_id"],
                        segment["node_id"],
                        segment["participant_id"],
                        segment["segment_start"],
                        segment["segment_end"],
                        segment["content_preview"],
                        segment["created_at"],
                    ),
                )

    def get_document_snapshot(self, document_id: int) -> dict | None:
        with get_connection() as conn:
            document = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if not document:
                return None
            segments = conn.execute(
                "SELECT * FROM coded_segments WHERE document_id = ? ORDER BY id",
                (document_id,),
            ).fetchall()
        return {
            "document": dict(document),
            "segments": [dict(row) for row in segments],
        }

    def restore_document_snapshot(self, snapshot: dict) -> None:
        document = snapshot["document"]
        with get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO documents
                        (id, project_id, participant_id, title, content, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document["id"],
                        document["project_id"],
                        document["participant_id"],
                        document["title"],
                        document["content"],
                        document["created_at"],
                    ),
                )
                for segment in snapshot["segments"]:
                    conn.execute(
                        """
                        INSERT INTO coded_segments
                            (id, document_id, node_id, participant_id, segment_start,
                             segment_end, content_preview, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            segment["id"],
                            segment["document_id"],
                            segment["node_id"],
                            segment["participant_id"],
                            segment["segment_start"],
                            segment["segment_end"],
                            segment["content_preview"],
                            segment["created_at"],
                        ),
                    )

    def get_node_subtree_snapshot(self, node_id: int) -> dict:
        with get_connection() as conn:
            nodes = []
            queue = [node_id]
            while queue:
                current_id = queue.pop(0)
                row = conn.execute(
                    "SELECT * FROM nodes WHERE id = ?",
                    (current_id,),
                ).fetchone()
                if not row:
                    continue
                nodes.append(dict(row))
                child_rows = conn.execute(
                    "SELECT id FROM nodes WHERE parent_id = ? ORDER BY position, id",
                    (current_id,),
                ).fetchall()
                queue.extend(row["id"] for row in child_rows)

            node_ids = [node["id"] for node in nodes]
            segments = []
            if node_ids:
                placeholders = ",".join("?" for _ in node_ids)
                rows = conn.execute(
                    f"""
                    SELECT * FROM coded_segments
                    WHERE node_id IN ({placeholders})
                    ORDER BY id
                    """,
                    node_ids,
                ).fetchall()
                segments = [dict(row) for row in rows]

        return {"nodes": nodes, "segments": segments}

    def restore_node_subtree_snapshot(self, snapshot: dict) -> None:
        with get_connection() as conn:
            with conn:
                for node in snapshot["nodes"]:
                    conn.execute(
                        """
                        INSERT INTO nodes
                            (id, project_id, parent_id, name, color, position, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            node["id"],
                            node["project_id"],
                            node["parent_id"],
                            node["name"],
                            node["color"],
                            node["position"],
                            node["created_at"],
                        ),
                    )
                for segment in snapshot["segments"]:
                    conn.execute(
                        """
                        INSERT INTO coded_segments
                            (id, document_id, node_id, participant_id, segment_start,
                             segment_end, content_preview, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            segment["id"],
                            segment["document_id"],
                            segment["node_id"],
                            segment["participant_id"],
                            segment["segment_start"],
                            segment["segment_end"],
                            segment["content_preview"],
                            segment["created_at"],
                        ),
                    )

    def get_node_layout(self, project_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, parent_id, position
                FROM nodes
                WHERE project_id = ?
                ORDER BY id
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def restore_node_layout(self, layout: list[dict]) -> None:
        with get_connection() as conn:
            with conn:
                conn.executemany(
                    "UPDATE nodes SET parent_id = ?, position = ? WHERE id = ?",
                    [
                        (node["parent_id"], node["position"], node["id"])
                        for node in layout
                    ],
                )

    def get_participant_snapshot(self, participant_id: int) -> dict | None:
        with get_connection() as conn:
            participant = conn.execute(
                "SELECT * FROM participants WHERE id = ?",
                (participant_id,),
            ).fetchone()
            if not participant:
                return None
            documents = conn.execute(
                "SELECT id FROM documents WHERE participant_id = ? ORDER BY id",
                (participant_id,),
            ).fetchall()
            segments = conn.execute(
                "SELECT id FROM coded_segments WHERE participant_id = ? ORDER BY id",
                (participant_id,),
            ).fetchall()
        return {
            "participant": dict(participant),
            "document_ids": [row["id"] for row in documents],
            "segment_ids": [row["id"] for row in segments],
        }

    def restore_participant_snapshot(self, snapshot: dict) -> None:
        participant = snapshot["participant"]
        with get_connection() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO participants
                        (id, project_id, name, details, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        participant["id"],
                        participant["project_id"],
                        participant["name"],
                        participant["details"],
                        participant["created_at"],
                    ),
                )
                if snapshot["document_ids"]:
                    placeholders = ",".join("?" for _ in snapshot["document_ids"])
                    conn.execute(
                        f"""
                        UPDATE documents SET participant_id = ?
                        WHERE id IN ({placeholders})
                        """,
                        [participant["id"], *snapshot["document_ids"]],
                    )
                if snapshot["segment_ids"]:
                    placeholders = ",".join("?" for _ in snapshot["segment_ids"])
                    conn.execute(
                        f"""
                        UPDATE coded_segments SET participant_id = ?
                        WHERE id IN ({placeholders})
                        """,
                        [participant["id"], *snapshot["segment_ids"]],
                    )

    def get_project_entity_ids(self, project_id: int) -> dict[str, set[int]]:
        with get_connection() as conn:
            documents = conn.execute(
                "SELECT id FROM documents WHERE project_id = ?",
                (project_id,),
            ).fetchall()
            participants = conn.execute(
                "SELECT id FROM participants WHERE project_id = ?",
                (project_id,),
            ).fetchall()
        return {
            "documents": {row["id"] for row in documents},
            "participants": {row["id"] for row in participants},
        }


workspace_snapshot_repository = WorkspaceSnapshotRepository()
