import pytest

from jev_router_live import log as log_mod
from jev_router_live import status as status_mod


@pytest.fixture(autouse=True)
def _isolated_files(tmp_path, monkeypatch):
    """Keep tests from touching the developer's real ~/.jev-claude.log and /tmp/jev-claude."""
    monkeypatch.setattr(log_mod, "LOG_FILE", tmp_path / "jev-claude.log")
    monkeypatch.setattr(status_mod, "STATUS_DIR", tmp_path / "jev-claude")
