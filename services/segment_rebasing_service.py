from __future__ import annotations


def calculate_text_edit_delta(old_text: str, new_text: str) -> tuple[int, int, int]:
    if old_text == new_text:
        return 0, 0, 0

    prefix_length = 0
    shortest_length = min(len(old_text), len(new_text))
    while (
        prefix_length < shortest_length
        and old_text[prefix_length] == new_text[prefix_length]
    ):
        prefix_length += 1

    suffix_length = 0
    old_remaining = len(old_text) - prefix_length
    new_remaining = len(new_text) - prefix_length
    while (
        suffix_length < old_remaining
        and suffix_length < new_remaining
        and old_text[len(old_text) - 1 - suffix_length]
        == new_text[len(new_text) - 1 - suffix_length]
    ):
        suffix_length += 1

    return (
        prefix_length,
        len(old_text) - prefix_length - suffix_length,
        len(new_text) - prefix_length - suffix_length,
    )


def replace_all_and_rebase_segments(
    text: str, segments: list[dict], search_text: str, replacement: str
) -> tuple[str, list[dict], list[int], int]:
    if not search_text:
        return text, [dict(segment) for segment in segments], [], 0

    matches = _find_non_overlapping_matches(text, search_text)
    if not matches:
        return text, [dict(segment) for segment in segments], [], 0

    new_text_parts = []
    last_position = 0
    for start, end in matches:
        new_text_parts.append(text[last_position:start])
        new_text_parts.append(replacement)
        last_position = end
    new_text_parts.append(text[last_position:])
    new_text = "".join(new_text_parts)

    updated_segments = []
    deleted_segment_ids: list[int] = []
    for segment in segments:
        new_start = _map_position_after_replacements(
            int(segment["segment_start"]), matches, len(replacement), is_end=False
        )
        new_end = _map_position_after_replacements(
            int(segment["segment_end"]), matches, len(replacement), is_end=True
        )
        new_start = max(0, min(new_start, len(new_text)))
        new_end = max(0, min(new_end, len(new_text)))
        if new_end <= new_start:
            deleted_segment_ids.append(segment["id"])
            continue

        updated_segment = dict(segment)
        updated_segment["segment_start"] = new_start
        updated_segment["segment_end"] = new_end
        updated_segment["content_preview"] = new_text[new_start:new_end]
        updated_segments.append(updated_segment)

    return new_text, updated_segments, deleted_segment_ids, len(matches)


def _map_position_after_replacements(
    position: int,
    matches: list[tuple[int, int]],
    replacement_length: int,
    is_end: bool,
) -> int:
    delta = 0
    for start, end in matches:
        edit_length = end - start
        if position < start:
            break
        if position > end or (position == end and not is_end):
            delta += replacement_length - edit_length
            continue
        if position == start and is_end:
            return start + delta
        if start <= position <= end:
            return start + delta + (replacement_length if is_end else 0)
    return position + delta


def _find_non_overlapping_matches(text: str, search_text: str) -> list[tuple[int, int]]:
    matches = []
    start = 0
    while True:
        position = text.find(search_text, start)
        if position == -1:
            break
        end = position + len(search_text)
        matches.append((position, end))
        start = end
    return matches


def rebase_segments_for_edit(
    segments: list[dict],
    position: int,
    chars_removed: int,
    chars_added: int,
    current_text: str,
) -> tuple[list[dict], list[int]]:
    edit_old_end = position + chars_removed
    delta = chars_added - chars_removed
    updated_segments = []
    deleted_segment_ids = []

    for segment in segments:
        start = int(segment["segment_start"])
        end = int(segment["segment_end"])

        if chars_removed == 0:
            new_start, new_end = _rebase_for_insert(start, end, position, chars_added)
        elif end <= position:
            new_start, new_end = start, end
        elif start >= edit_old_end:
            new_start, new_end = start + delta, end + delta
        else:
            new_start, new_end = _rebase_for_replacement(
                start, end, position, edit_old_end, chars_added, delta
            )

        new_start = max(0, min(new_start, len(current_text)))
        new_end = max(0, min(new_end, len(current_text)))
        if new_end <= new_start:
            deleted_segment_ids.append(segment["id"])
            continue

        updated_segment = dict(segment)
        updated_segment["segment_start"] = new_start
        updated_segment["segment_end"] = new_end
        updated_segment["content_preview"] = current_text[new_start:new_end]
        updated_segments.append(updated_segment)

    return updated_segments, deleted_segment_ids


def _rebase_for_insert(
    start: int, end: int, position: int, chars_added: int
) -> tuple[int, int]:
    if position < start:
        return start + chars_added, end + chars_added
    if start <= position <= end:
        return start, end + chars_added
    return start, end


def _rebase_for_replacement(
    start: int,
    end: int,
    edit_start: int,
    edit_old_end: int,
    chars_added: int,
    delta: int,
) -> tuple[int, int]:
    if start < edit_start:
        new_start = start
    elif start >= edit_old_end:
        new_start = start + delta
    else:
        new_start = edit_start

    if end > edit_old_end:
        new_end = end + delta
    else:
        new_end = edit_start + chars_added

    return new_start, new_end
