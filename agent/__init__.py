"""Customer Support Agent module using Claude Agent SDK."""

from agent.prompts import SYSTEM_PROMPT, MODEL_ID
from agent.tools import (
    get_return_policy,
    get_product_info,
    web_search,
    get_technical_support,
    TOOLS,
)


async def prompt_stream(text: str):
    """Wrap a string prompt as an AsyncIterable for the Claude Agent SDK.

    The SDK closes stdin immediately for string prompts, which breaks
    bidirectional communication with SDK MCP servers. Using an AsyncIterable
    prompt triggers the stream_input() path which correctly waits for the
    first result before closing stdin.
    """
    yield {
        "type": "user",
        "session_id": "",
        "message": {"role": "user", "content": text},
        "parent_tool_use_id": None,
    }
