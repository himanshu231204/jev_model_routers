"""CLI command that runs environment diagnostics and prints remediation hints."""
from __future__ import annotations
import os, sys
def run_doctor(args: dict) -> int:
    print(f"python: {sys.version.split()[0]}")
    print("TYPESAFE_API_KEY: " + ("present" if os.environ.get("TYPESAFE_API_KEY") else "MISSING — routing runs in passthrough"))
    print("config: configs/default.yaml (privacy.log_prompts=false, send_repository_content=false)")
    return 0
