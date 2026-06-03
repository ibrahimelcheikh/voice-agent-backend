from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User
from app.core.config import settings
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    if not user or not pwd.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=24)},
        settings.JWT_SECRET, algorithm="HS256"
    )
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "name": user.name, "email": user.email}}

@router.post("/demo-login")
async def demo_login(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == "admin@primetechai.com"))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Demo user not found — run seed first")
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=24)},
        settings.JWT_SECRET, algorithm="HS256"
    )
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "demo_credentials": {"email": "admin@primetechai.com", "password": "demo1234"}}
