from jev_router_live.proxy import (
    apply_tier,
    claude_models,
    conversation_key,
    new_turn_prompt,
    sanitize_schema,
    session_of,
    start_proxy,
)


def test_new_turn_prompt_requires_tools_and_user_role():
    assert new_turn_prompt({"tools": [], "messages": [{"role": "user", "content": "hi"}]}) is None
    assert new_turn_prompt({"messages": [{"role": "user", "content": "hi"}]}) is None
    assert new_turn_prompt({"tools": [{}], "messages": [{"role": "assistant", "content": "hi"}]}) is None


def test_new_turn_prompt_strips_system_reminder():
    body = {
        "tools": [{}],
        "messages": [{"role": "user", "content": "<system-reminder>noise</system-reminder>do the thing"}],
    }
    assert new_turn_prompt(body) == "do the thing"


def test_new_turn_prompt_none_for_tool_result_continuation():
    body = {
        "tools": [{}],
        "messages": [{"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}],
    }
    assert new_turn_prompt(body) is None


def test_apply_tier_strips_thinking_for_haiku():
    body = {"model": "x", "thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}
    apply_tier(body, "haiku")
    assert body["model"] == "claude-haiku-4-5-20251001"
    assert "thinking" not in body
    assert "output_config" not in body


def test_apply_tier_keeps_thinking_for_opus():
    body = {"model": "x", "thinking": {"type": "adaptive"}}
    apply_tier(body, "opus")
    assert body["thinking"] == {"type": "adaptive"}


def test_sanitize_schema_converts_boolean_exclusive_bounds():
    schema = {"minimum": 1, "exclusiveMinimum": True}
    sanitize_schema(schema)
    assert schema == {"exclusiveMinimum": 1}


def test_sanitize_schema_drops_false_exclusive_bound():
    schema = {"minimum": 1, "exclusiveMinimum": False}
    sanitize_schema(schema)
    assert schema == {"minimum": 1}


def test_claude_models_falls_back_to_static_tiers():
    models = claude_models([])
    assert {m["tier"] for m in models} == {"haiku", "sonnet", "opus", "fable"}


def test_session_of_parses_metadata():
    body = {"metadata": {"user_id": '{"session_id": "abc"}'}}
    assert session_of(body) == "abc"
    assert session_of({}) == ""


def test_conversation_key_is_stable_for_same_first_message():
    a = {"metadata": {"user_id": '{"session_id": "s1"}'}, "messages": [{"content": "hello"}]}
    b = {"metadata": {"user_id": '{"session_id": "s1"}'}, "messages": [{"content": "hello"}]}
    c = {"metadata": {"user_id": '{"session_id": "s1"}'}, "messages": [{"content": "different"}]}
    assert conversation_key(a) == conversation_key(b)
    assert conversation_key(a) != conversation_key(c)


def test_start_proxy_head_probe_and_passthrough_of_manual_model():
    def fail_route(**kwargs):
        raise AssertionError("route should not be called for a manually selected model")

    handle = start_proxy(upstream_url="http://127.0.0.1:1", route=fail_route)
    try:
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", handle.port, timeout=2)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        assert resp.status == 200
        conn.close()
    finally:
        handle.close()


def test_new_turn_prompt_skips_trailing_system_message():
    # Current Claude Code appends a role:"system" context message after the user's prompt.
    body = {
        "tools": [{}],
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "rename x"}]},
            {"role": "system", "content": [{"type": "text", "text": "skills listing..."}]},
        ],
    }
    assert new_turn_prompt(body) == "rename x"


def test_new_turn_prompt_trailing_system_after_tool_result_is_continuation():
    body = {
        "tools": [{}],
        "messages": [
            {"role": "user", "content": "rename x"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": "Bash", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]},
            {"role": "system", "content": [{"type": "text", "text": "reminder"}]},
        ],
    }
    assert new_turn_prompt(body) is None
