from __future__ import annotations

from pathlib import Path

import pytest

from utils.app_paths import set_test_user_data_dir


@pytest.fixture(autouse=True)
def isolated_app_data(tmp_path: Path):
    data_root = tmp_path / "appdata"
    set_test_user_data_dir(data_root)
    yield
    set_test_user_data_dir(data_root)
