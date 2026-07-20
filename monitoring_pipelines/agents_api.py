"""
Tusk Copilot - FastAPI Router
Exposes POST /agents/copilot for the Tusk multi-agent chat system.
The ai/ path is registered in app.py before this module is imported.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from ai.copilot.copilot import TuskCopilot

router = APIRouter(prefix="/agents", tags=["Tusk Copilot"])
tusk = TuskCopilot()


class CopilotChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post(
    "/copilot",
    summary="Chat with Tusk - Multi-Agent ETL Observability Copilot",
    description=(
        "Send a natural language question to Tusk. "
        "Tusk will automatically detect intent, route to the relevant specialized agents "
        "(Observability, Monitoring, Alerts), "
        "and synthesize a structured response. "
        "Pass the same conversation_id across turns to maintain multi-turn memory."
    )
)
def copilot_chat(body: CopilotChatRequest):
    return tusk.chat(body.message, body.conversation_id)
