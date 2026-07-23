"""Run swytchcode exec with optional JSON input on stdin."""

import json
import os
import shutil
import subprocess
import sys
from typing import Any

from .errors import SwytchcodeError


def _resolve_bin() -> str:
    """
    Resolve the swytchcode binary path using the following order:

    1. SWYTCHCODE_BIN env var — explicit override.
    2. PATH lookup via shutil.which — the standard resolution.
    3. Common install-path fallbacks for when PATH is not configured.
    """
    # 1. Explicit override
    explicit = os.environ.get("SWYTCHCODE_BIN", "").strip()
    if explicit:
        return explicit

    # 2. PATH lookup
    found = shutil.which("swytchcode")
    if found:
        return found

    # 3. Common install-path fallbacks
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(
                local_app_data, "Programs", "swytchcode", "bin", "swytchcode.exe"
            ),
        ]
    else:
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".local", "bin", "swytchcode"),
            "/usr/local/bin/swytchcode",
        ]

    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return "swytchcode"  # fall through; subprocess.run reports FileNotFoundError if still missing


def exec_(  # noqa: A001 - shadowing intentional for API consistency with JS/Go
    canonical_id: str,
    input: Any = None,
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    raw: bool = False,
    dry_run: bool = False,
    allow_raw: bool = False,
    timeout: float | None = None,
) -> Any:
    """
    Run swytchcode exec <canonical_id> with optional JSON args on stdin.

    Returns parsed JSON (default) or raw stdout as str when raw=True.
    The swytchcode binary must be on PATH.

    The input argument is the kernel args object sent on stdin. Use this shape so the
    kernel builds the request correctly: body (request body), params (query/path params),
    Authorization (auth header value), headers (map of header name to value); other
    top-level keys are passed as query params.

    Args:
        canonical_id: Swytchcode canonical command ID (e.g. "api.account.create").
        input: Optional args object; serialized as JSON to stdin. Keys: body, params,
            Authorization, headers, and any other as query params. None for no stdin.
        cwd: Working directory for the process. Defaults to current directory.
        env: Extra environment variables merged with os.environ.
        raw: If True, use --raw and return stdout as a string.
        dry_run: If True, pass --dry-run; request details are output instead of calling the server.
        allow_raw: If True, pass --allow-raw; required for executing raw methods (kernel default is disabled).
        timeout: Optional timeout in seconds for the subprocess.

    Returns:
        Parsed result (any) or raw string when raw is True.

    Raises:
        SwytchcodeError: When the process fails, exits non-zero, or stdout is invalid JSON.
    """
    canonical_id = canonical_id.strip()
    if not canonical_id:
        raise SwytchcodeError("canonical_id must be a non-empty string")

    flag = "--raw" if raw else "--json"
    bin_path = _resolve_bin()
    cmd = [bin_path, "exec", canonical_id, flag]
    if dry_run:
        cmd.append("--dry-run")
    if allow_raw:
        cmd.append("--allow-raw")

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    stdin_payload: bytes | None = None
    if input is not None:
        stdin_payload = json.dumps(input).encode("utf-8")

    try:
        result = subprocess.run(
            cmd,
            input=stdin_payload,
            capture_output=True,
            cwd=cwd or os.getcwd(),
            env=run_env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise SwytchcodeError(
            f"swytchcode exec timed out after {timeout} seconds", e
        ) from e
    except FileNotFoundError as e:
        hint = (
            f"using binary at {bin_path!r}"
            if "SWYTCHCODE_BIN" in os.environ
            else "install it with: npm install -g swytchcode (or set SWYTCHCODE_BIN=/path/to/binary)"
        )
        raise SwytchcodeError(f"Failed to spawn swytchcode — {hint}", e) from e
    except OSError as e:
        raise SwytchcodeError("Failed to run swytchcode", e) from e

    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    stdout = result.stdout.decode("utf-8", errors="replace")

    if result.returncode != 0:
        msg = stderr or "swytchcode exec failed"
        raise SwytchcodeError(msg, result.returncode)

    if raw:
        return stdout

    if not stdout.strip():
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise SwytchcodeError("Invalid JSON output from swytchcode", stdout) from e
