import json

from jev_router_live.config import AUTO_MODEL
from jev_router_live.settings import read_saved_model, restore_saved_model


def test_read_saved_model_ignores_sentinel(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"model": AUTO_MODEL}))
    assert read_saved_model(file) is None


def test_read_saved_model_returns_real_model(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"model": "claude-opus-5"}))
    assert read_saved_model(file) == "claude-opus-5"


def test_read_saved_model_missing_file(tmp_path):
    assert read_saved_model(tmp_path / "nope.json") is None


def test_restore_saved_model_puts_previous_back(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"model": AUTO_MODEL, "other": 1}))
    assert restore_saved_model("claude-sonnet-5", file) is True
    assert json.loads(file.read_text()) == {"model": "claude-sonnet-5", "other": 1}


def test_restore_saved_model_deletes_key_when_no_previous(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"model": AUTO_MODEL}))
    assert restore_saved_model(None, file) is True
    assert "model" not in json.loads(file.read_text())


def test_restore_saved_model_leaves_real_choice_alone(tmp_path):
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"model": "claude-opus-5"}))
    assert restore_saved_model("claude-sonnet-5", file) is False
    assert json.loads(file.read_text())["model"] == "claude-opus-5"
