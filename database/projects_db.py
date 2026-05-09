import sqlite3

from repositories.project_repository import project_repository


def add_project(name, description=""):
    try:
        project_repository.add(name, description)
    except sqlite3.IntegrityError as e:
        raise e


def get_all_projects():
    return project_repository.list_all()


def rename_project(project_id, new_name):
    project_repository.rename(project_id, new_name)


def delete_project(project_id):
    project_repository.delete(project_id)
