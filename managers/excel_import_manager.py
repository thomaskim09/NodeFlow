import openpyxl
import database
from PySide6.QtWidgets import QApplication


def import_data(project_id, file_path, mappings, progress_callback=None):
    """
    Imports data from an Excel file into the NodeFlow database.

    Args:
        project_id (int): The ID of the project to import into.
        file_path (str): The path to the .xlsx file.
        mappings (dict): A dictionary mapping 'title', 'content', and 'participant'
                         to the corresponding Excel column headers.
        progress_callback (function, optional): A function to call with progress updates.

    Returns:
        A tuple of (number_of_docs_imported, list_of_errors)
    """
    try:
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        sheet = workbook.active
    except Exception as e:
        return 0, [f"Failed to open or read the Excel file: {e}"]

    headers = [cell.value for cell in sheet[1]]
    try:
        title_col_idx = headers.index(mappings["title"])
        content_col_idx = headers.index(mappings["content"])
        participant_col_name = mappings.get("participant")
        participant_col_idx = (
            headers.index(participant_col_name)
            if participant_col_name and participant_col_name != "<Assign Later>"
            else None
        )
    except ValueError as e:
        return 0, [f"A mapped column was not found in the Excel file: {e}"]

    # Cache existing participants to reduce database calls
    participants_in_db = {
        p["name"]: p["id"] for p in database.get_participants_for_project(project_id)
    }
    existing_docs = database.get_documents_for_project(project_id)
    existing_titles = {doc["title"] for doc in existing_docs}

    docs_imported = 0
    errors = []

    # Iterate over rows, skipping the header
    for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        QApplication.processEvents()  # Keep UI responsive

        title = row[title_col_idx].value
        content = row[content_col_idx].value

        # Basic validation
        if not title or not content:
            errors.append(f"Row {row_idx}: Skipped due to empty title or content.")
            continue

        title = str(title).strip()
        if title in existing_titles:
            original_title = title
            counter = 1
            while title in existing_titles:
                title = f"{original_title} (copy {counter})"
                counter += 1
        content = str(content).strip()
        participant_id = None

        if participant_col_idx is not None:
            participant_name = row[participant_col_idx].value
            if participant_name:
                participant_name = str(participant_name).strip()
                if participant_name in participants_in_db:
                    participant_id = participants_in_db[participant_name]
                else:
                    # Participant not found, create them and update our cache
                    try:
                        database.add_participant(project_id, participant_name)
                        newly_added_participants = {
                            p["name"]: p["id"]
                            for p in database.get_participants_for_project(project_id)
                        }
                        participant_id = newly_added_participants.get(participant_name)
                        participants_in_db[participant_name] = participant_id
                    except Exception as e:
                        errors.append(
                            f"Row {row_idx}: Could not create new participant '{participant_name}'. Error: {e}"
                        )
                        continue

        try:
            database.add_document(project_id, title, content, participant_id)
            docs_imported += 1
            existing_titles.add(title)
        except Exception as e:
            errors.append(
                f"Row {row_idx}: Failed to import document '{title}'. Error: {e}"
            )

    return docs_imported, errors
