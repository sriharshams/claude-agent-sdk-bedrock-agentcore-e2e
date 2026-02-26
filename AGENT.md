# AGENT.md — Engineering Guide for claude-agent-sdk-bedrock-agentcore-e2e

## Project Scope
This repository is an end-to-end customer support system built with Claude Agent SDK on Amazon Bedrock AgentCore.

It includes:
- Local agent development (`agent/`)
- Production runtime (`runtime/`)
- Streamlit frontend (`frontend/`)
- Infrastructure and provisioning (`prerequisite/`, `scripts/`, `utils/`)
- Progressive workshop notebooks (`lab-01` through `lab-07`)

This is a Claude Agent SDK project, not a Strands Agents project.

## Canonical Runtime Path
Primary serving path is `runtime/app.py` through `POST /invocations`.

Flow in `runtime/app.py`:
1. Force Bedrock backend:
   - `os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"`
   - `os.environ.pop("CLAUDECODE", None)`
2. Read request payload:
   - `prompt`
   - optional `actor_id`, `session_id`, `stream`
3. Build MCP server map:
   - Always include in-process SDK server from `agent.mcp_server.get_mcp_server()`
   - Optionally include gateway MCP config from `agent.gateway_client.get_gateway_mcp_config()` when bearer token exists
4. Retrieve memory context (if `MEMORY_ID` configured) via `CustomerSupportMemoryManager.retrieve_context()`
5. Invoke SDK with:
   - `query(prompt=prompt_stream(enhanced_prompt), options=ClaudeAgentOptions(...))`
6. Return:
   - JSON in non-streaming mode (`_sync_response`)
   - SSE in streaming mode (`_stream_response`)
7. Save interaction after response via `CustomerSupportMemoryManager.save_interaction()`

## Non-Negotiable Rules
1. Always use Bedrock backend: set `CLAUDE_CODE_USE_BEDROCK=1`.
2. Always clear nested-session guard for non-interactive contexts: `os.environ.pop("CLAUDECODE", None)`.
3. Always wrap prompt using `prompt_stream()` when using SDK MCP servers. Do not pass raw string prompts.
4. Claude SDK tools must accept one `args` dict and return dict content payloads.
5. AgentCore Gateway MCP config must use `"type": "http"` (not `"url"`).
6. Keep runtime on port `8080` unless deployment contract changes.

## Module Map (What lives where)
- `agent/__init__.py`: `prompt_stream()` AsyncIterable helper.
- `agent/tools.py`: Customer support tools (`@tool`) and `TOOLS` list.
- `agent/mcp_server.py`: In-process MCP server via `create_sdk_mcp_server()`.
- `agent/memory_hooks.py`: Memory resource lifecycle and `CustomerSupportMemoryManager`.
- `agent/gateway_client.py`: Gateway URL lookup and MCP config builder.
- `agent/prompts.py`: `SYSTEM_PROMPT` and `MODEL_ID`.
- `runtime/app.py`: Flask runtime (`/ping`, `/invocations`) for AgentCore Runtime.
- `frontend/main.py`: Streamlit app entry point + Cognito auth + streaming UI.
- `frontend/chat.py`: Runtime invoke helpers and chat state manager.
- `frontend/chat_utils.py`: frontend utility helpers (SSM/config/formatting).
- `utils/aws_helpers.py`: shared AWS helpers (SSM, secrets, Cognito, IAM, cleanup).
- `prerequisite/`: CloudFormation templates and Lambda source for workshop resources.
- `scripts/`: prerequisite deploy, cleanup, and SSM listing scripts.
- `images/`: architecture and UI diagrams.
- `lab-*.ipynb`: workshop progression and operational workflow.

## Invocation/Data Flow
Request lifecycle:
1. User enters prompt in Streamlit (`frontend/main.py`) or calls runtime API directly.
2. Frontend calls AgentCore runtime endpoint with bearer token and session header.
3. Runtime composes MCP server map:
   - local tools MCP
   - optional gateway MCP with JWT auth
4. Runtime retrieves memory context (if available) and prepends to prompt.
5. Runtime invokes Claude Agent SDK query loop with tool allowlist.
6. Tool execution occurs through MCP routing:
   - local tools from `agent/tools.py`
   - gateway tools from AgentCore Gateway
