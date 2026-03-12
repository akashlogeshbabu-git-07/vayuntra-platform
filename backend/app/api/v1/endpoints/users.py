"""User management endpoints"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant, require_roles
from app.core.security import hash_password
from app.db.models.models import User, UserRole, Tenant

router = APIRouter()


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    tenant_id: UUID
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

    def model_post_init(self, __context):
        if hasattr(self, "role") and hasattr(self.role, "value"):
            object.__setattr__(self, "role", self.role.value)


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.SOC_ANALYST


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_users(
    current_user=Depends(require_roles([UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.tenant_id == tenant.id).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "is_active": u.is_active,
                "tenant_id": str(u.tenant_id),
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "total": len(users),
    }


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "tenant_id": str(current_user.tenant_id),
        "is_active": current_user.is_active,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }


@router.post("/", status_code=201)
async def create_user(
    payload: UserCreate,
    current_user=Depends(require_roles([UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "tenant_id": str(user.tenant_id),
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user=Depends(require_roles([UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    return {"id": str(user.id), "email": user.email, "role": user.role.value, "is_active": user.is_active}
