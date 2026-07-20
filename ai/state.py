"""
Tusk Copilot - Shared State Definition
Defines the typed state object that flows through all LangGraph nodes.
"""

from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
import operator


def merge_contexts(left: dict, right: dict) -> dict:
    merged = dict(left) if left else {}
    if right:
        merged.update(right)
    return merged


class CopilotState(TypedDict):
    """
    Shared state that persists across all Tusk agent nodes in the graph.

    Fields:
        messages:       Full conversation history (user + assistant turns).
        user_query:     The current user question being processed.
        active_agents:  List of agent names the router has decided to execute.
        agent_context:  Dict accumulating outputs from each agent node.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_query: str
    active_agents: list[str]
    agent_context: Annotated[dict, merge_contexts]
    chat_history: list
