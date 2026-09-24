from jev_router.providers.registry import PROVIDERS
from jev_router.providers.anthropic import AnthropicProvider

def test_registry_has_vendors():
    assert {"anthropic", "openai", "ollama"} <= set(PROVIDERS)

def test_anthropic_translate_sets_model():
    p = AnthropicProvider()
    out = p.translate({"body": {"messages": []}}, "claude-sonnet")
    assert out["body"]["model"] == "claude-sonnet"

def test_providers_never_import_core():
    import ast, pathlib
    for f in pathlib.Path("src/jev_router/providers").glob("*.py"):
        tree = ast.parse(f.read_text())
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any("jev_router.core" in m for m in mods), f