7. Runtime returns response (JSON or SSE stream).
8. Runtime stores interaction to AgentCore Memory.

Modes:
- Non-streaming: `_sync_response()` returns `{"message": ...}` JSON.
- Streaming: `_stream_response()` returns `text/event-stream` with `data:` chunks and `[DONE]`.

## Environment and Dependencies
Runtime expectations:
- Python `3.11+` (local docs and Docker use Python 3.11)
- Virtual environment at `.venv/`
- AWS credentials configured for target account/region

Core dependencies (`requirements.txt`):
- `claude-agent-sdk>=0.1.44`
- `bedrock-agentcore==1.1.1`
- `bedrock-agentcore-starter-toolkit==0.2.3`
- `mcp>=1.0.0`
- `flask>=2.3`
- `boto3`, `botocore`, `ddgs`, `pyyaml`
- `streamlit-cognito-auth`
- `aws-opentelemetry-distro==0.14.0`

Frontend dependencies (`frontend/requirements.txt`):
- `streamlit`
- `requests`
- `boto3`
- `streamlit-cognito-auth`

Runtime defaults:
- `PORT=8080`
- `PYTHONUNBUFFERED=1`

## SSM/Secrets Contract
All operational parameters are under `/app/customersupport/agentcore/*`.

Common keys used by code paths:
- `/app/customersupport/agentcore/memory_id`
  - read/write in `agent/memory_hooks.py`
  - read in `runtime/app.py`
- `/app/customersupport/agentcore/gateway_id`
  - read in `agent/gateway_client.py`
- `/app/customersupport/agentcore/runtime_arn`
  - read in `frontend/chat.py`
- `/app/customersupport/agentcore/client_id`
  - read in `utils/aws_helpers.py`, `frontend/chat_utils.py`
  - provisioned in `prerequisite/cognito.yaml`
- `/app/customersupport/agentcore/pool_id`
  - read in `utils/aws_helpers.py`, `frontend/chat_utils.py`
  - provisioned in `prerequisite/cognito.yaml`
- `/app/customersupport/agentcore/client_secret`
  - written in `utils/aws_helpers.py`
- `/app/customersupport/agentcore/cognito_discovery_url`
  - written in `utils/aws_helpers.py`
  - provisioned in `prerequisite/cognito.yaml`
- `/app/customersupport/agentcore/runtime_execution_role_arn`
  - written/read in `utils/aws_helpers.py`

Additional keys created by templates/notebooks include:
- `/app/customersupport/agentcore/web_client_id`
- `/app/customersupport/agentcore/cognito_auth_scope`
- `/app/customersupport/agentcore/cognito_token_url`
- `/app/customersupport/agentcore/cognito_auth_url`
- `/app/customersupport/agentcore/cognito_domain`
- `/app/customersupport/agentcore/gateway_iam_role`
- `/app/customersupport/agentcore/lambda_arn`
- `/app/customersupport/agentcore/runtime_iam_role`

Secrets:
- Cognito config secret is stored in AWS Secrets Manager via `utils/aws_helpers.py` (`customer_support_agent`).
- Do not hardcode credentials, tokens, or account-specific values in repo files.

## Local Development Commands
Run from the project root directory.

1. Setup venv and dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r frontend/requirements.txt
```

2. Set Bedrock backend:
```bash
export CLAUDE_CODE_USE_BEDROCK=1
```

3. Quick SDK smoke test:
```bash
CLAUDE_CODE_USE_BEDROCK=1 python -c "
import os; os.environ.pop('CLAUDECODE', None)
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
async def run():
    async for msg in query(prompt='Say hello', options=ClaudeAgentOptions(permission_mode='bypassPermissions', max_turns=1)):
        if hasattr(msg, 'result'):
            print(msg.result)
