from repositories.participant_repository import participant_repository


def add_participant(project_id, name, details=""):
    participant_repository.add(project_id, name, details)


def get_participants_for_project(project_id):
    return participant_repository.list_for_project(project_id)


def get_participant_for_document(document_id: int) -> int | None:
    return participant_repository.get_for_document(document_id)


def update_participant(participant_id, name, details):
    participant_repository.update(participant_id, name, details)


def delete_participant(participant_id):
    participant_repository.delete(participant_id)
