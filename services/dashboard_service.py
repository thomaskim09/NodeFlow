from __future__ import annotations

from dataclasses import dataclass, field

import database


@dataclass
class DashboardQuery:
    project_id: int
    doc_id: int
    part_id: int
    node_id: int


@dataclass
class DashboardService:
    _cache: dict[tuple[int, int, int, int], dict] = field(default_factory=dict)

    def clear_cache(self) -> None:
        self._cache.clear()

    def load(self, query: DashboardQuery) -> dict:
        key = (query.project_id, query.doc_id, query.part_id, query.node_id)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        nodes = database.get_nodes_for_project(query.project_id)
        nodes_map, nodes_by_parent = self.build_node_hierarchy(nodes)
        results = {
            "nodes": nodes,
            "nodes_map": nodes_map,
            "nodes_by_parent": nodes_by_parent,
        }
        if query.node_id != -1:
            all_project_segments = database.get_coded_segments_for_project(query.project_id)
            node_stats, _ = self.calculate_direct_stats(all_project_segments)
            results.update(
                {
                    "node_id": query.node_id,
                    "aggregated_stats": self.calculate_aggregated_stats(
                        nodes_by_parent, node_stats
                    ),
                    "all_project_segments": all_project_segments,
                }
            )
        else:
            total_words, segments = self.get_scoped_data(
                query.project_id, query.doc_id, query.part_id
            )
            node_stats, coded_words = self.calculate_direct_stats(segments)
            results.update(
                {
                    "participant_stats": self.calculate_participant_stats(
                        query.project_id, segments
                    ),
                    "total_words": total_words,
                    "segments": segments,
                    "coded_words": coded_words,
                    "aggregated_stats": self.calculate_aggregated_stats(
                        nodes_by_parent, node_stats
                    ),
                    "co_occurrence_matrix": self.calculate_co_occurrence(
                        segments, nodes
                    )[0],
                    "co_occurrence_headers": self.calculate_co_occurrence(
                        segments, nodes
                    )[1],
                }
            )

        self._cache[key] = results
        return results

    def get_scoped_data(
        self, project_id: int, doc_id: int, part_id: int
    ) -> tuple[int, list[dict]]:
        if doc_id != -1:
            total_words = database.get_document_word_count(doc_id)
            segments = database.get_coded_segments_for_document(doc_id)
            if part_id != -1:
                participant = next(
                    (
                        p["name"]
                        for p in database.get_participants_for_project(project_id)
                        if p["id"] == part_id
                    ),
                    None,
                )
                if participant:
                    segments = [
                        segment
                        for segment in segments
                        if segment["participant_name"] == participant
                    ]
            return total_words, segments

        if part_id != -1:
            return (
                database.get_word_count_for_participant(project_id, part_id),
                database.get_coded_segments_for_participant(project_id, part_id),
            )

        return (
            database.get_project_word_count(project_id),
            database.get_coded_segments_for_project(project_id),
        )

    @staticmethod
    def calculate_direct_stats(segments: list[dict]) -> tuple[dict[int, dict], int]:
        node_stats: dict[int, dict] = {}
        total_coded_words = 0
        for seg in segments:
            node_stats.setdefault(seg["node_id"], {"word_count": 0, "segment_count": 0})
            word_count = len(seg["content_preview"].split())
            node_stats[seg["node_id"]]["segment_count"] += 1
            node_stats[seg["node_id"]]["word_count"] += word_count
            total_coded_words += word_count
        return node_stats, total_coded_words

    @staticmethod
    def build_node_hierarchy(nodes: list[dict]) -> tuple[dict[int, dict], dict[int | None, list[dict]]]:
        nodes_map = {node["id"]: node for node in nodes}
        nodes_by_parent: dict[int | None, list[dict]] = {node["id"]: [] for node in nodes}
        nodes_by_parent[None] = []
        for node in nodes:
            nodes_by_parent.setdefault(node["parent_id"], []).append(node)
        for child_nodes in nodes_by_parent.values():
            child_nodes.sort(key=lambda item: (item.get("position", 0) or 0, item["name"]))
        return nodes_map, nodes_by_parent

    @staticmethod
    def calculate_aggregated_stats(
        nodes_by_parent: dict[int | None, list[dict]],
        node_stats: dict[int, dict],
    ) -> dict[int, dict[str, int]]:
        aggregated_stats: dict[int, dict[str, int]] = {}

        def recurse(parent_id: int | None) -> tuple[int, int]:
            word_total = 0
            segment_total = 0
            for node in nodes_by_parent.get(parent_id, []):
                child_words, child_segments = recurse(node["id"])
                direct_stats = node_stats.get(node["id"], {})
                total_words = direct_stats.get("word_count", 0) + child_words
                total_segments = direct_stats.get("segment_count", 0) + child_segments
                aggregated_stats[node["id"]] = {
                    "word_count": total_words,
                    "segment_count": total_segments,
                }
                word_total += total_words
                segment_total += total_segments
            return word_total, segment_total

        recurse(None)
        return aggregated_stats

    @staticmethod
    def calculate_co_occurrence(
        segments: list[dict], nodes: list[dict]
    ) -> tuple[dict[str, dict[str, int]], list[str]]:
        node_name_by_id = {node["id"]: node["name"] for node in nodes}
        matrix: dict[str, dict[str, int]] = {}
        segments_by_range: dict[tuple[int, int, int], list[int]] = {}

        for seg in segments:
            key = (seg["document_id"], seg["segment_start"], seg["segment_end"])
            segments_by_range.setdefault(key, []).append(seg["node_id"])

        for node_ids in segments_by_range.values():
            unique_node_ids = sorted(set(node_ids))
            for i, node1_id in enumerate(unique_node_ids):
                for node2_id in unique_node_ids[i:]:
                    name1 = node_name_by_id.get(node1_id)
                    name2 = node_name_by_id.get(node2_id)
                    if not name1 or not name2:
                        continue
                    matrix.setdefault(name1, {})
                    matrix[name1][name2] = matrix[name1].get(name2, 0) + 1
                    if name1 != name2:
                        matrix.setdefault(name2, {})
                        matrix[name2][name1] = matrix[name2].get(name1, 0) + 1

        return matrix, sorted(matrix.keys())

    @staticmethod
    def calculate_participant_stats(project_id: int, segments: list[dict]) -> dict[int, dict]:
        participant_stats = {
            participant["id"]: {
                "word_count": 0,
                "segment_count": 0,
                "name": participant["name"],
            }
            for participant in database.get_participants_for_project(project_id)
        }
        for seg in segments:
            participant_id = seg.get("participant_id")
            if participant_id is not None and participant_id in participant_stats:
                word_count = len(seg["content_preview"].split())
                participant_stats[participant_id]["word_count"] += word_count
                participant_stats[participant_id]["segment_count"] += 1
        return participant_stats


dashboard_service = DashboardService()
