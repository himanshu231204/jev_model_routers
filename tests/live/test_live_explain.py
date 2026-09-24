from jev_router_live.explain import format_explanation


def test_no_status():
    assert "no routing decision" in format_explanation(None)


def test_manual_status():
    assert "manually" in format_explanation({"manual": True})


def test_full_report_contains_key_fields():
    status = {
        "prompt": "fix the failing test",
        "tier": "sonnet",
        "model": "claude-sonnet-5",
        "confidence": 0.94,
        "reason": "jev",
        "metrics": {
            "taskComplexity": 0.5,
            "reasoningRequired": 0.6,
            "toolComplexity": 0.3,
            "contextSize": 0.1,
        },
        "jev": {
            "request": {"state": {"session": {"current_model": "claude-haiku-4-5-20251001", "context_tokens": 6200}}},
            "response": {},
        },
    }
    report = format_explanation(status)
    assert "SONNET" in report
    assert "94%" in report
    assert "Jev recommendation" in report
    assert "6200" in report
