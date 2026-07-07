from repositories.segment_repository import segment_repository


def add_coded_segment(document_id, node_id, participant_id, start, end, text_preview):
    return segment_repository.add(
        document_id, node_id, participant_id, start, end, text_preview
    )


def get_coded_segments_for_nodes(project_id, node_ids, document_id=None):
    return segment_repository.get_for_nodes(project_id, node_ids, document_id)


# Replace the existing get_coded_segments_for_document function
# in database/segments_db.py with this corrected version.


def get_coded_segments_for_document(document_id):
    return segment_repository.get_for_document(document_id)


def get_coded_segments_for_project(project_id):
    return segment_repository.get_for_project(project_id)


def get_coded_segments_for_participant(project_id, participant_id):
    return segment_repository.get_for_participant(project_id, participant_id)


def delete_coded_segment(segment_id):
    segment_repository.delete(segment_id)


def update_coded_segment(segment_id, new_start, new_end, new_content_preview):
    segment_repository.update(segment_id, new_start, new_end, new_content_preview)


def update_coded_segment_with_remark(
    segment_id, new_start, new_end, new_content_preview, new_remark
):
    segment_repository.update(
        segment_id, new_start, new_end, new_content_preview, new_remark
    )


def update_coded_segment_remark(segment_id, remark):
    segment_repository.update_remark(segment_id, remark)


def get_node_statistics(project_id, document_id=None):
    return segment_repository.get_node_statistics(project_id, document_id)


def get_participant_statistics(project_id, document_id=None):
    return segment_repository.get_participant_statistics(project_id, document_id)


def get_word_count_for_participant(project_id, participant_id):
    return segment_repository.get_word_count_for_participant(project_id, participant_id)
