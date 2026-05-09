from repositories.base import connect, initialize_database


def get_db_connection():
    """Compatibility wrapper for legacy imports."""
    return connect()


def create_tables():
    initialize_database()
