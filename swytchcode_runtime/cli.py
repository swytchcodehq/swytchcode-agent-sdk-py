"""Run a swytchcode CLI subcommand with --json and parse the output."""

from __future__ import annotations
import json
import os
import subprocess
from typing import Any

from .exec import _resolve_bin
from .errors import SwytchcodeError


def run_cli(args: list[str], *, cwd: str | None = None, env: dict | None = None) -> Any:
    cmd = [_resolve_bin(), *args]
    if "--json" not in args:
        cmd.append("--json")

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        r = subprocess.run(
            cmd, capture_output=True, cwd=cwd or os.getcwd(), env=run_env
        )
    except FileNotFoundError as e:
        raise SwytchcodeError(
            "Failed to spawn swytchcode; is the CLI installed?", e
        ) from e

    if r.returncode != 0:
        raise SwytchcodeError(
            r.stderr.decode("utf-8", "replace").strip() or "command failed",
            r.returncode,
        )

    out = r.stdout.decode("utf-8", "replace").strip()
    if not out:
        return None

    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise SwytchcodeError("Invalid JSON from swytchcode", out) from e
