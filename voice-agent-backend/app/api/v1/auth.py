"""/api/v1/auth — login (JWT) + current-user for both apps."""
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.models import User, Tenant
from .deps import Principal, get_principal

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


def _verify(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], (hashed or "").encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _issue(user: User) -> str:
    return jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM,
    )


async def _me_payload(user: User, db: AsyncSession) -> dict:
    role = "operator" if user.tenant_id is None else "merchant"
    tenant_name = None
    if user.tenant_id:
        t = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalars().first()
        tenant_name = t.business_name if t else None
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "role": role, "title": user.title,
        "tenant_id": user.tenant_id, "tenant_name": tenant_name,
    }


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == req.email))).scalars().first()
    if not user or not _verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return {"access_token": _issue(user), "token_type": "bearer", "user": await _me_payload(user, db)}


@router.get("/me")
async def me(principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db)):
    return await _me_payload(principal.user, db)
