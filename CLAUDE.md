# CLAUDE.md — Project Instructions for Claude Code

## Project Overview

Customer Support Agent built with **Claude Agent SDK** (`claude-agent-sdk`) deployed on **Amazon Bedrock AgentCore**. This is NOT a Strands Agents project — it uses the Claude Agent SDK exclusively.

- **Model**: `global.anthropic.claude-haiku-4-5-20251001-v1:0` via Bedrock
- **Backend env var**: `CLAUDE_CODE_USE_BEDROCK=1` (required, no Anthropic API key)
- **Runtime**: Flask server on port 8080 (not BedrockAgentCoreApp)
- **Python**: 3.11+ with venv at `.venv/`

## Critical SDK Patterns

### 1. Tool handlers accept a single `args` dict, return a dict

```python
@tool(name="my_tool", description="...", input_schema={...})
async def my_tool(args):
    value = args["param_name"]
    return {"content": [{"type": "text", "text": f"Result: {value}"}]}
```

**NEVER** use keyword arguments (`async def my_tool(param: str, **kwargs)`).
**NEVER** return JSON strings (`return json.dumps({...})`).

### 2. Always use `prompt_stream()` with SDK MCP servers

String prompts close stdin immediately, breaking bidirectional MCP communication. Always wrap prompts:

```python
from agent import prompt_stream

async for msg in query(prompt=prompt_stream(user_input), options=options):
    ...
```

The helper is in `agent/__init__.py`. Root cause: `client.py:134` calls `end_input()` for strings; `stream_input()` correctly waits for AsyncIterable prompts.

### 3. Gateway config uses `"type": "http"`, not `"url"`

Valid MCP server types: `sdk`, `stdio`, `sse`, `http`. AgentCore Gateway uses streamable HTTP:

```python
{"type": "http", "url": gateway_url, "headers": {"Authorization": f"Bearer {token}"}}
```

### 4. Environment setup for SDK

These two lines must run before any `claude_agent_sdk` imports:

```python
os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
os.environ.pop("CLAUDECODE", None)  # Prevents nested session error
```

### 5. Permission mode for non-interactive contexts

Notebooks and servers require: `permission_mode="bypassPermissions"` in `ClaudeAgentOptions`.

## File Layout

```
agent/                   # Core agent module
  __init__.py            # prompt_stream() helper + exports
  tools.py               # 4 tools: get_return_policy, get_product_info, web_search, get_technical_support
  mcp_server.py          # create_sdk_mcp_server() wrapping tools
  memory_hooks.py        # CustomerSupportMemoryManager (retrieve/save pattern)
  gateway_client.py      # get_gateway_mcp_config() for external MCP
  prompts.py             # SYSTEM_PROMPT, MODEL_ID

runtime/app.py           # Flask server (/ping, /invocations) on port 8080
frontend/                # Streamlit web app with Cognito auth
utils/aws_helpers.py     # SSM, Cognito, IAM, cleanup utilities
prerequisite/            # CloudFormation templates + Lambda code
scripts/                 # prereq.sh, cleanup.sh
```

## SSM Parameter Names

All config is in SSM Parameter Store under `/app/customersupport/agentcore/`:

| Parameter | Description |
|-----------|-------------|
| `gateway_iam_role` | IAM role ARN for Gateway (NOT `gateway_role_arn`) |
| `gateway_id` | Gateway resource ID |
| `gateway_url` | Gateway MCP endpoint URL |
| `lambda_arn` | Lambda function ARN |
| `memory_id` | AgentCore Memory resource ID |
| `runtime_arn` | AgentCore Runtime ARN |
| `runtime_execution_role_arn` | IAM role for Runtime execution |
| `pool_id` | Cognito User Pool ID |
| `client_id` | Cognito App Client ID |
| `client_secret` | Cognito App Client Secret |
| `cognito_discovery_url` | OIDC discovery URL |

## Key Dependencies

- `claude-agent-sdk>=0.1.44` — Agent framework (wraps Claude Code CLI as subprocess)
- `bedrock-agentcore==1.1.1` — Memory, identity, evaluation
- `bedrock-agentcore-starter-toolkit==0.2.3` — Runtime deployment, evaluation client
- `mcp>=1.0.0` — MCP server library
- `flask>=2.3` — Runtime HTTP server
- `ddgs` — DuckDuckGo search for web_search tool

## Testing Commands

```bash
# Activate venv
source .venv/bin/activate

# Quick test: agent without tools (verify Bedrock connectivity)
CLAUDE_CODE_USE_BEDROCK=1 python -c "
import os; os.environ.pop('CLAUDECODE', None)
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
async def run():
    async for msg in query(prompt='Say hello', options=ClaudeAgentOptions(permission_mode='bypassPermissions', max_turns=1)):
        if hasattr(msg, 'result'): print(msg.result)
asyncio.run(run())
"

# Full test: agent with MCP tools
CLAUDE_CODE_USE_BEDROCK=1 python -c "
import os; os.environ.pop('CLAUDECODE', None)
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from agent import prompt_stream
from agent.mcp_server import get_mcp_server
from agent.prompts import SYSTEM_PROMPT
sdk_server = get_mcp_server()
options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={'customer-support': sdk_server},
    allowed_tools=['mcp__customer-support__*'],
    permission_mode='bypassPermissions', max_turns=10,
)
async def run():
    async for msg in query(prompt=prompt_stream('What is the return policy for laptops?'), options=options):
        if hasattr(msg, 'result'): print(msg.result)
asyncio.run(run())
"
```

## Common Pitfalls

- **`SdkMcpTool` has `.name` not `.__name__`** — Tools created by `@tool` are `SdkMcpTool` objects, not functions
- **`bedrock_agentcore.evaluation` requires `strands_evals`** — Use `bedrock_agentcore_starter_toolkit.Evaluation` instead
- **`Runtime()` needs `.configure()` before `.invoke()`** — Even if `.bedrock_agentcore.yaml` exists
- **`Runtime.launch()` with existing agent** — Pass `auto_update_on_conflict=True`
- **`requestHeaderAllowlist`** — Only `Authorization` and `X-Amzn-Bedrock-AgentCore-Runtime-Custom-*` are valid
- **Jupyter can't run `!cmd &`** — Use `subprocess.Popen()` for background processes

## Git

- Author: `sriharshams-aws <ssrihars@amazon.com>`
- Do NOT include `Co-Authored-By` lines in commit messages
- Do NOT mention Claude, AI, Copilot, Codex, or any AI assistant in commit messages
- Write commit messages as if the developer wrote the code directly
- `.bedrock_agentcore.yaml` is gitignored (contains account-specific config)
- Root `Dockerfile` is gitignored (auto-generated by starter toolkit)
- `runtime/Dockerfile` IS committed (our manual reference)
- No credentials are hardcoded anywhere; all from SSM Parameter Store
