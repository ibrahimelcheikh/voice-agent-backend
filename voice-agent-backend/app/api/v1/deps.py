"""Auth + tenant-scoping dependencies for /api/v1.

Roles are derived from the existing `User` model, no schema change:
  * OPERATOR  — User.tenant_id IS NULL  → PrimeOps; may act across all tenants.
  * MERCHANT  — User.tenant_id set       → the merchant app; scoped to that tenant.

`Principal` bundles the user with helpers. `scope_tenant()` resolves the effective
tenant_id for a request: an operator may target any tenant via `?tenant_id=`, a
merchant is always forced onto its own tenant.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.models import User


@dataclass
class Principal:
    user: User

    @property
    def is_operator(self) -> bool:
        return self.user.tenant_id is None

    @property
    def tenant_id(self) -> Optional[str]:
        return self.user.tenant_id


def _decode(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject")
    return sub


async def get_principal(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    user_id = _decode(token)
    user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return Principal(user=user)


async def require_operator(principal: Principal = Depends(get_principal)) -> Principal:
    if not principal.is_operator:
        raise HTTPException(status_code=403, detail="Operator access required")
    return principal


def scope_tenant(principal: Principal, requested: Optional[str]) -> Optional[str]:
    """Effective tenant_id for a request. Merchants are locked to their own tenant;
    operators may target any tenant (or None = all, where the endpoint supports it)."""
    if principal.is_operator:
        return requested
    if requested and requested != principal.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot access another tenant")
    return principal.tenant_id


async def require_tenant(
    principal: Principal = Depends(get_principal),
    tenant_id: Optional[str] = Query(None),
) -> str:
    """Resolve a REQUIRED tenant scope. A merchant uses its own tenant; an operator
    must pass ?tenant_id=. Raises 400 if an operator omits it."""
    tid = scope_tenant(principal, tenant_id)
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    return tid
