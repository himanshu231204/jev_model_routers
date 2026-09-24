from jev_router_live import status as status_mod


def test_write_read_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr(status_mod, "STATUS_DIR", tmp_path / "jev-claude")

    status_mod.write_decision("sess-1", {"tier": "sonnet", "reason": "jev"})
    status_mod.write_decision("sess-1", {"tier": "opus", "reason": "jev"})

    result = status_mod.read_status("sess-1")
    assert result["tier"] == "opus"
    assert len(result["history"]) == 2
    assert result["history"][0]["tier"] == "sonnet"


def test_read_missing_session_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(status_mod, "STATUS_DIR", tmp_path / "jev-claude")
    assert status_mod.read_status("does-not-exist") is None


def test_write_status_ignores_empty_session(tmp_path, monkeypatch):
    monkeypatch.setattr(status_mod, "STATUS_DIR", tmp_path / "jev-claude")
    status_mod.write_status("", {"tier": "opus"})
    assert not (tmp_path / "jev-claude").exists()


def test_prune_stale_removes_old_files(tmp_path, monkeypatch):
    monkeypatch.setattr(status_mod, "STATUS_DIR", tmp_path / "jev-claude")
    status_mod.write_status("old", {"tier": "haiku"})
    status_mod.write_status("fresh", {"tier": "opus"})

    import os
    import time

    old_file = status_mod._file_for("old")
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_file, (old_time, old_time))

    removed = status_mod.prune_stale()
    assert removed == 1
    assert status_mod.read_status("old") is None
    assert status_mod.read_status("fresh") is not None
