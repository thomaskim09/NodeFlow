from repositories.document_repository import document_repository


def add_document(project_id, title, text, participant_id=None, source_metadata=None):
    return document_repository.add(
        project_id, title, text, participant_id, source_metadata
    )


def get_documents_for_project(project_id):
    return document_repository.list_for_project(project_id)


def get_document_content(document_id):
    return document_repository.get_content(document_id)


def delete_document(document_id):
    document_repository.delete(document_id)


def update_document_text_only(document_id, new_content):
    document_repository.update_content(document_id, new_content)


def update_document_text_and_segments(
    document_id, new_content, segments, deleted_segment_ids
):
    document_repository.update_content_and_segments(
        document_id, new_content, segments, deleted_segment_ids
    )


def get_document_word_count(document_id):
    return document_repository.get_word_count(document_id)


def get_project_word_count(project_id):
    return document_repository.get_project_word_count(project_id)


def check_document_exists(project_id: int, title: str, content: str) -> bool:
    return document_repository.exists(project_id, title, content)
