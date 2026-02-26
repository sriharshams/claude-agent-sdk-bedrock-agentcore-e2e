"""AgentCore Memory integration for Claude Agent SDK.

Unlike Strands Agents which uses HookProvider callbacks, Claude Agent SDK
uses a manual retrieve/save pattern around the query() call.
"""

import logging
import uuid

import boto3
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from boto3.session import Session

from utils.aws_helpers import get_ssm_parameter, put_ssm_parameter

boto_session = Session()
REGION = boto_session.region_name

logger = logging.getLogger(__name__)

ACTOR_ID = "customer_001"
SESSION_ID = str(uuid.uuid4())

memory_client = MemoryClient(region_name=REGION)
memory_name = "CustomerSupportMemory"


def create_or_get_memory_resource():
    """Create or retrieve the AgentCore Memory resource.

    Uses USER_PREFERENCE and SEMANTIC strategies for personalized support.
    """
    try:
        memory_id = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
        memory_client.gmcp_client.get_memory(memoryId=memory_id)
        return memory_id
    except Exception:
        try:
            strategies = [
                {
                    StrategyType.USER_PREFERENCE.value: {
                        "name": "CustomerPreferences",
                        "description": "Captures customer preferences and behavior",
                        "namespaces": ["support/customer/{actorId}/preferences"],
                    }
                },
                {
                    StrategyType.SEMANTIC.value: {
                        "name": "CustomerSupportSemantic",
                        "description": "Stores facts from conversations",
                        "namespaces": ["support/customer/{actorId}/semantic"],
                    }
                },
            ]
            print("Creating AgentCore Memory resources. This can take a couple of minutes...")
            response = memory_client.create_memory_and_wait(
                name=memory_name,
                description="Customer support agent memory",
                strategies=strategies,
                event_expiry_days=90,
            )
            memory_id = response["id"]
            try:
                put_ssm_parameter("/app/customersupport/agentcore/memory_id", memory_id)
            except Exception as e:
                raise e
            return memory_id
        except Exception:
            return None


def delete_memory(memory_id):
    """Delete a memory resource."""
    try:
        ssm_client = boto3.client("ssm", region_name=REGION)
        memory_client.delete_memory(memory_id=memory_id)
        ssm_client.delete_parameter(Name="/app/customersupport/agentcore/memory_id")
    except Exception:
        pass


class CustomerSupportMemoryManager:
    """Memory manager for Claude Agent SDK customer support agent.

    Instead of hook-based callbacks (Strands pattern), this uses explicit
    retrieve_context() and save_interaction() calls around the query() call.

    Usage:
        manager = CustomerSupportMemoryManager(memory_id, memory_client, actor_id, session_id)

        # Before query()
        context = manager.retrieve_context(user_query)
        enhanced_prompt = f"Customer Context:\\n{context}\\n\\n{user_query}" if context else user_query

        # After query()
        manager.save_interaction(user_query, agent_response)
    """

    def __init__(
        self, memory_id: str, client: MemoryClient, actor_id: str, session_id: str
    ):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }

    def retrieve_context(self, query_text: str) -> str:
        """Retrieve customer context from memory before processing a query.

        Args:
            query_text: The customer's query text.

        Returns:
            Formatted context string, or empty string if no context found.
        """
        try:
            all_context = []

            for context_type, namespace in self.namespaces.items():
                memories = self.client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=namespace.format(actorId=self.actor_id),
                    query=query_text,
                    top_k=3,
                )
                for memory in memories:
                    if isinstance(memory, dict):
                        content = memory.get("content", {})
                        if isinstance(content, dict):
                            text = content.get("text", "").strip()
                            if text:
                                all_context.append(f"[{context_type.upper()}] {text}")

            if all_context:
                context_text = "\n".join(all_context)
                logger.info(f"Retrieved {len(all_context)} customer context items")
                return context_text

        except Exception as e:
            logger.error(f"Failed to retrieve customer context: {e}")

        return ""

    def save_interaction(self, user_query: str, agent_response: str):
        """Save a customer support interaction to memory.

        Args:
            user_query: The customer's query.
            agent_response: The agent's response text.
        """
        try:
            if user_query and agent_response:
                self.client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[
                        (user_query, "USER"),
                        (agent_response, "ASSISTANT"),
                    ],
                )
                logger.info("Saved support interaction to memory")
        except Exception as e:
            logger.error(f"Failed to save support interaction: {e}")
