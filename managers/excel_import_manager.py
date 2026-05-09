from services.import_service import import_service


def import_data(project_id, file_path, mappings, progress_callback=None):
    return import_service.import_excel_data(project_id, file_path, mappings)
