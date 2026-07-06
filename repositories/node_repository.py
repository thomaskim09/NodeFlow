from __future__ import annotations

from repositories.base import get_connection
from repositories.cache_invalidation import invalidate_analysis_cache


class NodeRepository:
    def add(self, project_id: int, name: str, parent_id: int | None, color: str) -> int:
        with get_connection() as conn:
            with conn:
                if parent_id is None:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM nodes WHERE project_id = ? AND parent_id IS NULL",
                        (project_id,),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM nodes WHERE parent_id = ?",
                        (parent_id,),
                    ).fetchone()
                position = row[0]
                cursor = conn.execute(
                    "INSERT INTO nodes (project_id, name, parent_id, color, position) VALUES (?, ?, ?, ?, ?)",
                    (project_id, name, parent_id, color, position),
                )
                node_id = cursor.lastrowid
        invalidate_analysis_cache()
        return node_id

    def list_for_project(self, project_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE project_id = ? ORDER BY position, name",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_name(self, node_id: int, new_name: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("UPDATE nodes SET name = ? WHERE id = ?", (new_name, node_id))
        invalidate_analysis_cache()

    def update_color(self, node_id: int, new_color: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("UPDATE nodes SET color = ? WHERE id = ?", (new_color, node_id))
        invalidate_analysis_cache()

    def delete_with_children(self, node_id: int) -> None:
        with get_connection() as conn:
            cursor = conn.cursor()
            nodes_to_delete = [node_id]
            query_ids = [node_id]
            while query_ids:
                placeholders = ",".join("?" for _ in query_ids)
                rows = cursor.execute(
                    f"SELECT id FROM nodes WHERE parent_id IN ({placeholders})",
                    query_ids,
                ).fetchall()
                child_ids = [row["id"] for row in rows]
                nodes_to_delete.extend(child_ids)
                query_ids = child_ids
            placeholders = ",".join("?" for _ in nodes_to_delete)
            with conn:
                conn.execute(
                    f"DELETE FROM coded_segments WHERE node_id IN ({placeholders})",
                    nodes_to_delete,
                )
                conn.execute(
                    f"DELETE FROM nodes WHERE id IN ({placeholders})",
                    nodes_to_delete,
                )
        invalidate_analysis_cache()

    def update_order(self, node_positions: list[tuple[int, int]]) -> None:
        with get_connection() as conn:
            with conn:
                conn.executemany("UPDATE nodes SET position = ? WHERE id = ?", node_positions)
        invalidate_analysis_cache()

    def update_parent(self, node_id: int, new_parent_id: int | None) -> None:
        with get_connection() as conn:
            with conn:
                if new_parent_id is None:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM nodes WHERE project_id = (SELECT project_id FROM nodes WHERE id = ?) AND parent_id IS NULL",
                        (node_id,),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM nodes WHERE parent_id = ?",
                        (new_parent_id,),
                    ).fetchone()
                conn.execute(
                    "UPDATE nodes SET parent_id = ?, position = ? WHERE id = ?",
                    (new_parent_id, row[0], node_id),
                )
        invalidate_analysis_cache()

    def get_descendants(self, node_id: int) -> list[int]:
        with get_connection() as conn:
            cursor = conn.cursor()
            all_descendants: list[int] = []
            query_ids = [node_id]
            while query_ids:
                placeholders = ",".join("?" for _ in query_ids)
                rows = cursor.execute(
                    f"SELECT id FROM nodes WHERE parent_id IN ({placeholders})",
                    query_ids,
                ).fetchall()
                child_ids = [row["id"] for row in rows]
                if not child_ids:
                    break
                all_descendants.extend(child_ids)
                query_ids = child_ids
        return all_descendants

    def merge(self, source_node_id: int, target_node_id: int) -> None:
        if source_node_id == target_node_id:
            raise ValueError("A node cannot be merged with itself.")

        with get_connection() as conn:
            with conn:
                rows = conn.execute(
                    "SELECT id, project_id FROM nodes WHERE id IN (?, ?)",
                    (source_node_id, target_node_id),
                ).fetchall()
                nodes = {row["id"]: row for row in rows}
                if source_node_id not in nodes or target_node_id not in nodes:
                    raise ValueError("Both nodes must exist.")
                if nodes[source_node_id]["project_id"] != nodes[target_node_id]["project_id"]:
                    raise ValueError("Nodes from different projects cannot be merged.")

                descendants = set()
                pending = [source_node_id, target_node_id]
                while pending:
                    parent_id = pending.pop()
                    child_ids = [
                        row["id"]
                        for row in conn.execute(
                            "SELECT id FROM nodes WHERE parent_id = ?", (parent_id,)
                        ).fetchall()
                    ]
                    descendants.update((parent_id, child_id) for child_id in child_ids)
                    pending.extend(child_ids)
                if (source_node_id, target_node_id) in descendants or (
                    target_node_id,
                    source_node_id,
                ) in descendants:
                    raise ValueError("Ancestor and descendant nodes cannot be merged.")

                next_position = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE parent_id = ?",
                    (target_node_id,),
                ).fetchone()[0]
                children = conn.execute(
                    "SELECT id FROM nodes WHERE parent_id = ? ORDER BY position, id",
                    (source_node_id,),
                ).fetchall()
                conn.executemany(
                    "UPDATE nodes SET parent_id = ?, position = ? WHERE id = ?",
                    [
                        (target_node_id, next_position + index, child["id"])
                        for index, child in enumerate(children)
                    ],
                )
                conn.execute(
                    "UPDATE coded_segments SET node_id = ? WHERE node_id = ?",
                    (target_node_id, source_node_id),
                )
                conn.execute("DELETE FROM nodes WHERE id = ?", (source_node_id,))
        invalidate_analysis_cache()


node_repository = NodeRepository()
