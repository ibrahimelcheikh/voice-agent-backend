from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from app.db.database import get_db
from app.models.models import FAQ
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CreateFAQ(BaseModel):
    question: str
    answer: str
    category: str = "general"
    agent_id: Optional[str] = None


class UpdateFAQ(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None


def _faq_dict(f: FAQ) -> dict:
    return {"id": f.id, "agent_id": f.agent_id, "question": f.question,
            "answer": f.answer, "category": f.category, "times_asked": f.times_asked,
            "created_at": str(f.created_at)}


@router.get("/")
async def list_faqs(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(FAQ)
    if category:
        q = q.where(FAQ.category == category)
    q = q.order_by(desc(FAQ.times_asked))
    rows = (await db.execute(q)).scalars().all()
    return {"success": True, "data": [_faq_dict(f) for f in rows]}


@router.get("/search")
async def search_faqs(q: str, db: AsyncSession = Depends(get_db)):
    like = f"%{q}%"
    rows = (await db.execute(
        select(FAQ).where(or_(FAQ.question.ilike(like), FAQ.answer.ilike(like)))
    )).scalars().all()
    return {"success": True, "data": [_faq_dict(f) for f in rows], "query": q}


@router.post("/")
async def create_faq(data: CreateFAQ, db: AsyncSession = Depends(get_db)):
    faq = FAQ(**data.model_dump())
    db.add(faq)
    await db.commit()
    return {"success": True, "message": "FAQ created", "data": _faq_dict(faq)}


@router.put("/{faq_id}")
async def update_faq(faq_id: str, data: UpdateFAQ, db: AsyncSession = Depends(get_db)):
    f = (await db.execute(select(FAQ).where(FAQ.id == faq_id))).scalars().first()
    if not f:
        return {"success": False, "error": "FAQ not found"}
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(f, key, value)
    await db.commit()
    return {"success": True, "message": "FAQ updated", "data": _faq_dict(f)}


@router.delete("/{faq_id}")
async def delete_faq(faq_id: str, db: AsyncSession = Depends(get_db)):
    f = (await db.execute(select(FAQ).where(FAQ.id == faq_id))).scalars().first()
    if not f:
        return {"success": False, "error": "FAQ not found"}
    await db.delete(f)
    await db.commit()
    return {"success": True, "message": "FAQ deleted"}
