from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.models.models import Agent, BehaviorConfig, AgentStatus
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CreateAgent(BaseModel):
    name: str
    type: str
    language: str = "en"
    voice_id: str = "alloy"
    behavior_config_id: Optional[str] = None
    phone_number: Optional[str] = None

class UpdateStatus(BaseModel):
    status: str

@router.get("/")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = result.scalars().all()
    return {"success": True, "data": [
        {"id": a.id, "name": a.name, "type": a.type, "language": a.language,
         "voice_id": a.voice_id, "status": a.status, "phone_number": a.phone_number,
         "calls_today": a.calls_today, "total_calls": a.total_calls,
         "avg_score": a.avg_score, "behavior_config_id": a.behavior_config_id}
        for a in agents
    ]}

@router.post("/")
async def create_agent(data: CreateAgent, db: AsyncSession = Depends(get_db)):
    agent = Agent(**data.model_dump())
    db.add(agent)
    await db.commit()
    return {"success": True, "message": "Agent created", "data": {"id": agent.id}}

@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {"success": True, "data": {
        "id": agent.id, "name": agent.name, "type": agent.type,
        "status": agent.status, "calls_today": agent.calls_today,
        "total_calls": agent.total_calls, "avg_score": agent.avg_score,
        "phone_number": agent.phone_number, "voice_id": agent.voice_id,
    }}

@router.put("/{agent_id}/status")
async def update_status(agent_id: str, data: UpdateStatus, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.status = data.status
    await db.commit()
    return {"success": True, "message": f"Status updated to {data.status}"}

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.is_active = False
    await db.commit()
    return {"success": True, "message": "Agent deleted"}
