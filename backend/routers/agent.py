"""Agent router — POST /agent/chat using Claude Sonnet 4.5 (Emergent Universal Key)."""
from fastapi import APIRouter, Depends

from models.schemas import AgentChatRequest, AgentChatResponse
from services.auth_service import get_current_user
from services import agent_service

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
async def chat(req: AgentChatRequest, user=Depends(get_current_user)):
    out = await agent_service.chat(req.session_id, req.message, req.customer_id)
    return AgentChatResponse(**out)


@router.get("/tools")
async def tools(user=Depends(get_current_user)):
    return {"tools": agent_service.TOOL_DEFS}
