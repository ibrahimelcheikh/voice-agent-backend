from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import BehaviorConfig
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import re

router = APIRouter()


class CreateBehaviorConfig(BaseModel):
    name: str
    system_prompt: str
    hard_rules: List[dict] = []
    soft_rules: List[dict] = []
    blocked_topics: List[str] = []
    escalation_triggers: List[str] = []
    data_extraction_fields: List[str] = []
    max_call_duration: int = 480


def _lockfile(c: BehaviorConfig) -> dict:
    """The canonical behavior-config lock-file JSON."""
    return {
        "name": c.name,
        "version": c.version,
        "system_prompt": c.system_prompt,
        "hard_rules": c.hard_rules or [],
        "soft_rules": c.soft_rules or [],
        "blocked_topics": c.blocked_topics or [],
        "escalation_triggers": c.escalation_triggers or [],
        "data_extraction_fields": c.data_extraction_fields or [],
        "max_call_duration": c.max_call_duration,
    }


@router.get("/")
async def list_configs(db: AsyncSession = Depends(get_db)):
    configs = (await db.execute(select(BehaviorConfig))).scalars().all()
    return {"success": True, "data": [
        {"id": c.id, "name": c.name, "version": c.version,
         "hard_rules_count": len(c.hard_rules or []),
         "soft_rules_count": len(c.soft_rules or []),
         "blocked_topics_count": len(c.blocked_topics or []),
         "created_at": str(c.created_at)}
        for c in configs
    ]}


@router.post("/")
async def create_config(data: CreateBehaviorConfig, db: AsyncSession = Depends(get_db)):
    config = BehaviorConfig(**data.model_dump(), version=1, versions=[])
    db.add(config)
    await db.commit()
    return {"success": True, "message": "Behavior config created", "data": {"id": config.id}}


@router.get("/{config_id}")
async def get_config(config_id: str, db: AsyncSession = Depends(get_db)):
    config = (await db.execute(
        select(BehaviorConfig).where(BehaviorConfig.id == config_id)
    )).scalars().first()
    if not config:
        raise HTTPException(404, "Config not found")
    return {"success": True, "data": {"id": config.id, **_lockfile(config)}}


@router.put("/{config_id}")
async def update_config(config_id: str, data: CreateBehaviorConfig, db: AsyncSession = Depends(get_db)):
    config = (await db.execute(
        select(BehaviorConfig).where(BehaviorConfig.id == config_id)
    )).scalars().first()
    if not config:
        raise HTTPException(404, "Config not found")

    # Snapshot the current version before mutating.
    history = list(config.versions or [])
    history.append({"snapshot_at": datetime.utcnow().isoformat(), **_lockfile(config)})
    config.versions = history

    config.version += 1
    for key, value in data.model_dump().items():
        setattr(config, key, value)
    await db.commit()
    return {"success": True, "message": f"Config updated to version {config.version}",
            "data": {"id": config.id, "version": config.version}}


@router.get("/{config_id}/versions")
async def config_versions(config_id: str, db: AsyncSession = Depends(get_db)):
    config = (await db.execute(
        select(BehaviorConfig).where(BehaviorConfig.id == config_id)
    )).scalars().first()
    if not config:
        raise HTTPException(404, "Config not found")
    history = list(config.versions or [])
    # Include the current/live version as the head of the history.
    current = {"snapshot_at": "current", **_lockfile(config)}
    return {"success": True, "data": {
        "current_version": config.version,
        "versions": [current] + list(reversed(history)),
    }}


@router.post("/{config_id}/export")
async def export_config(config_id: str, db: AsyncSession = Depends(get_db)):
    config = (await db.execute(
        select(BehaviorConfig).where(BehaviorConfig.id == config_id)
    )).scalars().first()
    if not config:
        raise HTTPException(404, "Config not found")
    payload = _lockfile(config)
    # Content-Disposition headers must be latin-1 / ASCII-safe.
    slug = re.sub(r"[^a-z0-9]+", "_", config.name.lower()).strip("_") or "behavior_config"
    filename = f"{slug}_v{config.version}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_config(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    try:
        raw = await file.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(422, f"Invalid JSON file: {e}")

    config = BehaviorConfig(
        name=data.get("name", "Imported Config"),
        version=data.get("version", 1),
        system_prompt=data.get("system_prompt", ""),
        hard_rules=data.get("hard_rules", []),
        soft_rules=data.get("soft_rules", []),
        blocked_topics=data.get("blocked_topics", []),
        escalation_triggers=data.get("escalation_triggers", []),
        data_extraction_fields=data.get("data_extraction_fields", []),
        max_call_duration=data.get("max_call_duration", 480),
        versions=[],
    )
    db.add(config)
    await db.commit()
    return {"success": True, "message": "Behavior config imported",
            "data": {"id": config.id, "name": config.name}}
