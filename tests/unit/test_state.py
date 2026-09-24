from jev_router.state.memory import MemoryStore
from jev_router.core.lifecycle import TurnState, state_key

def test_memory_pin_and_isolation():
    s = MemoryStore()
    s.pin(state_key("a", "s1", "c1", None), TurnState(turn_id="t1", model="m-strong", tier="strong", reason="r"))
    assert s.get(state_key("a", "s1", "c1", None)).model == "m-strong"
    assert s.get(state_key("a", "s1", "c1", "sub1")) is None

def test_sqlite_roundtrip(tmp_path):
    from jev_router.state.sqlite import SqliteStore
    s = SqliteStore(str(tmp_path / "t.db"))
    s.pin(state_key("a", "s", "c", None), TurnState(turn_id="t", model="m1", tier="fast", reason="r"))
    assert s.get(state_key("a", "s", "c", None)).model == "m1"
