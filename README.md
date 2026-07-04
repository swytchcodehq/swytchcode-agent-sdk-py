# swytchcode-runtime (Python)

Thin runtime wrapper around the Swytchcode CLI. Calls `swytchcode exec` for you so you can stay in Python without shell boilerplate.

**Requires:** The `swytchcode` CLI must be installed. The binary is located automatically — no configuration needed in most environments. Resolution order:

1. `SWYTCHCODE_BIN` env var — explicit override.
2. `$PATH` lookup via `shutil.which` — the standard system resolution.
3. Common install paths — `~/.local/bin`, `/usr/local/bin` (Unix) or `%LOCALAPPDATA%\Programs\swytchcode\bin` (Windows).

## Install

```bash
pip install swytchcode-runtime
```

Or from the repo:

```bash
pip install /path/to/runtime-libraries/python-runtime
```

## Use

### JSON mode (default)

```python
from swytchcode_runtime import exec

result = exec("api.account.create", {"email": "test@example.com"})
# result is parsed JSON (any)
```

Equivalent to: `swytchcode exec api.account.create --json` with args on stdin.

**Request input (args):** The second argument is the kernel **args** object (sent as JSON on stdin). Use this shape so the kernel builds the request correctly:
- **body** — Request body (dict).
- **params** — Query/path params (e.g. `{"id": "cluster-123"}`).
- **Authorization** — Auth header value (e.g. `"Bearer token123"`).
- **headers** — Additional request headers (e.g. `{"X-Request-Id": "abc-123"}`).
- Other top-level keys are passed as query params.

Example with body, params, and headers:

```python
exec("api.cluster.get", {
    "params": {"id": "cluster-123"},
    "Authorization": "Bearer token123",
    "headers": {"X-Request-Id": "abc-123"},
})
```

### Raw mode

Get stdout as a string instead of parsing JSON:

```python
from swytchcode_runtime import exec

output = exec("api.report.export", {"id": "123"}, raw=True)
# output is the raw stdout string
```

### Options

- **cwd** – Working directory for the process (default: current directory).
- **env** – Extra environment variables (merged with `os.environ`).
- **raw** – If `True`, use `--raw` and return stdout as a string.
- **dry_run** – If `True`, pass `--dry-run` to the CLI; request details (method, url, headers, body) are output instead of calling the server.
- **allow_raw** – If `True`, pass `--allow-raw` to the CLI; required for executing raw methods (kernel has this disabled by default).

This runtime invokes `swytchcode exec [canonical_id]` with the flags above. For full exec behavior, see the Swytchcode kernel documentation.

### Environment variables

| Variable | Description |
|----------|-------------|
| `SWYTCHCODE_BIN` | Override the resolved binary path. Set this only when automatic resolution does not find the correct binary (e.g. non-standard install locations or virtualised environments). |
| `SWYTCHCODE_TOKEN` | Auth token passed to the CLI via the process environment. |

### Error handling

Failures raise `SwytchcodeError` (spawn error, non-zero exit, invalid JSON). Use the helper to narrow:

```python
from swytchcode_runtime import exec, SwytchcodeError, is_swytchcode_error

try:
    exec("api.account.create", {"email": "test@example.com"})
except Exception as e:
    if is_swytchcode_error(e):
        print(e.message, e.cause)
    raise
```

## What this library is

- A thin process wrapper over the Swytchcode shell.
- A stable call surface: `exec(canonical_id, input=None, *, cwd=..., env=..., raw=...)`.
- A convenience for developers and IDE agents.

## What this library is not

- An HTTP SDK or API client.
- A replacement for the shell. All authority stays in the Swytchcode CLI.

This library **must not** and **does not**:

- Read `.swytchcode/*` or parse `tooling.json`.
- Validate schemas or add retries/timeouts.
- Call the registry or embed auth logic.

It is a pipe, not a brain.

## For Cursor / IDE agents

Generate code that uses this runtime instead of subprocess boilerplate.

**Preferred:**

```python
from swytchcode_runtime import exec

def create_account(input: dict) -> any:
    return exec("api.account.create", input)
```

**Avoid:** subprocess boilerplate, HTTP calls, or config parsing. Use `exec(...)` and let the CLI handle execution and policy.

## Agentic workflows (framework integrations)

On top of `exec`, the runtime exposes a small agentic surface that turns Swytchcode tools
into the native tool objects each agent framework expects. The Swytchcode part is the same
two lines regardless of framework:

```python
from swytchcode_runtime import Swytchcode
from swytchcode_runtime.providers.anthropic import AnthropicProvider

swx = Swytchcode(provider=AnthropicProvider())
tools = swx.tools.get(toolkits=["stripe"])   # framework-native tools, full param schemas
```

### Selecting tools — `swx.tools.get(...)`

Pass exactly one selector; IDs resolve against your local Swytchcode state and remote search:

- `toolkits=["stripe"]` — every enabled tool whose integration matches a toolkit.
- `tools=["charges.charge.create"]` — explicit canonical IDs.
- `search="refund a charge"` — natural-language discovery (via `swytchcode discover`).

Each returned tool carries a **full input schema** — every field is surfaced to the model, with
only the truly-required ones marked `required` — and an `execute` callback that runs `swytchcode
exec` for you (empty optional values are stripped before the call so APIs like Stripe don't reject them).

### Supported providers

| Framework | Import | Who runs the tool loop |
|-----------|--------|------------------------|
| Anthropic Claude | `providers.anthropic.AnthropicProvider` | you (Messages API + `swx.handle_tool_calls`) |
| OpenAI Agents SDK | `providers.openai_agents.OpenAIAgentsProvider` | the SDK |
| Vercel AI SDK | `providers.vercel.VercelProvider` | the SDK |
| LangGraph | `providers.langgraph.LangGraphProvider` | the prebuilt agent |
| CrewAI | `providers.crewai.CrewAIProvider` | the crew |

### Non-agentic APIs (Anthropic Messages)

When you run the tool loop yourself, `handle_tool_calls` executes each `tool_use` block and
returns the `tool_result` blocks to send back:

```python
import anthropic
client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-sonnet-5", max_tokens=1024, tools=tools,
    messages=[{"role": "user", "content": "Refund charge ch_123 for $20"}],
)
results = swx.handle_tool_calls(msg)   # runs the tool calls, returns tool_result blocks
```

One runnable file per framework lives in `sdk-examples/`. Install the matching framework SDK
(`pip install openai-agents` / `anthropic` / `ai` / `langgraph` / `crewai`) alongside the
`swytchcode` CLI.
