import os


def get_resource_path(filename: str) -> str:
    os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    resource_folder_path = os.path.join(project_root, "resource")
    os.makedirs(resource_folder_path, exist_ok=True)
    full_path = os.path.join(resource_folder_path, filename)
    return full_path
