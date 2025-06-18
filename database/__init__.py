# Replace the contents of database/__init__.py with this updated version

# Core
from .db_core import get_db_connection, create_tables  # noqa: F401

# Projects
from .projects_db import (
    add_project,
    get_all_projects,
    rename_project,
    delete_project,
)  # noqa: F401

# Participants
from .participants_db import (
    add_participant,
    get_participants_for_project,
    update_participant,
    delete_participant,
)  # noqa: F401

# Documents
from .documents_db import (
    add_document,
    get_documents_for_project,
    get_document_content,
    delete_document,
    update_document_text_only,
    get_document_word_count,
    get_project_word_count,
)  # noqa: F401

# Nodes
from .nodes_db import (
    add_node,
    get_nodes_for_project,
    update_node_name,
    update_node_color,
    delete_node,
    update_node_order,
    update_node_parent,
)  # noqa: F401

# Coded Segments
from .segments_db import (
    add_coded_segment,
    get_coded_segments_for_document,
    get_coded_segments_for_project,
    get_coded_segments_for_participant,
    delete_coded_segment,
    get_node_statistics,
    get_word_count_for_participant,
)  # noqa: F401
