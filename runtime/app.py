"""Flask server for AgentCore Runtime deployment.

This is the production runtime server that runs inside the AgentCore sandbox.
It exposes /ping (health check) and /invocations (main agent endpoint) on port 8080.

Key pattern: Uses Claude Agent SDK's query() function with CLAUDE_CODE_USE_BEDROCK=1
to invoke Claude models via Amazon Bedrock.
"""

import asyncio
import json
import logging
import os
import sys
import uuid

from flask import Flask, Response, jsonify, request

# Ensure Bedrock backend is used
os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
# Allow SDK to launch (unset nested-session guard if present)
os.environ.pop("CLAUDECODE", None)

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import ClaudeAgentOptions, query

from agent import prompt_stream
from agent.mcp_server import get_mcp_server
from agent.memory_hooks import (
    CustomerSupportMemoryManager,
    memory_client,
)
from agent.gateway_client import get_gateway_mcp_config
from agent.prompts import SYSTEM_PROMPT
from utils.aws_helpers import get_ssm_parameter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the in-process MCP server
sdk_server = get_mcp_server()

# Load memory ID from environment or SSM
MEMORY_ID = os.environ.get("MEMORY_ID")
if not MEMORY_ID:
    try:
        MEMORY_ID = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
    except Exception:
        logger.warning("No memory ID found - running without memory")
        MEMORY_ID = None


@app.route("/ping", methods=["GET"])
def ping():
    """Health check endpoint required by AgentCore Runtime."""
    return jsonify({"status": "healthy"}), 200


@app.route("/invocations", methods=["POST"])
def invocations():
    """Main agent invocation endpoint.

    Accepts JSON payload with:
        - prompt (str): The user's query
        - actor_id (str, optional): Customer identifier for memory
        - session_id (str, optional): Session identifier for continuity
        - stream (bool, optional): Whether to stream the response

    Returns:
        JSON response with the agent's message.
    """
    try:
        body = request.json or {}
        user_input = body.get("prompt", "")
        actor_id = body.get("actor_id", "default_customer")
        session_id = body.get("session_id", str(uuid.uuid4()))
        stream = body.get("stream", False)

        if not user_input:
            return jsonify({"error": "No prompt provided"}), 400

        # Get authorization header for gateway access
        auth_header = request.headers.get("Authorization", "")

        # Build MCP servers config
        mcp_servers = {"customer-support": sdk_server}

        # Add gateway if auth header is available
        if auth_header:
            try:
                gateway_config = get_gateway_mcp_config(
                    bearer_token=auth_header.replace("Bearer ", "")
                )
                mcp_servers["agentcore-gateway"] = gateway_config
            except Exception as e:
                logger.warning(f"Could not configure gateway: {e}")

        # Retrieve memory context if available
        enhanced_prompt = user_input
        memory_manager = None

        if MEMORY_ID:
            try:
                memory_manager = CustomerSupportMemoryManager(
                    memory_id=MEMORY_ID,
                    client=memory_client,
                    actor_id=actor_id,
                    session_id=session_id,
                )
                context = memory_manager.retrieve_context(user_input)
                if context:
                    enhanced_prompt = f"Customer Context:\n{context}\n\n{user_input}"
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {e}")

        # Build Claude Agent SDK options
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers=mcp_servers,
            allowed_tools=["mcp__customer-support__*", "mcp__agentcore-gateway__*"],
            permission_mode="bypassPermissions",
            max_turns=10,
        )

        if stream:
            return _stream_response(enhanced_prompt, options, memory_manager, user_input)
        else:
            return _sync_response(enhanced_prompt, options, memory_manager, user_input)

    except Exception as e:
        logger.error(f"Invocation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def _sync_response(enhanced_prompt, options, memory_manager, original_query):
    """Handle synchronous (non-streaming) response."""
    response_text = ""

    async def run_agent():
        nonlocal response_text
        async for msg in query(prompt=prompt_stream(enhanced_prompt), options=options):
            if hasattr(msg, "result"):
                response_text = msg.result

    asyncio.run(run_agent())

    # Save interaction to memory
    if memory_manager and response_text:
        try:
            memory_manager.save_interaction(original_query, response_text)
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")

    return jsonify({"message": response_text})


def _stream_response(enhanced_prompt, options, memory_manager, original_query):
    """Handle streaming (SSE) response."""

    def generate():
        response_text = ""

        async def run_agent():
            nonlocal response_text
            async for msg in query(prompt=prompt_stream(enhanced_prompt), options=options):
                if hasattr(msg, "content"):
                    chunk = msg.content
                    response_text += chunk
                    yield f"data: {chunk}\n\n"
                elif hasattr(msg, "result"):
                    response_text = msg.result

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            gen = run_agent()
            # Collect and yield from async generator
            while True:
                try:
                    chunk = loop.run_until_complete(gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

        # Save interaction to memory
        if memory_manager and response_text:
            try:
                memory_manager.save_interaction(original_query, response_text)
            except Exception as e:
                logger.warning(f"Failed to save to memory: {e}")

        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Customer Support Agent on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
