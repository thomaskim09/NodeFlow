from services.segment_rebasing_service import (
    rebase_segments_for_edit,
    replace_all_and_rebase_segments,
)


def _segment(start, end, segment_id=1):
    return {
        "id": segment_id,
        "document_id": 1,
        "node_id": 1,
        "participant_id": 1,
        "segment_start": start,
        "segment_end": end,
        "content_preview": "",
    }


def test_insert_before_segment_shifts_range():
    updated, deleted = rebase_segments_for_edit(
        [_segment(6, 10)],
        position=0,
        chars_removed=0,
        chars_added=6,
        current_text="hello alpha beta",
    )

    assert deleted == []
    assert updated[0]["segment_start"] == 12
    assert updated[0]["segment_end"] == 16
    assert updated[0]["content_preview"] == "beta"


def test_delete_before_segment_shifts_range_back():
    updated, deleted = rebase_segments_for_edit(
        [_segment(12, 16)],
        position=0,
        chars_removed=6,
        chars_added=0,
        current_text="alpha beta",
    )

    assert deleted == []
    assert updated[0]["segment_start"] == 6
    assert updated[0]["segment_end"] == 10
    assert updated[0]["content_preview"] == "beta"


def test_replace_inside_segment_keeps_segment_attached():
    updated, deleted = rebase_segments_for_edit(
        [_segment(0, 10)],
        position=6,
        chars_removed=4,
        chars_added=5,
        current_text="alpha delta",
    )

    assert deleted == []
    assert updated[0]["segment_start"] == 0
    assert updated[0]["segment_end"] == 11
    assert updated[0]["content_preview"] == "alpha delta"


def test_replace_across_left_boundary_adjusts_to_surviving_text():
    updated, deleted = rebase_segments_for_edit(
        [_segment(6, 16)],
        position=0,
        chars_removed=10,
        chars_added=2,
        current_text="XX gamma",
    )

    assert deleted == []
    assert updated[0]["segment_start"] == 0
    assert updated[0]["segment_end"] == 8
    assert updated[0]["content_preview"] == "XX gamma"


def test_delete_entire_segment_removes_it():
    updated, deleted = rebase_segments_for_edit(
        [_segment(6, 10)],
        position=6,
        chars_removed=4,
        chars_added=0,
        current_text="alpha ",
    )

    assert updated == []
    assert deleted == [1]


def test_multiple_edits_can_be_applied_in_sequence():
    segments = [_segment(6, 10)]
    segments, deleted = rebase_segments_for_edit(
        segments,
        position=0,
        chars_removed=0,
        chars_added=4,
        current_text="say alpha beta",
    )
    assert deleted == []

    segments, deleted = rebase_segments_for_edit(
        segments,
        position=10,
        chars_removed=4,
        chars_added=5,
        current_text="say alpha delta",
    )

    assert deleted == []
    assert segments[0]["segment_start"] == 10
    assert segments[0]["segment_end"] == 15
    assert segments[0]["content_preview"] == "delta"


def test_replace_all_rebases_segments_from_original_text():
    text = "of alpha of beta of gamma"
    segments = [_segment(3, 16)]

    new_text, updated, deleted, count = replace_all_and_rebase_segments(
        text, segments, "of", "around"
    )

    assert count == 3
    assert deleted == []
    assert new_text == "around alpha around beta around gamma"
    assert updated[0]["segment_start"] == 7
    assert updated[0]["segment_end"] == 24
    assert updated[0]["content_preview"] == "alpha around beta"


def test_replace_all_keeps_segment_boundary_before_match():
    text = "alpha of beta"
    segments = [_segment(0, 6)]

    new_text, updated, deleted, count = replace_all_and_rebase_segments(
        text, segments, "of", "around"
    )

    assert count == 1
    assert deleted == []
    assert new_text == "alpha around beta"
    assert updated[0]["segment_start"] == 0
    assert updated[0]["segment_end"] == 6
    assert updated[0]["content_preview"] == "alpha "
