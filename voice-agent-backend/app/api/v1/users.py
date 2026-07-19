"""/api/v1/users — the internal PrimeOps team (operators, i.e. User.tenant_id IS NULL)."""
import secrets
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import User, UserRole
from .deps import Principal, require_operator

router = APIRouter()


def serialize(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email,
            "role": u.title or "Support", "active": u.is_active}


@router.get("")
async def list_users(principal: Principal = Depends(require_operator),
                     db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(User).where(User.tenant_id.is_(None)).order_by(User.created_at)
    )).scalars().all()
    return {"items": [serialize(u) for u in rows]}


class UserIn(BaseModel):
    name: str
    email: str
    role: Optional[str] = "Support"     # display title
    password: Optional[str] = None


@router.post("")
async def create_user(data: UserIn, principal: Principal = Depends(require_operator),
                      db: AsyncSession = Depends(get_db)):
    pwd = data.password or secrets.token_urlsafe(12)
    pw_hash = bcrypt.hashpw(pwd.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
    u = User(tenant_id=None, role=UserRole.owner, name=data.name, email=data.email,
             password_hash=pw_hash, title=data.role, is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return serialize(u)