asyncio.run(run())
"
```

4. MCP tools test with `prompt_stream()`:
```bash
CLAUDE_CODE_USE_BEDROCK=1 python -c "
import os; os.environ.pop('CLAUDECODE', None)
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from agent import prompt_stream
from agent.mcp_server import get_mcp_server
from agent.prompts import SYSTEM_PROMPT
options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={'customer-support': get_mcp_server()},
    allowed_tools=['mcp__customer-support__*'],
    permission_mode='bypassPermissions',
    max_turns=10,
)
async def run():
    async for msg in query(prompt=prompt_stream('What is the return policy for laptops?'), options=options):
        if hasattr(msg, 'result'):
            print(msg.result)
asyncio.run(run())
"
```

5. Run runtime locally:
```bash
export CLAUDE_CODE_USE_BEDROCK=1
python runtime/app.py
```

6. Run Streamlit frontend:
```bash
cd frontend
streamlit run main.py
```

## Deployment and Cleanup Commands
1. Deploy prerequisites:
```bash
bash scripts/prereq.sh
```

2. List SSM parameters:
```bash
bash scripts/list_ssm_parameters.sh
```

3. Cleanup resources:
```bash
bash scripts/cleanup.sh
```

Operational cautions:
- Ensure AWS credentials and region are configured before scripts.
- `scripts/cleanup.sh` is interactive and destructive.
- `scripts/prereq.sh` expects zip tooling and may require Linux package install adaptation on non-Linux environments.

## Coding Conventions for This Repo
1. Tool contract:
   - `async def tool_name(args): ...`
   - return Claude SDK content dict (`{"content": [{"type":"text","text":"..."}]}`).
2. Prompt handling:
   - use `prompt_stream()` for SDK query paths that involve MCP servers.
3. Gateway config:
   - build via `get_gateway_mcp_config()`
   - keep `"type": "http"` and JWT auth header.
4. Memory usage:
   - retrieve context before query
   - save interaction after response.
5. Keep runtime endpoints and payload contracts stable:
   - `GET /ping`
   - `POST /invocations`.
6. Prefer centralized AWS helper usage (`utils/aws_helpers.py`) over ad-hoc duplicated calls when editing backend paths.

## Common Pitfalls and Fixes
1. Nested session startup failures:
   - Fix: `os.environ.pop("CLAUDECODE", None)` before SDK usage.
2. MCP server type mismatch for gateway:
   - Fix: use `"type": "http"`.
3. Broken tool invocation signature:
   - Fix: single `args` dict for all `@tool` handlers.
4. MCP communication breaking with raw string prompts:
   - Fix: use `prompt_stream()`.
5. Missing memory context:
   - Fix: verify `/app/customersupport/agentcore/memory_id` exists and memory resource is active.
6. Runtime invoke auth issues:
   - Fix: verify Cognito token and `Authorization` header forwarding.
7. SSM key drift across older notebooks/templates:
   - Fix: check actual key usage in current code before refactors.

## Change Checklist for Agents
If editing `agent/tools.py`:
- verify tool schema, args parsing, and return dict format.

If editing `agent/mcp_server.py`:
- verify server name/version and tool registration list.

If editing `agent/memory_hooks.py`:
- verify retrieve/save flow and SSM key consistency.

If editing `agent/gateway_client.py`:
- verify gateway key lookup and MCP type remains `"http"`.

If editing `runtime/app.py`:
- verify `/invocations` contract, stream and non-stream paths, and memory save behavior.

If editing `frontend/*`:
- verify session state keys, auth token usage, runtime ARN resolution, and streaming UX.

If editing `utils/aws_helpers.py`:
- verify SSM/Secrets/IAM side effects and cleanup compatibility.

If editing infra (`prerequisite/*`, `scripts/*`):
- verify parameter names, role/policy outputs, and notebook compatibility.

If editing notebooks:
- verify commands and parameter names match current code contracts.

## Source-of-Truth and Drift Policy
Precedence for conflicts:
1. Executable code in repository (`agent/`, `runtime/`, `frontend/`, `utils/`)
2. This `AGENT.md`
3. `CLAUDE.md`
4. `README.md` and notebook narrative text

Drift rules:
- When behavior changes in code, update `AGENT.md` in the same change.
- Keep `AGENT.md` and `CLAUDE.md` aligned on non-negotiable SDK/runtime rules.
- Never commit secrets, tokens, or account-specific sensitive values.
