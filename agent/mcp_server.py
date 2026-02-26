"""In-process MCP server wrapping customer support tools for Claude Agent SDK."""

from claude_agent_sdk import create_sdk_mcp_server

from agent.tools import (
    get_return_policy,
    get_product_info,
    web_search,
    get_technical_support,
)

# Create an in-process MCP server that exposes all customer support tools
# This can be used directly in ClaudeAgentOptions.mcp_servers
server = create_sdk_mcp_server(
    name="customer-support",
    version="1.0.0",
    tools=[get_return_policy, get_product_info, web_search, get_technical_support],
)


def get_mcp_server():
    """Return the configured MCP server instance."""
    return server


if __name__ == "__main__":
    # When run as a standalone process, start the MCP server
    server.run()
