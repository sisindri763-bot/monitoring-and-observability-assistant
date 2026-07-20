"""
Tusk Copilot - Main Chat Interface
Handles conversation session management and invokes the LangGraph agent graph.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import cast
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import CopilotState
from ..orchestrator.agent_router import tusk_graph

logger = logging.getLogger(__name__)


class TuskCopilot:
    """
    Main Tusk Copilot class.
    Manages conversation sessions and routes messages through the LangGraph agent graph.
    Each session is identified by a unique conversation_id (thread_id for LangGraph MemorySaver).
    """

    def __init__(self):
        self.graph = tusk_graph

    def chat(self, message: str, conversation_id: str | None = None) -> dict:
        """
        Process a user message through the Tusk agent graph.

        Args:
            message:         The user's natural language query.
            conversation_id: Optional session ID (UUID). A new one is created if not provided.

        Returns:
            A dict containing the assistant response, conversation_id, and agent context.
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        # LangGraph thread config (MemorySaver uses thread_id for session persistence)
        config = {"configurable": {"thread_id": conversation_id}}

        # Retrieve existing conversation history from MemorySaver checkpoint
        chat_history: list = []
        try:
            checkpoint = self.graph.get_state(cast(RunnableConfig, config))
            if checkpoint and checkpoint.values:
                stored_msgs = checkpoint.values.get("messages", [])
                # Keep last 10 messages for context window efficiency
                chat_history = list(stored_msgs)[-10:]
        except Exception:
            pass  # No prior checkpoint — first message in session

        # Build state for this turn — only append the new user message
        # (MemorySaver operator.add will merge with existing messages)
        input_state = {
            "messages": [HumanMessage(content=message)],
            "user_query": message,
            "active_agents": [],
            "agent_context": {},
            "chat_history": chat_history,  # Pass history for LLM context
        }

        try:
            # Run the full agent graph
            result = self.graph.invoke(
                cast(CopilotState, input_state),
                config=cast(RunnableConfig, config)
            )

            # Extract the last AI message from the result
            messages = result.get("messages", [])
            response_text = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
                    response_text = str(msg.content)
                    break

            if not response_text:
                response_text = (
                    "I'm sorry, I wasn't able to generate a response for that. "
                    "Please try asking about your ETL pipelines, execution logs, "
                    "health scores, or alert webhooks."
                )

            return {
                "success": True,
                "conversation_id": conversation_id,
                "message": response_text,
                "agents_used": result.get("active_agents", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.exception(f"[Tusk] Graph execution error: {e}")
            return {
                "success": False,
                "conversation_id": conversation_id,
                "message": (
                    f"Tusk encountered an error processing your request. "
                    f"Please try again. (Details: {str(e)})"
                ),
                "agents_used": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
