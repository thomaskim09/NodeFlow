from __future__ import annotations

from repositories.base import get_connection


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
                return cursor.lastrowid

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

    def update_color(self, node_id: int, new_color: str) -> None:
        with get_connection() as conn:
            with conn:
                conn.execute("UPDATE nodes SET color = ? WHERE id = ?", (new_color, node_id))

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

    def update_order(self, node_positions: list[tuple[int, int]]) -> None:
        with get_connection() as conn:
            with conn:
                conn.executemany("UPDATE nodes SET position = ? WHERE id = ?", node_positions)

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


node_repository = NodeRepository()
