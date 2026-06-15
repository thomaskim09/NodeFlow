from __future__ import annotations

import database
from repositories.base import initialize_database

PROJECT_NAME = "NVivo Export Demo"


def ensure_fresh_project() -> int:
    for project in database.get_all_projects():
        if project["name"] == PROJECT_NAME:
            database.delete_project(project["id"])
            break
    database.add_project(
        PROJECT_NAME,
        "Rich seed data for testing coding, filtering, and every Excel export mode.",
    )
    for project in database.get_all_projects():
        if project["name"] == PROJECT_NAME:
            return project["id"]
    raise RuntimeError("Failed to create demo project.")


def add_document(project_id: int, participant_id: int, title: str, text: str) -> int:
    return database.add_document(project_id, title, text, participant_id)


def code_snippet(document_id: int, node_id: int, participant_id: int, content: str, snippet: str) -> None:
    start = content.index(snippet)
    end = start + len(snippet)
    database.add_coded_segment(document_id, node_id, participant_id, start, end, snippet)


def main() -> None:
    initialize_database()
    project_id = ensure_fresh_project()

    participants = {
        "R1": database.add_participant(project_id, "R1"),
        "R2": database.add_participant(project_id, "R2"),
        "R3": database.add_participant(project_id, "R3"),
        "R4": database.add_participant(project_id, "R4"),
        "R5": database.add_participant(project_id, "R5"),
    }

    product_strategy = database.add_node(project_id, "Product Strategy", None, "#FFB3BA")
    itinerary_design = database.add_node(project_id, "Itinerary Design", product_strategy, "#FFDFBA")
    optional_activities = database.add_node(project_id, "Optional Activities", itinerary_design, "#FFFFBA")
    pricing_range = database.add_node(project_id, "Pricing Range", optional_activities, "#BAFFC9")

    operations = database.add_node(project_id, "Operations", None, "#BAE1FF")
    booking_flow = database.add_node(project_id, "Booking Flow", operations, "#E0BBE4")
    reservations = database.add_node(project_id, "Reservations and Payments", booking_flow, "#FFD6E5")
    support_handoff = database.add_node(project_id, "Support Handoff", booking_flow, "#D4A5A5")

    tech_gaps = database.add_node(project_id, "Tech Gaps", None, "#A5D4A5")
    architecture_recovery = database.add_node(project_id, "Architecture Recovery", tech_gaps, "#A5A5D4")
    memory_rebuild = database.add_node(project_id, "Memory Rebuild", architecture_recovery, "#FFCC00")

    analytics = database.add_node(project_id, "Analytics and Reporting", None, "#FF6600")
    dashboards = database.add_node(project_id, "Dashboard Use", analytics, "#FF3300")
    excel_exports = database.add_node(project_id, "Excel Exports", analytics, "#CC3300")

    nodes = {
        "product_strategy": product_strategy,
        "itinerary_design": itinerary_design,
        "optional_activities": optional_activities,
        "pricing_range": pricing_range,
        "operations": operations,
        "booking_flow": booking_flow,
        "reservations": reservations,
        "support_handoff": support_handoff,
        "tech_gaps": tech_gaps,
        "architecture_recovery": architecture_recovery,
        "memory_rebuild": memory_rebuild,
        "analytics": analytics,
        "dashboards": dashboards,
        "excel_exports": excel_exports,
    }

    documents = [
        (
            "R1 - Product Center",
            "R1",
            (
                "I led the plan to make itinerary the center of the universe. "
                "Product is it. Optional activities should stay visible without forcing commitment."
            ),
            [
                ("product_strategy", "make itinerary the center of the universe"),
                ("itinerary_design", "Product is it"),
                ("optional_activities", "Optional activities should stay visible"),
            ],
        ),
        (
            "R1 - Price Framing",
            "R1",
            (
                "Prices should contribute to the total trip expenses as a clear range. "
                "People want to compare optional add-ons before they book."
            ),
            [
                ("pricing_range", "total trip expenses as a clear range"),
                ("optional_activities", "optional add-ons before they book"),
            ],
        ),
        (
            "R2 - Booking WIP",
            "R2",
            (
                "It can be a work in progress itinerary with optional everything before confirmation. "
                "Booking should connect itinerary choices with reservation and payment in one flow."
            ),
            [
                ("itinerary_design", "work in progress itinerary"),
                ("booking_flow", "Booking should connect itinerary choices"),
                ("reservations", "reservation and payment in one flow"),
            ],
        ),
        (
            "R2 - Support Delays",
            "R2",
            (
                "Support needs a better handoff when pricing changes. "
                "Right now the reservation follow-up is fragmented across tools."
            ),
            [
                ("support_handoff", "Support needs a better handoff"),
                ("reservations", "reservation follow-up is fragmented"),
            ],
        ),
        (
            "R3 - Memory Pieces",
            "R3",
            (
                "I am picking up memory pieces to recreate the vision of the old code architecture. "
                "The rebuild is slower because key flows live only in people's heads."
            ),
            [
                ("architecture_recovery", "recreate the vision of the old code architecture"),
                ("memory_rebuild", "picking up memory pieces"),
            ],
        ),
        (
            "R3 - Reporting Gap",
            "R3",
            (
                "The dashboard is good for trends but weak for quote review. "
                "Excel exports need to preserve hierarchy and respondent detail together."
            ),
            [
                ("dashboards", "dashboard is good for trends"),
                ("excel_exports", "preserve hierarchy and respondent detail together"),
            ],
        ),
        (
            "R4 - Reservations",
            "R4",
            (
                "Reservation and payment should appear as one committed step after itinerary review. "
                "Users ask for clearer status before they commit money."
            ),
            [
                ("reservations", "one committed step after itinerary review"),
                ("booking_flow", "clearer status before they commit money"),
            ],
        ),
        (
            "R4 - Optional Choices",
            "R4",
            (
                "Optional activities are fine when they look bundled into a larger trip story. "
                "The price range should update as people toggle those choices."
            ),
            [
                ("optional_activities", "look bundled into a larger trip story"),
                ("pricing_range", "price range should update"),
            ],
        ),
        (
            "R5 - Executive Review",
            "R5",
            (
                "Leaders want a workbook that combines classification quotes with respondent counts. "
                "They do not want to merge two exports by hand every week."
            ),
            [
                ("excel_exports", "combines classification quotes with respondent counts"),
                ("analytics", "merge two exports by hand every week"),
            ],
        ),
        (
            "R5 - Dashboard Limits",
            "R5",
            (
                "The dashboard helps with broad patterns. "
                "Researchers still need coded quotes by finding, node, and sub-node."
            ),
            [
                ("dashboards", "dashboard helps with broad patterns"),
                ("excel_exports", "coded quotes by finding, node, and sub-node"),
            ],
        ),
        (
            "R2 - Architecture Debt",
            "R2",
            (
                "Architecture recovery is hard when naming is inconsistent. "
                "Memory rebuild starts with documenting one export flow at a time."
            ),
            [
                ("architecture_recovery", "naming is inconsistent"),
                ("memory_rebuild", "documenting one export flow at a time"),
            ],
        ),
        (
            "R1 - Analytics Team",
            "R1",
            (
                "Analytics wants Excel exports that are clean enough to hand to another team. "
                "Dashboard snapshots are helpful but not enough for audit review."
            ),
            [
                ("excel_exports", "clean enough to hand to another team"),
                ("dashboards", "not enough for audit review"),
            ],
        ),
    ]

    segment_count = 0
    document_count = 0
    for title, participant_key, text, codings in documents:
        participant_id = participants[participant_key]
        document_id = add_document(project_id, participant_id, title, text)
        document_count += 1
        for node_key, snippet in codings:
            code_snippet(document_id, nodes[node_key], participant_id, text, snippet)
            segment_count += 1

    print(
        f"Created demo project '{PROJECT_NAME}' with {document_count} documents and {segment_count} coded segments."
    )


if __name__ == "__main__":
    main()
