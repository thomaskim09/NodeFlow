from __future__ import annotations

from pathlib import Path

from services.desktop_shortcut_service import (
    PROMPT_STATE_NEVER,
    PROMPT_STATE_PENDING,
    desktop_shortcut_service,
)


def test_should_not_prompt_when_not_packaged(monkeypatch):
    monkeypatch.setattr(desktop_shortcut_service, "is_supported", lambda: True)
    monkeypatch.setattr(desktop_shortcut_service, "is_packaged_build", lambda: False)
    monkeypatch.setattr(desktop_shortcut_service, "shortcut_exists", lambda: False)

    assert desktop_shortcut_service.should_prompt(
        {
            "desktop_shortcut_prompt_state": PROMPT_STATE_PENDING,
            "desktop_shortcut_prompt_count": 0,
        }
    ) is False


def test_should_prompt_once_after_deferring(monkeypatch):
    monkeypatch.setattr(desktop_shortcut_service, "is_supported", lambda: True)
    monkeypatch.setattr(desktop_shortcut_service, "is_packaged_build", lambda: True)
    monkeypatch.setattr(desktop_shortcut_service, "shortcut_exists", lambda: False)

    assert desktop_shortcut_service.should_prompt(
        {
            "desktop_shortcut_prompt_state": PROMPT_STATE_PENDING,
            "desktop_shortcut_prompt_count": 1,
        }
    ) is True


def test_should_not_prompt_after_second_deferral(monkeypatch):
    monkeypatch.setattr(desktop_shortcut_service, "is_supported", lambda: True)
    monkeypatch.setattr(desktop_shortcut_service, "is_packaged_build", lambda: True)
    monkeypatch.setattr(desktop_shortcut_service, "shortcut_exists", lambda: False)

    assert desktop_shortcut_service.should_prompt(
        {
            "desktop_shortcut_prompt_state": PROMPT_STATE_NEVER,
            "desktop_shortcut_prompt_count": 2,
        }
    ) is False


def test_mark_deferred_stops_prompting_after_second_time():
    first = desktop_shortcut_service.mark_deferred()
    second = desktop_shortcut_service.mark_deferred()

    assert first["desktop_shortcut_prompt_state"] == PROMPT_STATE_PENDING
    assert first["desktop_shortcut_prompt_count"] == 1
    assert second["desktop_shortcut_prompt_state"] == PROMPT_STATE_NEVER
    assert second["desktop_shortcut_prompt_count"] == 2


def test_macos_target_path_prefers_app_bundle(monkeypatch):
    monkeypatch.setattr(
        "sys.executable", "/Applications/NodeFlow.app/Contents/MacOS/NodeFlow"
    )

    assert desktop_shortcut_service._macos_target_path() == Path(
        "/Applications/NodeFlow.app"
    )
