"""AgentCore Gateway MCP client for Claude Agent SDK.

Connects to AgentCore Gateway as an external MCP server, exposing shared tools
(check_warranty_status, web_search) via the MCP protocol with JWT authentication.
"""

import boto3
from boto3.session import Session

from utils.aws_helpers import get_ssm_parameter

boto_session = Session()
REGION = boto_session.region_name


def get_gateway_url(gateway_id: str = None) -> str:
    """Get the AgentCore Gateway URL.

    Args:
        gateway_id: Optional gateway ID. If not provided, reads from SSM.

    Returns:
        The gateway URL string.
    """
    if not gateway_id:
        gateway_id = get_ssm_parameter("/app/customersupport/agentcore/gateway_id")

    gateway_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    gateway_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
    return gateway_response["gatewayUrl"]


def get_gateway_mcp_config(bearer_token: str, gateway_id: str = None) -> dict:
    """Build the MCP server configuration for AgentCore Gateway.

    This returns a config dict that can be used in ClaudeAgentOptions.mcp_servers.

    Args:
        bearer_token: JWT bearer token for authentication.
        gateway_id: Optional gateway ID. If not provided, reads from SSM.

    Returns:
        MCP server configuration dict for use in ClaudeAgentOptions.

    Example:
        gateway_config = get_gateway_mcp_config(bearer_token)
        options = ClaudeAgentOptions(
            mcp_servers={
                "customer-support": sdk_server,          # In-process tools
                "agentcore-gateway": gateway_config,      # External Gateway tools
            }
        )
    """
    gateway_url = get_gateway_url(gateway_id)
    return {
        "type": "http",
        "url": gateway_url,
        "headers": {"Authorization": f"Bearer {bearer_token}"},
    }
