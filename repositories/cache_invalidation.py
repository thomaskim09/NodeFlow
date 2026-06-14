from __future__ import annotations


def invalidate_analysis_cache() -> None:
    # Lazy import avoids a repository -> service -> database import cycle.
    from services.dashboard_service import dashboard_service

    dashboard_service.clear_cache()
