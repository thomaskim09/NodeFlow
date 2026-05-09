from __future__ import annotations

from pathlib import Path

import docx
import openpyxl

import database


class ImportService:
    def read_text_document(self, file_path: str) -> tuple[str, str]:
        path = Path(file_path)
        if path.suffix.lower() == ".docx":
            document = docx.Document(path)
            content = "\n\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            content = path.read_text(encoding="utf-8")
        return path.name, content

    def import_excel_data(
        self,
        project_id: int,
        file_path: str,
        mappings: dict[str, str],
    ) -> tuple[int, list[str]]:
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True)
            sheet = workbook.active
        except Exception as exc:
            return 0, [f"Failed to open or read the Excel file: {exc}"]

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
        except ValueError as exc:
            return 0, [f"A mapped column was not found in the Excel file: {exc}"]

        participants_in_db = {
            p["name"]: p["id"] for p in database.get_participants_for_project(project_id)
        }
        existing_titles = {
            doc["title"] for doc in database.get_documents_for_project(project_id)
        }

        docs_imported = 0
        errors: list[str] = []

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            title = row[title_col_idx].value
            content = row[content_col_idx].value
            if not title or not content:
                errors.append(f"Row {row_idx}: Skipped due to empty title or content.")
                continue

            title = str(title).strip()
            if title in existing_titles:
                base_title = title
                counter = 1
                while title in existing_titles:
                    title = f"{base_title} (copy {counter})"
                    counter += 1

            content = str(content).strip()
            participant_id = None
            if participant_col_idx is not None:
                participant_name = row[participant_col_idx].value
                if participant_name:
                    participant_name = str(participant_name).strip()
                    participant_id = participants_in_db.get(participant_name)
                    if participant_id is None:
                        try:
                            database.add_participant(project_id, participant_name)
                            participant_id = next(
                                (
                                    p["id"]
                                    for p in database.get_participants_for_project(project_id)
                                    if p["name"] == participant_name
                                ),
                                None,
                            )
                            participants_in_db[participant_name] = participant_id
                        except Exception as exc:
                            errors.append(
                                f"Row {row_idx}: Could not create participant '{participant_name}'. Error: {exc}"
                            )
                            continue

            try:
                database.add_document(project_id, title, content, participant_id)
                existing_titles.add(title)
                docs_imported += 1
            except Exception as exc:
                errors.append(
                    f"Row {row_idx}: Failed to import document '{title}'. Error: {exc}"
                )

        return docs_imported, errors


import_service = ImportService()
