#!/usr/bin/env python3
"""Launches the real OpenAI Codex CLI with the local per-turn routing proxy in front of it."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from jev_router_live.codex_proxy import CODEX_AUTO_MODEL, start_codex_proxy
from jev_router_live.env_file import load_env

PROVIDER = "jev"
ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXPLAIN_SKILL = ROOT / "skills" / "codex" / "jev-explain" / "SKILL.md"


def install_codex_skill(home: Path | None = None) -> Path:
    home = home or Path.home()
    target = home / ".agents" / "skills" / "jev-router-explain" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(EXPLAIN_SKILL.read_bytes())
    return target


def _resolve_codex() -> str | None:
    return shutil.which("codex")


def codex_args(base_url: str, args: list[str]) -> list[str]:
    has_model = any(a in ("--model", "-m") or a.startswith("--model=") for a in args)
    prefix = [] if has_model else ["--model", CODEX_AUTO_MODEL]
    return [
        *prefix,
        "--config", f'model_provider="{PROVIDER}"',
        "--config", f'model_providers.{PROVIDER}.name="Jev Router"',
        "--config", f'model_providers.{PROVIDER}.base_url="{base_url}"',
        "--config", f'model_providers.{PROVIDER}.wire_api="responses"',
        "--config", f'model_providers.{PROVIDER}.requires_openai_auth=true',
        "--config", f'model_providers.{PROVIDER}.supports_websockets=false',
        *args,
    ]


def main() -> None:
    load_env()
    try:
        install_codex_skill()
    except OSError as exc:
        sys.stderr.write(f"[jev] could not install the Codex explanation skill: {exc}\n")

    codex = _resolve_codex()
    if not codex:
        sys.stderr.write(
            "[jev] OpenAI Codex is not installed, or `codex` is not on your PATH.\n"
            "[jev] jev-codex runs the real Codex CLI; install it first:\n"
            "[jev]   https://developers.openai.com/codex/cli\n"
        )
        sys.exit(1)

    args = sys.argv[1:]
    status_id = f"codex-{os.getpid()}"
    os.environ["JEV_CODEX_STATUS_ID"] = status_id
    close = lambda: None  # noqa: E731

    if os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY"):
        handle = start_codex_proxy(status_id=status_id)
        close = handle.close
        args = codex_args(f"http://127.0.0.1:{handle.port}", args)
    else:
        sys.stderr.write(
            "[jev] no JEV_API_KEY found - starting Codex without routing\n"
            f"[jev] add JEV_API_KEY=... to {Path.home() / '.jev-router.env'} and restart jev-codex\n"
        )

    try:
        result = subprocess.run([codex, *args], env=os.environ)
        code = result.returncode
    except OSError as exc:
        close()
        sys.stderr.write(f"[jev] could not start Codex: {exc}\n")
        sys.exit(1)
    close()
    sys.exit(code)


if __name__ == "__main__":
    main()
